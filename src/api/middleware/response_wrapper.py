import json
import logging
from typing import Any

_logger = logging.getLogger(__name__)

# Wrap only successful JSON responses into the unified envelope.
_JSON_PREFIX = "application/json"


def _parse_content_type(headers: list) -> str:
    for name, value in headers:
        if name == b"content-type":
            ct = value.decode("latin-1").split(";", 1)[0].strip().lower()
            return ct
    return ""


def _set_header(headers: list, name: bytes, value: bytes) -> list:
    out = [(n, v) for n, v in headers if n.lower() != name]
    out.append((name, value))
    return out


class ResponseWrapper:
    """Pure ASGI middleware that wraps successful JSON responses.

    Response shape:
        { "code": int, "msg": "ok", "data": <original body> }

    Binary/file downloads, non-JSON payloads and error responses (non-2xx)
    pass through unchanged.
    """

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_message = None
        body_chunks = []
        should_wrap = False

        async def send_wrapper(message: dict) -> None:
            nonlocal start_message, should_wrap
            mtype = message["type"]
            if mtype == "http.response.start":
                start_message = message
                status = message.get("status", 200)
                content_type = _parse_content_type(message.get("headers", []))
                if 200 <= status < 300 and content_type == _JSON_PREFIX:
                    should_wrap = True
                return
            if mtype == "http.response.body":
                body_chunks.append(message.get("body", b""))
                if message.get("more_body"):
                    return
                # Final body chunk received; now emit the (possibly wrapped) response.
                body = b"".join(body_chunks)
                if should_wrap:
                    try:
                        payload = json.loads(body) if body else {}
                        enveloped = json.dumps(
                            {
                                "code": start_message["status"],
                                "msg": "ok",
                                "data": payload,
                            }
                        ).encode("utf-8")
                        headers = _set_header(
                            start_message.get("headers", []),
                            b"content-length",
                            str(len(enveloped)).encode("latin-1"),
                        )
                        await send({**start_message, "headers": headers})
                        await send({"type": "http.response.body", "body": enveloped})
                    except Exception:  # noqa: BLE001 - never break the response chain
                        _logger.exception("Failed to wrap API response body")
                        await send(start_message)
                        await send({"type": "http.response.body", "body": body})
                else:
                    await send(start_message)
                    await send({"type": "http.response.body", "body": body})
                return
            await send(message)

        await self.app(scope, receive, send_wrapper)


def install_response_wrapper(app) -> None:
    """Install the response envelope middleware on the ASGI application."""
    app.add_middleware(ResponseWrapper)  # type: ignore[arg-type]
