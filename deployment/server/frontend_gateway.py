"""Serve the built VisionDrive frontend and proxy its same-origin APIs."""

from __future__ import annotations

import asyncio
import http.client
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode

import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response


FRONTEND_ROOT = Path(
    os.environ.get("FRONTEND_ROOT", Path.home() / "visiondrive/app/frontend")
).resolve()
BACKEND_HOST = os.environ.get("FRONTEND_BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("FRONTEND_BACKEND_PORT", "8080"))
JPEG_GATEWAY_HOST = os.environ.get(
    "FRONTEND_JPEG_GATEWAY_HOST",
    os.environ.get("FRONTEND_WEBRTC_HOST", "127.0.0.1"),
)
JPEG_GATEWAY_PORT = int(os.environ.get(
    "FRONTEND_JPEG_GATEWAY_PORT",
    os.environ.get("FRONTEND_WEBRTC_PORT", "8003"),
))
JPEG_PROXY_WORKERS = max(
    6,
    min(32, int(os.environ.get("FRONTEND_JPEG_PROXY_WORKERS", str(os.cpu_count() or 8)))),
)
JPEG_PROXY_EXECUTOR = ThreadPoolExecutor(
    max_workers=JPEG_PROXY_WORKERS,
    thread_name_prefix="visiondrive-jpeg-proxy",
)

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def _proxy_request(
    method: str,
    host: str,
    port: int,
    path: str,
    headers: dict[str, str],
    body: bytes,
) -> tuple[int, list[tuple[str, str]], bytes]:
    forwarded_headers = {
        name: value
        for name, value in headers.items()
        if name.lower() not in HOP_BY_HOP_HEADERS | {"host", "content-length", "origin"}
    }
    forwarded_headers["Host"] = f"{host}:{port}"
    forwarded_headers["Content-Length"] = str(len(body))

    connection = http.client.HTTPConnection(host, port, timeout=60)
    try:
        connection.request(method, path, body=body, headers=forwarded_headers)
        upstream = connection.getresponse()
        response_body = upstream.read()
        response_headers = [
            (name, value)
            for name, value in upstream.getheaders()
            if name.lower() not in HOP_BY_HOP_HEADERS | {"content-length"}
        ]
        return upstream.status, response_headers, response_body
    finally:
        connection.close()


async def _proxy_http(
    request: Request,
    host: str,
    port: int,
    upstream_path: str,
    executor: ThreadPoolExecutor | None = None,
) -> Response:
    query = urlencode(list(request.query_params.multi_items()))
    path = f"/{upstream_path}"
    if query:
        path = f"{path}?{query}"

    forwarded_headers = dict(request.headers)
    if request.client and request.client.host:
        # Always overwrite client-supplied forwarding headers at this trusted
        # same-host gateway boundary.
        forwarded_headers["x-forwarded-for"] = request.client.host
        forwarded_headers["x-real-ip"] = request.client.host

    status, headers, body = await asyncio.get_running_loop().run_in_executor(
        executor,
        _proxy_request,
        request.method,
        host,
        port,
        path,
        forwarded_headers,
        await request.body(),
    )
    return Response(content=body, status_code=status, headers=dict(headers))


@app.api_route(
    "/api/{upstream_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_backend(request: Request, upstream_path: str) -> Response:
    return await _proxy_http(request, BACKEND_HOST, BACKEND_PORT, f"api/{upstream_path}")


@app.api_route(
    "/jpeg/{upstream_path:path}",
    methods=["GET", "HEAD", "OPTIONS"],
)
async def proxy_jpeg(request: Request, upstream_path: str) -> Response:
    """Proxy stateless JPEG frames without any WebRTC signaling."""
    return await _proxy_http(
        request,
        JPEG_GATEWAY_HOST,
        JPEG_GATEWAY_PORT,
        upstream_path,
        executor=JPEG_PROXY_EXECUTOR,
    )


@app.websocket("/ws/{upstream_path:path}")
async def proxy_websocket(websocket: WebSocket, upstream_path: str) -> None:
    query = urlencode(list(websocket.query_params.multi_items()))
    upstream_url = f"ws://{BACKEND_HOST}:{BACKEND_PORT}/ws/{upstream_path}"
    if query:
        upstream_url = f"{upstream_url}?{query}"

    try:
        async with websockets.connect(upstream_url) as upstream:
            await websocket.accept()

            async def client_to_upstream() -> None:
                while True:
                    message = await websocket.receive()
                    if message["type"] == "websocket.disconnect":
                        return
                    if message.get("text") is not None:
                        await upstream.send(message["text"])
                    elif message.get("bytes") is not None:
                        await upstream.send(message["bytes"])

            async def upstream_to_client() -> None:
                async for message in upstream:
                    if isinstance(message, str):
                        await websocket.send_text(message)
                    else:
                        await websocket.send_bytes(message)

            tasks = {
                asyncio.create_task(client_to_upstream()),
                asyncio.create_task(upstream_to_client()),
            }
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*done, *pending, return_exceptions=True)
    except WebSocketDisconnect:
        pass
    except Exception:
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close(code=1011)


@app.get("/{requested_path:path}", include_in_schema=False)
async def serve_frontend(requested_path: str) -> FileResponse:
    candidate = (FRONTEND_ROOT / requested_path).resolve()
    if candidate.is_relative_to(FRONTEND_ROOT) and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(FRONTEND_ROOT / "index.html")
