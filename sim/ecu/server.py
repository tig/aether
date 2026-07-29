"""TCP line server for the software ECU."""

from __future__ import annotations

import argparse
import socketserver
import threading
from pathlib import Path
from typing import Callable

from .pages import CalibrationStore
from .protocol import handle_line


class _EcuHandler(socketserver.StreamRequestHandler):
    store: CalibrationStore
    on_connect: Callable[[], None] | None = None

    def handle(self) -> None:
        if self.on_connect:
            self.on_connect()
        self.wfile.write(b"AESP 0 READY\n")
        self.wfile.flush()
        while True:
            raw = self.rfile.readline()
            if not raw:
                break
            text = raw.decode("utf-8", errors="replace")
            resp = handle_line(self.store, text)
            self.wfile.write((resp + "\n").encode("utf-8"))
            self.wfile.flush()


class EcuServer:
    """Background TCP server holding one CalibrationStore."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        store: CalibrationStore | None = None,
        flash_path: Path | str | None = None,
    ) -> None:
        self.host = host
        self._requested_port = port
        self.store = store or CalibrationStore()
        self.flash_path = Path(flash_path) if flash_path else None
        if self.flash_path and self.flash_path.is_file():
            self.store.load_flash_file(self.flash_path)

        class _Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        handler = type(
            "BoundEcuHandler",
            (_EcuHandler,),
            {"store": self.store, "on_connect": None},
        )
        self._server = _Server((self.host, self._requested_port), handler)
        self.port: int = int(self._server.server_address[1])
        self._thread: threading.Thread | None = None

    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="ecu-sim",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self.flash_path:
            self.store.save_flash_file(self.flash_path)
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> "EcuServer":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aether software-only ECU sim (AESP)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument(
        "--flash-file",
        default=None,
        help="JSON flash image path (load on start, save on stop)",
    )
    args = p.parse_args(argv)
    store = CalibrationStore()
    flash_path = Path(args.flash_file) if args.flash_file else None
    if flash_path and flash_path.is_file():
        store.load_flash_file(flash_path)

    with EcuServer(
        host=args.host, port=args.port, store=store, flash_path=flash_path
    ) as srv:
        print(
            f"ecu-sim listening on {srv.endpoint} signature={store.signature}",
            flush=True,
        )
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            print("ecu-sim stopping", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
