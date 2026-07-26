"""Single source of truth pentru configul providerilor AI (modele + limite + rute).

De ce exista: numele de modele erau hardcodate in `synthesis_providers.py::_PROVIDERS`,
`agent_synthesis.py::_PROVIDER_MAX_CONTEXT` si `agent_synthesis.py::max_json_chars` — trei
locuri, plus `lead_search.py` si `companies.py` chemau Groq direct cu un model retras.
Cand un model dispare din catalogul providerului (ex. Qwen retras de Cerebras, Llama-4-Scout
retras de Groq, Llama-3.1-405B retras de SambaNova) codul cadea TACUT pe fallback. Aici e
sursa unica; logica de sinteza citeste de aici — ZERO nume de model hardcodate in ea.

REGULA §0 (nenegociabila): fiecare `model` de mai jos a fost confirmat live in catalogul
providerului (GET /v1/models) INAINTE de a fi scris. Se re-verifica lunar cu
`tools/check_ai_models.py` (§6). Numele si limitele EXPIRA — nu le trata ca adevar fix.

Prioritatea proprietarului: DURABILITATE > calitate > simplitate > cost.
"""

from __future__ import annotations

# ── Config provideri (verificat live GET /v1/models 2026-07-25) ───────────────
# Campuri per provider:
#   model         — id-ul EXACT din catalogul providerului (§0)
#   max_context   — fereastra de context in tokens (garda §4)
#   temporary_free— True daca gratuitatea expira (SambaNova) → marcat pt monitorizare
#   api_key_attr  — atributul din backend.config.settings (None pt Claude CLI/Max)
#   url           — endpoint (None pt Claude CLI); pt gemini contine "{model}"
#   endpoint_kind — "claude_cli" | "openai_compat" | "gemini" (dispatch in synthesis)
#   json_char_budget — cate caractere de date JSON incap in prompt (ex-max_json_chars)
AI_PROVIDERS: dict[str, dict] = {
    "claude": {
        # Pilon calitate — $0 marginal prin abonamentul Max (subprocess CLI, fara API key).
        # NU se atinge subprocesul (flags/env-strip ANTHROPIC_API_KEY/effort/timeout) — doar
        # acest literal e sursa numelui de model.
        "model": "claude-opus-4-8",
        "max_context": 150_000,
        "temporary_free": False,
        "api_key_attr": None,
        "url": None,
        "endpoint_kind": "claude_cli",
        "json_char_budget": 50_000,
    },
    "openrouter": {
        # DeepSeek prin OpenRouter, PLATIT-ieftin (nu :free) — proprietarul a ales stabilitatea
        # peste gratuitate. Verificat 2026-07-25: PRESENT, pret $0.20/M in + $0.80/M out
        # (~$0.008/raport). max_context citit din `context_length` al catalogului OpenRouter.
        "model": "deepseek/deepseek-chat",
        "max_context": 163_840,
        "temporary_free": False,
        "api_key_attr": "openrouter_api_key",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "endpoint_kind": "openai_compat",
        "json_char_budget": 20_000,
    },
    "sambanova": {
        # Bonus temporar. `Meta-Llama-3.1-405B-Instruct` cerut de brief a fost RETRAS din
        # catalog (verificat 2026-07-25). SUBSTITUIT cu Meta-Llama-3.3-70B-Instruct (PRESENT,
        # gratuit, 131k) — optiunea (a) a auditorului, pana la veto explicit al proprietarului.
        # temporary_free=True: cand expira creditul, §5 (429) + §3 il scot din lant automat.
        "model": "Meta-Llama-3.3-70B-Instruct",
        "max_context": 131_072,
        "temporary_free": True,
        "api_key_attr": "sambanova_api_key",
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "endpoint_kind": "openai_compat",
        "json_char_budget": 20_000,
    },
    "gemini": {
        # Ultimul pe ambele rute (fallback autonom gratuit).
        "model": "gemini-2.5-flash",
        "max_context": 1_000_000,
        "temporary_free": False,
        "api_key_attr": "google_ai_api_key",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "endpoint_kind": "gemini",
        "json_char_budget": 400_000,
    },
    "groq": {
        # Ruta VITEZA #1. Inlocuieste `meta-llama/llama-4-scout-17b-16e-instruct` RETRAS
        # (era 404 tacut la fiecare sectiune scurta). llama-3.1-8b-instant = 14.400 req/zi
        # (vs 1.000 pe scout) — permisivitatea bate dimensiunea pe ruta de viteza.
        "model": "llama-3.1-8b-instant",
        "max_context": 131_072,
        "temporary_free": False,
        "api_key_attr": "groq_api_key",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "endpoint_kind": "openai_compat",
        "json_char_budget": 20_000,
    },
    "cerebras": {
        # Ruta VITEZA #2. max_context = 128k (docs Cerebras pt gpt-oss-120b).
        # PROVENIENTA (EXPIRA — re-verifica): "8192 free-tier cap" (blog 2026 + consultant)
        # INFIRMAT empiric 2026-07-25 — un prompt de ~17k tokens a primit 200 cu
        # total_tokens=17119, FARA trunchiere. `/v1/models` NU expune context. Rate-limit real
        # 30k tok/min => nu se poate proba >~29k pe acest tier (429 confunda cu overflow).
        # Protectia reala contra trunchierii tacite = detectia de overflow la RUNTIME (§4),
        # nu acest numar static.
        "model": "gpt-oss-120b",
        "max_context": 128_000,
        "temporary_free": False,
        "api_key_attr": "cerebras_api_key",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "endpoint_kind": "openai_compat",
        "json_char_budget": 20_000,
    },
    "mistral": {
        # Ruta VITEZA #3 (fallback european).
        "model": "mistral-small-latest",
        "max_context": 128_000,
        "temporary_free": False,
        "api_key_attr": "mistral_api_key",
        "url": "https://api.mistral.ai/v1/chat/completions",
        "endpoint_kind": "openai_compat",
        "json_char_budget": 20_000,
    },
}

