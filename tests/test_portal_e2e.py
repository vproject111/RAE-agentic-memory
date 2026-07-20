import os
import sys
import time
import subprocess
import pytest

playwright_mod = pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright

PORT = 8098

@pytest.fixture(scope="module", autouse=True)
def run_portal():
    # Start portal on port 8098 using current python binary path
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    env["NICEGUI_SCREEN_TEST_PORT"] = str(PORT)
    proc = subprocess.Popen(
        [sys.executable, "rae-portal/main.py"],
        env=env
    )
    # Wait for NiceGUI to start up
    time.sleep(3.0)
    yield
    proc.terminate()
    proc.wait()

def test_portal_navigation_and_wcga():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Access portal
        page.goto(f"http://localhost:{PORT}/")
        page.wait_for_timeout(1000)
        
        # Assert page title contains expected portal title
        assert "RAE Suite Portal" in page.title()

        # 2. Cookie consent verification
        # Click on "Akceptuję Wszystkie" cookies button
        accept_button = page.locator('button:has-text("Akceptuję Wszystkie")')
        if accept_button.is_visible():
            accept_button.click()
            page.wait_for_timeout(500)

        # 3. Accessibility controls (WCGA Contrast toggle)
        # Click contrast toggle button
        contrast_btn = page.locator('button[aria-label="Przełącz wysoki kontrast (WCGA)"]')
        assert contrast_btn.is_visible()
        contrast_btn.click()
        page.wait_for_timeout(500)
        
        # HTML tag should have contrast class
        html_class = page.locator('html').get_attribute('class') or ""
        assert "wcga-contrast" in html_class

        # Click fonts toggle button
        fonts_btn = page.locator('button[aria-label="Przełącz rozmiar czcionek (WCGA)"]')
        assert fonts_btn.is_visible()
        fonts_btn.click()
        page.wait_for_timeout(500)
        
        html_class = page.locator('html').get_attribute('class') or ""
        assert "wcga-fonts" in html_class

        # 4. Standalone Evidence Page Validation
        page.goto(f"http://localhost:{PORT}/evidence")
        page.wait_for_timeout(1000)
        
        # Verify H1 semantic element is present and matches title
        h1_element = page.locator('h1')
        assert h1_element.is_visible()
        assert "Karta Dowodowa RAE" in h1_element.text_content()
        
        browser.close()
