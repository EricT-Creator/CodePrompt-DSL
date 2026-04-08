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

    MAX_REDIRECTS = 5

    def _decompose_url(self, url: str) -> tuple:
        parsed = urlparse(url)
        scheme = parsed.scheme or 'http'
        host = parsed.hostname or ''
        port = parsed.port or (443 if scheme == 'https' else 80)
        path = parsed.path or '/'
        if parsed.query:
            path = '%s?%s' % (path, parsed.query)
        return scheme, host, port, path

    def _compose_request(self, method: str, host: str, path: str,
                         extra_headers: Optional[dict],
                         payload: Optional[bytes]) -> bytes:
        req = '{method} {path} HTTP/1.1\r\n'.format(method=method, path=path)
        req += 'Host: {host}\r\n'.format(host=host)
        if extra_headers:
            for hk, hv in extra_headers.items():
                req += '{key}: {val}\r\n'.format(key=hk, val=hv)
        if payload is not None:
            req += 'Content-Length: {length}\r\n'.format(length=len(payload))
            if not extra_headers or 'Content-Type' not in extra_headers:
                req += 'Content-Type: application/json\r\n'
        req += 'Connection: close\r\n\r\n'
        data = req.encode('utf-8')
        if payload:
            data += payload
        return data

    def _read_response(self, raw: bytes) -> tuple:
        decoded = raw.decode('utf-8', errors='replace')
        head, _, body = decoded.partition('\r\n\r\n')
        header_lines = head.split('\r\n')
        status_parts = header_lines[0].split(' ', 2)
        status_code = int(status_parts[1])
        hdrs = {}
        for h in header_lines[1:]:
            if ':' in h:
                name, val = h.split(':', 1)
                hdrs[name.strip()] = val.strip()
        return status_code, hdrs, body

    def _execute(self, method: str, url: str,
                 headers: Optional[dict] = None,
                 params: Optional[dict] = None,
                 json_body: Optional[dict] = None,
                 timeout: float = 30.0) -> Response:
        target = url
        if params:
            joiner = '&' if '?' in target else '?'
            target = '{base}{sep}{qs}'.format(base=target, sep=joiner, qs=urlencode(params))
        for attempt in range(self.MAX_REDIRECTS + 1):
            t0 = time.time()
            scheme, host, port, path = self._decompose_url(target)
            body_bytes = json.dumps(json_body).encode('utf-8') if json_body else None
            request_data = self._compose_request(method, host, path, headers, body_bytes)
            conn = socket.create_connection((host, port), timeout=timeout)
            try:
                if scheme == 'https':
                    ctx = ssl.create_default_context()
                    conn = ctx.wrap_socket(conn, server_hostname=host)
                conn.sendall(request_data)
                buf = b''
                while True:
                    part = conn.recv(4096)
                    if not part:
                        break
                    buf += part
            finally:
                conn.close()
            ms = (time.time() - t0) * 1000
            code, resp_hdrs, resp_body = self._read_response(buf)
            if code in (301, 302) and 'Location' in resp_hdrs:
                target = resp_hdrs['Location']
                continue
            return Response(status_code=code, headers=resp_hdrs,
                            body=resp_body, elapsed_ms=round(ms, 2))
        raise RuntimeError('Exceeded max redirects (%d)' % self.MAX_REDIRECTS)

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._execute('GET', url, headers=headers, params=params, timeout=timeout)

    def post(self, url: str, headers: Optional[dict] = None,
             json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._execute('POST', url, headers=headers, json_body=json_body, timeout=timeout)

    def put(self, url: str, headers: Optional[dict] = None,
            json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._execute('PUT', url, headers=headers, json_body=json_body, timeout=timeout)

    def delete(self, url: str, headers: Optional[dict] = None,
               timeout: float = 30.0) -> Response:
        return self._execute('DELETE', url, headers=headers, timeout=timeout)