# ── Rute (LANTURI ORDONATE — fallback SECVENTIAL, ordinea e REALA) ─────────────
# CALITATE (rapoarte profunde): Claude pilon → DeepSeek(OpenRouter) → SambaNova(bonus) → Gemini
QUALITY_CHAIN: list[str] = ["claude", "openrouter", "sambanova", "gemini"]
# VITEZA (rapoarte rapide): Groq → Cerebras(garda §4) → Mistral → Gemini
SPEED_CHAIN: list[str] = ["groq", "cerebras", "mistral", "gemini"]

# Prag garda de context §4: sari providerul daca promptul > 90% din max_context
CONTEXT_GUARD_RATIO = 0.90


# ── Accesori ──────────────────────────────────────────────────────────────────
def get_provider(name: str) -> dict:
    """Ridica KeyError daca providerul nu e in config (fail loud, nu tacut)."""
    return AI_PROVIDERS[name]


def get_model(name: str) -> str:
    return AI_PROVIDERS[name]["model"]


def get_max_context(name: str) -> int:
    return AI_PROVIDERS[name].get("max_context", 12_000)


def get_json_char_budget(name: str) -> int:
    return AI_PROVIDERS[name].get("json_char_budget", 15_000)


# ── §4: estimare tokeni + garda de context ────────────────────────────────────
def estimate_tokens(text: str) -> int:
    """tiktoken cl100k_base daca e disponibil, altfel len/4 (aproximare)."""
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return len(text) // 4


def exceeds_context(provider: str, prompt: str) -> tuple[bool, int, int]:
    """True daca promptul depaseste 90% din max_context al providerului.
    Returneaza (depaseste, tokeni_estimati, limita_efectiva)."""
    est = estimate_tokens(prompt)
    limit = int(get_max_context(provider) * CONTEXT_GUARD_RATIO)
    return est > limit, est, limit


