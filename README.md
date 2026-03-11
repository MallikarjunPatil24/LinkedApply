# 🤖 LinkedIn AI Job Hunter

An intelligent LinkedIn automation bot built with Python and Selenium. Uses **TF-IDF cosine similarity** to match job descriptions against your resume — **no API key required**.

---

## 📁 Project Structure

```
linkedin automation/
├── bot.py              # Main automation script
├── config.py           # Central settings (loaded from .env)
├── resume_agent.py     # Offline resume matching (TF-IDF)
├── test_driver.py      # WebDriver connection test
├── applied_jobs.csv    # Pandas log of all processed jobs
├── requirements.txt    # Python dependencies
├── .env                # 🔐 Your credentials (DO NOT SHARE)
├── .gitignore
└── resume.pdf          # ← Place YOUR resume here
```

---

## ⚡ Quick Start

### 1. Install dependencies
```powershell
pip install -r requirements.txt
```

### 2. Configure your credentials
Edit `.env`:
```
LINKEDIN_EMAIL=you@email.com
LINKEDIN_PASSWORD=yourpassword

JOB_SEARCH_KEYWORDS=Python Developer
JOB_SEARCH_LOCATION=India
DRY_RUN=True
MIN_MATCH_SCORE=85
MAX_PAGES=3
```

### 3. Add your resume
Place your CV at the root of the project as **`resume.pdf`**.

### 4. Test the WebDriver
```powershell
python test_driver.py
```
Expected: `✅ ALL TESTS PASSED — WebDriver is ready!`

### 5. Run in Dry Run mode (safe — no clicks)
```powershell
python bot.py
```
The bot will open Chrome, search jobs, highlight matching Apply buttons in **red**, and log results to `applied_jobs.csv` with status `DRY_RUN`.

### 6. Go live (when you're ready)
In `.env`, set:
```
DRY_RUN=False
```
Then run `python bot.py` again.

---

## 🧠 How Resume Matching Works

1. Your `resume.pdf` text is extracted via `PyPDF2`.
2. Each job description is vectorized alongside your resume using **TF-IDF** (Term Frequency–Inverse Document Frequency).
3. **Cosine similarity** is computed between the two vectors → scaled to a 0–100 score.
4. Only jobs with score ≥ `MIN_MATCH_SCORE` (default: **85%**) get an Easy Apply attempt.
5. If no `resume.pdf` is found, a keyword-overlap heuristic is used as fallback.

---

## 📊 applied_jobs.csv Columns

| Column | Description |
|---|---|
| `job_id` | LinkedIn's unique job ID |
| `title` | Job title |
| `company` | Company name |
| `match_score` | TF-IDF match score (0–100) |
| `status` | `APPLIED`, `DRY_RUN`, `SKIPPED_LOW_SCORE`, `NO_EASY_APPLY`, etc. |
| `applied_at` | Timestamp |
| `url` | Job listing URL |

---

## ⚠️ Important Notes

- This bot uses **`undetected-chromedriver`** to bypass LinkedIn's bot detection.
- A **persistent Chrome profile** is saved in `chrome_profile/` — this retains login cookies so you won't need to re-enter credentials on every run.
- LinkedIn's Terms of Service prohibit automated scraping. Use responsibly and for personal/educational purposes only.
- Always test with `DRY_RUN=True` before going live.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| Chrome doesn't launch | Install Google Chrome, then `pip install --upgrade undetected-chromedriver` |
| Login fails | LinkedIn may show CAPTCHA — complete it manually in the browser window |
| Low match scores | Add more keywords to your `resume.pdf` or lower `MIN_MATCH_SCORE` in `.env` |
| Bot stops mid-page | LinkedIn changed its HTML — update CSS selectors in `bot.py` |
