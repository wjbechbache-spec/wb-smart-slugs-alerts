import os, json, requests, smtplib
from email.mime.text import MIMEText
from datetime import datetime

GAMMA_URL = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false"
SEEN_FILE = "seen_slugs.json"

# Tes mots-clés (garde les tiens)
SERIOUS_KEYWORDS = ["presidential", "election", "senate", "house", "prime minister", "israel", "russia", "ukraine", "brazil"]
BANNED_KEYWORDS = ["nfl", "cfb", "football", "basketball"]

def is_smart(event):
    text = (event.get("title","") + " " + event.get("slug","")).lower()
    if any(k in text for k in BANNED_KEYWORDS):
        return False
    if any(k in text for k in SERIOUS_KEYWORDS):
        return True
    return False

def main():
    # 1. Charge l'historique
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            seen_slugs = set(json.load(f))
    else:
        seen_slugs = set()
    
    print(f"Fetching {GAMMA_URL} - {len(seen_slugs)} already seen")
    r = requests.get(GAMMA_URL, timeout=20)
    r.raise_for_status()
    events = r.json()

    all_slugs = []
    new_slugs = []
    for ev in events:
        if not is_smart(ev):
            continue
        slug = ev.get("slug")
        if not slug:
            continue
        all_slugs.append(slug)
        if slug not in seen_slugs:
            new_slugs.append(ev)

    print(f"Found {len(all_slugs)} SMART, {len(new_slugs)} NEW")

    # 2. Si rien de nouveau, on sauvegarde quand même tout pour ne pas répéter
    # On met à jour la mémoire avec TOUS les slugs vus
    seen_slugs.update(all_slugs)
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(list(seen_slugs)), f, indent=2)
    
    print(f"Saved {len(seen_slugs)} slugs to {SEEN_FILE}")

    if not new_slugs:
        print("No new slugs, no email")
        return

    # 3. Envoie l'email seulement pour les vrais nouveaux
    body = f"Nouveaux SMART slugs trouvés ({len(new_slugs)}):\n\n"
    for ev in new_slugs[:20]:
        vol = ev.get("volume", "N/A")
        slug = ev.get("slug")
        title = ev.get("title")
        body += f"- {title} | slug: {slug} | vol: {vol}\nhttps://polymarket.com/event/{slug}\n\n"

    msg = MIMEText(body)
    msg["Subject"] = f"[SMART ALERT] {len(new_slugs)} nouveaux slugs"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_FROM"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)
    print("Email sent")

if __name__ == "__main__":
    main()
