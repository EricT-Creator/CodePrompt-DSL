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

    def __init__(self, redirect_limit: int = 5) -> None:
        self._redir_limit = redirect_limit

    def _break_url(self, url: str) -> tuple:
        up = urlparse(url)
        proto = up.scheme or 'http'
        host = up.hostname or ''
        port = up.port or (443 if proto == 'https' else 80)
        resource_path = up.path or '/'
        if up.query:
            resource_path = '%s?%s' % (resource_path, up.query)
        return proto, host, port, resource_path

    def _create_message(self, http_method: str, host: str, path: str,
                        extra_headers: Optional[dict],
                        body_payload: Optional[bytes]) -> bytes:
        msg = '{method} {path} HTTP/1.1\r\n'.format(method=http_method, path=path)
        msg += 'Host: {host}\r\n'.format(host=host)
        if extra_headers:
            for header_name, header_val in extra_headers.items():
                msg += '{n}: {v}\r\n'.format(n=header_name, v=header_val)
        if body_payload is not None:
            msg += 'Content-Length: {length}\r\n'.format(length=len(body_payload))
            if not extra_headers or 'Content-Type' not in extra_headers:
                msg += 'Content-Type: application/json\r\n'
        msg += 'Connection: close\r\n\r\n'
        wire = msg.encode('utf-8')
        if body_payload:
            wire += body_payload
        return wire

    def _extract_response(self, raw: bytes) -> tuple:
        text = raw.decode('utf-8', errors='replace')
        header_text, _, body_text = text.partition('\r\n\r\n')
        lines = header_text.split('\r\n')
        first_line = lines[0].split(' ', 2)
        sc = int(first_line[1])
        hd = {}
        for header_line in lines[1:]:
            sep = header_line.find(':')
            if sep > 0:
                hd[header_line[:sep].strip()] = header_line[sep + 1:].strip()
        return sc, hd, body_text

    def _call(self, method: str, url: str,
              headers: Optional[dict] = None,
              params: Optional[dict] = None,
              json_body: Optional[dict] = None,
              timeout: float = 30.0) -> Response:
        endpoint = url
        if params:
            link = '&' if '?' in endpoint else '?'
            endpoint = '{url}{link}{qs}'.format(url=endpoint, link=link, qs=urlencode(params))
        hops = 0
        while hops <= self._redir_limit:
            begin = time.time()
            proto, host, port, path = self._break_url(endpoint)
            content_bytes = json.dumps(json_body).encode('utf-8') if json_body else None
            message = self._create_message(method, host, path, headers, content_bytes)
            sock = socket.create_connection((host, port), timeout=timeout)
            try:
                if proto == 'https':
                    ctx = ssl.create_default_context()
                    sock = ctx.wrap_socket(sock, server_hostname=host)
                sock.sendall(message)
                buffer = b''
                while True:
                    piece = sock.recv(4096)
                    if not piece:
                        break
                    buffer += piece
            finally:
                sock.close()
            time_ms = (time.time() - begin) * 1000
            status_code, resp_headers, resp_body = self._extract_response(buffer)
            if status_code in (301, 302) and 'Location' in resp_headers:
                endpoint = resp_headers['Location']
                hops += 1
                continue
            return Response(
                status_code=status_code,
                headers=resp_headers,
                body=resp_body,
                elapsed_ms=round(time_ms, 2),
            )
        raise RuntimeError('Exceeded redirect limit of %d' % self._redir_limit)

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._call('GET', url, headers=headers, params=params, timeout=timeout)

    def post(self, url: str, headers: Optional[dict] = None,
             json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._call('POST', url, headers=headers, json_body=json_body, timeout=timeout)

    def put(self, url: str, headers: Optional[dict] = None,
            json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._call('PUT', url, headers=headers, json_body=json_body, timeout=timeout)

    def delete(self, url: str, headers: Optional[dict] = None,
               timeout: float = 30.0) -> Response:
        return self._call('DELETE', url, headers=headers, timeout=timeout)
