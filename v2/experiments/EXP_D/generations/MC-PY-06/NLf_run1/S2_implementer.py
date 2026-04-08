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
        self._max_redir = max_redirects

    def _split_url(self, url: str) -> tuple:
        parts = urlparse(url)
        scheme = parts.scheme or 'http'
        host = parts.hostname or ''
        port = parts.port
        if port is None:
            port = 443 if scheme == 'https' else 80
        path = parts.path or '/'
        if parts.query:
            path = '%s?%s' % (path, parts.query)
        return scheme, host, port, path

    def _format_request(self, method: str, host: str, path: str,
                        hdrs: Optional[dict], body: Optional[bytes]) -> bytes:
        line = '{m} {p} HTTP/1.1\r\n'.format(m=method, p=path)
        line += 'Host: {h}\r\n'.format(h=host)
        if hdrs:
            for key, value in hdrs.items():
                line += '{k}: {v}\r\n'.format(k=key, v=value)
        if body is not None:
            line += 'Content-Length: {n}\r\n'.format(n=len(body))
            if not hdrs or 'Content-Type' not in hdrs:
                line += 'Content-Type: application/json\r\n'
        line += 'Connection: close\r\n\r\n'
        result = line.encode('utf-8')
        if body:
            result += body
        return result

    def _decode_response(self, data: bytes) -> tuple:
        text = data.decode('utf-8', errors='replace')
        head_section, _, body_section = text.partition('\r\n\r\n')
        lines = head_section.split('\r\n')
        tokens = lines[0].split(' ', 2)
        code = int(tokens[1])
        parsed_headers = {}
        for ln in lines[1:]:
            colon_pos = ln.find(':')
            if colon_pos > 0:
                parsed_headers[ln[:colon_pos].strip()] = ln[colon_pos + 1:].strip()
        return code, parsed_headers, body_section

    def _do_request(self, method: str, url: str,
                    headers: Optional[dict] = None,
                    params: Optional[dict] = None,
                    json_body: Optional[dict] = None,
                    timeout: float = 30.0) -> Response:
        target_url = url
        if params:
            separator = '&' if '?' in target_url else '?'
            target_url = '{base}{sep}{query}'.format(
                base=target_url, sep=separator, query=urlencode(params)
            )
        redir_count = 0
        while redir_count <= self._max_redir:
            t_start = time.time()
            scheme, host, port, path = self._split_url(target_url)
            payload = json.dumps(json_body).encode('utf-8') if json_body else None
            req_bytes = self._format_request(method, host, path, headers, payload)
            sock = socket.create_connection((host, port), timeout=timeout)
            try:
                if scheme == 'https':
                    ssl_ctx = ssl.create_default_context()
                    sock = ssl_ctx.wrap_socket(sock, server_hostname=host)
                sock.sendall(req_bytes)
                received = b''
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    received += chunk
            finally:
                sock.close()
            elapsed = (time.time() - t_start) * 1000
            status, resp_headers, resp_body = self._decode_response(received)
            if status in (301, 302) and 'Location' in resp_headers:
                target_url = resp_headers['Location']
                redir_count += 1
                continue
            return Response(
                status_code=status,
                headers=resp_headers,
                body=resp_body,
                elapsed_ms=round(elapsed, 2),
            )
        raise RuntimeError('Max redirects exceeded (%d)' % self._max_redir)

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._do_request('GET', url, headers=headers, params=params, timeout=timeout)

    def post(self, url: str, headers: Optional[dict] = None,
             json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._do_request('POST', url, headers=headers, json_body=json_body, timeout=timeout)

    def put(self, url: str, headers: Optional[dict] = None,
            json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._do_request('PUT', url, headers=headers, json_body=json_body, timeout=timeout)

    def delete(self, url: str, headers: Optional[dict] = None,
               timeout: float = 30.0) -> Response:
        return self._do_request('DELETE', url, headers=headers, timeout=timeout)
