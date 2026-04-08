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

    REDIR_CAP = 5

    def _parse_target(self, url: str) -> tuple:
        u = urlparse(url)
        s = u.scheme or 'http'
        h = u.hostname or ''
        p = u.port or (443 if s == 'https' else 80)
        r = u.path or '/'
        if u.query:
            r = '%s?%s' % (r, u.query)
        return s, h, p, r

    def _serialize_request(self, method: str, host: str, path: str,
                           custom_hdrs: Optional[dict],
                           payload: Optional[bytes]) -> bytes:
        text = '%s %s HTTP/1.1\r\n' % (method, path)
        text += 'Host: %s\r\n' % host
        if custom_hdrs:
            for ck, cv in custom_hdrs.items():
                text += '%s: %s\r\n' % (ck, cv)
        if payload is not None:
            text += 'Content-Length: %d\r\n' % len(payload)
            if not custom_hdrs or 'Content-Type' not in custom_hdrs:
                text += 'Content-Type: application/json\r\n'
        text += 'Connection: close\r\n\r\n'
        encoded = text.encode('utf-8')
        if payload:
            encoded += payload
        return encoded

    def _deserialize_response(self, data: bytes) -> tuple:
        content = data.decode('utf-8', errors='replace')
        header_section, _, body_section = content.partition('\r\n\r\n')
        all_lines = header_section.split('\r\n')
        tokens = all_lines[0].split(' ', 2)
        status = int(tokens[1])
        h_dict = {}
        for hl in all_lines[1:]:
            colon = hl.find(':')
            if colon > 0:
                h_dict[hl[:colon].strip()] = hl[colon + 1:].strip()
        return status, h_dict, body_section

    def _fire(self, method: str, url: str,
              headers: Optional[dict] = None,
              params: Optional[dict] = None,
              json_body: Optional[dict] = None,
              timeout: float = 30.0) -> Response:
        dest = url
        if params:
            joiner = '&' if '?' in dest else '?'
            dest = '%s%s%s' % (dest, joiner, urlencode(params))
        hops = 0
        while hops <= self.REDIR_CAP:
            start = time.time()
            scheme, host, port, path = self._parse_target(dest)
            body_data = json.dumps(json_body).encode('utf-8') if json_body else None
            raw_req = self._serialize_request(method, host, path, headers, body_data)
            sock = socket.create_connection((host, port), timeout=timeout)
            try:
                if scheme == 'https':
                    ctx = ssl.create_default_context()
                    sock = ctx.wrap_socket(sock, server_hostname=host)
                sock.sendall(raw_req)
                buf = b''
                while True:
                    frag = sock.recv(4096)
                    if not frag:
                        break
                    buf += frag
            finally:
                sock.close()
            ms = (time.time() - start) * 1000
            sc, rh, rb = self._deserialize_response(buf)
            if sc in (301, 302) and 'Location' in rh:
                dest = rh['Location']
                hops += 1
                continue
            return Response(status_code=sc, headers=rh, body=rb,
                            elapsed_ms=round(ms, 2))
        raise RuntimeError('Redirect cap of %d exceeded' % self.REDIR_CAP)

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._fire('GET', url, headers=headers, params=params, timeout=timeout)

    def post(self, url: str, headers: Optional[dict] = None,
             json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._fire('POST', url, headers=headers, json_body=json_body, timeout=timeout)

    def put(self, url: str, headers: Optional[dict] = None,
            json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._fire('PUT', url, headers=headers, json_body=json_body, timeout=timeout)

    def delete(self, url: str, headers: Optional[dict] = None,
               timeout: float = 30.0) -> Response:
        return self._fire('DELETE', url, headers=headers, timeout=timeout)
