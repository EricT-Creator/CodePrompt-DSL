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

    def __init__(self) -> None:
        self.max_redir = 5

    def _dissect_url(self, url: str) -> tuple:
        parsed = urlparse(url)
        sch = parsed.scheme or 'http'
        h = parsed.hostname or ''
        p = parsed.port or (443 if sch == 'https' else 80)
        uri = parsed.path or '/'
        if parsed.query:
            uri = '%s?%s' % (uri, parsed.query)
        return sch, h, p, uri

    def _build_http_message(self, method: str, host: str, uri: str,
                            hdrs: Optional[dict],
                            payload: Optional[bytes]) -> bytes:
        message = '%s %s HTTP/1.1\r\n' % (method, uri)
        message += 'Host: %s\r\n' % host
        if hdrs:
            for key, val in hdrs.items():
                message += '%s: %s\r\n' % (key, val)
        if payload is not None:
            message += 'Content-Length: %d\r\n' % len(payload)
            if not hdrs or 'Content-Type' not in hdrs:
                message += 'Content-Type: application/json\r\n'
        message += 'Connection: close\r\n\r\n'
        raw = message.encode('utf-8')
        if payload:
            raw += payload
        return raw

    def _process_response(self, raw_data: bytes) -> tuple:
        full_text = raw_data.decode('utf-8', errors='replace')
        head, _, body = full_text.partition('\r\n\r\n')
        head_lines = head.split('\r\n')
        status_parts = head_lines[0].split(' ', 2)
        code = int(status_parts[1])
        h_map = {}
        for hl in head_lines[1:]:
            ci = hl.find(':')
            if ci > 0:
                h_map[hl[:ci].strip()] = hl[ci + 1:].strip()
        return code, h_map, body

    def _invoke(self, method: str, url: str,
                headers: Optional[dict] = None,
                params: Optional[dict] = None,
                json_body: Optional[dict] = None,
                timeout: float = 30.0) -> Response:
        target = url
        if params:
            sep = '&' if '?' in target else '?'
            target = '%s%s%s' % (target, sep, urlencode(params))
        redir_n = 0
        while redir_n <= self.max_redir:
            ts = time.time()
            scheme, host, port, uri = self._dissect_url(target)
            body_enc = json.dumps(json_body).encode('utf-8') if json_body else None
            msg = self._build_http_message(method, host, uri, headers, body_enc)
            conn = socket.create_connection((host, port), timeout=timeout)
            try:
                if scheme == 'https':
                    sc = ssl.create_default_context()
                    conn = sc.wrap_socket(conn, server_hostname=host)
                conn.sendall(msg)
                received = b''
                while True:
                    block = conn.recv(4096)
                    if not block:
                        break
                    received += block
            finally:
                conn.close()
            took_ms = (time.time() - ts) * 1000
            status_code, rh, rb = self._process_response(received)
            if status_code in (301, 302) and 'Location' in rh:
                target = rh['Location']
                redir_n += 1
                continue
            return Response(status_code=status_code, headers=rh, body=rb,
                            elapsed_ms=round(took_ms, 2))
        raise RuntimeError('Too many redirects (limit=%d)' % self.max_redir)

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._invoke('GET', url, headers=headers, params=params, timeout=timeout)

    def post(self, url: str, headers: Optional[dict] = None,
             json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._invoke('POST', url, headers=headers, json_body=json_body, timeout=timeout)

    def put(self, url: str, headers: Optional[dict] = None,
            json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._invoke('PUT', url, headers=headers, json_body=json_body, timeout=timeout)

    def delete(self, url: str, headers: Optional[dict] = None,
               timeout: float = 30.0) -> Response:
        return self._invoke('DELETE', url, headers=headers, timeout=timeout)
