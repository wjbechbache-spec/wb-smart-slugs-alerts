import os, json

HISTORY_FILE = "seen_slugs.json"

# Charge historique
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        seen_slugs = set(json.load(f))
else:
    seen_slugs = set()

# --- TON CODE EXISTANT QUI RÉCUPÈRE new_slugs ---
# Garde tout ton code d'avant pour récupérer depuis Polymarket

# --- NOUVEAU: FILTRE FORT IMPACT ---
def is_high_impact(slug, vol):
    low_impact_keywords = ["senate-election-winner", "house-election", "governor-winner"]
    if any(k in slug for k in low_impact_keywords):
        return vol >= 2_000_000  # Rejette Kansas 444k et Ohio 841k
    return True

# Applique les 3 filtres
truly_new = []
for item in new_slugs: # new_slugs vient de ton code existant
    if item['slug'] in seen_slugs:
        continue
    if not is_high_impact(item['slug'], item.get('volume',0)):
        print(f"Rejet faible impact: {item['slug']}")
        continue
    if item.get('tier','A') not in ['A','B']:
        continue
    truly_new.append(item)

if not truly_new:
    print("Aucun nouveau slug SMART à fort impact")
    exit(0)

# --- TON CODE D'ENVOI EMAIL avec truly_new ---

# Sauvegarde après envoi
seen_slugs.update([s['slug'] for s in truly_new])
with open(HISTORY_FILE, "w") as f:
    json.dump(list(seen_slugs), f, indent=2)
