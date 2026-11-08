"""Cross-browser signed-in upload, train, and evaluation-chart smoke test."""

import argparse
import time

from playwright.sync_api import expect, sync_playwright


def run(browser_name, base_url):
    with sync_playwright() as playwright:
        browser_type = getattr(playwright, browser_name)
        browser = browser_type.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        suffix = str(time.time_ns())
        username = f"browser_{suffix[-12:]}"
        password = "BrowserSmokePass123!"
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.locator("#reg-username").fill(username)
        page.locator("#reg-email").fill(f"{username}@example.test")
        page.locator("#reg-password").fill(password)
        page.locator("#registration-form button[type=submit]").click()
        page.locator("#registration-feedback").get_by_text(
            "Registration successful", exact=False
        ).wait_for(timeout=15000)

        page.locator("#login-username").fill(username)
        page.locator("#login-password").fill(password)
        page.locator("#login-form button[type=submit]").click()
        page.wait_for_url(f"{base_url}/", timeout=15000)
        page.locator("#upload-form").wait_for(state="visible")

        csv_rows = ["x1,x2,label"]
        csv_rows.extend(
            f"{index},{index % 7},{'high' if index >= 40 else 'low'}"
            for index in range(80)
        )
        page.locator("#csv-file").set_input_files({
            "name": "browser-smoke.csv",
            "mimeType": "text/csv",
            "buffer": ("\n".join(csv_rows) + "\n").encode("utf-8"),
        })
        page.locator("#upload-btn").click()
        page.locator("#upload-feedback").get_by_text(
            "uploaded successfully", exact=False
        ).wait_for(timeout=20000)

        target = page.locator("#target-column-select")
        expect(target).to_be_enabled(timeout=15000)
        target.select_option(label="label")
        algorithm = page.locator("#algorithm-select")
        expect(algorithm).to_be_enabled(timeout=10000)
        algorithm.select_option("decision_tree")
        page.locator("#train-btn").click()

        page.get_by_role("heading", name="Classification Performance Chart").wait_for(
            timeout=30000
        )
        canvas = page.locator("#evaluation-chart")
        expect(canvas).to_be_visible(timeout=10000)
        assert canvas.evaluate("element => element.tagName.toLowerCase()") == "canvas"
        assert canvas.evaluate("element => element.width > 0 && element.height > 0")
        assert page.evaluate(
            "Boolean(window.Chart && Chart.getChart(document.querySelector('#evaluation-chart')))"
        )
        assert not page_errors, f"Browser JavaScript errors: {page_errors}"

        print(f"PASS browser={browser_name} version={browser.version}")
        context.close()
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    run(args.browser, args.base_url)
