# Roadmap Imbunatatiri RIS — Deep Research 2026-03-21

## Prioritati: CRITICAL > HIGH > MEDIUM > LOW
## Format: [ID] Actiune — Fisier — Efort — Impact — Depinde de

---

## SAPTAMANA 1 — Quick Wins (toate independente, orice ordine)

- [QW1] **git init** — Proiect fara version control
  ```bash
  cd C:\Proiecte\Sistem_Inteligent_Analize
  git init
  git add .
  git commit -m "Initial commit — RIS v1.0 (Faze 1-6 complete)"
  ```
  Efort: 5 min | Impact: MEDIUM

- [QW2] **PRAGMA synchronous=NORMAL + mmap_size** — `backend/database.py:21`
  ```python
  # Adauga dupa linia 21:
  await self._db.execute("PRAGMA synchronous=NORMAL")
  await self._db.execute("PRAGMA mmap_size=268435456")  # 256MB
  ```
  Efort: 10 min | Impact: HIGH (write performance +50-100%)

- [QW3] **CUI debounce** — `frontend/src/pages/NewAnalysis.tsx:195`
  ```typescript
  // Inlocuieste validare pe onChange cu debounce 300ms
  const [cuiTimer, setCuiTimer] = useState<NodeJS.Timeout>();
  const handleCuiChange = (val: string) => {
    setAnswers(prev => ({...prev, cui: val}));
    clearTimeout(cuiTimer);
    setCuiTimer(setTimeout(() => validateCui(val), 300));
  };
  ```
  Efort: 15 min | Impact: MEDIUM (UX)

- [QW4] **Logs limita 100** — `frontend/src/pages/AnalysisProgress.tsx:46`
  ```typescript
  setLogs(prev => [...prev.slice(-99), newLog]);
  ```
  Efort: 5 min | Impact: MEDIUM (previne memory leak)

- [QW5] **Anti-halucinare prompts** — `backend/prompts/section_prompts.py`
  Adauga in prompt-urile "competition" si "recommendations":
  > "Daca nu ai date suficiente pentru aceasta sectiune, scrie: 'Date insuficiente — nu se pot formula concluzii.' NU inventa informatii."
  Efort: 30 min | Impact: HIGH (calitate rapoarte)

- [QW6] **Secret key random** — `backend/config.py:32`
  ```python
  import secrets
  app_secret_key: str = secrets.token_urlsafe(32)
  ```
  Efort: 15 min | Impact: MEDIUM

---

## SAPTAMANA 2 — Securitate & Stabilitate

- [S1] **API Key auth middleware** — `backend/main.py`
  Depinde de: QW6
  ```python
  # In config.py:
  api_key: str = ""  # gol = skip auth (backward compat)

  # In main.py — middleware:
  @app.middleware("http")
  async def auth_middleware(request: Request, call_next):
      if settings.api_key:
          if request.url.path not in ("/api/health",):
              key = request.headers.get("X-API-Key", "")
              if key != settings.api_key:
                  return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
      return await call_next(request)
  ```
  Efort: 1-2h | Impact: CRITICAL

- [S2] **Rate limiting simplu** — `backend/main.py`
  ```python
  from collections import defaultdict
  import time

  _rate_limit: dict[str, list[float]] = defaultdict(list)

  @app.middleware("http")
  async def rate_limit_middleware(request: Request, call_next):
      ip = request.client.host if request.client else "unknown"
      now = time.time()
      _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < 60]
      if len(_rate_limit[ip]) >= 120:  # 120 req/min
          return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
      _rate_limit[ip].append(now)
      return await call_next(request)
  ```
  Efort: 1h | Impact: HIGH

- [S3] **Teste minimale** — `tests/` (director nou)
  ```
  tests/
    __init__.py
    test_cui_validator.py    — 10 teste: valid, invalid, edge cases
    test_api_smoke.py        — 15 teste: GET pe fiecare endpoint, status 200/404
    test_anaf_client.py      — 5 teste: mock response parsing
    conftest.py              — pytest fixtures (app, client)
  ```
  Efort: 4-6h | Impact: CRITICAL

- [S4] **Token tracking AI** — `backend/agents/agent_synthesis.py`
  ```python
  logger.info(
      f"AI | provider={provider} | section={section_key} | "
      f"input_chars={len(prompt)} | output_chars={len(result)} | "
      f"latency_ms={int(elapsed*1000)} | fallback={is_fallback}"
  )
  ```
  Efort: 1h | Impact: MEDIUM

---

## SAPTAMANA 3-4 — Performance & Arhitectura

- [P1] **Lazy imports backend** — `backend/agents/orchestrator.py`, `agents/*.py`
  Depinde de: S3 (teste inainte de refactorizare!)
  Muta importuri grele (LangGraph, Playwright, matplotlib) din top-level in functii.
  Target: backend cold start < 4s
  Efort: 1-2h | Impact: HIGH

- [P2] **React.lazy routes** — `frontend/src/App.tsx`
  ```tsx
  import { Suspense, lazy } from "react";
  const Dashboard = lazy(() => import("./pages/Dashboard"));
  const NewAnalysis = lazy(() => import("./pages/NewAnalysis"));
  // ... toate paginile

  // In JSX:
  <Suspense fallback={<div className="flex items-center justify-center h-screen">
    <div className="animate-spin ...">Loading...</div>
  </div>}>
    <Routes>...</Routes>
  </Suspense>
  ```
  Efort: 30 min | Impact: MEDIUM

- [A1] **Sparge agent_verification.py** — 1063 LOC → 5 module
  Depinde de: S3 (OBLIGATORIU!)
  ```
  backend/agents/verification/
    __init__.py
    scoring.py           (~200 LOC)
    due_diligence.py     (~100 LOC)
    early_warnings.py    (~80 LOC)
    benchmark.py         (~100 LOC)
    relations.py         (~80 LOC)
  ```
  Efort: 2-3h | Impact: MEDIUM

- [A2] **Normalizeaza AI output format** — `backend/agents/agent_synthesis.py`
  Depinde de: S3
  Adauga post-processing care normalizeaza output-ul indiferent de provider
  (ex: strip bullet points din Groq cand sectiunea e pentru narativ)
  Efort: 2-3h | Impact: MEDIUM

---

## VIITOR (nice to have)

- [V1] Accessibility frontend (ARIA labels, semantic HTML) — 3-4h | LOW
- [V2] Gunicorn multi-worker (testeaza pe Windows) — 15 min | LOW
- [V3] Structured JSON logging — 2h | LOW

---

## Diagrama Dependinte

```
QW1 ─────────────────────────────────────────────
QW2 ─────────────────────────────────────────────  (independente)
QW3 ─────────────────────────────────────────────
QW4 ─────────────────────────────────────────────
QW5 ─────────────────────────────────────────────
QW6 ──→ S1 (auth middleware)
         │
S2 ──────┤ (independente)
S3 ──────┤──→ P1 (lazy imports)
         │──→ A1 (sparge verification)
S4 ──────┘──→ A2 (normalizeaza output)
              │
              ├──→ P2 (React.lazy) [independent]
              │
              └──→ V1, V2, V3 (viitor)
```
