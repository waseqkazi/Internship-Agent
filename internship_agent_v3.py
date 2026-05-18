# ============================================================
#  MBA INTERNSHIP AGENT v3
#  Two-agent system + Google Sheets output
#  Runs on PythonAnywhere daily, results on your phone
# ============================================================

import os, time, re, json
from datetime import datetime, timedelta
from jobspy import scrape_jobs
from groq import Groq
from duckduckgo_search import DDGS
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv



# ============================================================
#  CONFIG — FILL THESE IN
# ============================================================

load_dotenv()

GROQ_API_KEY        = os.getenv("GROQ_API_KEY")
SHEET_NAME          = os.getenv("SHEET_NAME")
CREDENTIALS_FILE    = os.getenv("CREDENTIALS_FILE") # file you'll upload
MIN_FIT_SCORE       = 6

MY_PROFILE = """
NAME: Wasequddin Kazi
PROGRAM: MBA (General Management), COEP Technological University, Pune — First Year (2025-present)
SPECIALIZATION: Business Analytics + Operations & Strategy
BACKGROUND: Mechanical Engineer + Data Analyst turned MBA

EDUCATION:
- MBA General Management — COEP Technological University, Pune (2025-present)
- PG-DBDA (Big Data Analytics) — CDAC NOIDA (2022-2023), CGPA 7.3/10
- B.E. Mechanical Engineering — Deogiri Institute, Aurangabad (2017-2021), CGPA 7.9/10

WORK EXPERIENCE:
1. Data Analyst Intern — HiCounselor (Remote, Aug 2022 – Feb 2023)
   - Built ensemble ML models for weather prediction using Python and Seaborn
   - Cleaned, analyzed and visualized large geographical and climatic datasets
   - Delivered end-to-end analytics project independently in remote setting

2. Engineering Intern — Eminent Engineering Endeavours, Aurangabad (Aug 2021 – Sep 2022)
   - Studied manufacturing processes including 3D printing and additive manufacturing
   - Applied mechanical engineering principles in startup operations environment

3. Freelance Data Project — Saudi Commission for Health Specialties (Remote, Jul 2023)
   - Delivered baseline information retrieval model for team of engineers and data scientists
   - Ensured reproducibility and consistent benchmarking across experiments

4. Mathematics Tutor — Private, Aurangabad (Aug 2023 – Aug 2025)
   - Independently managed tutoring operation for 2 years

KEY PROJECT:
- SAE BAJA: Designed and manufactured suspension system for all-terrain vehicle
  Second-in-command of suspension department, national M-BAJA competition

CERTIFICATIONS:
- BCG Strategy Consulting Job Simulation (Forage)
- Power BI Data Analysis & Visualization (Coursera/Udemy)
- Google Sheets stock comparison with dynamic data feeds (Coursera)

TECHNICAL SKILLS:
Python, Power BI, SQL (basic), Excel (advanced), Machine Learning,
Seaborn, Pandas, scikit-learn

BUSINESS SKILLS:
Process optimization, data-driven decision making, strategic thinking,
analytical reasoning, engineering rigor, team leadership

UNIQUE ANGLE:
Mechanical engineering foundation + advanced data analytics + MBA =
understands operations on the floor AND can quantify and improve them through data.

TARGET: 2-month paid MBA internship in Operations, Supply Chain, or Strategy Consulting
"""

SEARCH_TERMS = [
    #"MBA Operations Intern",
    #"Operations Internship MBA stipend",
    #"Supply Chain Intern MBA",
    #"Strategy Operations Intern paid",
    #"Management Trainee",
    #"Process Optimization intern",
    #"Process Optimization Trainee",
    #"Operations Analyst Trainee",
    #"Operations Research intern",
    "Data scientist",
    "Power Bi Devloper"
]

client = Groq(api_key=GROQ_API_KEY)

# ============================================================
#  CONNECT TO GOOGLE SHEETS
# ============================================================

HEADERS = [
    "Company", "Role", "Link", "Stipend", "Fit Score",
    "Fit Reasoning", "Company Intel", "Key Angle",
    "Status", "Date Found", "Follow-up Date", "Cover Letter", "Notes"
]

