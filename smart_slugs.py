import requests, smtplib, json, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GAMMA_URL = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&order=volume24hr&ascending=false"
SEEN_FILE = "seen_slugs.json"

SERIOUS_KEYWORDS = ["election", "president", "senate", "house", "prime minister", "israel", "russia", "ukraine", "brazil", "midterms"]
BANNED_KEYWORDS = ["nfl", "cfb", "football"]

def is_smart(event):
    text = (event.get("title","") + " " + event.get("slug","")).lower()
    if any(k in text for k in BANNED_KEYWORDS):
        return False
    if any(k in text for k in SERIOUS_KEYWORDS):
        return True
    return False

def main():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                seen = set(json.load(f))
        except:
            seen = set()
    else:
        seen = set()

    print(f"Fetching {GAMMA_URL} - {len(seen)} already seen")
    r = requests.get(GAMMA_URL, timeout=20)
    r.raise_for_status()
    events = r.json()

    new_slugs = []
    current_slugs = []
    for ev in events:
        if not is_smart(ev): continue
        slug = ev.get("slug")
        if not slug: continue
        current_slugs.append(slug)
        if slug not in seen:
            new_slugs.append(ev)

    print(f"Found {len(current_slugs)} SMART, {len(new_slugs)} NEW")
    
    # SAUVEGARDE TOUJOURS, même si 0 nouveau
    all_seen = seen.union(set(current_slugs))
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(list(all_seen)), f, indent=2)
    print(f"Saved {len(all_seen)} slugs to {SEEN_FILE}")

    if not new_slugs:
        print("No new slugs, no email")
        return

    # Email avec les bons noms de secrets
    gmail_user = os.getenv("GMAIL_USER") or os.getenv("EMAIL_FROM")
    gmail_pass = os.getenv("GMAIL_PASS") or os.getenv("GMAIL_APP_PASSWORD")
    email_to = os.getenv("EMAIL_TO") or gmail_user

    if not gmail_user or not gmail_pass:
        print("No email creds, skip sending")
        return

    body = f"Nouveaux SMART slugs trouvés ({len(new_slugs)}):\n\n"
    for ev in new_slugs[:20]:
        body += f"- {ev.get('title')} | slug: {ev.get('slug')} | vol: {ev.get('volume','N/A')}\nhttps://polymarket.com/event/{ev.get('slug')}\n\n"

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = email_to
    msg["Subject"] = f"[SMART ALERT] {len(new_slugs)} nouveaux slugs"
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
    print("Email sent")

if __name__ == "__main__":
    main()
