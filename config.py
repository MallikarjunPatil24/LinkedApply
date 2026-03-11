"""
config.py — Central Configuration for LinkedIn AI Job Hunter
All settings are loaded from .env for security.
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# ── Credentials ──────────────────────────────────────────────
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# ── Job Search ───────────────────────────────────────────────
JOB_SEARCH_KEYWORDS = os.getenv("JOB_SEARCH_KEYWORDS", "Full Stack Developer React Node.js")
JOB_SEARCH_LOCATION = os.getenv("JOB_SEARCH_LOCATION", "India")
MAX_PAGES           = int(os.getenv("MAX_PAGES", 5))

# ── Bot Behaviour ─────────────────────────────────────────────
DRY_RUN        = os.getenv("DRY_RUN", "True").lower() == "true"
MIN_MATCH_SCORE = int(os.getenv("MIN_MATCH_SCORE", 85))

# ── File Paths ────────────────────────────────────────────────
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
RESUME_PATH       = os.path.join(BASE_DIR, "resume.pdf")
CSV_LOG_PATH      = os.path.join(BASE_DIR, "applied_jobs.csv")
CHROME_PROFILE_DIR = os.path.join(BASE_DIR, "chrome_profile")

# ── Timing (seconds) — randomised in bot.py for human-like feel ──
MIN_DELAY = 1.5
MAX_DELAY = 4.0

# ── LinkedIn URLs ────────────────────────────────────────────
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_JOBS_URL  = (
    "https://www.linkedin.com/jobs/search/"
    "?keywords={keywords}&location={location}&f_LF=f_AL"
)

# ── Sanity check ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Config Loaded ===")
    print(f"  Email           : {LINKEDIN_EMAIL}")
    print(f"  Keywords        : {JOB_SEARCH_KEYWORDS}")
    print(f"  Location        : {JOB_SEARCH_LOCATION}")
    print(f"  Min Match Score : {MIN_MATCH_SCORE}%")
    print(f"  Dry Run Mode    : {DRY_RUN}")
    print(f"  Max Pages       : {MAX_PAGES}")
    print(f"  Resume Path     : {RESUME_PATH}")
    print(f"  CSV Log         : {CSV_LOG_PATH}")