def connect_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds    = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    gc       = gspread.authorize(creds)
    sheet    = gc.open(SHEET_NAME).sheet1

    # Add headers if sheet is empty
    if sheet.row_count == 0 or sheet.cell(1, 1).value != "Company":
        sheet.insert_row(HEADERS, 1)
        print("  ✓ Headers added to sheet")

    return sheet


def load_existing_links(sheet):
    try:
        links = sheet.col_values(3)  # Column C = Link
        return set(links[1:])        # Skip header
    except:
        return set()


def push_to_sheet(sheet, jobs_list):
    for job in jobs_list:
        row = [job.get(h, "") for h in HEADERS]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        time.sleep(0.5)  # avoid Google API rate limit
    print(f"  ✓ Pushed {len(jobs_list)} rows to Google Sheets")


# ============================================================
#  JOB SEARCH + FILTER
# ============================================================
SEARCH_LOCATIONS = ["India", "Remote"]

def search_jobs():
    print("\n🔍 Searching LinkedIn, Indeed, Glassdoor...")
    import pandas as pd
    all_jobs = []
    for location in SEARCH_LOCATIONS:
        for term in SEARCH_TERMS:
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin", "indeed", "glassdoor","zip_recruiter"],
                    search_term=term,
                    location=location,
                    results_wanted=30,
                    hours_old=48,
                    country_indeed="INDIA",
                    linkedin_fetch_description=True
                    )
                if len(jobs) > 0:
                        all_jobs.append(jobs)
                        print(f"  ✓ '{term}' → {len(jobs)} results")
                time.sleep(2)
            except Exception as e:
                print(f"  ✗ '{term}' failed: {e}")

    if not all_jobs:
        print("  ✗ No results from any platform. Check your internet connection.")
        return pd.DataFrame()
    combined = pd.concat(all_jobs, ignore_index=True).drop_duplicates(subset=["job_url"])
    print(f"  Total unique: {len(combined)}")
    return combined


def filter_jobs(jobs):
    print("\n🎯 Filtering for paid ops roles...")
    role_kw  = ["operations", "ops", "supply chain", "strategy", "mba"]
    pay_kw   = ["stipend", "paid", "compensation", "$", "salary"]
    excl_kw  = ["senior manager", "director", "vp ", "10+ years", "vice president"]

    def is_good(row):
        text = (str(row.get("description","")) + " " + str(row.get("title",""))).lower()
        return (any(k in text for k in role_kw) and
                any(k in text for k in pay_kw)  and
                not any(k in text for k in excl_kw))

    filtered = jobs[jobs.apply(is_good, axis=1)]
    print(f"  Kept {len(filtered)} after filtering")
    return filtered


# ============================================================
#  AGENT 1 — RESEARCHER
# ============================================================

def agent_1_researcher(company, role, description):
    print(f"\n  🔎 Agent 1 researching {company}...")
    snippets = []

    with DDGS() as ddgs:
        for q in [f"{company} operations 2025",
                  f"{company} MBA internship",
                  f"{company} supply chain news"]:
            try:
                results = list(ddgs.text(q, max_results=3))
                for r in results:
                    snippets.append(f"• {r['title']}: {r['body'][:250]}")
                time.sleep(1)
            except Exception as e:
                print(f"    Search warning: {e}")

    web_intel = "\n".join(snippets[:9]) or "No web results found."

    prompt = f"""You are a sharp MBA career researcher.

CANDIDATE PROFILE:
{MY_PROFILE}

COMPANY: {company}
ROLE: {role}
JOB DESCRIPTION: {description[:600]}

WEB RESEARCH:
{web_intel}

Reply in EXACTLY this format:

COMPANY_INTEL:
[2-3 specific facts about {company}'s operations or recent moves]

FIT_SCORE: [1-10 only]

FIT_REASONING:
[2-3 sentences on why candidate is a strong or weak match]

KEY_ANGLE:
[One sentence: the strongest hook for the cover letter]"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=450
    )
    brief = res.choices[0].message.content
    match = re.search(r"FIT_SCORE:\s*(\d+)", brief)
    score = int(match.group(1)) if match else 0
    print(f"  📊 Fit score: {score}/10")
    return brief, score


# ============================================================
#  AGENT 2 — WRITER
# ============================================================

def agent_2_writer(company, role, description, research_brief):
    print(f"  ✍️  Agent 2 writing cover letter...")

    prompt = f"""You are an expert MBA cover letter writer.

