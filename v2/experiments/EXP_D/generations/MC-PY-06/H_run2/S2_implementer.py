import socket
import json
import time
import ssl
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, urlencode


@dataclass
class Response:
    status_code: int
    headers: dict
    body: str
    elapsed_ms: float


class HTTPClient:

    REDIRECT_LIMIT = 5

    def _url_components(self, url: str) -> tuple:
        u = urlparse(url)
        scheme = u.scheme or 'http'
        host = u.hostname or ''
        port = u.port or (443 if scheme == 'https' else 80)
        resource = u.path or '/'
        if u.query:
            resource = '%s?%s' % (resource, u.query)
        return scheme, host, port, resource

    def _make_raw_request(self, verb: str, host: str, resource: str,
                          custom_headers: Optional[dict],
                          content: Optional[bytes]) -> bytes:
        out = '%s %s HTTP/1.1\r\n' % (verb, resource)
        out += 'Host: %s\r\n' % host
        if custom_headers:
            for hn, hv in custom_headers.items():
                out += '%s: %s\r\n' % (hn, hv)
        if content is not None:
            out += 'Content-Length: %d\r\n' % len(content)
            if not custom_headers or 'Content-Type' not in custom_headers:
                out += 'Content-Type: application/json\r\n'
        out += 'Connection: close\r\n\r\n'
        encoded = out.encode('utf-8')
        if content:
            encoded += content
        return encoded

    def _interpret_response(self, raw_bytes: bytes) -> tuple:
        as_text = raw_bytes.decode('utf-8', errors='replace')
        headers_block, _, body_text = as_text.partition('\r\n\r\n')
        all_lines = headers_block.split('\r\n')
        pieces = all_lines[0].split(' ', 2)
        http_code = int(pieces[1])
        header_dict = {}
        for hl in all_lines[1:]:
            idx = hl.find(':')
            if idx > 0:
                header_dict[hl[:idx].strip()] = hl[idx + 1:].strip()
        return http_code, header_dict, body_text

    def _perform(self, method: str, url: str,
                 headers: Optional[dict] = None,
                 params: Optional[dict] = None,
                 json_body: Optional[dict] = None,
                 timeout: float = 30.0) -> Response:
        dest = url
        if params:
            glue = '&' if '?' in dest else '?'
            dest = '%s%s%s' % (dest, glue, urlencode(params))
        for _ in range(self.REDIRECT_LIMIT + 1):
            clock_start = time.time()
            scheme, host, port, resource = self._url_components(dest)
            body_data = json.dumps(json_body).encode('utf-8') if json_body else None
            wire = self._make_raw_request(method, host, resource, headers, body_data)
            s = socket.create_connection((host, port), timeout=timeout)
            try:
                if scheme == 'https':
                    ssl_context = ssl.create_default_context()
                    s = ssl_context.wrap_socket(s, server_hostname=host)
                s.sendall(wire)
                accumulator = b''
                while True:
                    segment = s.recv(4096)
                    if not segment:
                        break
                    accumulator += segment
            finally:
                s.close()
            ms_elapsed = (time.time() - clock_start) * 1000
            code, rh, rb = self._interpret_response(accumulator)
            if code in (301, 302) and 'Location' in rh:
                dest = rh['Location']
                continue
            return Response(status_code=code, headers=rh, body=rb,
                            elapsed_ms=round(ms_elapsed, 2))
        raise RuntimeError('Redirect limit reached (%d)' % self.REDIRECT_LIMIT)

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._perform('GET', url, headers=headers, params=params, timeout=timeout)

    def post(self, url: str, headers: Optional[dict] = None,
             json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._perform('POST', url, headers=headers, json_body=json_body, timeout=timeout)

    def put(self, url: str, headers: Optional[dict] = None,
            json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._perform('PUT', url, headers=headers, json_body=json_body, timeout=timeout)

    def delete(self, url: str, headers: Optional[dict] = None,
               timeout: float = 30.0) -> Response:
        return self._perform('DELETE', url, headers=headers, timeout=timeout)
