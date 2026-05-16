# test_scraper.py
# Run from src/ folder: python3 test_scraper.py
# Output saved to test_output.txt (open in Notepad or VS Code)

from scraper import fetch_9anoun_code, fetch_9anoun_jort

OUTPUT_FILE = "test_output.txt"

lines = []

def log(text=""):
    print(text)
    lines.append(str(text))

log("=" * 60)
log("  TEST SCRAPER — 9anoun.tn")
log("=" * 60)

# ── Test 1: Code du Travail ───────────────────────────────────────
log("\nTEST 1 — Code du Travail (licenciement)")
log("-" * 60)
content, url = fetch_9anoun_code("licenciement")
log(f"URL    : {url}")
log(f"Chars  : {len(content)}")
log(f"\nContenu:\n{content[:800]}")

# ── Test 2: Code des Obligations ─────────────────────────────────
log("\n" + "=" * 60)
log("TEST 2 — Code des Obligations (contrat)")
log("-" * 60)
content, url = fetch_9anoun_code("contrat")
log(f"URL    : {url}")
log(f"Chars  : {len(content)}")
log(f"\nContenu:\n{content[:800]}")

# ── Test 3: JORT récent ───────────────────────────────────────────
log("\n" + "=" * 60)
log("TEST 3 — JORT (travail)")
log("-" * 60)
content, url = fetch_9anoun_jort("travail")
log(f"URL    : {url}")
log(f"Chars  : {len(content)}")
log(f"\nContenu:\n{content[:800]}")

# ── Test 4: Code Pénal ───────────────────────────────────────────
log("\n" + "=" * 60)
log("TEST 4 — Code de Procédure (délai)")
log("-" * 60)
content, url = fetch_9anoun_code("délai")
log(f"URL    : {url}")
log(f"Chars  : {len(content)}")
log(f"\nContenu:\n{content[:800]}")

# ── Save to file ──────────────────────────────────────────────────
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

log("\n" + "=" * 60)
log(f"✅ Résultats sauvegardés dans : {OUTPUT_FILE}")
log("   Ouvrez ce fichier dans VS Code ou Notepad pour lire l'arabe.")
log("=" * 60)
