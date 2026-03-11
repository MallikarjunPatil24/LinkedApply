from resume_agent import ResumeAgent
r = ResumeAgent()

tests = [
    ("Full Stack JD", "We are looking for a full stack developer with react node express mongodb javascript html css git rest api tailwind"),
    ("Frontend JD",   "Frontend developer react javascript html css firebase tailwind git vercel"),
    ("Python ML JD",  "Python data engineer machine learning tensorflow pandas numpy aws databricks"),
]

for name, jd in tests:
    res = r.score(jd)
    print(f"{name}: {res['score']}% -> {res['verdict']}")
    print(f"  {res['reason']}")
