#!/usr/bin/env python3
"""
Brisbane Daily News Digest — Outlook Email Integration
Fetches Brisbane/Queensland news and sends a formatted HTML digest via Outlook SMTP.
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BRISBANE_TZ = ZoneInfo("Australia/Brisbane")

RSS_FEEDS = [
    ("Brisbane",            "https://news.google.com/rss/search?q=Brisbane&hl=en-AU&gl=AU&ceid=AU:en"),
    ("Queensland",          "https://news.google.com/rss/search?q=Queensland+news&hl=en-AU&gl=AU&ceid=AU:en"),
    ("Brisbane City Council", "https://news.google.com/rss/search?q=Brisbane+City+Council&hl=en-AU&gl=AU&ceid=AU:en"),
]

MAX_ITEMS = 10
REQUEST_TIMEOUT = 12
FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BrisbaneNewsBot/2.0)"}


# ---------------------------------------------------------------------------
# News fetching
# ---------------------------------------------------------------------------

def fetch_feed_items() -> list[dict]:
    """Fetch and deduplicate news items from all configured RSS feeds."""
    seen: set[str] = set()
    items: list[dict] = []

    for feed_label, feed_url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            log.warning("Could not parse feed '%s': %s", feed_label, exc)
            continue

        for entry in parsed.entries:
            link = entry.get("link", "").strip()
            if not link or link in seen:
                continue

            seen.add(link)
            source = entry.get("source", {}).get("title", feed_label)
            items.append({
                "title":     entry.get("title", "Untitled").strip(),
                "link":      link,
                "published": entry.get("published", ""),
                "source":    source,
            })

            if len(items) >= MAX_ITEMS:
                return items

    return items


def extract_article_text(url: str) -> str:
    """Download a page and return its main readable text."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=FETCH_HEADERS)
        resp.raise_for_status()
        doc = Document(resp.text)
        soup = BeautifulSoup(doc.summary(), "html.parser")
        return " ".join(soup.stripped_strings)
    except Exception as exc:
        log.debug("Could not extract text from %s: %s", url, exc)
        return ""


def summarize(text: str, title: str, max_words: int = 65) -> str:
    """Return a short summary, falling back to the article title."""
    if not text:
        return title
    words = text.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + "..."


def enrich_items(items: list[dict]) -> list[dict]:
    """Add a 'summary' key to each item by fetching its article text."""
    enriched = []
    for item in items:
        log.info("  Extracting: %s", item["title"][:70])
        text = extract_article_text(item["link"])
        enriched.append({**item, "summary": summarize(text, item["title"])})
    return enriched


# ---------------------------------------------------------------------------
# Email builders
# ---------------------------------------------------------------------------

# Outlook-safe blue (matches Outlook's own brand palette)
BRAND_BLUE = "#0078D4"
ACCENT_LIGHT = "#EFF6FC"
BORDER_COLOR = "#D0E4F3"


