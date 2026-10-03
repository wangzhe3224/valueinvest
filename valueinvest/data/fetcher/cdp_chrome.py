"""Generic Chrome DevTools Protocol (CDP) transport over websocket-client.

Drives a local, headed Chrome via its remote-debugging endpoint so that
websites protected by a Cloudflare managed challenge (which blocks every
plain-HTTP client, incl. TLS-impersonating ones) can be loaded and read by a
real browser. This module knows nothing about any particular website: the
caller supplies the "page ready" JS predicate and the expressions to evaluate.

Requirements: a Chrome binary (auto-detected on macOS, or override with the
``VALUEINVEST_CHROME_PATH`` env var) and the optional ``websocket-client``
package (``pip install valueinvest[macrotrends]``).

Threading: a :class:`CDPTab` is NOT thread-safe. Use one tab per thread.

Usage::

    from valueinvest.data.fetcher.cdp_chrome import CDPTab

    with CDPTab() as tab:
        tab.navigate_and_wait("https://example.com", "document.readyState === 'complete'")
        value = tab.evaluate("document.title")
"""
import contextlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, cast

__all__ = [
    "DEFAULT_CDP_PORT",
    "ChromeDebuggerError",
    "CDPTab",
    "ensure_debugger",
    "is_debugger_alive",
    "launch_debugger_chrome",
]

DEFAULT_CDP_PORT = 9222

_LAUNCH_HINT_EN = (
    "/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome "
    "--remote-debugging-port={port} --user-data-dir=/tmp/chrome-debug-profile --no-first-run"
)
_LAUNCH_HINT_ZH = (
    "请先启动带远程调试的 Chrome（详见项目 CLAUDE.md），或在提示后查看 Chrome 窗口完成人机验证"
)


class ChromeDebuggerError(RuntimeError):
    """Transport-level failure (endpoint down, launch failed, challenge not
    solved, CDP timeout). The message always carries an actionable hint."""


def is_debugger_alive(port: int = DEFAULT_CDP_PORT, timeout: float = 2.0) -> bool:
    """True iff ``http://127.0.0.1:{port}/json/version`` answers with JSON."""
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/json/version", timeout=timeout
        ) as resp:
            return resp.status == 200 and b"Browser" in resp.read()
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _chrome_binary() -> str | None:
    override = os.environ.get("VALUEINVEST_CHROME_PATH")
    if override:
        return override
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(mac):
        return mac
    return shutil.which("google-chrome") or shutil.which("chromium")


