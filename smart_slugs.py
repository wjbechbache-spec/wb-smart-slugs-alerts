import requests, smtplib, json, os
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GAMMA_URL = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&order=volume24hr&ascending=false"

SERIOUS_KEYWORDS = ["uk", "britain", "england", "parliament", "commons", "lords", "prime minister", "bank of england", "inflation", "gdp", "election", "law", "bill", "ftse", "boe"]

BANNED_KEYWORDS = ["elon", "meme", "tiktok", "mrbeast", "tweet", "dogecoin"]

# --- NOUVEAU : BLACKLIST TIER C (US Local) ---
TIER_C_BLACKLIST = ["governor", "mayor", "city-council", "house-distr", "texas-senate", "senate-election-winner", "kansas-senate", "ohio-senate"]

SEEN_FILE = "seen_slugs.json"

def is_smart(event):
    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()
    slug = (event.get("slug") or "").lower()
    
    text = f"{title} {desc} {slug}"

    # 1. Bloque Tier C US Local
    if any(k in text for k in TIER_C_BLACKLIST):
        return False

    # 2. Bloque BANNED
    if any(k in text for k in BANNED_KEYWORDS):
        return False

    # 3. Garde SMART
    if any(k in text for k in SERIOUS_KEYWORDS):
        return True
    
    return False

def main():
    # Charge historique
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            seen_slugs = set(json.load(f))
    else:
        seen_slugs = set()

    print(f"Fetching {GAMMA_URL}")
    r = requests.get(GAMMA_URL, timeout=20)
    r.raise_for_status()
    events = r.json()

    new_slugs = []
    for ev in events:
        slug = ev.get("slug")
        if not slug:
            continue
        if slug in seen_slugs:
            continue
        if is_smart(ev):
            new_slugs.append(ev)

    if not new_slugs:
        print("Aucun nouveau slug SMART à fort impact")
        return

    # Prépare email
    body = f"Nouveaux SMART slugs trouvés ({len(new_slugs)}):\n\n"
    for ev in new_slugs:
        body += f"- {ev.get('title')} | slug: {ev.get('slug')} | vol: {ev.get('volume24hr', 'N/A')}\nhttps://polymarket.com/event/{ev.get('slug')}\n\n"

    print(body)

    # Envoi email
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_PASS")
    if gmail_user and gmail_pass:
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = gmail_user
        msg['Subject'] = f"[SMART ALERT] {len(new_slugs)} nouveaux slugs"
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
        print("Email envoyé")
    else:
        print("GMAIL secrets non configurés")

    # Sauvegarde historique
    seen_slugs.update([e.get("slug") for e in new_slugs])
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_slugs), f, indent=2)

if __name__ == "__main__":
    main()
