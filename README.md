## 👋 Meet Your AI Job Hunter

This isn't just a click-bot. It's a smart assistant that reads job descriptions, compares them to your resume using math (Cosine Similarity), and only applies to the roles where you actually have a shot.

**The best part?** It runs entirely on your machine. No cloud, no subscription, no API keys.

---

### 🛠️ Setting Up (The 3-Minute Version)

1. **Get the Gear:** Open your terminal and run:
`pip install -r requirements.txt`
2. **Tell it who you are:** Pop open the `.env` file and add your LinkedIn login.
* *Self-Correction:* If you're worried about security, the bot uses a "Persistent Profile," meaning once you log in manually once, the bot just remembers your session like a normal browser.


3. **Feed it your Resume:** Drop your `resume.pdf` into the folder. The bot reads this to understand your skills.

---

### 🤖 How the "Brain" Works (Simplified)

Instead of just looking for the word "Python," the bot looks at the **importance** of words.

* **TF (Term Frequency):** How often does "React" appear in the job post?
* **IDF (Inverse Document Frequency):** Is "React" a unique skill, or is it a common word like "the" or "and"?
* **The Result:** It creates a "Match Score." If the job asks for Cloud Architecture and your resume is all about Front-end, the bot will see a low score (e.g., 20%) and quietly skip it to save your reputation.

---

### 🚦 Safety First: The "Dry Run" Feature

I've set the default to `DRY_RUN=True`.

* **What happens:** The bot will open Chrome, find jobs, and do all the math.
* **The Visual:** It will highlight the "Apply" button in **bright red** so you can see what it *would* have clicked.
* **The Log:** Check `applied_jobs.csv` to see your scores. If they look good, flip the switch to `False` and let it fly.

---

### 🩹 Quick Fixes for Common Headaches

| If this happens... | Do this... |
| --- | --- |
| **LinkedIn asks for a CAPTCHA** | Don't panic. Just solve it manually in the window that the bot opened. The bot will wait for you. |
| **Scores are too low (0-40%)** | Your resume might be a scan/image. Make sure your `resume.pdf` has selectable text! |
| **It's skipping good jobs** | Lower the `MIN_MATCH_SCORE` in your `.env` to 70 or 75. |

---

### ⚖️ A Final "Peer-to-Peer" Warning

LinkedIn is like a hawk with bot detection. Even though we use `undetected-chromedriver` (which hides the "automation" flag), don't run this 24/7. Use it for 30 minutes, then give it a rest. Think of it as a power-tool: incredibly useful, but you still have to keep your eyes on it!

**Would you like me to help you write a "Human-Behavior" function that mimics random mouse movements so the bot looks even more like a real person?**
