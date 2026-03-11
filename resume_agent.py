"""
resume_agent.py — Offline Resume vs Job Description Matcher
Uses TF-IDF Cosine Similarity (scikit-learn). No API key required.
"""

import os
import re
import logging

import PyPDF2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config

logger = logging.getLogger(__name__)


class ResumeAgent:
    def __init__(self):
        self.resume_text = self._load_resume()
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        # Pre-fit vectorizer on resume so we only do it once
        self._resume_vector = None
        if self.resume_text:
            self._fit()

    # ── Private Helpers ───────────────────────────────────────

    def _load_resume(self) -> str:
        """Extract text from resume.pdf. Returns empty string if not found."""
        if not os.path.exists(config.RESUME_PATH):
            logger.warning(
                f"[WARN] resume.pdf not found at {config.RESUME_PATH}. "
                "Using mock scoring mode."
            )
            return ""
        try:
            text = []
            with open(config.RESUME_PATH, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text.append(page.extract_text() or "")
            combined = " ".join(text)
            combined = self._clean_text(combined)
            logger.info(f"[OK] Resume loaded: {len(combined)} characters extracted.")
            return combined
        except Exception as e:
            logger.error(f"[ERROR] Failed to read resume.pdf: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        """Normalize whitespace and remove special characters."""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s.,%-]", "", text)
        return text.strip().lower()

    def _fit(self):
        """Fit vectorizer and compute resume vector."""
        try:
            self._resume_vector = self.vectorizer.fit_transform([self.resume_text])
        except ValueError as e:
            logger.error(f"[ERROR] Vectorizer fit failed: {e}")
            self._resume_vector = None

    # ── Public API ────────────────────────────────────────────

    # Your 12 most important skills from the resume
    # Score = how many of these appear in the JD / 12 * 100
    CORE_SKILLS = [
        "react", "node", "mongodb", "javascript",
        "express", "html", "css", "firebase",
        "git", "rest", "api", "tailwind",
    ]

    def score(self, job_description: str) -> dict:
        """
        Score = (# of YOUR core skills mentioned in the JD) / 12 * 100
        Apply if score >= MIN_MATCH_SCORE (50%) — i.e. if JD mentions 6+ of your skills.
        """
        if not self.resume_text:
            return self.score_mock(job_description)

        job_clean = self._clean_text(job_description)
        if not job_clean:
            return {"score": 0, "verdict": "[SKIP]", "reason": "Empty JD."}

        matched = [skill for skill in self.CORE_SKILLS if skill in job_clean]
        score   = int(len(matched) / len(self.CORE_SKILLS) * 100)

        verdict = "[APPLY]" if score >= config.MIN_MATCH_SCORE else "[SKIP]"
        reason  = (
            f"Core skills matched: {matched or ['none']} "
            f"= {len(matched)}/{len(self.CORE_SKILLS)} = {score}% "
            f"(threshold: {config.MIN_MATCH_SCORE}%)"
        )
        return {"score": score, "verdict": verdict, "reason": reason}


    def score_mock(self, job_description: str = "") -> dict:
        """
        Mock scoring when no resume.pdf is present.
        Uses simple keyword overlap heuristic.
        """
        tech_keywords = [
            "python", "django", "flask", "fastapi", "sql", "postgresql",
            "docker", "kubernetes", "aws", "git", "linux", "api", "rest",
            "machine learning", "pandas", "numpy", "selenium", "automation",
            "javascript", "react", "node", "data", "engineer", "developer",
        ]
        jd_lower = job_description.lower()
        matched = [kw for kw in tech_keywords if kw in jd_lower]
        score = min(100, int((len(matched) / len(tech_keywords)) * 100) + 30)
        verdict = "[APPLY - mock]" if score >= config.MIN_MATCH_SCORE else "[SKIP - mock]"
        return {
            "score": score,
            "verdict": verdict,
            "reason": f"Mock mode — matched keywords: {matched or ['none']}",
        }


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = ResumeAgent()

    sample_jd = """
    We are looking for a Python Developer with experience in Django, REST APIs,
    PostgreSQL, Docker, and AWS. Strong understanding of automation, pandas,
    and data pipelines required.
    """
    result = agent.score(sample_jd)
    print("\n=== Resume Match Result ===")
    print(f"  Score   : {result['score']}%")
    print(f"  Verdict : {result['verdict']}")
    print(f"  Reason  : {result['reason']}")
