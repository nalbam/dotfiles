#!/usr/bin/env python3
"""Aggregate the live model lists of the active mode behind the authenticated gateway."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen


ENDPOINTS = {
    "chat": ["/v1/chat/completions", "/v1/completions", "/v1/responses"],
    "embedding": ["/v1/embeddings"],
    "reranker": ["/v1/rerank", "/v1/score"],
}


class CatalogError(Exception):
    def __init__(self, status: int, message: str, service: str | None = None):
        super().__init__(message)
        self.status = status
        self.service = service


def read_targets(path: Path) -> list[dict]:
    targets = json.loads(path.read_text())
    if not isinstance(targets, list):
        raise ValueError("catalog targets must be a list")
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("service"), str) or not target["service"]:
            raise ValueError("invalid catalog service")
        if (not isinstance(target.get("kind"), str) or target["kind"] not in ENDPOINTS
                or not isinstance(target.get("url"), str)):
            raise ValueError("invalid catalog API kind or URL")
        url = urlsplit(target["url"])
        if (url.scheme != "http" or not url.hostname or not url.port
                or url.username or url.password or url.path != "/v1/models" or url.query or url.fragment):
            raise ValueError("invalid catalog backend URL")
    return targets


def fetch_models(target: dict) -> list[dict]:
    service = target["service"]
    try:
        with urlopen(target["url"], timeout=3) as response:
            payload = response.read(1024 * 1024 + 1)
    except HTTPError as error:
        error.close()
        raise CatalogError(503, "Model service is unavailable", service) from error
    except (URLError, OSError) as error:
        raise CatalogError(503, "Model service is unavailable", service) from error
    except HTTPException as error:
        raise CatalogError(502, "Model service returned an invalid HTTP response", service) from error
    try:
        if len(payload) > 1024 * 1024:
            raise ValueError("model list is too large")
        data = json.loads(payload)
        if not isinstance(data, dict) or data.get("object") != "list" or not isinstance(data.get("data"), list):
            raise ValueError("invalid model list")
        models = []
        for model in data["data"]:
            if (not isinstance(model, dict) or not isinstance(model.get("id"), str)
                    or not model["id"] or model.get("object") != "model"):
                raise ValueError("invalid model entry")
            models.append({**model, "service": service, "capabilities": [target["kind"]],
                           "endpoints": ENDPOINTS[target["kind"]]})
        return models
    except (ValueError, UnicodeError) as error:
        raise CatalogError(502, "Model service returned an invalid model list", service) from error


class CatalogHandler(BaseHTTPRequestHandler):
    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path not in ("/health", "/v1/models"):
            self.send_json(404, {"error": {"message": "Not found"}})
            return
        try:
            targets = read_targets(self.server.targets_path)
        except (OSError, ValueError) as error:
            self.log_error("Catalog configuration unavailable: %s", type(error).__name__)
            self.send_json(503, {"error": {"message": "Catalog configuration is unavailable"}})
            return
        if path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                lists = list(executor.map(fetch_models, targets))
        except CatalogError as error:
            self.send_json(error.status, {"error": {"message": str(error), "service": error.service}})
            return
        self.send_json(200, {"object": "list", "data": [model for models in lists for model in models]})


class CatalogServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], targets_path: Path):
        self.targets_path = targets_path
        super().__init__(address, CatalogHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=Path, default=Path(__file__).with_name("model-targets.json"))
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    with CatalogServer(("0.0.0.0", args.port), args.targets) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
