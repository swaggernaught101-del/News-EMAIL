import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=Brisbane&hl=en-AU&gl=AU&ceid=AU:en",
    "https://news.google.com/rss/search?q=Queensland+news&hl=en-AU&gl=AU&ceid=AU:en",
    "https://news.google.com/rss/search?q=Brisbane+City+Council&hl=en-AU&gl=AU&ceid=AU:en",
]

MAX_ITEMS = 8
REQUEST_TIMEOUT = 12


def fetch_feed_items() -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    seen_links = set()

    for feed_url in RSS_FEEDS:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            link = entry.get("link", "").strip()
            title = entry.get("title", "Untitled").strip()
            published = entry.get("published", "")

            if not link or link in seen_links:
                continue

            seen_links.add(link)
            items.append({"title": title, "link": link, "published": published})

    return items[:MAX_ITEMS]


def extract_article_text(url: str) -> str:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        doc = Document(response.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "html.parser")
        text = " ".join(soup.stripped_strings)
        return text
    except Exception:
        return ""


def summarize_text(text: str, title: str) -> str:
    if not text:
        return f"No full article text available. Headline suggests: {title}."

    words = text.split()
    snippet = " ".join(words[:70])
    return snippet + ("..." if len(words) > 70 else "")


def build_digest(items: List[Dict[str, str]]) -> str:
    if not items:
        return "No Brisbane news items were found today."

    lines = ["Good morning! Here's your Brisbane news digest:\n"]

    for idx, item in enumerate(items, start=1):
        article_text = extract_article_text(item["link"])
        summary = summarize_text(article_text, item["title"])

        lines.append(f"{idx}. {item['title']}")
        if item["published"]:
            lines.append(f"   Published: {item['published']}")
        lines.append(f"   Summary: {summary}")
        lines.append(f"   Link: {item['link']}\n")

    lines.append("Have a great day! ☀️")
    return "\n".join(lines)


def send_email(subject: str, body: str) -> None:
    email_from = os.getenv("EMAIL_FROM")
    email_to = os.getenv("EMAIL_TO")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    required = {
        "EMAIL_FROM": email_from,
        "EMAIL_TO": email_to,
        "SMTP_USER": smtp_user,
        "SMTP_PASSWORD": smtp_password,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    msg = MIMEMultipart()
    msg["From"] = email_from
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(email_from, [email_to], msg.as_string())


def main() -> None:
    items = fetch_feed_items()
    digest = build_digest(items)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    subject = f"Brisbane News Digest - {today}"
    send_email(subject, digest)


if __name__ == "__main__":
    main()
