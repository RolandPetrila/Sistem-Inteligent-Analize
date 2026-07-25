"""§6 — Test lunar de validitate a modelelor AI.

Tiparul "premisa care expira, netestata" a lovit RIS de mai multe ori (Qwen retras de
Cerebras, Llama-4-Scout retras de Groq, Llama-3.1-405B retras de SambaNova). Modelele AI
se schimba LUNAR. Acest script, rulat periodic, confirma ca fiecare model din
`backend/agents/ai_models.py` inca exista in catalogul providerului (GET /v1/models).

Utilizare:
    python tools/check_ai_models.py           # raport + exit code (0 = tot OK, 1 = probleme)

NU se pune in RIS_TEST.bat (ar face suita flaky si ar consuma cota live). Logica PURA
(`check_model_against_catalog`) e testata separat in tests/ cu cataloage mock + un nume
fals injectat (dovada de non-vacuitate — vezi tests/test_ai_models_config.py).

Securitate: NU afiseaza NICIODATA valori de chei. Doar nume de model + prezent/absent.
"""

from __future__ import annotations

import os
import sys

# Permite rularea ca script (python tools/check_ai_models.py) — adauga radacina proiectului.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents import ai_models  # noqa: E402


def catalog_url_for(cfg: dict) -> str | None:
    """Deriveaza URL-ul de listare a modelelor din endpoint-ul de chat al providerului."""
    kind = cfg.get("endpoint_kind")
    if kind == "claude_cli":
        return None  # Claude prin CLI/Max — fara catalog REST
    if kind == "gemini":
        return "https://generativelanguage.googleapis.com/v1beta/models"
    url = cfg.get("url") or ""
    # openai_compat: .../chat/completions -> .../models
    if "/chat/completions" in url:
        return url.replace("/chat/completions", "/models")
    return None


def check_model_against_catalog(provider: str, model: str, catalog: list[str]) -> dict:
    """PURA (testabila): modelul din config apare in catalogul live?
    `catalog` = lista de id-uri de model returnata de provider. Returneaza un verdict."""
    present = model in set(catalog or [])
    return {
        "provider": provider,
        "model": model,
        "present": present,
        "catalog_size": len(catalog or []),
        "status": "OK" if present else "LIPSA_IN_CATALOG",
    }


def _fetch_catalog(provider: str, cfg: dict, api_key: str) -> tuple[list[str] | None, str | None]:
    """Live GET al catalogului. Returneaza (lista_id_uri, eroare)."""
    import httpx

    url = catalog_url_for(cfg)
    if url is None:
        return None, "fara catalog REST (Claude CLI)"
    try:
        if cfg.get("endpoint_kind") == "gemini":
            r = httpx.get(url, headers={"x-goog-api-key": api_key}, timeout=30)
            r.raise_for_status()
            return [m.get("name", "").replace("models/", "") for m in r.json().get("models", [])], None
        r = httpx.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
        r.raise_for_status()
        return [m.get("id") for m in r.json().get("data", [])], None
    except Exception as e:
        return None, str(e)[:200]


def _sambanova_responds(cfg: dict, api_key: str) -> bool | None:
    """§6: pt providerii temporary_free (SambaNova) — mai raspunde? (creditul poate fi consumat)."""
    import httpx

    try:
        r = httpx.post(
            cfg["url"],
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": cfg["model"], "messages": [{"role": "user", "content": "1+1="}], "max_tokens": 3},
            timeout=30,
        )
        return r.status_code == 200
    except Exception:
        return False


def _read_env_key(api_key_attr: str) -> str:
    """Citeste cheia din backend.config.settings (fara a o afisa)."""
    from backend.config import settings

    return getattr(settings, api_key_attr, "") or ""


def main() -> int:
    problems = 0
    print("=== §6 Verificare validitate modele AI (GET /v1/models) ===\n")
    for provider, cfg in ai_models.AI_PROVIDERS.items():
        model = cfg["model"]
        api_key_attr = cfg.get("api_key_attr")
        if cfg.get("endpoint_kind") == "claude_cli":
            print(f"  [SKIP] {provider:11s} {model} — Claude CLI/Max, fara catalog REST")
            continue
        api_key = _read_env_key(api_key_attr) if api_key_attr else ""
        if not api_key:
            print(f"  [SKIP] {provider:11s} {model} — {api_key_attr} neconfigurat")
            continue

        catalog, err = _fetch_catalog(provider, cfg, api_key)
        if err:
            print(f"  [EROARE] {provider:11s} nu am putut lista catalogul: {err}")
            problems += 1
            continue

        verdict = check_model_against_catalog(provider, model, catalog)
        if verdict["present"]:
            extra = ""
            if cfg.get("temporary_free"):
                responds = _sambanova_responds(cfg, api_key) if provider == "sambanova" else None
                if responds is False:
                    extra = "  ⚠ temporary_free: NU mai raspunde (credit consumat?)"
                    problems += 1
                elif responds is True:
                    extra = "  (temporary_free: raspunde OK)"
            print(f"  [OK]   {provider:11s} {model} — prezent ({verdict['catalog_size']} modele){extra}")
        else:
            print(f"  [!!!]  {provider:11s} {model} — LIPSA IN CATALOG (retras?) — actualizeaza ai_models.py")
            problems += 1

    print(f"\n=== {'TOTUL OK' if problems == 0 else f'{problems} PROBLEME'} ===")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
