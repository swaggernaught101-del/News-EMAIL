# Brisbane News Email Automation

Sends a **daily 9:30 AM Brisbane-time email** with summarised local news — delivered straight to your Outlook inbox.

## What it does

- Pulls recent Brisbane/Queensland stories from Google News RSS feeds
- Extracts and summarises each article (up to ~65 words per story)
- Builds a clean, **Outlook-compatible HTML email** (with a plain-text fallback)
- Sends via Outlook SMTP every morning at **09:30 AEST** using GitHub Actions

---

## Setup

### 1. Add GitHub Actions secrets

Go to your repo **Settings → Secrets and variables → Actions** and add the following:

| Secret | Description |
|--------|-------------|
| `EMAIL_FROM` | Your Outlook address (e.g. `you@outlook.com`) |
| `EMAIL_TO` | Recipient address — comma-separate for multiple |
| `SMTP_USER` | Your Outlook login (usually same as `EMAIL_FROM`) |
| `SMTP_PASSWORD` | Your Outlook password or App Password |
| `SMTP_HOST` | *(optional)* — see table below |
| `SMTP_PORT` | *(optional)* — defaults to `587` |

#### Which SMTP host should I use?

| Account type | `SMTP_HOST` value |
|---|---|
| Personal `@outlook.com` / `@hotmail.com` / `@live.com` | `smtp-mail.outlook.com` *(default — leave secret blank)* |
| Microsoft 365 / work or school account | `smtp.office365.com` |

> **App Password (recommended):** In your Microsoft account go to
> **Security → Advanced security options → App passwords** and generate a
> dedicated password for this script. This avoids storing your main password
> and works even when two-step verification is on.

### 2. Enable SMTP AUTH on your account

For **personal Outlook.com** accounts SMTP AUTH is on by default.

For **Microsoft 365** accounts an admin may need to enable it:
*Microsoft 365 admin centre → Users → [your user] → Mail → Manage email apps →
tick "Authenticated SMTP".*

### 3. Push to GitHub

The workflow runs on GitHub Actions, so the code must live in a GitHub repository.
Once pushed, the daily schedule starts automatically.

### 4. (Optional) Run locally to test

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export EMAIL_FROM="you@outlook.com"
export EMAIL_TO="you@outlook.com"
export SMTP_USER="you@outlook.com"
export SMTP_PASSWORD="your-password-or-app-password"
# SMTP_HOST and SMTP_PORT default to Outlook personal values

python news_digest.py
```

---

## Schedule

| Setting | Value |
|---------|-------|
| Cron (UTC) | `30 23 * * *` |
| Delivery time | **09:30 AEST (UTC+10)** |

Brisbane does not observe daylight saving, so this schedule stays accurate year-round.

---

## Files

| File | Purpose |
|------|---------|
| `news_digest.py` | Fetches news, builds HTML email, sends via Outlook SMTP |
| `.github/workflows/daily-brisbane-news.yml` | Daily scheduled automation |
| `requirements.txt` | Python dependencies |
