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
        self._redirect_max = 5

    def _extract_url_parts(self, url: str) -> tuple:
        p = urlparse(url)
        scheme = p.scheme if p.scheme else 'http'
        host = p.hostname or ''
        port = p.port if p.port else (443 if scheme == 'https' else 80)
        path = p.path if p.path else '/'
        if p.query:
            path = '{base}?{qs}'.format(base=path, qs=p.query)
        return scheme, host, port, path

    def _assemble_request(self, method: str, host: str, path: str,
                          user_headers: Optional[dict],
                          body_content: Optional[bytes]) -> bytes:
        text = '{verb} {uri} HTTP/1.1\r\n'.format(verb=method, uri=path)
        text += 'Host: {h}\r\n'.format(h=host)
        if user_headers:
            for k, v in user_headers.items():
                text += '{name}: {val}\r\n'.format(name=k, val=v)
        if body_content is not None:
            text += 'Content-Length: {sz}\r\n'.format(sz=len(body_content))
            if not user_headers or 'Content-Type' not in user_headers:
                text += 'Content-Type: application/json\r\n'
        text += 'Connection: close\r\n\r\n'
        raw = text.encode('utf-8')
        if body_content:
            raw += body_content
        return raw

    def _parse_raw_response(self, data: bytes) -> tuple:
        decoded = data.decode('utf-8', errors='replace')
        hdr_block, _, body_block = decoded.partition('\r\n\r\n')
        hdr_lines = hdr_block.split('\r\n')
        status_tokens = hdr_lines[0].split(' ', 2)
        status_num = int(status_tokens[1])
        headers_map = {}
        for line in hdr_lines[1:]:
            colon = line.find(':')
            if colon > 0:
                headers_map[line[:colon].strip()] = line[colon + 1:].strip()
        return status_num, headers_map, body_block

    def _request(self, method: str, url: str,
                 headers: Optional[dict] = None,
                 params: Optional[dict] = None,
                 json_body: Optional[dict] = None,
                 timeout: float = 30.0) -> Response:
        active_url = url
        if params:
            connector = '&' if '?' in active_url else '?'
            active_url = '{u}{c}{q}'.format(u=active_url, c=connector, q=urlencode(params))
        attempts = 0
        while attempts <= self._redirect_max:
            tick = time.time()
            scheme, host, port, path = self._extract_url_parts(active_url)
            encoded_body = json.dumps(json_body).encode('utf-8') if json_body else None
            packet = self._assemble_request(method, host, path, headers, encoded_body)
            connection = socket.create_connection((host, port), timeout=timeout)
            try:
                if scheme == 'https':
                    wrapper = ssl.create_default_context()
                    connection = wrapper.wrap_socket(connection, server_hostname=host)
                connection.sendall(packet)
                response_buf = b''
                while True:
                    recv_data = connection.recv(4096)
                    if not recv_data:
                        break
                    response_buf += recv_data
            finally:
                connection.close()
            duration_ms = (time.time() - tick) * 1000
            code, r_headers, r_body = self._parse_raw_response(response_buf)
            if code in (301, 302) and 'Location' in r_headers:
                active_url = r_headers['Location']
                attempts += 1
                continue
            return Response(status_code=code, headers=r_headers,
                            body=r_body, elapsed_ms=round(duration_ms, 2))
        raise RuntimeError('Redirect limit of %d exceeded' % self._redirect_max)

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._request('GET', url, headers=headers, params=params, timeout=timeout)

    def post(self, url: str, headers: Optional[dict] = None,
             json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._request('POST', url, headers=headers, json_body=json_body, timeout=timeout)

    def put(self, url: str, headers: Optional[dict] = None,
            json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._request('PUT', url, headers=headers, json_body=json_body, timeout=timeout)

    def delete(self, url: str, headers: Optional[dict] = None,
               timeout: float = 30.0) -> Response:
        return self._request('DELETE', url, headers=headers, timeout=timeout)
