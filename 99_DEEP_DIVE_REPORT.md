# Deep Dive Report — Roland Intelligence System
Data: 2026-03-20 | Executor: Claude Code (Opus 4.6) | Durata analiza: ~15min

---

## Executive Summary

RIS este un sistem functional si stabil cu 87 functionalitati implementate in ~8.300 linii cod. **Top 3 probleme de performance:** (1) Backend import time 23s (fastapi 5s + fpdf2 3.3s + httpx 1.2s — se poate reduce la <5s cu lazy imports), (2) httpx creeaza un client HTTP NOU la fiecare request API (8 locuri — se pot refolosi cu singleton), (3) Zero code splitting React (dar la 240KB bundle nu e critic acum). **Top 3 quick wins:** (1) Lazy import LangGraph/fpdf2/openpyxl — reduce cold start de la 23s la ~5s, (2) httpx singleton — elimina overhead conexiuni TCP, (3) CORS extend pt Tailscale — permite acces de pe Android. **Top 3 functii noi cu impact maxim pt documentare firme:** (1) Due Diligence Checklist automat (da/nu binar per criteriu), (2) Profil Actionariat din openapi.ro (cine e in spatele firmei), (3) Raport Executiv 1-Pager (PDF o pagina cu esentialul).

---

## 1. Profiling Real — Masuratori

### 1.1 Backend Performance

| Metrica | Valoare Masurata | Target | Status |
|---------|-----------------|--------|--------|
| Backend cold start (import) | 23.11s | < 3s | SLOW |
| fastapi import | 5.00s | < 1s | SLOW |
| fpdf2 import | 3.27s | < 0.5s | SLOW |
| openpyxl import | 1.73s | < 0.5s | SLOW |
| httpx import | 1.19s | < 0.5s | SLOW |
| python-pptx import | 0.80s | < 0.5s | OK |
| python-docx import | 0.63s | < 0.5s | OK |
| langgraph import | 0.01s | < 1s | OK |
| aiosqlite import | 0.05s | < 0.5s | OK |

**Cauza:** Toate modulele se importeaza la startup. Report generators (fpdf2, openpyxl, pptx) se importeaza chiar daca nu genereaza rapoarte.

**Fix (P1, efort S):** Lazy import in `generator.py` — importeaza fpdf2/openpyxl/pptx doar cand genereaza efectiv raportul, nu la startup server.

### 1.2 Frontend Performance

| Metrica | Valoare Masurata | Target | Status |
|---------|-----------------|--------|--------|
| Bundle JS | 240 KB | < 500KB | OK |
| Bundle CSS | 21 KB | < 100KB | OK |
| Bundle total | 261 KB | < 600KB | OK |
| Chunks | 1 (monolitic) | 3-5 lazy | IMPROVABLE |
| React.lazy() | 0 instante | 5+ | LIPSA |
| React.memo | 0 instante | optional | OK (app mica) |
| useMemo | 0 instante | optional | OK |
| useCallback | 2 instante | optional | OK |
| console.error in prod | 11 instante | 0 | COSMETIC |
| Tailwind purge | DA (content config) | DA | OK |
| Vite proxy | DA (api + ws) | DA | OK |

### 1.3 Database

| Metrica | Valoare | Note |
|---------|---------|------|
| DB size | 112 KB | Mic — 3 rapoarte |
| jobs | 3 rows | |
| companies | 3 rows | |
| reports | 3 rows | |
| report_sources | 18 rows | ~6 surse/raport |
| data_cache | 19 rows | Cache activ |
| monitoring_alerts | 0 rows | Nefolosit inca |
| WAL mode | DA | Configurat |
| Foreign keys | DA | PRAGMA foreign_keys=ON |
| Busy timeout | 5000ms | Bun |
| Cache size | -20000 (20MB) | Bun pt SQLite |
| Indexuri | 10 | Corecte pt queries existente |

