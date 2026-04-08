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

    def __init__(self, follow_redirects: int = 5) -> None:
        self._follow = follow_redirects

    def _analyze_url(self, raw_url: str) -> tuple:
        result = urlparse(raw_url)
        protocol = result.scheme or 'http'
        hostname = result.hostname or ''
        port_num = result.port or (443 if protocol == 'https' else 80)
        request_uri = result.path or '/'
        if result.query:
            request_uri = '{path}?{query}'.format(path=request_uri, query=result.query)
        return protocol, hostname, port_num, request_uri

    def _construct_http_request(self, verb: str, host: str, uri: str,
                                extra_headers: Optional[dict],
                                body: Optional[bytes]) -> bytes:
        req_str = '{v} {u} HTTP/1.1\r\n'.format(v=verb, u=uri)
        req_str += 'Host: {h}\r\n'.format(h=host)
        if extra_headers:
            for hname, hval in extra_headers.items():
                req_str += '{n}: {v}\r\n'.format(n=hname, v=hval)
        if body is not None:
            req_str += 'Content-Length: {cl}\r\n'.format(cl=len(body))
            if not extra_headers or 'Content-Type' not in extra_headers:
                req_str += 'Content-Type: application/json\r\n'
        req_str += 'Connection: close\r\n\r\n'
        out = req_str.encode('utf-8')
        if body:
            out += body
        return out

    def _handle_response(self, raw: bytes) -> tuple:
        as_str = raw.decode('utf-8', errors='replace')
        hdrs, _, bdy = as_str.partition('\r\n\r\n')
        hdr_lines = hdrs.split('\r\n')
        parts = hdr_lines[0].split(' ', 2)
        code_val = int(parts[1])
        headers_result = {}
        for header_l in hdr_lines[1:]:
            pos = header_l.find(':')
            if pos > 0:
                headers_result[header_l[:pos].strip()] = header_l[pos + 1:].strip()
        return code_val, headers_result, bdy

    def _run(self, method: str, url: str,
             headers: Optional[dict] = None,
             params: Optional[dict] = None,
             json_body: Optional[dict] = None,
             timeout: float = 30.0) -> Response:
        location = url
        if params:
            bridge = '&' if '?' in location else '?'
            location = '{u}{b}{p}'.format(u=location, b=bridge, p=urlencode(params))
        count = 0
        while count <= self._follow:
            t = time.time()
            protocol, hostname, port_num, uri = self._analyze_url(location)
            json_bytes = json.dumps(json_body).encode('utf-8') if json_body else None
            wire_data = self._construct_http_request(method, hostname, uri, headers, json_bytes)
            s = socket.create_connection((hostname, port_num), timeout=timeout)
            try:
                if protocol == 'https':
                    ssl_c = ssl.create_default_context()
                    s = ssl_c.wrap_socket(s, server_hostname=hostname)
                s.sendall(wire_data)
                response_bytes = b''
                while True:
                    incoming = s.recv(4096)
                    if not incoming:
                        break
                    response_bytes += incoming
            finally:
                s.close()
            elapsed = (time.time() - t) * 1000
            sc, rh, rb = self._handle_response(response_bytes)
            if sc in (301, 302) and 'Location' in rh:
                location = rh['Location']
                count += 1
                continue
            return Response(status_code=sc, headers=rh, body=rb,
                            elapsed_ms=round(elapsed, 2))
        raise RuntimeError('Max redirects exceeded (%d)' % self._follow)

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._run('GET', url, headers=headers, params=params, timeout=timeout)

    def post(self, url: str, headers: Optional[dict] = None,
             json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._run('POST', url, headers=headers, json_body=json_body, timeout=timeout)

    def put(self, url: str, headers: Optional[dict] = None,
            json_body: Optional[dict] = None, timeout: float = 30.0) -> Response:
        return self._run('PUT', url, headers=headers, json_body=json_body, timeout=timeout)

    def delete(self, url: str, headers: Optional[dict] = None,
               timeout: float = 30.0) -> Response:
        return self._run('DELETE', url, headers=headers, timeout=timeout)
