import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SCRIPT = Path(__file__).resolve().parents[1] / "stacks/dgx-spark/api/catalog.py"
spec = importlib.util.spec_from_file_location("api_catalog", SCRIPT)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class BackendHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.server.requests.append((self.path, self.headers.get("Authorization")))
        body = json.dumps(self.server.payload).encode()
        self.send_response(self.server.status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.targets_path = Path(temporary.name) / "model-targets.json"
        self.targets = []
        self.backends = []
        for service, kind, length in (("llm", "chat", 262144), ("embedding", "embedding", 32768),
                                     ("reranker", "reranker", 32768)):
            server = ThreadingHTTPServer(("127.0.0.1", 0), BackendHandler)
            server.payload = {"object": "list", "data": [{
                "id": "example/" + service, "object": "model", "owned_by": "vllm",
                "created": 123, "max_model_len": length,
            }]}
            server.status = 200
            server.requests = []
            self.start_server(server)
            self.backends.append(server)
            self.targets.append({"service": service, "kind": kind,
                                 "url": f"http://127.0.0.1:{server.server_port}/v1/models"})
        self.write_targets(self.targets)
        server = catalog.CatalogServer(("127.0.0.1", 0), self.targets_path)
        self.start_server(server)
        self.base = f"http://127.0.0.1:{server.server_port}"

    def start_server(self, server) -> None:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

    def write_targets(self, targets: list[dict]) -> None:
        temporary = self.targets_path.with_suffix(".next")
        temporary.write_text(json.dumps(targets))
        temporary.replace(self.targets_path)

    def get(self, path: str = "/v1/models") -> tuple[int, dict]:
        request = Request(self.base + path, headers={"Authorization": "Bearer test-only"})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_lists_live_models_with_capabilities_without_forwarding_the_key(self) -> None:
        status, data = self.get()
        self.assertEqual(status, 200)
        self.assertEqual(data["object"], "list")
        self.assertEqual([model["id"] for model in data["data"]],
                         ["example/llm", "example/embedding", "example/reranker"])
        self.assertEqual(data["data"][0]["max_model_len"], 262144)
        self.assertEqual(data["data"][1]["capabilities"], ["embedding"])
        self.assertEqual(data["data"][2]["endpoints"], ["/v1/rerank", "/v1/score"])
        for backend in self.backends:
            self.assertEqual(backend.requests, [("/v1/models", None)])

    def test_mode_updates_are_visible_without_restarting_the_catalog(self) -> None:
        self.assertEqual(len(self.get()[1]["data"]), 3)
        self.backends[0].payload["data"][0]["id"] = "qwen3.8-flash-next"
        self.write_targets([{**self.targets[0], "service": "flash"}])
        status, data = self.get()
        self.assertEqual(status, 200)
        self.assertEqual([model["id"] for model in data["data"]], ["qwen3.8-flash-next"])
        self.assertEqual(data["data"][0]["service"], "flash")
        self.write_targets([])
        self.assertEqual(self.get(), (200, {"object": "list", "data": []}))

    def test_unavailable_backend_returns_503_instead_of_a_partial_success(self) -> None:
        self.backends[1].status = 503
        status, data = self.get()
        self.assertEqual(status, 503)
        self.assertEqual(data["error"]["service"], "embedding")
        self.assertNotIn("data", data)

    def test_invalid_backend_response_returns_502_and_recovers_after_correction(self) -> None:
        self.backends[2].payload = {"object": "list", "data": [{"object": "model", "id": None}]}
        status, data = self.get()
        self.assertEqual(status, 502)
        self.assertEqual(data["error"]["service"], "reranker")
        self.backends[2].payload = {"object": "list", "data": [{"object": "model", "id": "example/fixed"}]}
        self.assertEqual(self.get()[1]["data"][2]["id"], "example/fixed")

    def test_missing_configuration_fails_readiness_and_catalog_requests(self) -> None:
        self.targets_path.rename(self.targets_path.with_suffix(".missing"))
        for path in ("/health", "/v1/models"):
            with self.subTest(path=path):
                status, data = self.get(path)
                self.assertEqual(status, 503)
                self.assertNotIn("data", data)

    def test_malformed_target_fails_readiness_without_contacting_backends(self) -> None:
        self.write_targets([{**self.targets[0], "kind": ["chat"]}])
        self.assertEqual(self.get("/health")[0], 503)
        self.assertEqual(self.get()[0], 503)
        self.assertFalse(any(backend.requests for backend in self.backends))
