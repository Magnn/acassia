import sys
from playwright.sync_api import Playwright, TimeoutError as PwTimeoutError, sync_playwright


BASE_URL = "http://localhost:5000/dashboard"


def expect_visible(page, selector: str, timeout: int = 10000):
    page.wait_for_selector(selector, state="visible", timeout=timeout)


def open_builder_if_needed(page):
    # Already in builder?
    try:
        if page.locator("#view-builder:visible").count() > 0:
            return
    except Exception:
        pass

    # Open "Fluxos" view then open first flow card (real user path).
    try:
        flux_nav = page.locator("#n-fluxos")
        if flux_nav.count() > 0:
            flux_nav.first.click()
            page.wait_for_timeout(900)
    except Exception:
        pass

    # Enter main folder first (cards inside folder view).
    try:
        folder = page.get_by_text("Pasta Principal").first
        if folder.count() > 0 and folder.is_visible():
            folder.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass

    card = page.locator("#fluxos-list-grid .fluxo-list-item:visible").first
    card.wait_for(state="visible", timeout=10000)
    card.click()
    page.wait_for_timeout(2400)
    if page.locator("#view-builder:visible").count() > 0:
        return

    # Final assertion.
    expect_visible(page, "#view-builder")


def open_first_editable_node_inspector(page):
    node = page.locator('#nodes-container .flow-node:not([data-node-type="trigger"])').first
    if node.count() == 0:
        node = page.locator('#nodes-container .flow-node').first
    node.wait_for(state="visible", timeout=10000)
    node.click()
    # Ensure inspector is visible.
    expect_visible(page, "#flow-inspector")


def change_any_inspector_field(page):
    # Prefer textareas/inputs, then select fallback.
    editable = page.locator(
        "#flow-inspector-node-mount textarea:visible, "
        "#flow-inspector-node-mount input[type='text']:visible, "
        "#flow-inspector-node-mount input[type='number']:visible"
    ).first
    if editable.count() > 0:
        editable.click()
        editable.type(" teste", delay=25)
        return
    sel = page.locator("#flow-inspector-node-mount select:visible").first
    if sel.count() > 0:
        cur = sel.input_value()
        opts = sel.locator("option")
        for i in range(opts.count()):
            val = opts.nth(i).get_attribute("value") or ""
            if val and val != cur:
                sel.select_option(val)
                return
    raise AssertionError("No editable field found in inspector.")


def verify_unsaved_alert_by_clicking_outside(page):
    # Click canvas outside inspector.
    canvas = page.locator("#flow-canvas-area")
    canvas.wait_for(state="visible", timeout=10000)
    box = canvas.bounding_box()
    if not box:
        raise AssertionError("Canvas bounding box unavailable.")
    page.mouse.click(box["x"] + 60, box["y"] + 60)
    expect_visible(page, "#modal-flow-config-unsaved")


def verify_unsaved_alert_by_keyboard_esc(page):
    # Dismiss modal from keyboard and trigger again with ESC.
    page.keyboard.press("Escape")
    page.wait_for_timeout(220)
    page.keyboard.press("Escape")
    expect_visible(page, "#modal-flow-config-unsaved")


def verify_save_closes_inspector(page):
    # Keep editing via keyboard and then save.
    page.keyboard.press("Escape")
    page.wait_for_timeout(220)
    page.locator("#flow-inspector .flow-inspector-btn-save").first.click()
    # Inspector should close and return to canvas interaction.
    page.wait_for_selector("#flow-inspector", state="hidden", timeout=10000)


def run(playwright: Playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1600, "height": 900})
    page = context.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)

    open_builder_if_needed(page)
    open_first_editable_node_inspector(page)
    change_any_inspector_field(page)
    verify_unsaved_alert_by_clicking_outside(page)
    verify_unsaved_alert_by_keyboard_esc(page)
    verify_save_closes_inspector(page)

    context.close()
    browser.close()


if __name__ == "__main__":
    try:
        with sync_playwright() as p:
            run(p)
        print("E2E keyboard/mouse test passed.")
    except (AssertionError, PwTimeoutError, Exception) as exc:
        print(f"E2E keyboard/mouse test failed: {exc}")
        sys.exit(1)
