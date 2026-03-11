"""
bot.py — LinkedIn AI Job Hunter (Main Automation Script)
=========================================================
Features:
  - Undetected Chrome (avoids LinkedIn bot detection)
  - Persistent Chrome profile (remembers login cookies)
  - TF-IDF resume matching — no API key needed
  - Pandas CSV tracking of applied jobs
  - Human-like delays & scroll behaviour
  - Dry Run mode: highlights Apply button but never clicks
"""

import csv
import logging
import os
import random
import time
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import undetected_chromedriver as uc
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config
from resume_agent import ResumeAgent

# ── Logging Setup ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(config.BASE_DIR, "bot.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class LinkedInBot:
    # ── CSS Selectors — multiple fallbacks per element ────────
    # LinkedIn changes class names often; we try each in order.
    SEL_EMAIL        = "#username"
    SEL_PASSWORD     = "#password"
    SEL_LOGIN_BTN    = "button[type='submit']"

    # Job card container — tries modern + legacy selectors
    SEL_JOB_CARDS_LIST = [
        "li.scaffold-layout__list-item",
        "li.jobs-search-results__list-item",
        "li.ember-view.jobs-search-results__list-item",
        "div.job-card-container",
        "[data-occludable-job-id]",
    ]

    # Job title inside a card
    SEL_JOB_TITLE_LIST = [
        ".job-card-list__title--link",
        ".job-card-list__title",
        "a.job-card-container__link strong",
        ".artdeco-entity-lockup__title",
    ]

    # Company name inside a card
    SEL_JOB_COMPANY_LIST = [
        ".artdeco-entity-lockup__subtitle span",
        ".job-card-container__primary-description",
        ".job-card-container__company-name",
        ".job-card-list__company-name",
    ]

    # Easy Apply button in the right panel
    SEL_EASY_APPLY_LIST = [
        "button.jobs-apply-button[aria-label*='Easy Apply']",
        "button[aria-label*='Easy Apply']",
        ".jobs-s-apply button",
        "button.jobs-apply-button",
    ]

    # Job description panel
    SEL_JOB_DESC_LIST = [
        ".jobs-description__content",
        ".jobs-description-content__text",
        "#job-details",
        ".job-view-layout",
    ]

    # ── Target job title keywords ─────────────────────────────
    # Apply immediately if the job title contains ANY of these words
    TARGET_TITLES = [
        "fresher", "fresher", "intern", "internship",
        "junior", "jr ", "entry level", "entry-level",
        "frontend developer", "frontend engineer",
        "front end developer", "front-end developer",
        "full stack", "fullstack",
        "software developer", "software engineer",
        "react developer", "react engineer",
        "node developer", "node engineer",
        "mern developer", "web developer",
        "associate developer", "associate engineer",
    ]

    SEL_CLOSE_MODAL = "button[aria-label='Dismiss']"
    NEXT_PAGE       = "button[aria-label='View next page']"

    @staticmethod
    def _is_target_job(title: str) -> bool:
        """Return True if the title matches any target role keyword."""
        t = title.lower()
        return any(kw in t for kw in LinkedInBot.TARGET_TITLES)


    def __init__(self):
        self.driver  = None
        self.wait    = None
        self.agent   = ResumeAgent()
        self.applied = self._load_applied_jobs()

        mode = "🟡 DRY RUN" if config.DRY_RUN else "🔴 LIVE"
        logger.info(f"Bot initialised — Mode: {mode}")

    # ── CSV Tracking ──────────────────────────────────────────

    def _load_applied_jobs(self) -> set:
        """Load already-applied job IDs from CSV to avoid duplicates."""
        path = config.CSV_LOG_PATH
        if not os.path.exists(path):
            # Create empty CSV with headers
            pd.DataFrame(columns=[
                "job_id", "title", "company", "match_score",
                "status", "applied_at", "url"
            ]).to_csv(path, index=False)
            return set()
        df = pd.read_csv(path)
        return set(df["job_id"].astype(str).tolist())

    def _log_job(self, job_id, title, company, score, status, url):
        """Append a job record to the CSV log."""
        row = {
            "job_id":      job_id,
            "title":       title,
            "company":     company,
            "match_score": score,
            "status":      status,
            "applied_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url":         url,
        }
        df = pd.read_csv(config.CSV_LOG_PATH)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(config.CSV_LOG_PATH, index=False)
        self.applied.add(str(job_id))

    # ── Chrome Setup ──────────────────────────────────────────

    def _start_driver(self):
        """Launch undetected Chrome with a persistent profile."""
        os.makedirs(config.CHROME_PROFILE_DIR, exist_ok=True)
        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={config.CHROME_PROFILE_DIR}")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        # Uncomment below for headless (not recommended — easier to detect):
        # options.add_argument("--headless=new")

        # Pin to Chrome 145 — update this if you upgrade Chrome
        self.driver = uc.Chrome(options=options, version_main=145)
        self.wait   = WebDriverWait(self.driver, 15)
        logger.info("[OK] Chrome launched with undetected-chromedriver.")

    # ── Human-Like Helpers ────────────────────────────────────

    def _sleep(self, min_s=None, max_s=None):
        """Randomised sleep to mimic human reading/interaction speed."""
        time.sleep(random.uniform(
            min_s or config.MIN_DELAY,
            max_s or config.MAX_DELAY
        ))

    def _human_scroll(self, pixels=None):
        """Scroll a random amount to simulate reading."""
        scroll_px = pixels or random.randint(300, 800)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_px});")
        self._sleep(0.5, 1.5)

    def _human_type(self, element, text: str):
        """Type text character-by-character with random delays."""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.04, 0.18))

    def _find_element_any(self, selectors: list, parent=None):
        """Try each CSS selector in order; return first match or None."""
        root = parent or self.driver
        for sel in selectors:
            try:
                return root.find_element(By.CSS_SELECTOR, sel)
            except NoSuchElementException:
                continue
        return None

    def _find_elements_any(self, selectors: list):
        """Try each CSS selector; return first non-empty list of elements."""
        for sel in selectors:
            try:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    logger.info(f"  [Selector] matched '{sel}' -> {len(els)} elements")
                    return els
            except Exception:
                continue
        return []

    def _highlight_element(self, element, color="red"):
        """Visually highlight a WebElement (used in Dry Run mode)."""
        self.driver.execute_script(
            f"arguments[0].style.border='3px solid {color}'; "
            f"arguments[0].style.backgroundColor='rgba(255,0,0,0.15)';",
            element
        )

    # ── Login ─────────────────────────────────────────────────

    def _is_logged_in(self) -> bool:
        return "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url

    def login(self):
        """Log into LinkedIn. Skips if already authenticated via saved cookie."""
        self.driver.get(config.LINKEDIN_LOGIN_URL)
        self._sleep(2, 4)

        if self._is_logged_in():
            logger.info("✅ Already logged in via saved session.")
            return

        logger.info("🔑 Logging in...")
        try:
            email_field = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, self.SEL_EMAIL)))
            self._human_type(email_field, config.LINKEDIN_EMAIL)
            self._sleep(0.5, 1.2)

            pwd_field = self.driver.find_element(By.CSS_SELECTOR, self.SEL_PASSWORD)
            self._human_type(pwd_field, config.LINKEDIN_PASSWORD)
            self._sleep(0.5, 1.2)

            self.driver.find_element(By.CSS_SELECTOR, self.SEL_LOGIN_BTN).click()
            self._sleep(4, 7)

            if self._is_logged_in():
                logger.info("✅ Login successful.")
            else:
                logger.warning("⚠️  Login might have failed or requires CAPTCHA. "
                               "Check the browser window.")
        except TimeoutException:
            logger.error("❌ Login form not found. LinkedIn may have changed its layout.")

    # ── Job Search ────────────────────────────────────────────

    def _build_search_url(self, page: int = 0) -> str:
        kw  = quote(config.JOB_SEARCH_KEYWORDS)
        loc = quote(config.JOB_SEARCH_LOCATION)
        offset = page * 25
        return (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={kw}&location={loc}&f_LF=f_AL&start={offset}"
        )

    def _get_job_cards(self):
        """Return all visible job card elements, trying multiple selectors."""
        # Extra scroll to trigger lazy-load rendering
        self.driver.execute_script("window.scrollTo(0, 400);")
        self._sleep(2, 3)
        self.driver.execute_script("window.scrollTo(0, 0);")
        self._sleep(1, 2)
        cards = self._find_elements_any(self.SEL_JOB_CARDS_LIST)
        if not cards:
            # Dump page source snippet for debugging
            source_snippet = self.driver.page_source[:500]
            logger.warning(f"  [DEBUG] No cards found. Page start: {source_snippet}")
        return cards


    def _get_job_description(self) -> str:
        """Extract job description text from the right-side panel."""
        self._sleep(1, 2)
        el = self._find_element_any(self.SEL_JOB_DESC_LIST)
        return el.text if el else ""


    def _get_job_id_from_url(self) -> str:
        """Extract job ID from the current URL."""
        url = self.driver.current_url
        if "currentJobId=" in url:
            return url.split("currentJobId=")[1].split("&")[0]
        if "/jobs/view/" in url:
            return url.split("/jobs/view/")[1].split("/")[0]
        return str(int(time.time()))   # fallback unique ID


    # ── Apply Flow ────────────────────────────────────────────

    def _click_btn(self, btn):
        """Click a button — falls back to JS click if intercepted."""
        try:
            btn.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", btn)

    def _dismiss_modal(self):
        """Close any open Easy Apply modal."""
        for sel in [
            "button[aria-label='Dismiss']",
            "button[aria-label='Cancel']",
            "button[data-test-modal-close-btn]",
        ]:
            try:
                self.driver.find_element(By.CSS_SELECTOR, sel).click()
                self._sleep(0.5, 1)
                # Confirm discard if dialog appears
                for discard_sel in [
                    "button[data-test-dialog-primary-btn]",
                    "button[aria-label='Discard']",
                ]:
                    try:
                        self.driver.find_element(By.CSS_SELECTOR, discard_sel).click()
                    except NoSuchElementException:
                        pass
                return
            except NoSuchElementException:
                continue

    # ── Smart form-answering constants ────────────────────────
    # Full project/experience block to paste when a textarea asks for experience
    EXPERIENCE_TEXT = (
        "Voice-Controlled AI Assistant – NVIDIA Jetson AGX Orin | Dec 2024 – Feb 2025\n"
        "Project Lead / AI Integration\n"
        "Engineered a real-time AI assistant for hands-free vehicle control, reducing driver "
        "distraction through low-latency voice command processing.\n"
        "Successfully bridged hardware and software by syncing MATLAB simulations with a "
        "React.js dashboard for live system monitoring and diagnostic visualization.\n"
        "Enhanced accessibility by implementing speech recognition logic capable of handling "
        "natural language commands for core vehicle functions."
    )

    # Keywords that indicate the question is about years of experience
    _EXP_YEAR_KEYWORDS = [
        "year", "years", "experience", "exp", "yrs", "how long",
        "how many year", "total experience",
    ]
    # Keywords that indicate the question is about notice period
    _NOTICE_KEYWORDS = [
        "notice", "notice period", "joining", "join", "availability",
        "available in", "days to join", "serve notice",
    ]
    # Keywords that indicate a textarea wants an experience description / cover
    _EXP_DESC_KEYWORDS = [
        "experience", "describe your experience", "background",
        "tell us", "summary", "project", "work experience",
        "relevant experience", "portfolio", "cover letter",
    ]

    def _get_field_label(self, element) -> str:
        """
        Try to find the visible label text associated with a form field.
        Works for standard <label for="id">, aria-label, placeholder, and
        nearby legend/span siblings.
        """
        label_text = ""
        try:
            field_id = element.get_attribute("id")
            if field_id:
                try:
                    lbl = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{field_id}']")
                    label_text = lbl.text.strip()
                except NoSuchElementException:
                    pass

            if not label_text:
                label_text = element.get_attribute("aria-label") or ""

            if not label_text:
                label_text = element.get_attribute("placeholder") or ""

            if not label_text:
                # Walk up to parent div and grab any visible text / legend
                parent = self.driver.execute_script(
                    "return arguments[0].closest('div.fb-dash-form-element,"
                    "div.jobs-easy-apply-form-element,li,fieldset');",
                    element
                )
                if parent:
                    label_text = parent.text[:120]
        except Exception:
            pass
        return label_text.lower()

    def _answer_basic_questions(self):
        """
        Intelligently fill in Easy Apply form fields by reading question labels.

        Handles:
          - Number / text inputs: years of experience, notice period, generic
          - Textareas: pastes full experience block when relevant
          - Select dropdowns: prefer 'Yes', fall back to first valid option
          - Radio buttons: prefer 'Yes' / 'Agree', fall back to first option
          - Checkboxes: check if 'agree' / 'authorise' type question
        """
        from selenium.webdriver.support.ui import Select as SeleniumSelect

        modal_sel = "div.jobs-easy-apply-modal"

        # ── 1. Text & Number inputs ───────────────────────────────────────
        inputs = self.driver.find_elements(
            By.CSS_SELECTOR,
            f"{modal_sel} input[type='text'], {modal_sel} input[type='number']",
        )
        for inp in inputs:
            try:
                # Skip already-filled fields
                if inp.get_attribute("value"):
                    continue
                if not inp.is_displayed() or not inp.is_enabled():
                    continue

                label = self._get_field_label(inp)

                if any(kw in label for kw in self._NOTICE_KEYWORDS):
                    # Notice period — answer "3" (or "90" for days)
                    answer = "90" if any(w in label for w in ["day", "days"]) else "3"
                    logger.info(f"    [FORM] Notice period field → '{answer}'")
                    self._human_type(inp, answer)

                elif any(kw in label for kw in self._EXP_YEAR_KEYWORDS):
                    # Years of experience — answer "1"
                    logger.info("    [FORM] Experience years field → '1'")
                    self._human_type(inp, "1")

                else:
                    # Generic input — safe fallback "1"
                    logger.info(f"    [FORM] Generic input ('{label[:40]}') → '1'")
                    self._human_type(inp, "1")

                self._sleep(0.4, 0.9)

            except Exception as ex:
                logger.debug(f"    [FORM] input error: {ex}")

        # ── 2. Textareas (cover letter / experience description) ──────────
        textareas = self.driver.find_elements(
            By.CSS_SELECTOR, f"{modal_sel} textarea"
        )
        for ta in textareas:
            try:
                if not ta.is_displayed() or not ta.is_enabled():
                    continue
                existing = ta.get_attribute("value") or ta.text or ""
                if existing.strip():
                    continue  # already filled

                label = self._get_field_label(ta)

                if any(kw in label for kw in self._EXP_DESC_KEYWORDS):
                    logger.info("    [FORM] Experience textarea → pasting experience block")
                    ta.click()
                    self._sleep(0.3, 0.6)
                    ta.clear()
                    # Use clipboard-style paste via JS for speed & reliability
                    self.driver.execute_script(
                        "arguments[0].value = arguments[1];", ta, self.EXPERIENCE_TEXT
                    )
                    # Trigger React/Vue change event so the field registers the value
                    self.driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                        "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                        ta,
                    )
                else:
                    logger.info(f"    [FORM] Generic textarea ('{label[:40]}') → pasting experience block")
                    self.driver.execute_script(
                        "arguments[0].value = arguments[1];", ta, self.EXPERIENCE_TEXT
                    )
                    self.driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                        "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                        ta,
                    )

                self._sleep(0.5, 1.0)

            except Exception as ex:
                logger.debug(f"    [FORM] textarea error: {ex}")

        # ── 3. Select dropdowns ───────────────────────────────────────────
        selects = self.driver.find_elements(
            By.CSS_SELECTOR, f"{modal_sel} select"
        )
        for sel in selects:
            try:
                if not sel.is_displayed():
                    continue
                dropdown = SeleniumSelect(sel)
                current = dropdown.first_selected_option
                if current.get_attribute("value") and "select" not in current.text.lower():
                    continue  # already has a meaningful selection

                label = self._get_field_label(sel)

                if any(kw in label for kw in self._NOTICE_KEYWORDS):
                    # Try to pick an option that contains "3" or "month"
                    picked = False
                    for opt in dropdown.options:
                        ot = opt.text.lower()
                        if "3" in ot or "three" in ot or "month" in ot:
                            dropdown.select_by_visible_text(opt.text)
                            logger.info(f"    [FORM] Notice dropdown → '{opt.text}'")
                            picked = True
                            break
                    if not picked and len(dropdown.options) > 1:
                        dropdown.select_by_index(1)

                else:
                    # Generic: prefer 'Yes', otherwise first non-empty option
                    yes_idx = next(
                        (i for i, o in enumerate(dropdown.options)
                         if "yes" in o.text.lower()),
                        -1,
                    )
                    if yes_idx != -1:
                        dropdown.select_by_index(yes_idx)
                        logger.info(f"    [FORM] Dropdown ('{label[:30]}') → 'Yes'")
                    elif len(dropdown.options) > 1:
                        dropdown.select_by_index(1)
                        logger.info(f"    [FORM] Dropdown ('{label[:30]}') → option[1]")

                self._sleep(0.4, 0.9)

            except Exception as ex:
                logger.debug(f"    [FORM] select error: {ex}")

        # ── 4. Radio buttons ──────────────────────────────────────────────
        fieldsets = self.driver.find_elements(
            By.CSS_SELECTOR, f"{modal_sel} fieldset"
        )
        for fs in fieldsets:
            try:
                radios = fs.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                if not radios:
                    continue
                if any(r.is_selected() for r in radios):
                    continue  # already answered

                labels = fs.find_elements(By.CSS_SELECTOR, "label")
                clicked = False
                # Prefer "Yes" / "Agree" labels
                for lbl in labels:
                    lt = lbl.text.lower()
                    if "yes" in lt or "agree" in lt or "authoris" in lt:
                        self._click_btn(lbl)
                        logger.info(f"    [FORM] Radio → '{lbl.text.strip()}'")
                        clicked = True
                        break
                if not clicked and labels:
                    self._click_btn(labels[0])
                    logger.info(f"    [FORM] Radio fallback → '{labels[0].text.strip()}'")

                self._sleep(0.4, 0.8)

            except Exception as ex:
                logger.debug(f"    [FORM] radio error: {ex}")

        # ── 5. Checkboxes (consent / agree type) ─────────────────────────
        checkboxes = self.driver.find_elements(
            By.CSS_SELECTOR, f"{modal_sel} input[type='checkbox']"
        )
        for cb in checkboxes:
            try:
                if not cb.is_displayed() or cb.is_selected():
                    continue
                label = self._get_field_label(cb)
                if any(kw in label for kw in ["agree", "consent", "authoris", "certif", "confirm"]):
                    self._click_btn(cb)
                    logger.info(f"    [FORM] Checkbox ('{label[:40]}') → checked")
                    self._sleep(0.3, 0.6)
            except Exception as ex:
                logger.debug(f"    [FORM] checkbox error: {ex}")

    def _try_easy_apply(self, job_id, title, company, score, url):
        """
        Full Easy Apply flow:
          1. Find & click Easy Apply button
          2. Wait for modal to appear
          3. Walk through each step: answer questions → click Next/Review/Submit
          4. Detect submission via button text inspection (not brittle aria-labels)
          5. Detect modal-close as confirmation of completion
        """
        # ── Find the Easy Apply button ────────────────────────
        self._sleep(1, 2)
        self.driver.execute_script("window.scrollTo(0, 300);")
        self._sleep(0.5, 1)

        apply_btn = self._find_element_any(self.SEL_EASY_APPLY_LIST)
        if not apply_btn:
            logger.info(f"  -> No Easy Apply button for: {title}")
            self._log_job(job_id, title, company, score, "NO_EASY_APPLY", url)
            return

        # ── Dry Run ───────────────────────────────────────────
        if config.DRY_RUN:
            self._highlight_element(apply_btn)
            logger.info(f"  [DRY RUN] Would apply: {title} @ {company} | {score}%")
            self._log_job(job_id, title, company, score, "DRY_RUN", url)
            self._sleep(1, 2)
            return

        # ── Click Easy Apply ──────────────────────────────────
        logger.info(f"  -> Clicking Easy Apply for: {title} @ {company}")
        try:
            self._click_btn(apply_btn)
        except Exception:
            self.driver.execute_script("arguments[0].click();", apply_btn)
        self._sleep(2.5, 4)

        # ── Wait for modal ────────────────────────────────────
        MODAL_SELECTORS = [
            "div.jobs-easy-apply-modal",
            "div[data-test-modal]",
            ".artdeco-modal",
        ]
        modal_found = False
        for ms in MODAL_SELECTORS:
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ms))
                )
                logger.info(f"  -> Modal opened (selector: {ms})")
                modal_found = True
                break
            except TimeoutException:
                continue

        if not modal_found:
            logger.warning("  -> Modal did not open. Skipping.")
            self._log_job(job_id, title, company, score, "MODAL_NOT_FOUND", url)
            return

        # ── Step loop ─────────────────────────────────────────
        SUBMIT_KEYWORDS = ["submit", "done", "apply now", "send application"]
        REVIEW_KEYWORDS = ["review"]
        NEXT_KEYWORDS   = ["next", "continue", "proceed"]

        # Broad selectors — finds the primary (blue) button(s) in modal footer
        BROAD_BTN_SELECTORS = [
            "div.jobs-easy-apply-modal footer button",
            "div[data-test-modal] footer button",
            ".artdeco-modal footer button",
            "div.jobs-easy-apply-modal button.artdeco-button--primary",
            ".artdeco-modal button.artdeco-button--primary",
        ]

        submitted = False
        for step in range(12):
            self._sleep(1.5, 2.5)

            # Answer visible form fields
            try:
                self._answer_basic_questions()
            except Exception as qe:
                logger.debug(f"  [FORM] Error at step {step+1}: {qe}")
            self._sleep(0.8, 1.5)

            # Discover buttons
            btn_candidates = []
            for bsel in BROAD_BTN_SELECTORS:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, bsel)
                    visible = [b for b in btns if b.is_displayed() and b.is_enabled()]
                    if visible:
                        btn_candidates = visible
                        break
                except Exception:
                    continue

            if not btn_candidates:
                logger.warning(f"  -> Step {step+1}: No modal buttons found. Stopping.")
                try:
                    # Debug: list all visible buttons on the page
                    all_btns = self.driver.find_elements(By.CSS_SELECTOR, "button")
                    vis = [b for b in all_btns if b.is_displayed()]
                    for b in vis[:8]:
                        logger.warning(f"     btn text='{b.text.strip()}' aria='{b.get_attribute('aria-label')}'")
                except Exception:
                    pass
                break

            # Log found buttons
            for b in btn_candidates:
                try:
                    logger.info(f"  [BTN] Step {step+1}: text='{b.text.strip()}' | aria='{b.get_attribute('aria-label')}'")
                except Exception:
                    pass

            # Classify buttons by text/aria
            submit_btn = None
            review_btn = None
            next_btn   = None

            for b in btn_candidates:
                try:
                    combined = ((b.text or "") + " " + (b.get_attribute("aria-label") or "")).lower()
                    if any(kw in combined for kw in SUBMIT_KEYWORDS):
                        submit_btn = b
                    elif any(kw in combined for kw in REVIEW_KEYWORDS):
                        review_btn = b
                    elif any(kw in combined for kw in NEXT_KEYWORDS):
                        next_btn = b
                except Exception:
                    pass

            def safe_click(btn):
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    self._sleep(0.4, 0.8)
                    self._click_btn(btn)
                except Exception:
                    self.driver.execute_script("arguments[0].click();", btn)

            if submit_btn:
                logger.info(f"  -> Step {step+1}: Clicking SUBMIT")
                safe_click(submit_btn)
                self._sleep(3, 5)
                submitted = True
                break
            elif review_btn:
                logger.info(f"  -> Step {step+1}: Clicking REVIEW")
                safe_click(review_btn)
            elif next_btn:
                logger.info(f"  -> Step {step+1}: Clicking NEXT")
                safe_click(next_btn)
            else:
                # Fallback: click rightmost primary button (usually Next)
                fallback = btn_candidates[-1]
                logger.info(f"  -> Step {step+1}: Fallback click on '{fallback.text.strip()}'")
                safe_click(fallback)

            # Check if modal closed (means success or skipped to confirmation)
            self._sleep(1.5, 2.5)
            still_open = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div.jobs-easy-apply-modal,.artdeco-modal,div[data-test-modal]"
            )
            visible_modals = [m for m in still_open if m.is_displayed()]
            if not visible_modals:
                logger.info(f"  -> Modal closed after step {step+1}. Treating as submitted.")
                submitted = True
                break

        # ── Result ────────────────────────────────────────────
        if submitted:
            logger.info(f"  [APPLIED] {title} @ {company} | Score: {score}%")
            self._log_job(job_id, title, company, score, "APPLIED", url)
        else:
            logger.warning(f"  [SUBMIT_FAILED] Could not finish form for: {title}")
            self._log_job(job_id, title, company, score, "SUBMIT_FAILED", url)
            self._dismiss_modal()

        self._sleep(2, 3)

    # ── Main Loop ─────────────────────────────────────────────

    def run(self):
        """Main entry point: login → search → score → apply."""
        self._start_driver()
        self.login()

        total_applied = 0
        total_skipped = 0
        total_already_done = 0

        for page in range(config.MAX_PAGES):
            url = self._build_search_url(page)
            logger.info(f"\n📄 Scraping page {page + 1} → {url}")
            self.driver.get(url)
            self._sleep(3, 5)
            self._human_scroll()

            job_cards = self._get_job_cards()
            if not job_cards:
                logger.info("  No job cards found. Ending early.")
                break

            logger.info(f"  Found {len(job_cards)} job(s) on this page.")

            for idx, card in enumerate(job_cards):
                try:
                    # Click card to load details
                    card.click()
                    self._sleep(2, 3.5)

                    job_id  = self._get_job_id_from_url()
                    job_url = self.driver.current_url

                    # Skip already-applied/logged jobs
                    if str(job_id) in self.applied:
                        logger.info(f"  [{idx+1}] Already processed job_id={job_id}. Skipping.")
                        total_already_done += 1
                        continue

                    # Extract metadata using fallback selectors
                    try:
                        title_el = self._find_element_any(self.SEL_JOB_TITLE_LIST, parent=card)
                        title = title_el.text.strip() if title_el else "Unknown Title"
                        company_el = self._find_element_any(self.SEL_JOB_COMPANY_LIST, parent=card)
                        company = company_el.text.strip() if company_el else "Unknown Company"
                    except Exception:
                        title   = "Unknown Title"
                        company = "Unknown Company"

                    # ── TITLE-BASED FILTER — no scoring needed ────────
                    if self._is_target_job(title):
                        logger.info(
                            f"  [{idx+1}] MATCH: {title} @ {company} -> APPLYING"
                        )
                        self._try_easy_apply(job_id, title, company, 100, job_url)
                        total_applied += 1
                    else:
                        logger.info(
                            f"  [{idx+1}] SKIP: {title} @ {company} -> not a target role"
                        )
                        self._log_job(job_id, title, company, 0, "SKIPPED_TITLE", job_url)
                        total_skipped += 1

                    self._human_scroll(random.randint(100, 400))
                    self._sleep()

                except Exception as e:
                    logger.error(f"  ❌ Error processing card {idx+1}: {e}")
                    continue

        # ── Session Summary ───────────────────────────────────
        logger.info("\n" + "=" * 50)
        logger.info("📊 SESSION SUMMARY")
        logger.info(f"  ✅ Attempted applies  : {total_applied}")
        logger.info(f"  ❌ Skipped (low score): {total_skipped}")
        logger.info(f"  ⏭️  Already processed : {total_already_done}")
        logger.info(f"  📁 Log saved to       : {config.CSV_LOG_PATH}")
        mode = "DRY RUN" if config.DRY_RUN else "LIVE"
        logger.info(f"  🔧 Mode               : {mode}")
        logger.info("=" * 50)

        input("\nPress Enter to close the browser...")
        try:
            type(self.driver).__del__ = lambda self: None
            self.driver.quit()
        except Exception:
            pass


# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    bot = LinkedInBot()
    bot.run()