def _item_html(index: int, item: dict) -> str:
    """Render a single news item as Outlook-compatible HTML table rows."""
    bg = "#FFFFFF" if index % 2 == 1 else "#F8FBFF"
    source_badge = (
        f'<span style="display:inline-block;background-color:{ACCENT_LIGHT};'
        f'color:{BRAND_BLUE};font-size:10px;font-weight:600;padding:1px 6px;'
        f'border-radius:2px;margin-left:6px;font-family:Calibri,Arial,sans-serif;">'
        f'{item["source"]}</span>'
        if item.get("source") else ""
    )
    pub_row = (
        f'<tr><td style="padding:0 20px 4px 20px;color:#888888;font-size:11px;'
        f'font-family:Calibri,Arial,sans-serif;">{item["published"]}</td></tr>'
        if item.get("published") else ""
    )
    return f"""
        <!--[if mso]><table width="560" cellpadding="0" cellspacing="0"><tr><td><![endif]-->
        <tr>
          <td style="background-color:{bg};border-bottom:1px solid {BORDER_COLOR};padding:0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="padding:14px 20px 6px 20px;">
                  <span style="display:inline-block;background-color:{BRAND_BLUE};color:#FFFFFF;
                               font-size:11px;font-weight:700;padding:2px 7px;border-radius:3px;
                               font-family:Calibri,Arial,sans-serif;">{index}</span>
                  {source_badge}
                </td>
              </tr>
              <tr>
                <td style="padding:4px 20px 0 20px;">
                  <a href="{item['link']}"
                     style="color:{BRAND_BLUE};font-size:15px;font-weight:700;
                            text-decoration:none;line-height:1.4;
                            font-family:Calibri,'Segoe UI',Arial,sans-serif;"
                  >{item['title']}</a>
                </td>
              </tr>
              {pub_row}
              <tr>
                <td style="padding:6px 20px 4px 20px;color:#333333;font-size:13px;
                           line-height:1.6;font-family:Calibri,'Segoe UI',Arial,sans-serif;">
                  {item['summary']}
                </td>
              </tr>
              <tr>
                <td style="padding:6px 20px 14px 20px;">
                  <a href="{item['link']}"
                     style="color:{BRAND_BLUE};font-size:12px;text-decoration:none;
                            font-family:Calibri,Arial,sans-serif;">
                    Read full article &#8250;
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!--[if mso]></td></tr></table><![endif]-->"""


def build_html_email(items: list[dict], date_str: str) -> str:
    """Return a fully Outlook-compatible HTML email string."""
    item_rows = "\n".join(_item_html(i, item) for i, item in enumerate(items, start=1))

    return f"""<!DOCTYPE html>
<html lang="en" xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:v="urn:schemas-microsoft-com:vml">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Brisbane News Digest</title>
  <!--[if mso]>
  <noscript><xml><o:OfficeDocumentSettings>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings></xml></noscript>
  <![endif]-->
  <style type="text/css">
    body, table, td, a {{ -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
    table, td {{ mso-table-lspace:0pt; mso-table-rspace:0pt; }}
    img {{ -ms-interpolation-mode:bicubic; border:0; }}
    a[x-apple-data-detectors] {{ color:inherit !important; }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:#F0F4F8;">

<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background-color:#F0F4F8;">
  <tr>
    <td align="center" style="padding:30px 10px;">

      <!--[if mso]><table width="600" cellpadding="0" cellspacing="0"><tr><td><![endif]-->
      <table width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;width:100%;background-color:#FFFFFF;
                    border-radius:6px;border:1px solid {BORDER_COLOR};">

        <!-- ===== HEADER ===== -->
        <tr>
          <td style="background-color:{BRAND_BLUE};padding:26px 30px;text-align:center;
                     border-radius:6px 6px 0 0;">
            <h1 style="margin:0;color:#FFFFFF;font-size:22px;font-weight:700;
                       letter-spacing:0.3px;
                       font-family:Calibri,'Segoe UI',Arial,sans-serif;">
              Brisbane Daily News Digest
            </h1>
            <p style="margin:6px 0 0 0;color:#CCE4F7;font-size:13px;
                      font-family:Calibri,Arial,sans-serif;">
              {date_str}
            </p>
          </td>
        </tr>

        <!-- ===== INTRO BANNER ===== -->
        <tr>
          <td style="background-color:{ACCENT_LIGHT};padding:14px 24px;
                     border-bottom:1px solid {BORDER_COLOR};">
            <p style="margin:0;color:#1A3A5C;font-size:13px;line-height:1.5;
                      font-family:Calibri,'Segoe UI',Arial,sans-serif;">
              Good morning! Here are today&#8217;s top
              <strong>{len(items)}</strong> stories from Brisbane and Queensland.
            </p>
          </td>
        </tr>

        <!-- ===== NEWS ITEMS ===== -->
        <tr>
          <td style="padding:0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              {item_rows}
            </table>
          </td>
        </tr>

        <!-- ===== FOOTER ===== -->
        <tr>
          <td style="background-color:{ACCENT_LIGHT};padding:18px 24px;text-align:center;
                     border-top:2px solid {BRAND_BLUE};border-radius:0 0 6px 6px;">
            <p style="margin:0;color:#888888;font-size:11px;line-height:1.7;
                      font-family:Calibri,Arial,sans-serif;">
              Delivered automatically every morning at 9:30 AM AEST via GitHub Actions.<br>
              News sourced from Google News RSS &#8212; Brisbane &amp; Queensland edition.
            </p>
          </td>
        </tr>

      </table>
      <!--[if mso]></td></tr></table><![endif]-->

    </td>
  </tr>
</table>

</body>
</html>"""


