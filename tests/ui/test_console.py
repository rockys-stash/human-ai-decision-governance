"""Browser tests for the decision console against the committed results and a seeded queue.

Run with ``uv run pytest -m ui`` after ``npm --prefix web run build``. Set
``GOVERNANCE_SCREENSHOTS=1`` to (re)write the screenshots in ``docs/screenshots``.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "docs" / "screenshots"
TOKEN = "ui-test-reviewer-token-01"
pytestmark = pytest.mark.ui

playwright_api = pytest.importorskip("playwright.sync_api")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _get(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


@pytest.fixture(scope="module")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    if not (ROOT / "web" / "dist" / "index.html").exists():
        pytest.skip("frontend not built (npm --prefix web run build)")
    import uvicorn

    from governance.api.app import create_app

    mp = pytest.MonkeyPatch()
    mp.setenv("GOVERNANCE_REVIEWER_TOKENS", f"ui:{TOKEN}")
    mp.delenv("GOVERNANCE_API_TOKEN", raising=False)
    app = create_app(
        ROOT,
        db_path=tmp_path_factory.mktemp("db") / "governance.db",
        seed_domains=("payments", "credit"),
        seed_cases=80,
    )
    mp.undo()
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{url}/api/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    yield url
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    with playwright_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture(scope="module")
def approval_case(base_url: str) -> str:
    q = _get(f"{base_url}/api/queue?tier=approval&domain=payments&limit=1")
    return str(q[0]["id"])


VIEWPORTS = {"desktop": {"width": 1440, "height": 900}, "mobile": {"width": 390, "height": 844}}

PAGES = [
    ("queue", "/queue", "Review queue"),
    ("audit", "/audit", "Chain integrity"),
    ("policy", "/policy?domain=payments", "Operating point"),
    ("experiments", "/experiments?exp=e2_regimes&domain=payments", "Where the errors come from"),
    ("frontier", "/experiments?exp=e3_frontier&domain=payments", "matched"),
    ("sensitivity", "/experiments?exp=e4_sensitivity&domain=payments", "one reviewer assumption"),
    ("shift", "/experiments?exp=e5_shift", "distribution shift"),
    ("calibration", "/calibration?domain=payments", "Reliability diagram"),
    ("method", "/method", "Limits of the evidence"),
]


def _open(
    browser: Any, base_url: str, viewport: str, path: str, marker: str, scheme: str = "light"
) -> Any:
    ctx = browser.new_context(viewport=VIEWPORTS[viewport], color_scheme=scheme)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base_url + path)
    page.get_by_text(marker, exact=False).first.wait_for(timeout=20000)
    page.wait_for_load_state("networkidle")
    page.errors = errors
    return page


def _assert_clean(page: Any) -> None:
    assert page.locator("h1").count() == 1
    assert not page.locator(".skeleton").count(), "loading skeleton still visible"
    assert not page.locator("[role=alert]").count(), "error state rendered"
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1, f"page scrolls horizontally by {overflow}px"
    assert not page.errors, page.errors


@pytest.mark.parametrize("viewport", list(VIEWPORTS))
@pytest.mark.parametrize(("name", "path", "marker"), PAGES)
def test_page_renders_real_data(
    browser: Any, base_url: str, viewport: str, name: str, path: str, marker: str
) -> None:
    page = _open(browser, base_url, viewport, path, marker)
    _assert_clean(page)
    if os.environ.get("GOVERNANCE_SCREENSHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{name}-{viewport}.png"), full_page=viewport == "mobile")
    page.context.close()


def test_case_inspector_and_read_only_state(
    browser: Any, base_url: str, approval_case: str
) -> None:
    page = _open(
        browser,
        base_url,
        "desktop",
        f"/queue/{approval_case}",
        "Why a person sees this case",
        "dark",
    )
    _assert_clean(page)
    assert page.get_by_role("heading", name="Mandatory approval").count() == 1
    # Not signed in: the decision box asks for a reviewer token instead of offering actions.
    page.get_by_label("Reviewer token").wait_for()
    assert page.get_by_role("button", name="Approve").count() == 0
    if os.environ.get("GOVERNANCE_SCREENSHOTS"):
        page.screenshot(path=str(SHOTS / "case-dark.png"))
    page.context.close()


def test_reviewer_flow_keyboard_and_audit(browser: Any, base_url: str, approval_case: str) -> None:
    page = _open(browser, base_url, "desktop", "/queue?domain=payments&tier=review", "Review queue")
    # j opens the first (highest expected cost) review case.
    page.keyboard.press("j")
    page.get_by_text("Why a person sees this case").wait_for()
    first_id = page.locator("#case-title").inner_text()
    page.get_by_label("Reviewer token").fill("wrong-token-000000")
    page.get_by_role("button", name="Sign in").click()
    page.get_by_text("was not accepted").wait_for()
    page.get_by_label("Reviewer token").fill(TOKEN)
    page.get_by_role("button", name="Sign in").click()
    page.get_by_text("Signed in as ui").wait_for()
    # a accepts the AI decision on a review case; the outcome is revealed only afterwards.
    assert page.get_by_text("Simulated outcome").count() == 0
    page.keyboard.press("a")
    page.get_by_text("Simulated outcome").wait_for()
    page.get_by_text("Decided by ui").wait_for()

    # Mandatory approval: override needs a reason; the submit stays disabled until it has one.
    page.goto(f"{base_url}/queue/{approval_case}")
    page.get_by_role("heading", name="Mandatory approval").wait_for()
    page.keyboard.press("o")
    submit = page.get_by_role("button", name="Override to")
    assert submit.is_disabled()
    # Focus moves to the reason field on the next tick; typing earlier would send shortcuts.
    playwright_api.expect(page.locator("textarea")).to_be_focused()
    page.keyboard.type("Vendor bank details changed the same day")
    assert submit.is_enabled()
    submit.click()
    page.get_by_text("(AI overridden)").wait_for()
    if os.environ.get("GOVERNANCE_SCREENSHOTS"):
        page.screenshot(path=str(SHOTS / "decided-desktop.png"))

    # Both decisions are in the audit log and the hash chain verifies.
    page.goto(f"{base_url}/audit")
    page.get_by_role("button", name="Verify chain").click()
    page.get_by_text("Intact").wait_for()
    assert page.locator("td", has_text="reviewer:ui").count() >= 2
    assert page.get_by_role("link", name=first_id).count() >= 1
    page.context.close()


def test_unknown_route_and_error_states(browser: Any, base_url: str) -> None:
    page = browser.new_page()
    page.goto(f"{base_url}/no/such/page")
    page.get_by_role("heading", name="Page not found").first.wait_for()
    page.goto(f"{base_url}/queue/payments-0-99999")
    page.get_by_text("unknown case").wait_for()
    page.get_by_role("button", name="Retry").wait_for()
    page.close()


AXE = ROOT / "web" / "node_modules" / "axe-core" / "axe.min.js"


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", list(VIEWPORTS))
def test_no_wcag_violations(
    browser: Any, base_url: str, approval_case: str, viewport: str, scheme: str
) -> None:
    """axe-core audit (WCAG 2.1 A/AA + best practices) of every view in both themes."""
    if not AXE.exists():
        pytest.skip("axe-core not installed (npm --prefix web ci)")
    # The app's CSP forbids inline scripts; the audit context bypasses it to inject axe.
    ctx = browser.new_context(viewport=VIEWPORTS[viewport], color_scheme=scheme, bypass_csp=True)
    page = ctx.new_page()
    found: dict[str, list[str]] = {}
    for _, path, marker in [*PAGES, ("case", f"/queue/{approval_case}", "Why a person sees")]:
        page.goto(base_url + path)
        page.get_by_text(marker, exact=False).first.wait_for(timeout=20000)
        page.wait_for_load_state("networkidle")
        page.add_script_tag(path=str(AXE))
        violations = page.evaluate(
            """async () => (await axe.run(document, {runOnly: ['wcag2a', 'wcag2aa', 'wcag21aa',
               'best-practice']})).violations.map(v => v.id + ': ' + v.nodes.map(n => n.target.join(' ')).join(', '))"""
        )
        if violations:
            found[path] = violations
    ctx.close()
    assert not found, found