# ── §3/§4/§5: clasificare erori (distinge "retras" / "cota" / "overflow" / "esec") ─
_GONE_MARKERS = (
    "model_not_found",
    "model_not_available",
    "model not found",
    "decommissioned",
    "does not exist",
    "no such model",
    "has been deprecated",
)
_QUOTA_MARKERS = (
    "rate_limit",
    "rate limit",
    "quota",
    "resource_exhausted",
    "too many requests",
    "insufficient_quota",
)
# §5b — PLATA/CREDIT (distinct de cota): creditul PLATIT s-a epuizat. Masurat real
# 2026-07-25 la DeepSeek direct: `402 + "Insufficient Balance"`. Semantic diferit de
# 429 (nu e rate-limit; nu se rezolva prin retry) SI de esec de continut (nu triplam
# circuit breaker-ul). Prins pe MARKER de body, NU pe status nud — la fel ca §3 ("gone"
# cere marker, fiindca un 402 gol poate fi tranzitoriu upstream). INTERZIS markerul nud
# "insufficient" (ar prinde "insufficient permissions" = auth -> trebuie sa ramana "fail").
# `insufficient_quota` NU e aici: ramane in _QUOTA_MARKERS, verificat INAINTE de plata.
_PAYMENT_MARKERS = (
    "insufficient balance",
    "insufficient_balance",
    "insufficient credit",
    "insufficient credits",
    "payment required",
    "payment_required",
)
_OVERFLOW_MARKERS = (
    "context_length_exceeded",
    "maximum context",
    "context window",
    "reduce the length",
    "too many tokens",
    "input is too long",
    "string too long",
)


def classify_http_error(status_code: int, body: str) -> str:
    """Clasifica un raspuns HTTP de eroare intr-o categorie de fallback:
    - "gone"     → §3: modelul a disparut din catalog (404 / marker) → INDISPONIBIL pe sesiune
    - "quota"    → §5: cota epuizata (429 / marker) → fallback, NU e esec de continut
    - "payment"  → §5b: credit PLATIT epuizat (402 + marker "insufficient balance") → fallback,
                   NU e esec de continut si NU e cota (nu se rezolva prin retry) → fara circuit
    - "overflow" → §4: prompt peste contextul real (400 + marker) → sari providerul
    - "fail"     → esec generic/tranzitoriu → circuit breaker

    Ordinea conteaza: un 429 cu 'quota' e cota, un 400 cu 'context_length_exceeded' e overflow.
    Quota se verifica INAINTE de plata: `insufficient_quota` (marker de cota) NU trebuie sa cada
    pe plata. Plata se prinde pe MARKER (nu pe status 402 nud), consecvent cu §3.

    DEVIATIE CONSTIENTA de la D3 ("la 404 / model_not_found"): "gone" cere un MARKER in body,
    NU doar `status_code == 404`. Motiv: un 404 GOL e adesea indisponibilitate TRANZITORIE upstream
    (ex. OpenRouter "No endpoints found for X") — a-l trata ca "gone" ar dezactiva PERMANENT
    providerul pe sesiune (pana la restart). Un 404 fara marker -> "fail" (circuit breaker cu TTL,
    recuperabil). Retragerea reala (ex. groq scout) vine mereu cu `model_not_found` in body -> prinsa.
    """
    b = (body or "").lower()
    if any(m in b for m in _GONE_MARKERS):
        return "gone"
    if status_code == 429 or any(m in b for m in _QUOTA_MARKERS):
        return "quota"
    if any(m in b for m in _PAYMENT_MARKERS):
        return "payment"
    if status_code in (400, 413) and any(m in b for m in _OVERFLOW_MARKERS):
        return "overflow"
    return "fail"


def extract_rate_limit_info(headers) -> str:
    """§5: extrage Retry-After / X-RateLimit-* din headere pt logare (fara valori sensibile)."""
    parts = []
    try:
        for h in headers:
            hl = h.lower()
            if hl == "retry-after" or "ratelimit" in hl:
                parts.append(f"{h}={headers[h]}")
    except Exception:
        return ""
    return "; ".join(parts)


# ── §3: registru de provideri INDISPONIBILI pe sesiune (proces, NU circuit TTL) ─
# Un model retras ramane marcat pana la restart (deploy) — NU redevine reincercabil
# dupa un TTL, cum ar face circuit breaker-ul. Restartul re-verifica (si §6 lunar prinde).
_UNAVAILABLE_PROVIDERS: set[str] = set()


def mark_unavailable(provider: str, model: str = "") -> None:
    _UNAVAILABLE_PROVIDERS.add(provider)


def is_unavailable(provider: str) -> bool:
    return provider in _UNAVAILABLE_PROVIDERS


def clear_unavailable() -> None:
    """Doar pentru teste / reset explicit."""
    _UNAVAILABLE_PROVIDERS.clear()
