"""Unit tests for Web UI server endpoints."""

import json
import threading
import unittest
import urllib.error
import urllib.request
from http import HTTPStatus

from doc_eval.server import DocEvalHandler, ThreadingHTTPServer


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Bind to port 0 for an available ephemeral port
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), DocEvalHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        return urllib.request.urlopen(req)

    def _post_json(self, path: str, payload: dict):
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urllib.request.urlopen(req)

    def test_health_endpoint(self):
        with self._get("/api/health") as res:
            self.assertEqual(res.status, HTTPStatus.OK)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["status"], "healthy")

    def test_presets_endpoint(self):
        with self._get("/api/presets") as res:
            self.assertEqual(res.status, HTTPStatus.OK)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("presets", data)
            self.assertIn("dimensions", data)
            self.assertIn("general", data["presets"])
            self.assertIn("rfc", data["presets"])

    def test_samples_endpoint(self):
        with self._get("/api/samples") as res:
            self.assertEqual(res.status, HTTPStatus.OK)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("samples", data)
            self.assertGreater(len(data["samples"]), 0)

    def test_static_index(self):
        with self._get("/") as res:
            self.assertEqual(res.status, HTTPStatus.OK)
            content = res.read().decode("utf-8")
            self.assertIn("TypeSafe", content)
            self.assertIn("DocEval", content)

    def test_evaluate_empty_payload(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post_json("/api/evaluate", {})
        self.assertEqual(ctx.exception.code, HTTPStatus.BAD_REQUEST)