def build_plain_email(items: list[dict], date_str: str) -> str:
    """Return a plain-text fallback email body."""
    lines = [
        f"Brisbane Daily News Digest — {date_str}",
        "=" * 52,
        f"Good morning! Here are today's top {len(items)} stories.",
        "",
    ]
    for i, item in enumerate(items, start=1):
        lines.append(f"{i}. {item['title']}")
        if item.get("source"):
            lines.append(f"   Source:    {item['source']}")
        if item.get("published"):
            lines.append(f"   Published: {item['published']}")
        lines.append(f"   {item['summary']}")
        lines.append(f"   Link: {item['link']}")
        lines.append("")
    lines += [
        "---",
        "Delivered automatically at 9:30 AM AEST via GitHub Actions.",
        "News sourced from Google News RSS — Brisbane & Queensland.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Outlook SMTP sender
# ---------------------------------------------------------------------------

def send_email(subject: str, html_body: str, plain_body: str) -> None:
    """
    Send a multipart HTML/plain email via Outlook SMTP.

    Required environment variables:
      EMAIL_FROM    – sender address (your Outlook address)
      EMAIL_TO      – recipient address (comma-separated for multiple)
      SMTP_USER     – Outlook login (usually same as EMAIL_FROM)
      SMTP_PASSWORD – Outlook password or App Password

    Optional environment variables (with Outlook defaults):
      SMTP_HOST – defaults to smtp-mail.outlook.com  (personal @outlook.com / @hotmail.com)
                  use smtp.office365.com for Microsoft 365 / work accounts
      SMTP_PORT – defaults to 587
    """
    required = ["EMAIL_FROM", "EMAIL_TO", "SMTP_USER", "SMTP_PASSWORD"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    email_from    = os.environ["EMAIL_FROM"]
    email_to      = os.environ["EMAIL_TO"]
    smtp_user     = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    smtp_host     = os.environ.get("SMTP_HOST", "smtp-mail.outlook.com")
    smtp_port     = int(os.environ.get("SMTP_PORT", "587"))

    recipients = [addr.strip() for addr in email_to.split(",") if addr.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = email_from
    msg["To"]      = email_to
    msg["X-Mailer"] = "Brisbane-News-Digest/2.0"

    # Plain text first; email clients display the last (preferred) part that they support.
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body,  "html",  "utf-8"))

    log.info("Connecting to %s:%s …", smtp_host, smtp_port)
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.sendmail(email_from, recipients, msg.as_string())

    log.info("Email sent to: %s", email_to)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("Fetching Brisbane news feeds …")
    raw_items = fetch_feed_items()

    if not raw_items:
        log.error("No news items found. Aborting.")
        return

    log.info("Fetched %d items. Extracting article text …", len(raw_items))
    items = enrich_items(raw_items)

    now_brisbane = datetime.now(tz=BRISBANE_TZ)
    date_str = now_brisbane.strftime("%A, %d %B %Y")
    subject  = f"Brisbane News Digest — {date_str}"

    log.info("Building email …")
    html_body  = build_html_email(items, date_str)
    plain_body = build_plain_email(items, date_str)

    log.info("Sending via Outlook SMTP …")
    send_email(subject, html_body, plain_body)
    log.info("Done.")


if __name__ == "__main__":
    main()
