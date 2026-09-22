"""Zero-dependency HTTP server for the Document Evaluation Web UI."""

from __future__ import annotations

import json
import mimetypes
import sys
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv

from doc_eval.dimensions import (
    DEFAULT_DIMENSIONS,
    PRESETS,
    dimensions_by_id,
    get_preset_dimensions,
    with_weights,
)
from doc_eval.documents import Document, _parse_frontmatter_and_headings
from doc_eval.evaluate import evaluate_document, evaluate_documents
from typesafe_sdk import TypeSafeClient

load_dotenv()

WEB_DIR = Path(__file__).parent / "web"
SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"


class DocEvalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep server log output clean
        sys.stderr.write(f"[doc-eval-ui] {args[0]} {args[1]}\n")

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/presets":
            self.handle_get_presets()
        elif path == "/api/samples":
            self.handle_get_samples()
        elif path == "/api/health":
            self._send_json({"status": "healthy", "service": "doc-eval-ui"})
        else:
            # Fall back to serving static frontend files
            if path in ("", "/"):
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 10 * 1024 * 1024:  # 10MB limit
            self._send_json({"error": "Payload too large (limit 10MB)"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return

        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as exc:
            self._send_json({"error": f"Invalid JSON payload: {exc}"}, HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/evaluate":
            self.handle_evaluate(payload)
        elif path == "/api/evaluate-batch":
            self.handle_evaluate_batch(payload)
        else:
            self._send_json({"error": f"Not found: {path}"}, HTTPStatus.NOT_FOUND)

    def handle_get_presets(self) -> None:
        data = {
            "presets": PRESETS,
            "dimensions": [
                {
                    "id": d.id,
                    "label": d.label,
                    "default_weight": d.weight,
                    "instructions": d.instructions,
                    "criteria": list(d.criteria),
                    "max_level": d.max_level,
                }
                for d in DEFAULT_DIMENSIONS
            ],
        }
        self._send_json(data)

    def handle_get_samples(self) -> None:
        samples = []
        if SAMPLES_DIR.exists():
            for p in sorted(SAMPLES_DIR.glob("*")):
                if p.is_file() and p.suffix.lower() in {".md", ".txt"}:
                    text = p.read_text(encoding="utf-8")
                    _, title, headings, meta = _parse_frontmatter_and_headings(text, p.name)
                    samples.append({
                        "name": p.name,
                        "title": title or p.name,
                        "filename": p.name,
                        "path": str(p),
                        "word_count": len(text.split()),
                        "headings": headings,
                        "text": text,
                    })
        self._send_json({"samples": samples})

    def _resolve_dimensions(self, payload: dict[str, Any]):
        preset_name = payload.get("preset", "general")
        dimensions = get_preset_dimensions(preset_name)
        weights_override = payload.get("weights")
        if weights_override and isinstance(weights_override, dict):
            # cast values to float
            cast_weights = {k: float(v) for k, v in weights_override.items()}
            dimensions = with_weights(cast_weights, dimensions)
        return dimensions

    def handle_evaluate(self, payload: dict[str, Any]) -> None:
        text = payload.get("text", "").strip()
        filename = payload.get("filename", "document.md")
        title = payload.get("title", "")

        if not text:
            sample_path = payload.get("path")
            if sample_path:
                p = Path(sample_path)
                if p.exists() and p.is_file():
                    text = p.read_text(encoding="utf-8")
                    filename = p.name

        if not text:
            self._send_json({"error": "No document text or valid file path provided"}, HTTPStatus.BAD_REQUEST)
            return

        try:
            dimensions = self._resolve_dimensions(payload)
            clean_text, parsed_title, headings, meta = _parse_frontmatter_and_headings(text, filename)
            doc = Document(
                path=Path(filename),
                text=clean_text,
                title=title or parsed_title or filename,
                word_count=len(text.split()),
                line_count=len(text.splitlines()),
                headings=headings,
                metadata=meta,
            )

            with TypeSafeClient() as client:
                res = evaluate_document(client, doc, dimensions)

            response_data = {
                "document": {
                    "name": doc.name,
                    "title": doc.title,
                    "word_count": doc.word_count,
                    "line_count": doc.line_count,
                    "headings": doc.headings,
                },
                "result": res.to_dict(),
                "dimensions": [
                    {
                        "id": d.id,
                        "label": d.label,
                        "weight": d.weight,
                        "max_level": d.max_level,
                        "criteria": list(d.criteria),
                    }
                    for d in dimensions
                ],
            }
            self._send_json(response_data)
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_evaluate_batch(self, payload: dict[str, Any]) -> None:
        docs_payload = payload.get("documents", [])
        if not docs_payload or not isinstance(docs_payload, list):
            self._send_json({"error": "Expected non-empty list of 'documents'"}, HTTPStatus.BAD_REQUEST)
            return

        try:
            dimensions = self._resolve_dimensions(payload)
            documents: list[Document] = []
            for item in docs_payload:
                text = item.get("text", "").strip()
                filename = item.get("filename", "untitled.md")
                title = item.get("title", "")
                if not text and item.get("path"):
                    p = Path(item["path"])
                    if p.exists() and p.is_file():
                        text = p.read_text(encoding="utf-8")
                        filename = p.name

                if text:
                    clean_text, parsed_title, headings, meta = _parse_frontmatter_and_headings(text, filename)
                    documents.append(
                        Document(
                            path=Path(filename),
                            text=clean_text,
                            title=title or parsed_title or filename,
                            word_count=len(text.split()),
                            line_count=len(text.splitlines()),
                            headings=headings,
                            metadata=meta,
                        )
                    )

            if not documents:
                self._send_json({"error": "No valid documents found in batch"}, HTTPStatus.BAD_REQUEST)
                return

            results = evaluate_documents(documents, dimensions, concurrency=5)

            response_data = {
                "results": [r.to_dict() for r in results],
                "dimensions": [
                    {
                        "id": d.id,
                        "label": d.label,
                        "weight": d.weight,
                        "max_level": d.max_level,
                        "criteria": list(d.criteria),
                    }
                    for d in dimensions
                ],
            }
            self._send_json(response_data)
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def start_server(port: int = 8000, host: str = "127.0.0.1", open_browser: bool = True) -> ThreadingHTTPServer:
    # Ensure mime types are populated
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("text/html", ".html")

    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, DocEvalHandler)
    url = f"http://{host}:{port}"
    print(f"\n✨ TypeSafe Document Evaluation UI is running at: {url}")
    print(f"   Press Ctrl+C to stop the server.\n")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    return httpd


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Start the Document Evaluation Web UI")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args(argv)

    httpd = start_server(port=args.port, host=args.host, open_browser=not args.no_browser)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
