# 🤖 MBA Internship Agent

Automated internship search and cover letter generation system built with Python and AI.

## What it does
- Searches LinkedIn, Indeed, Glassdoor daily for MBA ops internships
- Agent 1 researches each company and scores candidate fit (1-10)
- Agent 2 writes a tailored cover letter based on the research
- Skips jobs below fit score threshold automatically
- Pushes all results to Google Sheets — viewable on phone

## Stack
- Python
- JobSpy — job scraping
- Groq API / Llama 3.3 — AI brain (free)
- DuckDuckGo — company research
- Google Sheets API — output

## Setup
1. Clone the repo
2. Add your keys to .env
3. pip install -r requirements_v3.txt
4. python internship_agent_v3.py

## Built by
Wasequddin Kazi