CANDIDATE PROFILE:
{MY_PROFILE}

ROLE: {role} at {company}
JOB DESCRIPTION: {description[:600]}

RESEARCHER'S BRIEF:
{research_brief}

Write a cover letter:
- Exactly 3 paragraphs, max 250 words
- Para 1: Open with KEY_ANGLE, reference specific COMPANY_INTEL
- Para 2: Map 1-2 candidate achievements to role requirements
- Para 3: Unique value + ask for a 15-minute call
- Never write "I am excited to apply" or "I am passionate about"
- Sound like someone who did their homework

Write ONLY the letter. No commentary."""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    return res.choices[0].message.content


# ============================================================
#  HELPERS
# ============================================================

def parse_section(brief, label):
    pattern = rf"{label}:\s*(.*?)(?=\n[A-Z_]+:|$)"
    match   = re.search(pattern, brief, re.DOTALL)
    return match.group(1).strip() if match else ""


# ============================================================
#  MAIN
# ============================================================

def run():
    print("=" * 58)
    print("   MBA INTERNSHIP AGENT v3  //  → GOOGLE SHEETS")
    print("=" * 58)

    # Connect to sheet first
    print("\n📊 Connecting to Google Sheets...")
    sheet    = connect_sheet()
    existing = load_existing_links(sheet)
    print(f"  Already tracked: {len(existing)} jobs")

    jobs     = search_jobs()
    filtered = filter_jobs(jobs)

    new_jobs = []
    skipped  = skipped_score = errors = 0

    for _, row in filtered.iterrows():
        link = str(row.get("job_url", ""))
        if link in existing:
            skipped += 1
            continue

        company     = str(row.get("company",     "Unknown"))
        role        = str(row.get("title",        "Unknown"))
        description = str(row.get("description", ""))

        print(f"\n{'─'*50}")
        print(f"  {role} @ {company}")

        try:
            brief, score = agent_1_researcher(company, role, description)
            time.sleep(1)

            if score < MIN_FIT_SCORE:
                print(f"  ⏭  Skipping — score {score} below {MIN_FIT_SCORE}")
                skipped_score += 1
                continue

            letter = agent_2_writer(company, role, description, brief)
            time.sleep(1)

            new_jobs.append({
                "Company":        company,
                "Role":           role,
                "Link":           link,
                "Stipend":        str(row.get("min_amount", "Check listing")),
                "Fit Score":      f"{score}/10",
                "Fit Reasoning":  parse_section(brief, "FIT_REASONING"),
                "Company Intel":  parse_section(brief, "COMPANY_INTEL"),
                "Key Angle":      parse_section(brief, "KEY_ANGLE"),
                "Status":         "New",
                "Date Found":     datetime.now().strftime("%Y-%m-%d"),
                "Follow-up Date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "Cover Letter":   letter,
                "Notes":          ""
            })

        except Exception as e:
            print(f"  ✗ Error: {e}")
            errors += 1

    if new_jobs:
        print(f"\n📤 Pushing {len(new_jobs)} jobs to Google Sheets...")
        push_to_sheet(sheet, new_jobs)

    print(f"\n{'='*58}")
    print(f"  ✅ New jobs added      : {len(new_jobs)}")
    print(f"  ⏭  Skipped (seen)     : {skipped}")
    print(f"  📉 Skipped (low fit)  : {skipped_score}")
    print(f"  ✗  Errors             : {errors}")
    print(f"\n  Open Google Sheets on your phone to see results.")
    print(f"{'='*58}\n")


if __name__ == "__main__":
    run()