def launch_debugger_chrome(port: int = DEFAULT_CDP_PORT, timeout: float = 30.0) -> None:
    """Launch a headed Chrome with remote debugging (headless fails Cloudflare).

    Pops a visible Chrome window -- this is deliberate. Uses a dedicated
    profile under /tmp so it never clashes with a manually launched instance.
    """
    binary = _chrome_binary()
    if not binary:
        raise ChromeDebuggerError(
            f"No Chrome binary found. Set VALUEINVEST_CHROME_PATH or launch manually:\n"
            f"  {_LAUNCH_HINT_EN.format(port=port)}\n"
            f"  未找到 Chrome，请设置 VALUEINVEST_CHROME_PATH 或手动启动"
        )
    try:
        subprocess.Popen(  # noqa: S603 -- fixed binary path / args
            [
                binary,
                f"--remote-debugging-port={port}",
            f"--user-data-dir=/tmp/valueinvest-chrome-cdp-{port}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        raise ChromeDebuggerError(
            f"Cannot launch Chrome ({binary!r}): {e}. "
            f"Launch manually:\n  {_LAUNCH_HINT_EN.format(port=port)}\n"
            f"  无法启动 Chrome，请手动启动（{_LAUNCH_HINT_ZH}）"
        ) from e
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_debugger_alive(port):
            return
        time.sleep(0.5)
    raise ChromeDebuggerError(
        f"Chrome launched but debug port {port} did not come up within {timeout}s."
        f" | Chrome 已启动但调试端口 {port} 未在 {timeout} 秒内就绪"
    )


def ensure_debugger(port: int = DEFAULT_CDP_PORT) -> None:
    """Return if the debug endpoint is up; try to launch Chrome otherwise."""
    if is_debugger_alive(port):
        return
    launch_debugger_chrome(port)


def _new_target(port: int) -> dict:
    """Create a blank tab. Chrome 111+ requires PUT for /json/new."""
    url = f"http://127.0.0.1:{port}/json/new?about:blank"
    for method in ("PUT", "GET"):  # GET fallback for old Chrome
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return cast(dict, json.loads(resp.read().decode("utf-8")))
        except urllib.error.HTTPError as e:
            if method == "GET":  # both failed
                raise ChromeDebuggerError(
                    f"Cannot create a CDP tab on port {port}: {e}"
                    f" | 无法在端口 {port} 创建 CDP 标签页"
                ) from e
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise ChromeDebuggerError(
                f"Cannot reach Chrome debug port {port}: {e}. "
                f"Launch Chrome manually:\n  {_LAUNCH_HINT_EN.format(port=port)}\n"
                f"  无法连接 Chrome 调试端口，请手动启动（{_LAUNCH_HINT_ZH}）"
            ) from e
    raise ChromeDebuggerError("unreachable")  # pragma: no cover


class CDPTab:
    """One Chrome tab driven over CDP. Context manager; closes the tab on exit."""

    def __init__(self, port: int | None = None, ensure: bool = True) -> None:
        self.port = port or int(os.environ.get("VALUEINVEST_CDP_PORT", DEFAULT_CDP_PORT))
        self._ensure = ensure
        self._ws = None
        self._target_id: str | None = None
        self._msg_id = 0

    # -- lifecycle --------------------------------------------------------- #
    def __enter__(self) -> "CDPTab":
        if self._ensure:
            ensure_debugger(self.port)
        target = _new_target(self.port)
        self._target_id = target.get("id")
        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            raise ChromeDebuggerError(
                "Tab created but no webSocketDebuggerUrl returned (Chrome too old?)"
                " | 标签页已创建但未返回 webSocketDebuggerUrl"
            )
        try:
            import websocket  # optional dependency
        except ImportError as e:
            raise ChromeDebuggerError(
                "The 'websocket-client' package is required: pip install valueinvest[macrotrends]"
                " | 需要安装可选依赖 websocket-client"
            ) from e
        try:
            # suppress_origin: Chrome 111+ rejects CDP websockets carrying an
            # Origin header unless Chrome was started with --remote-allow-origins.
            self._ws = websocket.create_connection(ws_url, timeout=30, suppress_origin=True)
        except OSError as e:
            raise ChromeDebuggerError(
                f"CDP websocket connect failed: {e} | CDP websocket 连接失败"
            ) from e
        self._cmd("Page.enable")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._ws is not None:
            with contextlib.suppress(OSError):  # best-effort cleanup, never raise
                self._ws.close()
            self._ws = None
        if self._target_id:
            with contextlib.suppress(urllib.error.URLError, OSError):
                urllib.request.urlopen(
                    f"http://127.0.0.1:{self.port}/json/close/{self._target_id}", timeout=5
                ).read()
            self._target_id = None

    # -- protocol ---------------------------------------------------------- #
    def _cmd(self, method: str, params: dict | None = None,
             timeout: float = 60.0) -> dict:
        """Send one CDP command and wait for its matching response.

        Event frames (no ``id``) are skipped. The socket timeout is re-armed
        from the remaining wall-clock budget on every recv.
        """
        if self._ws is None:
            raise ChromeDebuggerError("CDPTab used outside of context manager")
        self._msg_id += 1
        msg_id = self._msg_id
        try:
            self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
            deadline = time.time() + timeout
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise ChromeDebuggerError(
                        f"CDP timeout waiting for {method} ({timeout}s)"
                        f" | CDP 等待 {method} 超时"
                    )
                self._ws.settimeout(remaining)
                raw = self._ws.recv()
                if not raw:  # connection closed
                    raise ChromeDebuggerError(f"CDP connection closed during {method}")
                msg = json.loads(raw)
                if msg.get("id") != msg_id:
                    continue  # event frame
                if "error" in msg:
                    raise ChromeDebuggerError(
                        f"CDP error from {method}: {msg['error']}"
                    )
                return msg.get("result", {})
        except ChromeDebuggerError:
            raise
        except Exception as e:  # WebSocketException, OSError, ValueError
            raise ChromeDebuggerError(f"CDP {method} failed: {e} | CDP 调用失败") from e

    # -- public API -------------------------------------------------------- #
    def navigate_and_wait(self, url: str, ready_js: str,
                          timeout: float = 90.0, poll_interval: float = 1.5) -> None:
        """Navigate to ``url`` and poll ``ready_js`` until it evaluates truthy.

        ``ready_js`` is a JS *expression string* (not a function). A timeout
        usually means a Cloudflare challenge is waiting for a human -- the
        error tells the user to look at the Chrome window.
        """
        self._cmd("Page.navigate", {"url": url}, timeout=30.0)
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self._cmd(
                "Runtime.evaluate",
                {"expression": ready_js, "returnByValue": True},
                timeout=10.0,
            )
            value = (result.get("result") or {}).get("value")
            if value:
                return
            time.sleep(poll_interval)
        raise ChromeDebuggerError(
            f"Page did not become ready within {timeout}s (Cloudflare challenge?). "
            f"Check the Chrome window, complete the check, then retry -- or launch "
            f"Chrome manually:\n  {_LAUNCH_HINT_EN.format(port=self.port)}\n"
            f"页面未在 {timeout} 秒内就绪(可能是 Cloudflare 验证)，"
            f"请查看 Chrome 窗口手动通过验证后重试，或手动启动 Chrome"
        )

    def evaluate(self, expression: str, timeout: float = 60.0) -> Any:
        """Evaluate a JS expression (awaiting promises), returning its value."""
        result = self._cmd(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": True, "returnByValue": True},
            timeout=timeout,
        )
        inner = result.get("result") or {}
        if inner.get("subtype") == "error" or result.get("exceptionDetails"):
            detail = result.get("exceptionDetails", {}).get("exception", {})
            raise ChromeDebuggerError(
                f"JS evaluation failed: {detail.get('description') or inner.get('description')}"
                f" | JS 求值失败"
            )
        return inner.get("value")
