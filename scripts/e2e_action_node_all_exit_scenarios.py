import sys
from playwright.sync_api import TimeoutError as PwTimeoutError, sync_playwright


BASE_URL = "http://localhost:5000/dashboard"
UNSAVED_MODAL = "#modal-flow-config-unsaved"


def expect_visible(page, selector: str, timeout: int = 10000):
    page.wait_for_selector(selector, state="visible", timeout=timeout)


def open_builder(page):
    if page.locator("#view-builder:visible").count() > 0:
        return
    page.locator("#n-fluxos").first.click()
    page.wait_for_timeout(900)
    folder = page.get_by_text("Pasta Principal").first
    if folder.count() > 0 and folder.is_visible():
        folder.click()
        page.wait_for_timeout(900)
    cards = page.locator("#fluxos-list-grid .fluxo-list-item:visible")
    total = cards.count()
    if total == 0:
        raise AssertionError("No visible flow cards found.")
    for i in range(total):
        cards.nth(i).click()
        expect_visible(page, "#view-builder")
        expect_visible(page, "#btn-flow-tab-automacao")
        page.wait_for_timeout(1200)
        return
    raise AssertionError("Could not open builder from flow cards.")


def open_action_inspector(page):
    if page.locator('#nodes-container .flow-node[data-node-type="acao"]').count() == 0:
        palette = page.locator('[data-flow-palette-type="acao"]').first
        palette.wait_for(state="visible", timeout=10000)
        palette.dispatch_event("click")
        page.wait_for_timeout(700)
    node = page.locator('#nodes-container .flow-node[data-node-type="acao"]:visible').first
    node.wait_for(state="visible", timeout=10000)
    node.click()
    expect_visible(page, "#flow-inspector")
    # Ensure this is node mode with footer save button.
    expect_visible(page, "#flow-inspector .flow-inspector-btn-save")


def make_action_dirty(page):
    add_btn = page.locator('[data-flow-acao-add="1"]:visible').first
    add_btn.wait_for(state="visible", timeout=10000)
    add_btn.click()
    page.wait_for_timeout(250)
    pick = page.locator('[data-flow-acao-pick*="etiqueta"]:visible, [data-flow-acao-pick*="adicionar_etiqueta"]:visible').first
    if pick.count() == 0:
        menu = page.locator('[data-flow-acao-menu]:visible').first
        menu.locator("text=/etiqueta/i").first.click()
    else:
        pick.click()
    page.wait_for_timeout(300)


def expect_unsaved_modal(page):
    expect_visible(page, UNSAVED_MODAL)


def discard_unsaved_and_close(page):
    page.evaluate("() => { if (typeof flowUnsavedConfigDiscard === 'function') flowUnsavedConfigDiscard(); }")
    page.wait_for_timeout(250)


def scenario_click_canvas_outside(page):
    canvas = page.locator("#flow-canvas-area")
    box = canvas.bounding_box()
    if not box:
        raise AssertionError("Canvas box not found.")
    page.mouse.click(box["x"] + 70, box["y"] + 70)
    expect_unsaved_modal(page)
    discard_unsaved_and_close(page)


def scenario_click_builder_header_outside(page):
    hdr = page.locator("#flow-builder-header")
    box = hdr.bounding_box()
    if not box:
        raise AssertionError("Builder header box not found.")
    page.mouse.click(box["x"] + 120, box["y"] + 25)
    expect_unsaved_modal(page)
    discard_unsaved_and_close(page)


def scenario_click_sidebar_outside(page):
    """Menu lateral fica fora de #view-builder — deve abrir o alerta como na marcação amarela."""
    sb = page.locator("#sidebar")
    box = sb.bounding_box()
    if not box:
        raise AssertionError("Sidebar box not found.")
    page.mouse.click(box["x"] + 40, box["y"] + 220)
    expect_unsaved_modal(page)
    discard_unsaved_and_close(page)


def scenario_press_escape(page):
    page.keyboard.press("Escape")
    expect_unsaved_modal(page)
    discard_unsaved_and_close(page)


def scenario_click_inspector_close_button(page):
    close_btn = page.locator("#flow-inspector .flow-node-inspector-close:visible").first
    if close_btn.count() == 0:
        return
    close_btn.click()
    expect_unsaved_modal(page)
    discard_unsaved_and_close(page)


def scenario_save_closes_inspector(page):
    save_btn = page.locator("#flow-inspector .flow-inspector-btn-save:visible").first
    save_btn.click()
    page.wait_for_selector("#flow-inspector", state="hidden", timeout=10000)
    # No unsaved modal should remain open.
    page.wait_for_selector(UNSAVED_MODAL, state="hidden", timeout=5000)


def run_single(playwright, scenario_name, scenario_fn):
    browser = playwright.chromium.launch(headless=True)
    try:
        context = browser.new_context(viewport={"width": 1600, "height": 900})
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        open_builder(page)
        open_action_inspector(page)
        make_action_dirty(page)
        scenario_fn(page)
        context.close()
    except Exception as exc:
        raise AssertionError(f"{scenario_name}: {exc}") from exc
    finally:
        browser.close()


def run():
    with sync_playwright() as p:
        run_single(p, "click_canvas_outside", scenario_click_canvas_outside)
        run_single(p, "click_builder_header_outside", scenario_click_builder_header_outside)
        run_single(p, "click_sidebar_outside", scenario_click_sidebar_outside)
        run_single(p, "press_escape", scenario_press_escape)
        run_single(p, "click_inspector_close", scenario_click_inspector_close_button)
        run_single(p, "save_closes_inspector", scenario_save_closes_inspector)


if __name__ == "__main__":
    try:
        run()
        print("E2E action-node exit scenarios passed.")
    except (AssertionError, PwTimeoutError, Exception) as exc:
        print(f"E2E action-node exit scenarios failed: {exc}")
        sys.exit(1)