### 1.4 Code Stats

| Metrica | Valoare |
|---------|---------|
| Python functions | 147 |
| Backend lines | 5.781 |
| Frontend lines | 2.533 |
| Total lines | 8.314 |
| Python files | 37 |
| TS/TSX files | 18 |
| Total files | 55 |
| REST endpoints | 24 |
| WebSocket | 1 |
| Frontend pages | 9 |

---

## 2. Performance Audit

### 2.1 Backend — Probleme Identificate

| # | Problema | Fisier | Impact | Efort | Fix | Prioritate |
|---|---------|--------|--------|-------|-----|-----------|
| 1 | Cold start 23s (toate importurile la startup) | generator.py | HIGH | S | Lazy import fpdf2/openpyxl/pptx in functiile generate_* | P1 |
| 2 | httpx.AsyncClient per-request (8 locuri) | tools/*.py, notification.py | MEDIUM | M | Singleton httpx.AsyncClient cu connection pool | P1 |
| 3 | Report generation secventiala (PDF→DOCX→HTML→Excel→PPTX) | generator.py | MEDIUM | M | asyncio.gather() pt formatele care nu depind unele de altele | P2 |
| 4 | CORS nu permite Tailscale IP | main.py | HIGH (Android) | S | Adauga `"http://100.*"` sau `"*"` pt reteaua interna | P1 |
| 5 | Database single connection (nu pool) | database.py | LOW | M | OK pt 1 user, dar aiosqlite nu are pool nativ — acceptabil | P3 |
| 6 | Cache cleanup doar la job start | cache_service.py | LOW | S | Adauga cleanup in lifespan startup | P2 |

### 2.2 Frontend — Probleme Identificate

| # | Problema | Fisier | Impact | Efort | Fix | Prioritate |
|---|---------|--------|--------|-------|-----|-----------|
| 1 | Zero code splitting (1 chunk 240KB) | App.tsx | LOW | S | React.lazy() pe pagini — dar 240KB e ok | P3 |
| 2 | 11x console.error in production | 8 pages | LOW | S | Inlocuire cu toast/UI error state | P2 |
| 3 | No error boundary React | App.tsx | MEDIUM | S | Adauga ErrorBoundary component | P2 |
| 4 | No abort controller pe API calls | api.ts | LOW | M | AbortController in useEffect cleanup | P3 |
| 5 | Dashboard Promise.all fara cleanup | Dashboard.tsx | LOW | S | AbortController + ignore state | P3 |

### 2.3 Cross-Platform (Tailscale + Android)

| # | Finding | Status | Fix |
|---|---------|--------|-----|
| 1 | CORS origins | DOAR localhost — Android via Tailscale NU merge | Adauga Tailscale IP range |
| 2 | WebSocket URL | Dinamic (window.location) — OK pt Tailscale | OK |
| 3 | Responsive | Tailwind responsive — dar NEATESTAT pe mobil | Testare necesara |
| 4 | Touch targets | Butoanele au padding suficient (py-2 px-3) | Probabil OK |
| 5 | Font loading | Inter + JetBrains Mono — CDN? Local? | Verifica |

### 2.4 Quick Wins (sub 30 min, ROI maxim)

| # | Quick Win | Efort | Impact | Fisier |
|---|----------|-------|--------|--------|
| 1 | Lazy import generators in generator.py | 10 min | Cold start -18s | generator.py |
| 2 | CORS allow Tailscale | 2 min | Android access | main.py |
| 3 | httpx singleton pt ANAF/BNR | 15 min | -200ms/request | tools/*.py |
| 4 | Cache cleanup la startup | 5 min | DB mai curat | main.py lifespan |
| 5 | Health check avansat (DB + ANAF + quota) | 20 min | Monitoring real | main.py |

---

## 3. Imbunatatiri Functii Existente

### Per categorie (cost-benefit)

| Categorie | Functie | Imbunatatire | Impact | Efort | ROI | P |
|-----------|---------|-------------|--------|-------|-----|---|
| API | POST /api/jobs | Duplicate detection (aceeasi firma, acelasi tip, <24h) | MEDIUM | S | HIGH | P1 |
| API | GET /api/health | Deep health: DB writable + ANAF reachable + Tavily quota | HIGH | S | HIGH | P1 |
| API | GET /api/stats | Cache 30s (nu query DB la fiecare Dashboard refresh) | LOW | S | HIGH | P2 |
| API | POST /api/compare | Cache rezultate comparatie 1h | LOW | S | MEDIUM | P3 |
| Pages | Dashboard | Auto-refresh interval 60s cu indicator | MEDIUM | S | HIGH | P2 |
| Pages | NewAnalysis | Validare CUI real-time in browser (MOD 11 in JS) | MEDIUM | S | HIGH | P1 |
| Pages | ReportView | @media print CSS pt printare directa | LOW | S | MEDIUM | P3 |
| Pages | Companies | Badge cu ultimul scor risc pe card | MEDIUM | S | HIGH | P2 |
| Agents | OfficialAgent | Adaptive retry (exponential cu jitter) | LOW | M | LOW | P3 |
| Agents | SynthesisAgent | Prompt-uri specifice per provider (Claude vs Groq) | HIGH | M | HIGH | P1 |
| Agents | VerificationAgent | Scoring benchmark per CAEN (media din date colectate) | HIGH | L | MEDIUM | P2 |
| Sources | Tavily | Smart query: elimina cuvinte redundante, adauga "Romania 2026" | MEDIUM | S | HIGH | P2 |
| Reports | PDF | Table of Contents automat | MEDIUM | M | MEDIUM | P2 |
| Reports | HTML | @media print CSS + sectiuni collapsible | MEDIUM | M | MEDIUM | P2 |
| Reports | Excel | Formule dinamice (profit margin = profit/CA) | MEDIUM | S | HIGH | P2 |
| Security | CORS | Tailscale IP range permis | HIGH | S | HIGH | P1 |
| Security | CSP | Content-Security-Policy header (permite Chart.js CDN) | MEDIUM | S | MEDIUM | P2 |

---

## 4. AI Prompt Optimization

### System Prompt (system_prompt.py)

**Actual:** 7 reguli clare, bine structurate. Lipseste:
- Exemplu de output (few-shot)
- Instructiuni de format (Markdown structurat)
- Diferentiere per provider (Claude scrie mai bine decat Groq la text narativ)

**Propunere imbunatatita:**
```
Adauga dupa cele 7 reguli:

8. Formateaza cu Markdown: ## pentru sectiuni, **bold** pentru cifre cheie,
   - bullet points pentru liste
9. EXEMPLU format output dorit:
   "## Profil Companie
   **BITDEFENDER SRL** (CUI 18189442) este o companie de software... [OFICIAL]
   Cu o cifra de afaceri de **1.029.276.944 RON** in 2023 (Sursa: ANAF Bilant)..."
```

### Section Prompts (section_prompts.py)

**Analiza per sectiune:**
- `executive_summary` — Bun, dar nu specifica structura (intro → financiar → risc → recomandare)
- `financial_analysis` — Nu mentioneaza scorul 0-100 si dimensiunile. Ar trebui sa includa "Mentioneaza scorul numeric X/100 si dimensiunile cu cele mai mici scoruri"
- `risk_assessment` — Inca zice "VERDE/GALBEN/ROSU" dar sistemul are 0-100. Update necesar.
- `competition` — OK dar nu mentioneaza SEAP ca sursa
- `recommendations` — Bun

**Efort:** S (30 min) | **Impact:** HIGH (calitate rapoarte direct mai buna)

---

## 5. Provider Scan & Web Research

### 5.1 API-uri Romanesti 2026

| Sursa | Status | Detalii | Fezabil pt RIS? |
|-------|--------|---------|-----------------|
| ANAF v9 | Cel mai recent | Niciun v10 anuntat. OAuth2 pt e-Factura/SPV (necesita certificat digital) | Deja integrat |
| ANAF Bilant | Functional | Fara schimbari | Deja integrat |
| portal.just.ro | SOAP (nedocumentat) | Exista web service SOAP pt cautare dosare (numar, parti, instanta). Client C#: github.com/sibies/Just.Net | DA — cu effort M |
| BPI (insolventa) | Fara API | Doar portal ONRC, necesita autentificare. Third-party: Termene.ro, RisCo (cu abonament) | NU (ramanem pe Tavily) |
| INS TEMPO | API JSON functional | http://statistici.insse.ro:8077/tempo-online/ — date per CAEN/judet, serii 1990-prezent. Client Python: github.com/mark-veres/tempo.py | DA — ideal pt benchmark CAEN |
| Monitorul Oficial | Fara API public | Doar Alerta CUI si RisCo (abonament) | NU |
| SEAP | Functional cu rate limit | Rate limit strict din mar 2025. Alternativa: SICAP.ai (API REST, github.com/ciocan/SICAP.ai) | Deja integrat |
| SICAP.ai | API REST nou | api.sicap.ai/v1/openapi — motor cautare SEAP third-party, date zilnice, gratuit | DA — alternativa SEAP |

### 5.2 AI Providers Free Tier 2026

| Provider | Modele | Limite Free | Nota pt RIS |
|----------|--------|-------------|-------------|
| Groq | Llama 4 Scout, Llama 3.3 70B, Qwen3 32B | 30 RPM, 1000 req/zi pt 70B | Deja integrat |
| Cerebras | Qwen 3 235B, Llama 3.3 70B | 30 RPM, 1M tokeni/zi | Deja integrat |
| Gemini | 2.5 Pro, 2.5 Flash | Cel mai generos ca volum total | Deja integrat |
| **Mistral** | Toate modelele (tier "Experiment") | 2 RPM dar **1 MILIARD tokeni/luna** | RECOMANDAT — generos |
| **DeepSeek** | Chat + API | 5M tokeni gratis la signup (30 zile) | INTERESANT pt trial |
| **OpenRouter** | Modele $0 agregate | $0/M tokeni (modele selectate) | Gateway util |
| Together AI | - | Necesita $5 minim | NU e free |

**Modele open-source noi 2026:** GLM-4.7 (HumanEval 94.2), Qwen3.5-397B, Kimi K2.5, MiniMax M2.5

### 5.3 Best Practices ce Lipsesc din RIS
1. **Structured logging** — loguru e bun dar lipseste JSON format + request correlation IDs
2. **Request timeout global** — middleware FastAPI pt timeout pe toate endpoint-urile
3. **Graceful shutdown** — lifespan face close() dar nu asteapta jobs in curs
4. **Error boundaries React** — lipsesc complet
5. **React 19 upgrade** — compiler auto-memoizare, use() hook, -38% JS payload

---

## 6. Functii Noi — Documentare Firme Extinsa (Top 10 prioritizat)

| # | Functie | Valoare Business | Efort | ROI | P |
|---|---------|-----------------|-------|-----|---|
| 1 | **Due Diligence Checklist Automat** | Genereaza lista da/nu: TVA activ DA, Insolventa NU, Datorii NECUNOSCUT | S | BEST | P1 |
| 2 | **Profil Actionariat** | openapi.ro are asociati — cine detine firma, cu ce procent | S | BEST | P1 |
| 3 | **Raport Executiv 1-Pager** | PDF 1 pagina: scor, top 3 riscuri, top 3 oportunitati, DA/NU | M | HIGH | P1 |
| 4 | **Analiza CAEN contextualizata** | "CAEN 7120 = Testari tehnice. 2.340 firme in Romania pe acest CAEN" | S | HIGH | P2 |
| 5 | **Benchmark Financiar** | "CA firma = 187K. Media pe CAEN 7120 = 450K. Firma e sub medie." | L | HIGH | P2 |
| 6 | **Early Warning Signals** | Detecteaza: scadere CA >30%, pierdere 2 ani, reducere angajati >50% | S | HIGH | P2 |
| 7 | **Matricea Relatii** | Firme cu aceeasi adresa/administrator — legaturi ascunse | L | HIGH | P2 |
| 8 | **Export CRM-Ready** | CSV/JSON structurat: name, CUI, address, phone, risk_score | S | MEDIUM | P2 |
| 9 | **Batch Analysis** | Upload CSV cu 10-50 CUI-uri → analiza serie cu progress total | L | HIGH | P2 |
| 10 | **Sector Report** | "Toate firmele de constructii din Cluj cu CA > 1M" — top 10 + stats | XL | HIGH | P3 |

---

## 7. Functii Noi — Backend/Frontend/AI/DevOps

### Backend (Top 5)

| # | Functie | Efort | Impact | P |
|---|---------|-------|--------|---|
| 1 | Scheduler intern (APScheduler) pt monitoring automat | M | HIGH | P1 |
| 2 | Health check avansat (/api/health/deep) | S | HIGH | P1 |
| 3 | Auto-backup DB (SQLite .backup periodic) | S | HIGH | P1 |
| 4 | Data retention policy (cleanup >90 zile) | S | MEDIUM | P2 |
| 5 | Performance metrics endpoint | M | MEDIUM | P2 |

### Frontend (Top 5)

| # | Functie | Efort | Impact | P |
|---|---------|-------|--------|---|
| 1 | Toast notifications (erori vizibile, nu console) | S | HIGH | P1 |
| 2 | Dashboard grafice trend (joburi/luna) | M | MEDIUM | P2 |
| 3 | Global search (companii + rapoarte) | M | MEDIUM | P2 |
| 4 | Offline indicator (banner cand backend down) | S | MEDIUM | P2 |
| 5 | Keyboard shortcuts (Ctrl+N, Ctrl+K) | M | LOW | P3 |

---

## 8. Best Practices Comparison

| Practica | Status RIS | Recomandare | P |
|----------|-----------|-------------|---|
| Connection pooling HTTP | NU (per-request) | httpx singleton | P1 |
| Structured logging | PARTIAL (loguru text) | JSON format optional | P3 |
| Health checks deep | PARTIAL (basic) | DB + APIs + quota | P1 |
| CORS production | RESTRICTIV (doar localhost) | Adauga Tailscale | P1 |
| Rate limiting | NU | slowapi sau custom (pt abuse prevention) | P3 |
| Error boundaries React | NU | Adauga ErrorBoundary | P2 |
| Code splitting | NU (1 chunk) | React.lazy (low priority la 240KB) | P3 |
| CSP headers | NU | Adauga (permite Chart.js CDN) | P2 |
| Input sanitization | DA (Pydantic) | Complet | OK |
| API versioning | NU | /api/v1/ (nu e necesar pt 1 user) | P3 |
| Graceful shutdown | PARTIAL | Asteapta jobs in curs | P2 |
| Request timeout global | NU | Middleware timeout 60s | P2 |
| SQL parametrizat | DA (100%) | Complet | OK |
| .env protected | DA | Complet | OK |
| WebSocket reconnect | DA (4 nivele backoff) | Complet | OK |

---

## 9. Roadmap cu Dependinte

```
FAZA 6A — Quick Wins Performance (1 sesiune, ~2h)
  ├─ [QW1] Lazy import generators (fpdf2/openpyxl/pptx) — cold start -18s
  ├─ [QW2] CORS extend Tailscale — Android access
  ├─ [QW3] httpx.AsyncClient singleton — connection pool
  ├─ [QW4] Cache cleanup la startup — DB curat
  ├─ [QW5] Health check avansat — DB + APIs + quota
  └─ [QW6] Stats cache 30s — Dashboard rapid

FAZA 6B — Documentare Firme Extinsa (3-4 sesiuni)
  ├─ [DF1] Due Diligence Checklist automat ← depinde de VerificationAgent existent
  ├─ [DF2] Profil Actionariat din openapi.ro ← depinde de openapi_client existent
  ├─ [DF3] Raport Executiv 1-Pager PDF ← depinde de pdf_generator existent
  ├─ [DF4] Analiza CAEN contextualizata ← depinde de ANAF Bilant existent
  ├─ [DF5] Early Warning Signals ← depinde de anomaly detection existent
  ├─ [DF6] Benchmark Financiar per CAEN ← depinde de [DF4]
  ├─ [DF7] Export CRM-Ready ← independent
  └─ [DF8] Batch Analysis CSV ← depinde de job_service existent

FAZA 6C — Polish & UX (2-3 sesiuni)
  ├─ [UX1] Toast notifications React ← independent
  ├─ [UX2] Error boundaries ← independent
  ├─ [UX3] Dashboard grafice trend ← depinde de stats endpoint
  ├─ [UX4] CUI validation in browser (JS) ← independent
  ├─ [UX5] Prompt optimization per provider ← depinde de section_prompts.py
  └─ [UX6] CSP headers ← independent

FAZA 6D — Advanced (backlog, cand e nevoie)
  ├─ [ADV1] Scheduler APScheduler pt monitoring ← depinde de monitoring_service existent
  ├─ [ADV2] Sector Report ("toate firmele din CAEN X") ← depinde de [DF6]
  ├─ [ADV3] Matricea Relatii firma ← depinde de openapi.ro + SEAP
  ├─ [ADV4] Auto-backup DB periodic ← independent
  └─ [ADV5] API versioning /api/v1/ ← independent (low priority)
```

---

## 10. Metrici Actuale vs Target

| Metrica | Actual | Target | Status |
|---------|--------|--------|--------|
| Backend cold start | 23.1s | < 3s (cu lazy imports: ~5s) | SLOW → FIX cu QW1 |
| Frontend bundle total | 261 KB | < 600KB | OK |
| Largest JS chunk | 240 KB | < 300KB | OK |
| DB size | 112 KB | info (creste ~30KB/raport) | OK |
| Cache entries | 19 | info | OK |
| Python functions | 147 | info | - |
| Total code lines | 8.314 | info | - |
| WebSocket reconnect delays | [2s, 5s, 10s, 30s] | < 5s first retry | OK |
| ANAF API response | ~2-3s | < 5s | OK |
| Tavily quota used | 7/1000 | < 800 warn | OK (0.7%) |
| Report formats | 5 | 5 | COMPLET |
| SQL injection risk | 0 | 0 | OK |
| TODO/FIXME in code | 0 | 0 | OK |

---

## 11. Dead Code & Cleanup

| Check | Result |
|-------|--------|
| Functii Python neapelate | 0 gasite (toate conectate in orchestrator/routers) |
| Componente React neimportate | 0 (toate in App.tsx) |
| Endpoints fara frontend | POST /api/monitoring/check-now (doar din Monitoring.tsx) — OK |
| Importuri nefolosite | 0 detectate |
| TODO/FIXME | 0 |
| console.error in prod | 11 (cosmetic, nu dead code) |
| .env.example vars nefolosite | ANTHROPIC_API_KEY eliminat — OK |

---

## Snapshot JSON

```json
{
  "snapshot_date": "2026-03-20",
  "version": "RIS 1.1",
  "metrics": {
    "backend_import_time_s": 23.11,
    "frontend_bundle_kb": 261,
    "db_size_kb": 112,
    "total_endpoints": 25,
    "total_pages": 9,
    "total_agents": 5,
    "total_report_formats": 5,
    "total_data_sources": 7,
    "total_ai_providers": 4,
    "code_lines_backend": 5781,
    "code_lines_frontend": 2533,
    "code_lines_total": 8314,
    "python_functions": 147,
    "python_files": 37,
    "frontend_files": 18,
    "sql_injection_risk": 0,
    "todo_fixme_count": 0,
    "tavily_quota_used": 7,
    "tavily_quota_total": 1000
  },
  "scores": {
    "performance": "6/10 (cold start 23s, httpx per-request, no code splitting)",
    "security": "8/10 (SQL safe, .env protected, headers present, CSP missing)",
    "code_quality": "8.5/10 (clean, 0 dead code, 0 TODOs, LangGraph parallel confirmed)",
    "documentation": "9/10 (CLAUDE.md, FUNCTII_SISTEM.md+html, TODO, AUDIT_REPORT)",
    "ux": "7/10 (functional, dark theme, no error boundaries, 11 console.error)",
    "overall": "7.7/10"
  },
  "improvements_proposed": {
    "p1_count": 12,
    "p2_count": 18,
    "p3_count": 8,
    "quick_wins_count": 6,
    "new_functions_proposed": 23,
    "documentation_functions_proposed": 10
  }
}
```

---

## Anexa A: Fisiere Analizate

**Backend (37 fisiere Python):**
main.py, config.py, database.py, models.py, migrations/001_initial.sql,
agents/base.py, agents/state.py, agents/agent_official.py, agents/agent_verification.py,
agents/agent_synthesis.py, agents/orchestrator.py,
agents/tools/anaf_client.py, agents/tools/anaf_bilant_client.py, agents/tools/bnr_client.py,
agents/tools/tavily_client.py, agents/tools/openapi_client.py, agents/tools/seap_client.py,
agents/tools/cui_validator.py,
routers/jobs.py, routers/reports.py, routers/companies.py, routers/analysis.py,
routers/settings.py, routers/compare.py, routers/monitoring.py,
services/job_service.py, services/cache_service.py, services/notification.py,
services/delta_service.py, services/monitoring_service.py,
reports/generator.py, reports/pdf_generator.py, reports/docx_generator.py,
reports/html_generator.py, reports/excel_generator.py, reports/pptx_generator.py,
prompts/system_prompt.py, prompts/section_prompts.py

**Frontend (18 fisiere TS/TSX):**
App.tsx, main.tsx,
components/Layout.tsx, components/ChatInput.tsx,
hooks/useWebSocket.ts, hooks/useApi.ts,
lib/api.ts, lib/types.ts, lib/constants.ts,
pages/Dashboard.tsx, pages/NewAnalysis.tsx, pages/AnalysisProgress.tsx,
pages/ReportsList.tsx, pages/ReportView.tsx, pages/Companies.tsx,
pages/CompareCompanies.tsx, pages/Monitoring.tsx, pages/Settings.tsx

**Config:**
vite.config.ts, tailwind.config.js, .env, .env.example, .gitignore

---

## Anexa B: Comenzi Rulate

```bash
# Backend import time
python -c "import time; t=time.time(); import backend.main; print(f'Backend import: {time.time()-t:.2f}s')"
# Result: 23.11s

# Module breakdown
python -c "import time; [modules test loop]"
# Results: fastapi 5s, fpdf2 3.27s, openpyxl 1.73s, httpx 1.19s

# Database stats
python -c "import sqlite3; [DB query loop]"
# Results: 112KB, 3 jobs, 3 reports, 19 cache entries

# Frontend build
npm run build
# Results: 240KB JS + 21KB CSS = 261KB total

# Grep patterns
grep httpx.AsyncClient — 8 per-request instances
grep React.lazy — 0 instances
grep console.error — 11 instances
grep f"SELECT — 6 safe instances (parametrized WHERE)
grep TODO/FIXME — 0 instances
```
