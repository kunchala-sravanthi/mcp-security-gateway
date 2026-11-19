"""Application entry point: Tkinter UI on main thread, MCP proxy in worker."""
from __future__ import annotations

import asyncio
import logging
import threading
import tkinter.messagebox

from app.approval.broker import ApprovalBroker
from app.config.settings import load_settings
from app.proxy.mcp_proxy import run_proxy
from app.ui.popup import ApprovalUI


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger("mcp_gateway")

    try:
        settings = load_settings()
    except Exception as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    broker = ApprovalBroker(settings.approval_timeout_seconds)
    proxy_errors: list[BaseException] = []

    def run_async_proxy() -> None:
        try:
            asyncio.run(run_proxy(settings, broker))
        except BaseException as exc:
            proxy_errors.append(exc)
            logger.exception("MCP proxy stopped unexpectedly")

    worker = threading.Thread(target=run_async_proxy, name="mcp-proxy", daemon=True)
    worker.start()

    ui = ApprovalUI(broker)
    try:
        ui.run()
    finally:
        if worker.is_alive():
            logger.warning("Approval UI closed. Stop the proxy process to finish shutdown.")
        if proxy_errors:
            logger.error("Proxy error: %s", proxy_errors[-1])


if __name__ == "__main__":
    main()
