"""
test_driver.py — WebDriver Connection Test
==========================================
Run this FIRST to verify your Selenium + undetected-chromedriver setup.
Usage:  python test_driver.py
"""

import sys
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def test_webdriver():
    print("=" * 55)
    print("  LinkedIn AI Job Hunter — WebDriver Connection Test")
    print("=" * 55)

    driver = None
    try:
        print("\n[1/4] Launching undetected Chrome...")
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        # Pin to Chrome 145 — change this number if you update Chrome
        driver = uc.Chrome(options=options, version_main=145)
        print("      ✅ Chrome launched OK")

        print("[2/4] Navigating to linkedin.com...")
        driver.get("https://www.linkedin.com")
        time.sleep(4)

        print("[3/4] Verifying page title...")
        title = driver.title
        print(f"      Page title: '{title}'")
        assert "LinkedIn" in title or "linkedin" in title.lower(), \
            f"Unexpected title: {title}"
        print("      ✅ LinkedIn page loaded OK")

        print("[4/4] Checking for login form element...")
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='login']")))
        print("      ✅ Login link detected OK\n")

        print("=" * 55)
        print("  ✅  ALL TESTS PASSED — WebDriver is ready!")
        print("=" * 55)
        return True

    except AssertionError as e:
        print(f"\n❌ ASSERTION FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting tips:")
        print("  1. Make sure Google Chrome is installed.")
        print("  2. Run: pip install undetected-chromedriver")
        print("  3. Ensure your Chrome version matches chromedriver.")
        return False
    finally:
        if driver:
            time.sleep(2)
            try:
                # Neutralize __del__ BEFORE quit so GC doesn't call quit() again
                # This prevents the harmless but noisy WinError 6 on Windows
                type(driver).__del__ = lambda self: None
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    success = test_webdriver()
    sys.exit(0 if success else 1)
