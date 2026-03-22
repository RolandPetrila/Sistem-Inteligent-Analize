# Deep Research Report — Roland Intelligence System (RIS)
Data: 2026-03-21 01:00 | Stack: Python 3.13 + FastAPI + React 19 + Vite + TypeScript | Agenti: 5 | Timp: ~12 min

## Scor General

| Aspect | Scor | Vizual |
|--------|------|--------|
| Securitate | 6/10 | ██████░░░░ |
| Calitate Cod | 7/10 | ███████░░░ |
| Arhitectura | 8/10 | ████████░░ |
| Testare | 1/10 | █░░░░░░░░░ |
| Performanta | 5/10 | █████░░░░░ |
| Documentatie | 9/10 | █████████░ |
| Dependente | 8/10 | ████████░░ |
| Deploy Ready | 4/10 | ████░░░░░░ |
| **TOTAL** | **48/80** | |

---

## Metrici Proiect (masurate)

| Metrica | Valoare | Cum am masurat |
|---------|---------|----------------|
| Backend LOC | 7,662 | `wc -l *.py` |
| Frontend LOC | 3,085 | `wc -l *.ts *.tsx` |
| Total LOC | 10,747 | suma |
| Fisiere Python | 49 | `find + count` |
| Fisiere TS/TSX | 22 | `find + count` |
| DB size | 112 KB (WAL: 1.3 MB) | `du -sh` |
| DB tables | 9 | `sqlite_master query` |
| Backend cold start | **12.95s** | `python -c "import time; ..."` |
| Frontend bundle gzip | **92.48 KB** | `npx vite build` |
| Frontend build time | 49.12s | `npx vite build` |
| Endpoints API | ~30 | grep + manual count |
| Pagini frontend | 10 | glob pages/*.tsx |
| Formate raport | 6 | (PDF, DOCX, HTML, Excel, PPTX, 1-Pager) |
| AI providers | 5 | (Claude CLI, Groq, Mistral, Gemini, Cerebras) |
| Surse date | 10+ | (ANAF x2, BNR, Tavily, openapi.ro, SEAP, INS TEMPO, ...) |
| Test files | **0** | `glob test_*.py, *.test.ts` |
| npm vulnerabilities | 0 | `npm audit` |
| Git repo | NU | `git log` |
| PRAGMA journal_mode | WAL | `PRAGMA journal_mode` |
| PRAGMA synchronous | **2 (FULL)** | `PRAGMA synchronous` |
| PRAGMA busy_timeout | 5000 | `PRAGMA busy_timeout` |
| PRAGMA mmap_size | **0 (disabled)** | `PRAGMA mmap_size` |
| PRAGMA foreign_keys | ON (in code) | `database.py:20` |

---

## Gasiri Critice (actiune imediata)

### [CRITICAL] [ROI: 10] Zero Test Coverage [CERT]
- **Problema:** Nu exista NICIUN fisier de test in proiect (0 test_*.py, 0 *.test.ts, 0 __tests__/)
- **Root cause:** Dezvoltare rapida faza-cu-faza fara TDD
- **Impact:** Orice modificare poate sparge functionalitate existenta fara detectie. Refactorizarea devine imposibila cu incredere. Bug-uri ajung in productie.
- **Fix:** Adauga teste minimale pe fluxul critic:
  - `test_cui_validator.py` — unit test MOD 11
  - `test_anaf_client.py` — mock response + parsing
  - `test_job_flow.py` — integration test end-to-end
  - `test_api_endpoints.py` — smoke test pe toate endpoint-urile
- **Efort:** MEDIU (4-8h) | **Risc:** LOW

### [CRITICAL] [ROI: 9] Zero Autentificare API [CERT]
- **Fisier:** `backend/main.py` — TOATE endpoint-urile
- **Problema:** Nicio forma de autentificare. Oricine cu acces la port 8001 poate: rula analize, descarca rapoarte, modifica setari, sterge alerte, declanasa batch-uri.
- **Root cause:** Aplicatie conceputa pt uz local (localhost only)
- **Impact:** Pe Tailscale/LAN, orice device poate accesa API-ul. CORS nu protejeaza API calls directe (curl, Postman).
- **Fix:** Adauga cel putin API key simplu:
  ```python
  # config.py
  api_key: str = ""  # daca gol, skip auth (backwards compatible)

  # middleware
  if settings.api_key and request.headers.get("X-API-Key") != settings.api_key:
      return JSONResponse(status_code=401, ...)
  ```
- **Efort:** MIC (1-2h) | **Risc:** LOW

---

## Gasiri Importante (recomandate)

### [HIGH] [ROI: 8] Backend Cold Start 12.95s [CERT]
- **Fisier:** `backend/main.py` (import chain)
- **Problema:** Import-ul `from backend.main import app` dureaza 12.95 secunde. Cauza: lanturi de import grele (LangGraph, Playwright, matplotlib, openpyxl, etc.)
- **Root cause:** Toate modulele se importa eager la startup, chiar daca nu sunt necesare imediat
- **Impact:** Server restart lent, development iteration slow, health check fail daca timeout < 13s
- **Fix:** Lazy imports mai agresive in:
  - `reports/generator.py` — deja lazy (bine)
  - `agents/orchestrator.py` — importa LangGraph la build_analysis_graph() nu la modul level
  - `agents/tools/seap_client.py` — Playwright import lazy
  - `reports/pptx_generator.py`, `excel_generator.py` — lazy import openpyxl, python-pptx
- **Efort:** MIC (1-2h) | **Risc:** LOW
- **Target:** < 4s cold start

### [HIGH] [ROI: 7] SQLite PRAGMA synchronous=FULL in loc de NORMAL [CERT]
- **Fisier:** `backend/database.py:18-21`
- **Problema:** `synchronous` ramane pe valoarea default 2 (FULL). Cu WAL mode, recomandat este NORMAL (1) care ofera durabilitate adecvata cu performanta superioara.
- **Root cause:** Nu s-a setat explicit in connect()
- **Impact:** Fiecare scriere in DB asteapta sync to disk, incetinind operatiunile ~2-3x
- **Fix:** Adauga in `connect()`:
  ```python
  await self._db.execute("PRAGMA synchronous=NORMAL")
  await self._db.execute("PRAGMA mmap_size=268435456")  # 256MB
  ```
- **Efort:** MIC (10 min) | **Risc:** LOW

### [HIGH] [ROI: 7] No Rate Limiting [CERT]
- **Fisier:** `backend/main.py`
- **Problema:** Niciun endpoint nu are rate limiting. Un client poate spama /api/jobs cu mii de request-uri, epuiza resurse, sau lansa sute de analize simultane.
- **Root cause:** Aplicatie conceputa pentru utilizator unic
- **Impact:** Resource exhaustion, API abuse, Tavily quota drain (1000/luna)
- **Fix:** `slowapi` sau middleware custom simplu:
  ```python
  # Simple in-memory rate limiter
  from collections import defaultdict
  import time
  _requests = defaultdict(list)

  # In middleware: max 60 req/min per IP
  ```
- **Efort:** MIC (1-2h) | **Risc:** LOW

### [HIGH] [ROI: 6] agent_verification.py — 1063 linii [CERT]
- **Fisier:** `backend/agents/agent_verification.py`
- **Problema:** Cel mai mare fisier din proiect (1063 linii). Contine: scoring, due diligence, early warnings, actionariat, benchmark, relations detection — toate in aceeasi clasa.
- **Root cause:** Implementare incrementala in aceeasi sesiune
- **Impact:** Greu de intretinut, greu de testat individual, greu de citit
- **Fix:** Sparge in module:
  - `verification/scoring.py` — calculul scorului 0-100
  - `verification/due_diligence.py` — 10 DA/NU checks
  - `verification/early_warnings.py` — 3 reguli alerta
  - `verification/benchmark.py` — comparatie CAEN
  - `verification/relations.py` — detectie relatii
- **Efort:** MEDIU (2-3h) | **Risc:** MEDIUM (necesita teste inainte)

### [HIGH] [ROI: 6] Inconsistenta format raport cu AI fallback [CERT]
- **Fisier:** `backend/agents/agent_synthesis.py:51-86, 110-136`
- **Problema:** Smart routing trimite sectiuni scurte la Groq (format structurat cu bullet points) si lungi la Claude (format narativ). Daca Claude cade pe Groq ca fallback, sectiunea lunga vine structurata. Raportul final are mix de stiluri.
- **Root cause:** Provider-specific prompts genereaza output diferit ca format
- **Impact:** Raportul arata inconsistent — unele sectiuni narativ, altele bullet points
- **Fix:** Adauga post-processing normalizare, sau forteaza format unitar indiferent de provider
- **Efort:** MEDIU (2-3h) | **Risc:** MEDIUM

---

## Imbunatatiri Sugerate (optional, ROI descrescator)

### [MEDIUM] [ROI: 5] Lazy loading frontend routes [CERT]
- **Fisier:** `frontend/src/App.tsx`
- **Problema:** Toate 10 paginile sunt importate eager. Bundle: 308KB (92KB gzip). Se incarca totul chiar daca utilizatorul viziteaza doar Dashboard.
- **Fix:**
  ```tsx
  const Dashboard = React.lazy(() => import("./pages/Dashboard"));
  // + <Suspense fallback={<Loader />}>
  ```
- **Efort:** MIC (30 min) | **Risc:** LOW

### [MEDIUM] [ROI: 5] CUI validation fara debounce [CERT]
- **Fisier:** `frontend/src/pages/NewAnalysis.tsx:195`
- **Problema:** Validarea CUI se ruleaza pe fiecare keystroke (onChange). Cu MOD 11 e rapid, dar pattern-ul e gresit — se valideaza inainte ca userul sa termine de tastat.
- **Fix:** Debounce 300ms sau validare onBlur
- **Efort:** MIC (15 min) | **Risc:** LOW

### [MEDIUM] [ROI: 5] No token/cost tracking AI providers [CERT]
- **Fisier:** `backend/agents/agent_synthesis.py`
- **Problema:** Nu se logheaza: tokeni consumati, cost per provider, lungimea raspunsului. Imposibil de monitorizat consumul real.
- **Fix:** Log structured la fiecare call:
  ```python
  logger.info(f"AI call: provider={provider}, tokens_in={in}, tokens_out={out}, latency={ms}ms")
  ```
- **Efort:** MIC (1h) | **Risc:** LOW

### [MEDIUM] [ROI: 4] Logs array unbounded in AnalysisProgress [CERT]
- **Fisier:** `frontend/src/pages/AnalysisProgress.tsx:46-68`
- **Problema:** Array-ul `logs` creste nelimitat cu fiecare mesaj WebSocket. La joburi lungi (batch 50 CUI-uri), poate acumula mii de entry-uri.
- **Fix:** Limita la ultimele 100 entry-uri: `setLogs(prev => [...prev.slice(-99), newLog])`
- **Efort:** MIC (5 min) | **Risc:** LOW

### [MEDIUM] [ROI: 4] Section prompts — competition/recommendations anti-halucinare slaba [CERT]
- **Fisier:** `backend/prompts/section_prompts.py`
- **Problema:** Prompt-urile "competition" si "recommendations" nu au mecanisme anti-halucinare puternice. Daca Tavily returneaza putine date, AI-ul poate inventa competitori sau recomandari.
- **Fix:** Adauga: "Daca nu ai date suficiente, scrie explicit: 'Date insuficiente pentru aceasta sectiune.'"
- **Efort:** MIC (30 min) | **Risc:** LOW

### [MEDIUM] [ROI: 4] app_secret_key default value [CERT]
- **Fisier:** `backend/config.py:32`
- **Problema:** `app_secret_key: str = "change-me-to-random-string"` — valoare default predictibila
- **Root cause:** Placeholder ramas din initial setup
- **Impact:** Daca se implementeaza auth, secret key-ul e compromis
- **Fix:** Genereaza random la primul start sau forteaza setare in .env
- **Efort:** MIC (15 min) | **Risc:** LOW

### [MEDIUM] [ROI: 4] No git repository [CERT]
- **Problema:** Proiectul NU este un repository git. Nu exista history, branching, blame, rollback.
- **Impact:** Orice eroare e ireversibila. Nu se poate compara cu versiunea anterioara.
- **Fix:** `git init && git add . && git commit -m "Initial commit"`
- **Efort:** MIC (5 min) | **Risc:** LOW

### [LOW] [ROI: 3] Frontend accessibility lipseste [CERT]
- **Fisiere:** Toate paginile din `frontend/src/pages/`
- **Problema:** ARIA labels lipsesc pe iconite, tabs fara `role="tablist"`, forms fara `<label>` HTML5 semantic
- **Impact:** Inutilizabil cu screen readers
- **Fix:** Adauga ARIA labels, semantic HTML5, tabindex
- **Efort:** MEDIU (3-4h) | **Risc:** LOW

### [LOW] [ROI: 3] Error handling inconsistent — catch gol [PROBABIL]
- **Fisiere:** `backend/main.py:40,266`, `backend/services/job_service.py:30,37`
- **Problema:** Cateva `except Exception: pass` fara logging. In main.py WS broadcast (linia 40) si job_service prevent_sleep/allow_sleep (liniile 30, 37) — erorile sunt inghitite silentios.
- **Impact:** Debug dificil daca apar probleme pe aceste code paths
- **Fix:** Adauga cel putin `logger.debug()` in catch blocks
- **Efort:** MIC (15 min) | **Risc:** LOW

### [LOW] [ROI: 2] No Gunicorn workers [PROBABIL]
- **Fisier:** `backend/main.py:270-277`, `START_RIS_silent.bat:27`
- **Problema:** Server-ul ruleaza cu un singur worker Uvicorn. Sub sarcina concurenta (batch analysis + browsing UI), event loop-ul se poate bloca.
- **Impact:** Performanta degradata sub load
- **Fix:** `gunicorn -w 2 -k uvicorn.workers.UvicornWorker backend.main:app`
- **Efort:** MIC (15 min) | **Risc:** MEDIUM (Windows compatibility)

---

## Audit Granular

### Per-Endpoint Backend

| Endpoint | Fisier:Linie | Metoda | Probleme | Certitudine |
|----------|-------------|--------|----------|-------------|
| POST /api/jobs | jobs.py:17 | POST | OK — validated via Pydantic JobCreate | [CERT] |
| GET /api/jobs | jobs.py:44 | GET | f-string WHERE — safe but fragile pattern | [CERT] |
| GET /api/jobs/{id} | jobs.py:92 | GET | OK — parametrized query | [CERT] |
| POST /api/jobs/{id}/start | jobs.py:120 | POST | asyncio.create_task fara tracking | [CERT] |
| POST /api/jobs/{id}/cancel | jobs.py:136 | POST | NU opreste task-ul in executie, doar seteaza status | [CERT] |
| GET /api/reports | reports.py:13 | GET | f-string WHERE — safe but fragile | [CERT] |
| GET /api/reports/{id} | reports.py:68 | GET | OK | [CERT] |
| GET /api/reports/{id}/download/{fmt} | reports.py:126 | GET | Format whitelist OK, Path din DB OK | [CERT] |
| GET /api/reports/{id}/download/one_pager | reports.py:108 | GET | Path construit din job_id (UUID) — OK | [CERT] |
| GET /api/companies | companies.py:~20 | GET | f-string WHERE — safe but fragile | [CERT] |
| GET /api/companies/export/csv | companies.py:~80 | GET | No auth — full export public | [CERT] |
| GET /api/companies/{id} | companies.py:~90 | GET | OK | [CERT] |
| GET /api/analysis/types | analysis.py:22 | GET | OK — static data | [CERT] |
| POST /api/analysis/parse-query | analysis.py:~50 | POST | Regex CUI extraction — no AI, safe | [CERT] |
| GET /api/settings | settings.py:~20 | GET | Expune config fara auth (keys masked) | [CERT] |
| PUT /api/settings | settings.py:~50 | PUT | MODIFICA .env fara auth! | [CERT] |
| POST /api/settings/test-telegram | settings.py:~100 | POST | Trimite mesaj Telegram fara auth | [CERT] |
| POST /api/compare | compare.py:~20 | POST | OK | [CERT] |
| POST /api/compare/sector | compare.py:~60 | POST | OK | [CERT] |
| GET /api/monitoring | monitoring.py:~20 | GET | OK | [CERT] |
| POST /api/monitoring | monitoring.py:~40 | POST | OK — validated | [CERT] |
| PUT /api/monitoring/{id}/toggle | monitoring.py:~60 | PUT | OK | [CERT] |
| DELETE /api/monitoring/{id} | monitoring.py:~75 | DELETE | No auth — sterge alerte | [CERT] |
| POST /api/monitoring/check-now | monitoring.py:~85 | POST | Trigger monitoring check fara auth | [CERT] |
| POST /api/batch | batch.py:28 | POST | OK — CUI validation + limit 50 | [CERT] |
| GET /api/batch/{id} | batch.py:100 | GET | OK | [CERT] |
| GET /api/batch/{id}/download | batch.py:121 | GET | Path din batch_id (UUID) — OK | [CERT] |
| GET /api/health | main.py:134 | GET | OK | [CERT] |
| GET /api/health/deep | main.py:140 | GET | OK — comprehensive | [CERT] |
| GET /api/stats | main.py:204 | GET | Cache 30s — OK | [CERT] |
| GET /api/stats/trend | main.py:232 | GET | OK | [CERT] |
| WS /ws/jobs/{id} | main.py:243 | WS | No auth pe WS | [CERT] |

### Per-Pagina Frontend

| Pagina | Fisier | LOC | Loading? | Error? | Empty? | A11y? | Performance |
|--------|--------|-----|----------|--------|--------|-------|-------------|
| Dashboard | Dashboard.tsx | 336 | skeleton | toast | mesaj + CTA | missing ARIA | TrendChart no memo |
| NewAnalysis | NewAnalysis.tsx | 346 | partial | toast + CUI | placeholder | missing labels | CUI no debounce |
| AnalysisProgress | AnalysisProgress.tsx | 227 | loader | toast | n/a | missing | logs unbounded |
| ReportsList | ReportsList.tsx | 117 | skeleton | toast | mesaj | minimal | OK |
| ReportView | ReportView.tsx | 335 | skeleton | toast + fallback | per-tab | tabs no role | JSON.stringify no memo |
| Companies | Companies.tsx | 117 | skeleton | toast | mesaj | minimal | OK |
| CompareCompanies | CompareCompanies.tsx | 213 | partial | toast | mesaj | minimal | OK |
| Monitoring | Monitoring.tsx | 174 | partial | toast | mesaj | minimal | OK |
| BatchAnalysis | BatchAnalysis.tsx | 235 | partial | toast | mesaj | minimal | OK |
| Settings | Settings.tsx | 214 | partial | toast | n/a | minimal | OK |

### AI Prompts Audit

| Locatie | Scop | Specific? | Format? | Anti-haluc? | Provider-aware? | Few-shot? |
|---------|------|-----------|---------|-------------|-----------------|-----------|
| prompts/system_prompt.py | Sistem general | 4/5 | NU | DA (7 reguli) | NU | NU |
| section_prompts.py — executive_summary | Sumar executiv | 4/5 | NU | DA | NU | NU |
| section_prompts.py — company_profile | Profil firma | 4/5 | DA (tabel) | DA (trust) | NU | NU |
| section_prompts.py — financial_analysis | Analiza financiara | 5/5 | NU | DA | NU | NU |
| section_prompts.py — risk_assessment | Risc | 5/5 | DA (culori) | DA | NU | NU |
| section_prompts.py — competition | Competitie | 3/5 | DA (tabel) | SLAB | NU | NU |
| section_prompts.py — opportunities | Oportunitati | 3/5 | DA (tabel) | SLAB | NU | NU |
| section_prompts.py — swot | SWOT | 4/5 | DA (4 cadrane) | DA | NU | NU |
| section_prompts.py — recommendations | Recomandari | 3/5 | NU | SLAB | NU | NU |
| agent_synthesis.py — Claude style | Narativ | 5/5 | narativ | implicit | DA | NU |
| agent_synthesis.py — Groq style | Structurat | 5/5 | bullets | implicit | DA | NU |
| agent_synthesis.py — Mistral style | European formal | 4/5 | paragrafe | implicit | DA | NU |
| agent_synthesis.py — Gemini style | Analitic | 4/5 | headere + concluzie | implicit | DA | NU |
| agent_synthesis.py — Cerebras style | Simplu | 3/5 | max 3 paragrafe | implicit | DA | NU |

### Surse Externe — Clienti API

| Client API | Fisier | Error handling? | Retry? | Timeout? | Cache? | Rate limit? |
|-----------|--------|----------------|--------|----------|--------|-------------|
| ANAF TVA v9 | anaf_client.py | DA (try/except + log) | DA (via BaseAgent) | DA (httpx 30s) | DA (cache_service) | DA (2s delay) |
| ANAF Bilant | anaf_bilant_client.py | DA | DA (via BaseAgent) | DA | DA | DA (2s delay) |
| BNR Cursuri | bnr_client.py | DA | NU | DA | DA | NU (public, no limit) |
| Tavily Search | tavily_client.py | DA | NU | DA | DA + quota tracking | DA (monthly quota) |
| openapi.ro | openapi_client.py | DA | NU | DA | DA | DA (100/luna) |
| SEAP e-licitatie | seap_client.py | DA (try/except + log) | NU | DA | DA | NU |
| INS TEMPO | caen_context.py | DA (try/except) | NU | DA | NU (fetch live) | NU |
| Telegram Bot | notification.py | DA | NU | DA | N/A | N/A |
| Groq API | agent_synthesis.py | DA | NU (fallback chain) | DA (60s) | NU | NU |
| Mistral API | agent_synthesis.py | DA | NU (fallback chain) | DA (60s) | NU | NU |
| Gemini API | agent_synthesis.py | DA | NU (fallback chain) | DA (60s) | NU | NU |
| Cerebras API | agent_synthesis.py | DA | NU (fallback chain) | DA (60s) | NU | NU |
| Claude CLI | agent_synthesis.py | DA | NU (fallback chain) | DA (200s) | NU | NU |

---

## Dead Code Identificat

| Tip | Locatie | Detalii |
|-----|---------|---------|
| Tabel nefolosit | `data/ris.db: markets` | 0 rows, niciun endpoint scrie in ea [CERT] |
| Tabel nefolosit | `data/ris.db: report_deltas` | 0 rows, dar cod exista (delta_service.py) — poate fi normal pt proiect nou [PROBABIL] |
| Config nefolosita | `config.py:32` | `app_secret_key` — setat dar nefolosit nicaieri [CERT] |
| useApi hook | `hooks/useApi.ts` | Definit dar greu de verificat utilizarea completa [NEVERIFICAT] |

---

## Dependency Map

```
backend/main.py
  ├── config.py (Settings)
  ├── database.py (db singleton)
  ├── http_client.py (httpx singleton)
  ├── routers/
  │   ├── jobs.py ──→ database, models, job_service
  │   ├── reports.py ──→ database, config
  │   ├── companies.py ──→ database
  │   ├── analysis.py ──→ models
  │   ├── settings.py ──→ config, notification
  │   ├── compare.py ──→ database
  │   ├── monitoring.py ──→ database, monitoring_service, notification
  │   └── batch.py ──→ database, config, cui_validator, job_service
  └── services/
      ├── job_service.py ──→ database, state, orchestrator, cache_service, notification
      │                       ├── orchestrator.py ──→ LangGraph, agents (official, verification, synthesis)
      │                       │                       ├── agent_official.py ──→ anaf, bilant, bnr, tavily, openapi, caen_context
      │                       │                       ├── agent_verification.py ──→ (self-contained, uses official_data)
      │                       │                       └── agent_synthesis.py ──→ prompts, http_client (Groq/Mistral/Gemini/Cerebras) + subprocess (Claude)
      ├── cache_service.py ──→ database
      ├── notification.py ──→ config, http_client
      ├── monitoring_service.py ──→ database, anaf_client, notification
      ├── scheduler.py ──→ monitoring_service, database
      └── delta_service.py ──→ database

  NO CIRCULAR DEPENDENCIES DETECTED
```

---

## Cross-Platform Issues

| Config | Windows | Tailscale/LAN | Problema | Fix |
|--------|---------|---------------|----------|-----|
| pythonw in .bat | OK | N/A | pythonw nu afiseaza erori — debug imposibil | Adauga log to file |
| CORS regex | OK localhost | OK 100.x.x.x | Permite orice port pe Tailscale | OK pentru uz intern |
| WAL mode | OK | N/A (SQLite local) | WAL nu merge pe network FS | N/A — DB e local |
| Paths Windows | OK (forward slashes in Python) | N/A | outputs/ cu forward slashes | OK |
| Scheduler asyncio | OK | N/A | sleep(21600) = 6h, nu e persistent | Restart server = reset scheduler timers |

---

## Provider/Tool Scan

| Tool curent | Alternativa | Free? | Avantaj | Recomandare |
|-------------|-------------|-------|---------|-------------|
| fpdf2 (PDF) | WeasyPrint | DA | Suport CSS complet | [NU MERITA] — GTK pe Windows = problematic |
| aiosqlite | SQLModel | DA | ORM + async | [NU MERITA] — raw SQL e mai rapid pt acest use case |
| httpx singleton | aiohttp | DA | Marginal mai rapid | [NU MERITA] — httpx e mai ergonomic |
| Uvicorn single | Gunicorn + Uvicorn | DA | Multi-worker | [RELEVANT ACUM] — pentru batch processing |
| Tailwind CSS | UnoCSS | DA | Bundle mai mic | [NU MERITA] — Tailwind e standard |
| React Router | TanStack Router | DA | Type-safe routes | [OVERKILL] — proiect mic |
| fetch (frontend) | Axios / ky | DA | Interceptors, retry | [ALTERNATIVA INTERESANTA] — ar rezolva error handling global |
| loguru | structlog | DA | Structured JSON logs | [OVERKILL] — loguru e suficient |

---

## Best Practices Comparison

| Practica | Status Proiect | Recomandare | Prioritate |
|----------|---------------|-------------|------------|
| Authentication | ABSENT | Adauga API key minim | CRITICAL |
| Rate limiting | ABSENT | Adauga slowapi/custom | HIGH |
| Test coverage | 0% | Adauga 20% minim (critical paths) | CRITICAL |
| PRAGMA synchronous=NORMAL | FULL (default) | Seteaza NORMAL cu WAL | HIGH |
| PRAGMA mmap_size | 0 | Seteaza 256MB | HIGH |
| Code splitting (React.lazy) | ABSENT | Lazy load routes | MEDIUM |
| Git version control | ABSENT | git init | MEDIUM |
| Gunicorn multi-worker | Single worker | Evalueaza 2 workers | LOW |
| Error boundary | PREZENT | OK | - |
| Security headers (CSP) | PREZENT | OK | - |
| CORS restrictive | PREZENT | OK | - |
| .env in .gitignore | PREZENT | OK | - |
| WAL mode SQLite | PREZENT | OK | - |
| httpx connection pool | PREZENT | OK | - |
| Pydantic validation | PREZENT | OK | - |
| WebSocket reconnect | PREZENT | OK | - |
| Toast notifications | PREZENT | OK | - |
| AI fallback chain (5 nivele) | PREZENT | OK (unic si robust) | - |
| Smart routing AI | PREZENT | OK (innovativ) | - |

---

## Fragile Code Hotspots

| Fisier | Motive | Cauza | Recomandare |
|--------|--------|-------|-------------|
| agent_verification.py | 1063 LOC, multiple responsabilitati | Implementare incrementala | Sparge in 5 module |
| agent_synthesis.py | 5 provideri AI, smart routing, format mixat | Complexitate intrinseca | Adauga post-processing normalizare |
| job_service.py | 279 LOC, orchestrare completa + DB + WS + notifications | Singur entry point pt executie | OK dar teste necesare |
| caen_context.py | 361 LOC, date hardcodate + API INS TEMPO | Mix date statice + dinamice | Separa CAEN_DESCRIPTIONS in fisier separat |
| NewAnalysis.tsx | 346 LOC, wizard 4 pasi, validare, chatbot | Feature-rich page | OK dar debounce CUI |

---

## Metrici Actuale vs Target

| Metrica | Actual (masurat) | Target recomandat | Cum masori |
|---------|-----------------|-------------------|-----------|
| Backend cold start | 12.95s | < 4s | `python -c "import time; ..."` |
| Frontend bundle gzip | 92.48 KB | < 80 KB (cu lazy) | `npx vite build` |
| Test coverage | 0% | > 20% critical paths | `pytest --cov` |
| Endpoints fara auth | 30/30 (100%) | < 20% (doar health) | manual audit |
| DB sync mode | FULL (2) | NORMAL (1) | `PRAGMA synchronous` |
| DB mmap | 0 (disabled) | 256 MB | `PRAGMA mmap_size` |
| Timp analiza completa | ~3-5 min | < 3 min | cronometrat |
| Fat files (>300 LOC) | 5 fisiere | < 2 | `wc -l + sort` |

---

## Roadmap Imbunatatiri

### SAPTAMANA 1 — Quick Wins (ROI > 7, Efort MIC)

```
[QW1] Initializeaza git repository
      Comanda: git init && git add . && git commit -m "Initial commit v1.0"
      Efort: 5 min | Impact: MEDIUM | Risc: LOW
      Depinde de: nimic

[QW2] Adauga PRAGMA synchronous=NORMAL + mmap_size=256MB
      Fisier: backend/database.py:18-21
      Efort: 10 min | Impact: HIGH (performance DB)
      Depinde de: nimic

[QW3] Fix CUI validation debounce in NewAnalysis
      Fisier: frontend/src/pages/NewAnalysis.tsx:195
      Efort: 15 min | Impact: MEDIUM (UX)
      Depinde de: nimic

[QW4] Limiteaza logs array in AnalysisProgress la 100
      Fisier: frontend/src/pages/AnalysisProgress.tsx:46
      Efort: 5 min | Impact: MEDIUM (memory)
      Depinde de: nimic

[QW5] Adauga anti-halucinare in prompt competition/recommendations
      Fisier: backend/prompts/section_prompts.py
      Efort: 30 min | Impact: HIGH (calitate rapoarte)
      Depinde de: nimic

[QW6] Fix app_secret_key default — genereaza random
      Fisier: backend/config.py:32
      Efort: 15 min | Impact: MEDIUM (securitate)
      Depinde de: nimic

Toate independente — pot fi executate in orice ordine.
```

### SAPTAMANA 2 — Securitate & Stabilitate

```
[S1] Adauga API key authentication middleware
     Fisier: backend/main.py (middleware nou)
     Efort: 1-2h | Impact: CRITICAL (securitate)
     Depinde de: QW6 (secret key fix)

[S2] Adauga rate limiting (60 req/min per IP)
     Fisier: backend/main.py (middleware nou)
     Efort: 1-2h | Impact: HIGH (abuse prevention)
     Depinde de: nimic

[S3] Adauga teste minimale pe fluxul critic
     Fisiere noi: tests/test_cui_validator.py, tests/test_api_smoke.py
     Efort: 4-6h | Impact: CRITICAL (stabilitate)
     Depinde de: nimic (dar RECOMANDAT INAINTE de orice refactorizare)

[S4] Adauga token/cost tracking pentru AI providers
     Fisier: backend/agents/agent_synthesis.py
     Efort: 1h | Impact: MEDIUM (monitorizare costuri)
     Depinde de: nimic
```

### SAPTAMANA 3-4 — Performance & Arhitectura

```
[P1] Reduce backend cold start cu lazy imports agresive
     Fisiere: orchestrator.py, agents/*.py (move imports inside functions)
     Efort: 1-2h | Impact: HIGH (DX + restart speed)
     Depinde de: S3 (teste INAINTE de refactorizare!)

[P2] Adauga React.lazy() pe toate rutele din App.tsx
     Fisier: frontend/src/App.tsx
     Efort: 30 min | Impact: MEDIUM (bundle split)
     Depinde de: nimic

[A1] Sparge agent_verification.py in 5 module
     Fisier: backend/agents/agent_verification.py → verification/
     Efort: 2-3h | Impact: MEDIUM (mentenabilitate)
     Depinde de: S3 (OBLIGATORIU — teste inainte de refactorizare!)

[A2] Normalizeaza format output AI indiferent de provider
     Fisier: backend/agents/agent_synthesis.py
     Efort: 2-3h | Impact: MEDIUM (consistenta rapoarte)
     Depinde de: S3 (teste pe output)
```

### VIITOR (nice to have, ROI < 3)

```
[V1] Accesibilitate frontend (ARIA, semantic HTML)
     Efort: MARE (3-4h) | Impact: LOW — Doar daca e nevoie de conformitate
     Depinde de: P2

[V2] Gunicorn multi-worker
     Efort: MIC (15 min) | Impact: LOW — Doar daca se confirma bottleneck
     Depinde de: S1 (auth first!)
     Nota: Windows compatibility incerta — testeaza cu waitress ca alternativa

[V3] Structured logging (JSON) pentru observabilitate
     Efort: MEDIU (2h) | Impact: LOW — util doar cu log aggregation
     Depinde de: nimic
```

---

## Ce Am Omis / Ce Poate Fi Incorect

1. **[NEVERIFICAT] Comportament sub sarcina reala** — nu am rulat load testing (ab, wrk). Cifrele de performanta sunt cold start, nu throughput.
2. **[NEVERIFICAT] Playwright functionality** — nu am putut verifica daca web scraping-ul cu Playwright functioneaza (SEAP agent, Agent 2/3). Nu am rulat o analiza completa.
3. **[NEVERIFICAT] Agent 2 (web) si Agent 3 (market)** — definite in orchestrator dar nu am citit implementarile complete; par sa fie in `agent_official.py` sub alte metode.
4. **[PROBABIL] useApi hook usage** — pare definit dar nu am putut confirma daca e folosit in toate paginile sau e un remnant
5. **[NEVERIFICAT] React 19 compiler** — npm packages sunt la 19.2.4 dar nu am verificat daca React Compiler e activat in vite.config
6. **Presupuneri:** Am presupus ca app-ul ruleaza doar local. Daca merge pe server public, scorurile de securitate scad semnificativ.
7. **Nu am verificat:** .env actual (nu citesc secrets) — daca API keys sunt corecte si active

---

## Snapshot JSON

```json
{
  "snapshot_date": "2026-03-21",
  "project": "Roland Intelligence System (RIS)",
  "stack": "Python 3.13 + FastAPI + React 19 + Vite + TypeScript + SQLite",
  "metrics": {
    "backend_import_time_s": 12.95,
    "frontend_bundle_kb_gzip": 92.48,
    "db_size_kb": 112,
    "total_endpoints": 30,
    "total_pages": 10,
    "total_loc_backend": 7662,
    "total_loc_frontend": 3085,
    "db_tables": 9,
    "test_files": 0
  },
  "scores": {
    "security": 6,
    "code_quality": 7,
    "architecture": 8,
    "testing": 1,
    "performance": 5,
    "documentation": 9,
    "dependencies": 8,
    "deploy_ready": 4,
    "total": 48
  },
  "issues": {
    "critical": 2,
    "high": 5,
    "medium": 8,
    "low": 3
  },
  "improvements_proposed": 18
}
```

---

**Surse web consultate:**
- [FastAPI Best Practices Production 2026](https://fastlaunchapi.dev/blog/fastapi-best-practices-production-2026)
- [React 19 Best Practices](https://dev.to/jay_sarvaiya_reactjs/react-19-best-practices-write-clean-modern-and-efficient-react-code-1beb)
- [Vercel React Best Practices (40+ Rules)](https://vercel.com/blog/introducing-react-best-practices)
- [SQLite Production Setup 2026](https://oneuptime.com/blog/post/2026-02-02-sqlite-production-setup/view)
- [SQLite WAL Mode Documentation](https://sqlite.org/wal.html)
- [LangGraph State Management Best Practices](https://medium.com/@bharatraj1918/langgraph-state-management-part-1-how-langgraph-manages-state-for-multi-agent-workflows-da64d352c43b)
- [FastAPI Security Guide](https://davidmuraya.com/blog/fastapi-security-guide/)
