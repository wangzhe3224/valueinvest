"""Live-only tests for the generic CDP Chrome transport.

Require a local Chrome debug endpoint (VALUEINVEST_CDP_PORT, default 9222)
and skip silently when it is down -- unlike test_fetcher.py's unguarded live
tests, these cannot run without the browser.
"""
import pytest

from valueinvest.data.fetcher.cdp_chrome import CDPTab, is_debugger_alive

_CDP_UP = is_debugger_alive()


@pytest.mark.skipif(not _CDP_UP, reason="local Chrome debug endpoint not running")
class TestCDPTab:
    def test_evaluate_sync(self):
        with CDPTab() as tab:
            assert tab.evaluate("6*7") == 42

    def test_evaluate_async(self):
        with CDPTab() as tab:
            assert tab.evaluate("Promise.resolve(21).then(x => x*2)") == 42

    def test_navigate_and_wait(self):
        with CDPTab() as tab:
            tab.navigate_and_wait("about:blank", "document.readyState === 'complete'",
                                  timeout=15)
            assert tab.evaluate("1+1") == 2

    def test_tab_closed_after_exit(self):
        tab = CDPTab()
        with tab:
            pass
        assert tab._ws is None
        assert tab._target_id is None
