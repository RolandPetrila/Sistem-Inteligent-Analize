"""
preflight_check.py — Verificare LIVE a tuturor conexiunilor INAINTE de o analiza.

De ce exista: cardul "Health Status" din dashboard e un snapshot usor (chei configurate),
NU un test real de conectivitate la fiecare sursa. Acest script apeleaza efectiv fiecare
sursa prin serviciul real (POST /api/settings/test/{service} — ruleaza IN serviciu, cu
cheile de PRODUCTIE, nu din shell) si spune clar GATA / NU E GATA.

Uz:
    python tools/preflight_check.py
    (sau dublu-click pe "Verifica conexiuni RIS" de pe desktop)

Exit code: 0 = toate CRITICE OK (gata de executie) · 1 = ceva critic e picat · 2 = serviciul e jos.

Cheia X-RIS-Key vine din settings (in memorie), NICIODATA afisata (R-SEC).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import httpx

    from backend.config import settings
except Exception as e:  # pragma: no cover
    print(f"Eroare import (ruleaza din folderul proiectului): {e}")
    sys.exit(2)

BASE = "http://127.0.0.1:8001"
KEY = getattr(settings, "ris_api_key", "") or ""
H = {"X-RIS-Key": KEY} if KEY else {}

# Categorii — verdictul de "gata de executie" se bazeaza DOAR pe CRITICE.
PROVIDERS_AI = ["groq", "gemini", "mistral", "cerebras"]        # lantul de sinteza (fallback)
SURSE_PRINCIPALE = ["anaf_tva", "anaf_bilant", "bnr", "openapi_ro", "seap", "tavily"]
SURSE_SECUNDARE = ["monitorul_oficial", "sanctions", "eurostat", "brave", "jina", "google_maps", "just"]
# Moarte extern, NEreparabile din cod — absenta lor NU blocheaza o analiza.
CUNOSCUTE_MOARTE = {"bpi", "ins_tempo", "aegrm"}

# CRITIC = macar un provider AI + sursele oficiale de baza. Fara ANAF/BNR nu ai analiza reala.
CRITICE = {"anaf_tva", "anaf_bilant", "bnr", "openapi_ro"}


def _test(client: httpx.Client, svc: str) -> tuple[bool, str]:
    try:
        r = client.post(f"{BASE}/api/settings/test/{svc}", headers=H, timeout=45)
        j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        ok = bool(j.get("success") or j.get("ok") or j.get("status") == "ok")
        msg = j.get("message") or j.get("detail") or j.get("error") or j.get("status") or ""
        return ok, (msg[:66] if isinstance(msg, str) else "")
    except Exception as e:
        return False, str(e)[:66]


def _claude_ready() -> tuple[bool, str]:
    """Claude nu are endpoint /test (e subproces). Verificare usoara a setup-ului:
    calea CLI + fisierul de credentiale Max exista. Testul DEFINITIV e o analiza reala."""
    cli = settings.claude_cli_path or ""
    creds = Path.home() / ".claude" / ".credentials.json"
    cli_ok = bool(cli) and Path(cli).exists()
    creds_ok = creds.exists()
    if cli_ok and creds_ok:
        return True, "CLI + login Max prezente (test definitiv = o analiza reala)"
    if not cli_ok:
        return False, "CLAUDE_CLI_PATH lipsa/gresit in .env"
    return False, "login Max lipsa (~/.claude/.credentials.json) — deschide Claude Code si logheaza-te"


def _section(client, title, services):
    print(f"\n{title}")
    results = {}
    for svc in services:
        ok, msg = _test(client, svc)
        results[svc] = ok
        mark = "[ OK ]" if ok else ("[MOART]" if svc in CUNOSCUTE_MOARTE else "[PICAT]")
        print(f"  {mark} {svc:<18} {msg}")
    return results


def main() -> int:
    print("=" * 64)
    print("  RIS — VERIFICARE CONEXIUNI (LIVE, prin serviciu)")
    print("=" * 64)

    # 0. Serviciul raspunde?
    try:
        h = httpx.get(f"{BASE}/api/health", timeout=8)
        if h.status_code != 200:
            print(f"\n[X] Serviciul RIS raspunde cu HTTP {h.status_code}. Porneste-l intai.")
            return 2
    except Exception:
        print("\n[X] Serviciul RIS (localhost:8001) NU raspunde. Porneste-l (dublu-click pe starter) si reincearca.")
        return 2
    print("\n[ OK ] Serviciul RIS raspunde (localhost:8001)")

    all_ok = {}
    with httpx.Client() as client:
        # Claude (subproces, verificare setup)
        c_ok, c_msg = _claude_ready()
        print("\nSINTEZA — Claude Opus (scrie raportul final)")
        print(f"  {'[ OK ]' if c_ok else '[PICAT]'} {'claude_cli':<18} {c_msg}")

        all_ok.update(_section(client, "PROVIDERI AI (fallback sinteza)", PROVIDERS_AI))
        all_ok.update(_section(client, "SURSE PRINCIPALE (oficiale, folosite mereu)", SURSE_PRINCIPALE))
        all_ok.update(_section(client, "SURSE SECUNDARE (folosite cand exista date)", SURSE_SECUNDARE))

    # Verdict — bazat DOAR pe critice + macar un provider AI + Claude/AI pt sinteza
    critice_jos = [s for s in CRITICE if not all_ok.get(s, False)]
    ai_up = [p for p in PROVIDERS_AI if all_ok.get(p, False)]
    sinteza_ok = c_ok or bool(ai_up)  # Claude SAU macar un fallback
    moarte = [s for s in CUNOSCUTE_MOARTE if not all_ok.get(s, True)]

    print("\n" + "=" * 64)
    if not critice_jos and sinteza_ok:
        print("  ✓ GATA DE EXECUTIE — toate sursele critice si sinteza sunt conectate.")
        code = 0
    else:
        print("  ! ATENTIE — NU porni o analiza importanta acum:")
        if critice_jos:
            print(f"      surse critice picate: {', '.join(critice_jos)}")
        if not sinteza_ok:
            print("      sinteza indisponibila: nici Claude, nici vreun provider AI de rezerva")
        code = 1
    _ = moarte  # calculat pt claritate; lista fixa oricum netestata (mereu jos)
    print(f"  (normal, ignora) moarte extern nereparabile: {', '.join(sorted(CUNOSCUTE_MOARTE))}")
    print("=" * 64)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
