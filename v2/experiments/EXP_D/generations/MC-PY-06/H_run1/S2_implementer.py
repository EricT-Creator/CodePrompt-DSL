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

    def __init__(self, max_redirects: int = 5) -> None:
        self._max_redirects = max_redirects

    def _parse_url(self, url: str) -> tuple:
        parsed = urlparse(url)
        scheme = parsed.scheme or 'http'
        host = parsed.hostname or ''
        port = parsed.port
        if port is None:
            port = 443 if scheme == 'https' else 80
        path = parsed.path or '/'
        if parsed.query:
            path = '%s?%s' % (path, parsed.query)
        return scheme, host, port, path

    def _build_request(self, method: str, host: str, path: str,
                       headers: Optional[dict], body_bytes: Optional[bytes]) -> bytes:
        request_line = '%s %s HTTP/1.1\r\n' % (method, path)
        header_lines = 'Host: %s\r\n' % host
        if headers:
            for k, v in headers.items():
                header_lines += '%s: %s\r\n' % (k, v)
        if body_bytes is not None:
            header_lines += 'Content-Length: %d\r\n' % len(body_bytes)
            if 'Content-Type' not in (headers or {}):
                header_lines += 'Content-Type: application/json\r\n'
        header_lines += 'Connection: close\r\n'
        raw = request_line + header_lines + '\r\n'
        result = raw.encode('utf-8')
        if body_bytes:
            result += body_bytes
        return result

    def _parse_response(self, data: bytes) -> tuple:
        text = data.decode('utf-8', errors='replace')
        header_part, _, body = text.partition('\r\n\r\n')
        lines = header_part.split('\r\n')
        status_line = lines[0]
        parts = status_line.split(' ', 2)
        code = int(parts[1])
        resp_headers = {}
        for line in lines[1:]:
            if ':' in line:
                k, v = line.split(':', 1)
                resp_headers[k.strip()] = v.strip()
        return code, resp_headers, body

    def _send_request(self, method: str, url: str,
                      headers: Optional[dict] = None,
                      params: Optional[dict] = None,
                      json_body: Optional[dict] = None,
                      timeout: float = 30.0) -> Response:
        redirects = 0
        current_url = url
        if params:
            sep = '&' if '?' in current_url else '?'
            current_url = '%s%s%s' % (current_url, sep, urlencode(params))
        while redirects <= self._max_redirects:
            start = time.time()
            scheme, host, port, path = self._parse_url(current_url)
            body_bytes = None
            if json_body is not None:
                body_bytes = json.dumps(json_body).encode('utf-8')
            raw_request = self._build_request(method, host, path, headers, body_bytes)
            sock = socket.create_connection((host, port), timeout=timeout)
            try:
                if scheme == 'https':
                    context = ssl.create_default_context()
                    sock = context.wrap_socket(sock, server_hostname=host)
                sock.sendall(raw_request)
                response_data = b''
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
            finally:
                sock.close()
            elapsed = (time.time() - start) * 1000
            code, resp_headers, body = self._parse_response(response_data)
            if code in (301, 302) and 'Location' in resp_headers:
                current_url = resp_headers['Location']
                redirects += 1
                continue
            return Response(
                status_code=code,
                headers=resp_headers,
                body=body,
                elapsed_ms=round(elapsed, 2),
            )
        raise RuntimeError('Too many redirects (max %d)' % self._max_redirects)

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._send_request('GET', url, headers=headers, params=params, timeout=timeout)

    def post(self, url: str, headers: Optional[dict] = None,
             json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._send_request('POST', url, headers=headers, json_body=json_body, timeout=timeout)

    def put(self, url: str, headers: Optional[dict] = None,
            json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._send_request('PUT', url, headers=headers, json_body=json_body, timeout=timeout)

    def delete(self, url: str, headers: Optional[dict] = None,
               timeout: float = 30.0) -> Response:
        return self._send_request('DELETE', url, headers=headers, timeout=timeout)
