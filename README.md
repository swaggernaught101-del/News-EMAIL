# Brisbane News Email Automation

This repository sends a **daily 9:30am Brisbane-time email** with summarized local news.

## What it does
- Pulls recent Brisbane-focused news items from Google News RSS feeds.
- Extracts article text where possible.
- Builds concise bullet-point summaries.
- Emails you the digest automatically every day at **09:30 Australia/Brisbane**.

## Setup

### 1) Add GitHub Actions secrets
In your GitHub repo, go to **Settings → Secrets and variables → Actions** and add:

- `EMAIL_FROM` – sender address (your Gmail address)
- `EMAIL_TO` – recipient address
- `SMTP_USER` – SMTP username (usually same as sender)
- `SMTP_PASSWORD` – SMTP app password
- `SMTP_HOST` – e.g. `smtp.gmail.com`
- `SMTP_PORT` – e.g. `587`

> For Gmail, create an App Password and use that in `SMTP_PASSWORD`.

### 2) Push this repository to GitHub
The workflow runs on GitHub Actions, so the code must be in a GitHub repo.

### 3) (Optional) Run locally to test
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python news_digest.py
```

## Schedule details
The workflow is configured with:
- Cron: `30 23 * * *` (UTC)
- Timezone conversion: **23:30 UTC = 09:30 Australia/Brisbane** (AEST, UTC+10)

If you ever need daylight-saving-aware schedules for other regions, adjust the cron accordingly.

## Files
- `news_digest.py` – fetches, summarizes, and emails the digest.
- `.github/workflows/daily-brisbane-news.yml` – daily scheduled automation.
- `requirements.txt` – Python dependencies.
