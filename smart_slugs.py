import requests, os, smtplib, json
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

POLY_API = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&order=volume24hr&ascending=false"
MIN_VOLUME = 10000
MIN_LIQUIDITY = 5000
DAYS_MIN = 7
DAYS_MAX = 90

SERIOUS_KEYWORDS = ["uk", "britain", "england", "parliament", "commons", "lords", "prime minister", "bank of england", "inflation", "gdp", "election", "law", "bill", "ftse", "boe"]
BANNED_KEYWORDS = ["elon", "meme", "tiktok", "mrbeast", "tweet", "dogecoin"]

# --- NOUVEAU : BLACKLIST TIER C (US Local) ---
TIER_C_BLACKLIST = ["governor", "mayor", "city-council", "house-district", "state-senate", "california-governor", "texas-senate"]

SEEN_FILE = "seen_slugs.json"

def is_smart(event):
    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()
    slug = (event.get("slug") or "").lower()
    volume = float(event.get("volume", 0) or 0)
    liquidity = float(event.get("liquidity", 0) or 0)
    end_date_str = event.get("endDate")

    # 1. BLOQUE TIER C EN PRIORITÉ (même si volume $41M)
    if any(kw in slug or kw in title for kw in TIER_C_BLACKLIST):
        return False, f"Tier C - Local US bloque ({slug})"

    if not any(k in title for k in SERIOUS_KEYWORDS): return False, "Pas UK/sérieux"
    if any(b in title for b in BANNED_KEYWORDS): return False, "Banni"
    if volume < MIN_VOLUME or liquidity < MIN_LIQUIDITY: return False, f"Vol {volume} / Liq {liquidity} faible"
    if len(desc) < 50: return False, "Pas de règles"
    try:
        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        delta = (end_date - datetime.now(timezone.utc)).days
        if not (DAYS_MIN <= delta <= DAYS_MAX): return False, f"Hors délai {delta}j"
    except: return False, "Pas de date"
    return True, "SMART OK - Tier A/B"

def send_email(new_events):
    user = os.getenv("EMAIL_USER")
    pwd = os.getenv("EMAIL_APP_PASSWORD")
    if not user or not pwd: return
    msg = MIMEMultipart()
    msg["From"] = user; msg["To"] = user
    msg["Subject"] = f"[SMART SLUGS] {len(new_events)} nouveaux - {datetime.now().strftime('%d/%m %H:%M')}"
    body = "Bonjour Waguih,\n\nNouveaux slugs SMART (Specifique, Mesurable, Acceptable, Realiste, Timeble) :\n\n"
    for ev in new_events:
        body += f"✅ {ev['title']}\n Slug: {ev['slug']}\n Vol: ${ev.get('volume',0):,.0f} | Liq: ${ev.get('liquidity',0):,.0f}\n Fin: {ev.get('endDate')}\n Lien: https://polymarket.com/event/{ev['slug']}\n\n"
    body += "\n-- Bot wb-smart-slugs-alerts (2h) - Tier A/B only"
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, pwd); server.send_message(msg)

def main():
    events = requests.get(POLY_API, timeout=20).json()
    seen = set(json.load(open(SEEN_FILE))) if os.path.exists(SEEN_FILE) else set()
    new_smart = []
    for ev in events:
        slug = ev.get("slug")
        if not slug or slug in seen: continue
        ok, reason = is_smart(ev)
        if ok: new_smart.append(ev); seen.add(slug)
    if new_smart:
        send_email(new_smart)
        with open(SEEN_FILE, "w") as f: json.dump(list(seen)[-500:], f)

if __name__ == "__main__": main()
