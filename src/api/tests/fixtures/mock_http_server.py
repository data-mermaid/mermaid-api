import json
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest



class MockServerRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.response_data = kwargs.pop("response_data")
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

        response_content = json.dumps(self.response_data)
        self.wfile.write(response_content.encode("utf-8"))

        return


class MockHTTPServer(HTTPServer):
    data = {}

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, response_data=self.data)


def get_free_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(("localhost", 0))
    _, port = s.getsockname()
    s.close()
    return port


@pytest.fixture
def mock_covariate_server():
    def _wraps(data):
        port = get_free_port()
        mock_server = MockHTTPServer(("localhost", port), MockServerRequestHandler)
        mock_server.data = data
        mock_server_thread = Thread(target=mock_server.serve_forever)
        mock_server_thread.setDaemon(True)
        mock_server_thread.start()

        return f"http://localhost:{port}"

    return _wraps
