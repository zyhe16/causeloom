"""Fixed-destination relay for the loopback-only local OpenCodex endpoint."""

from __future__ import annotations

import asyncio
import os


LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 10101
TARGET_HOST = os.environ.get("TARGET_HOST", "host.docker.internal")
TARGET_PORT = int(os.environ.get("TARGET_PORT", "10101"))
LOCAL_AUTHORITY = os.environ.get("LOCAL_AUTHORITY", f"127.0.0.1:{TARGET_PORT}")
MAX_HEADER_BYTES = 64 * 1024


def normalize_request_headers(header: bytes) -> bytes:
    """Present the fixed relay as a loopback client to OpenCodex.

    OpenCodex deliberately rejects data-plane requests whose HTTP authority is
    not local. Docker service discovery necessarily gives the endpoint a
    non-loopback name, so rewrite only the request authority/origin headers.
    The destination remains fixed and this relay is not a general HTTP proxy.
    """

    lines = header.split(b"\r\n")
    normalized: list[bytes] = []
    for line in lines:
        name, separator, _value = line.partition(b":")
        if not separator:
            normalized.append(line)
            continue
        lowered = name.strip().lower()
        if lowered == b"host":
            normalized.append(name + b": " + LOCAL_AUTHORITY.encode("ascii"))
        elif lowered in {b"origin", b"sec-websocket-origin"}:
            normalized.append(
                name + b": http://" + LOCAL_AUTHORITY.encode("ascii")
            )
        else:
            normalized.append(line)
    return b"\r\n".join(normalized)


async def copy(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def handle(
    client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
) -> None:
    try:
        request_header = await client_reader.readuntil(b"\r\n\r\n")
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        client_writer.close()
        await client_writer.wait_closed()
        return
    if len(request_header) > MAX_HEADER_BYTES:
        client_writer.close()
        await client_writer.wait_closed()
        return
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            TARGET_HOST, TARGET_PORT
        )
    except OSError:
        client_writer.close()
        await client_writer.wait_closed()
        return
    upstream_writer.write(normalize_request_headers(request_header))
    await upstream_writer.drain()
    await asyncio.gather(
        copy(client_reader, upstream_writer),
        copy(upstream_reader, client_writer),
        return_exceptions=True,
    )


async def main() -> None:
    server = await asyncio.start_server(handle, LISTEN_HOST, LISTEN_PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
