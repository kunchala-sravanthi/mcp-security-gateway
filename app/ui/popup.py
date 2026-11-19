"""Tkinter approval windows. Tkinter runs on the main thread."""
from __future__ import annotations

import json
import queue
import tkinter as tk
from tkinter import ttk
from typing import Any

from app.approval.broker import ApprovalBroker, ApprovalRequest


class ApprovalUI:
    def __init__(self, broker: ApprovalBroker) -> None:
        self.broker = broker
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("MCP Security Gateway")
        self.root.geometry("360x90")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._windows: dict[str, tk.Toplevel] = {}
        self._closed = False
        self.root.after(100, self._poll_events)

    def run(self) -> None:
        self.root.mainloop()

    def _poll_events(self) -> None:
        if self._closed:
            return
        try:
            while True:
                event, payload = self.broker.ui_events.get_nowait()
                if event == "request":
                    self._show_request(payload)
                elif event == "resolved":
                    self._close_request_window(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _show_request(self, request: ApprovalRequest) -> None:
        window = tk.Toplevel(self.root)
        window.title("MCP request approval")
        window.geometry("560x430")
        window.attributes("-topmost", True)
        window.resizable(True, True)
        window.protocol("WM_DELETE_WINDOW", lambda: self._decide(request, False))
        self._windows[request.request_id] = window

        frame = ttk.Frame(window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="MCP tool request needs your approval", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(frame, text=f"Server: {request.server_name}").pack(anchor="w", pady=(12, 2))
        ttk.Label(frame, text=f"Tool: {request.tool_name}", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Arguments:").pack(anchor="w", pady=(10, 3))

        details = tk.Text(frame, height=12, wrap="word", font=("Consolas", 9))
        details.pack(fill="both", expand=True)
        details.insert("1.0", json.dumps(request.arguments, indent=2, ensure_ascii=False, default=str))
        details.configure(state="disabled")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Block", command=lambda: self._decide(request, False)).pack(side="right")
        ttk.Button(buttons, text="Allow", command=lambda: self._decide(request, True)).pack(side="right", padx=(0, 8))
        window.lift()
        window.focus_force()

    def _decide(self, request: ApprovalRequest, allowed: bool) -> None:
        self.broker.resolve_from_ui(request.request_id, allowed)
        self._close_request_window(request.request_id)

    def _close_request_window(self, request_id: str) -> None:
        window = self._windows.pop(request_id, None)
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass

    def _on_close(self) -> None:
        # Closing the UI denies all visible requests (fail closed).
        self._closed = True
        self.broker.deny_all()
        for request_id in list(self._windows):
            self._close_request_window(request_id)
        self.root.destroy()
