# Roland Intelligence System (RIS)

## Overview
Sistem local de Business Intelligence care ruleaza pe Windows 10. Extrage automat date din surse publice romanesti (ANAF, ONRC, SEAP, etc.), le proceseaza prin agenti AI si produce rapoarte profesionale.

## Status
- **Faza 1:** Fundatie — COMPLETATA
- **Faza 2:** Agenti de date — COMPLETATA (Agent 1 + Agent 4 + LangGraph + Cache)
- **Faza 3:** Sinteza + Rapoarte — COMPLETATA (Synthesis + PDF + DOCX + HTML)
- **Faza 4:** UI complet + livrare — COMPLETATA (Chatbot + Settings + Notifications + ReportView)
- **Faza 4.5:** Audit + Extensii — COMPLETATA (ANAF Bilant, CUI Validation, Scoring 0-100, Cross-validation, Security headers)
- **Faza 5:** COMPLETATA — Excel, Chart.js, Comparator, Anomalii, Delta, Agent 2+3, openapi.ro, Monitoring, PPTX
- **Faza 6A:** COMPLETATA — Lazy imports, CORS Tailscale, httpx singleton, cache cleanup, health deep, stats cache
- **Faza 6B:** COMPLETATA — Due Diligence, Actionariat, Early Warnings, Export CSV, 1-Pager PDF, CAEN Context, Benchmark, Batch CSV
- **Faza 6C:** COMPLETATA — Toast notifications, Error Boundaries, Dashboard trend, CUI validator JS, Prompt optimization, CSP headers
- **Faza 6D:** COMPLETATA — Scheduler monitoring, INS TEMPO live, Auto-backup DB, Sector Report, Matricea Relatii, AI Smart Routing, AI Pre-processing, React 19
- **Faza 7A:** COMPLETATA — Data Quality: SEAP routing fix, httpx import, data_found logic, ONRC integration, completeness check, anti-halucinare, diagnostic in raport HTML
- **Faza 7B:** COMPLETATA — PATH TRAVERSAL fix, requirements.txt, .gitignore, PRAGMA optimize, sqlite3.backup, toast catches, 404 route, conditional reload, secret key warning
- **Faza 7C:** COMPLETATA — Batch persistent DB, rate limiting, API key auth (X-RIS-Key), api.ts complet, CSP hardened, SEAP cache, few-shot prompts
- **Faza 7D:** COMPLETATA — 28 pytest tests, 11 vitest tests, split agent_verification (scoring+completeness), React.lazy 10 pagini, retry logic (ANAF+openapi.ro)
- **Faza 7E:** COMPLETATA — CAEN fallback Bilant, retry BNR+SEAP, completeness gate <50%, anti-halucinare prompts (competition/opportunities/swot), GET /api/jobs/{id}/diagnostics, POST /api/jobs/{id}/retry-source/{source}
- **Faza 8A:** COMPLETATA — Gzip middleware, API caching headers, structured error codes (ErrorCode enum), cache stats endpoint, scheduler cache cleanup 12h
- **Faza 8B:** COMPLETATA — Trend scoring (growth factor), volatility index (CV multi-an), solvency ratio, age-adjusted scoring, angajati trend penalty, reputational nuantat
- **Faza 8C:** COMPLETATA — Dynamic word count per sectiune, context awareness injection, provider routing per section, ZIP auto-pack all formats
- **Faza 8D:** COMPLETATA — Orchestrator timing metrics per nod, error boundaries Agent 2/3, cache ANAF compare, consistent risk scoring, compare persistence DB, batch retry 2x, rich summary CSV
- **Faza 8E:** COMPLETATA — Smart alert severity (RED/YELLOW/GREEN), audit log monitoring, score history DB, expanded delta (TVA+split), Telegram severity icons
- **Faza 9A:** COMPLETATA — Parallel source fetching (asyncio.gather), error boundaries 5/5 agenti, request size 10MB, cache hit/miss tracking, data freshness tracking
- **Faza 9B:** COMPLETATA — Cash flow proxy intelligence, anomaly feedback loop (Agent 4→5), confidence scoring per dimension, provider capacity awareness auto-truncate
- **Faza 9C:** COMPLETATA — Pagination Companies+Reports (PAGE_SIZE 20), API key masking (Eye toggle), responsive mobile sidebar (drawer), ApiError class+429 handler, error codes in toast
- **Faza 9D:** COMPLETATA — Watermark CONFIDENTIAL (PDF diagonal + HTML CSS overlay), TOC DOCX (Word TOC field), TOC PDF (Cuprins page with page numbers)
- **Faza 9E:** COMPLETATA — Alert dedup 24h (monitoring_service), batch resume endpoint (POST /batch/{id}/resume)
- **Faza 10A:** COMPLETATA — CUI early return, Tavily quota pre-check, ANAF year-range smart, Tavily query merge, Confidence-aware synthesis, Cache versioning, Scheduler checkpoints DB, CORS preflight cache 24h
- **Faza 10B:** COMPLETATA — Trend decomposition (base growth+volatility+anomaly), Sector decile positioning, Output validation+self-correction, Cross-section coherence
- **Faza 10C:** COMPLETATA — Health status card live, Completeness gate badge, Search debouncing 300ms, CUI validator on Compare, Retry button on API errors
- **Faza 10D:** COMPLETATA — Time-series delta 2-5 ani, Financial ratios auto-calc, Chart.js data format return, PDF bookmarks, Excel CAGR KPI, DOCX custom properties
- **Faza 10E:** COMPLETATA — Severity throttling, Alert escalation retry 3x, Monitoring health endpoint, Batch state checkpoint, CSV pre-validation
- **Faza 10F:** COMPLETATA — Solvency stress matrix 3x3, Early warning confidence, Structured degradation 3-tier, Prompt injection hardening, Token budget enforcement, Parallel Agent 2+3, Request dedup, State checkpoint recovery, Anomaly flags delta, Sector percentile scoring, Parallel batch 2-CUI, Batch queue max 2, Fresh data option, Cache LRU 100MB, HTTP pool metrics, Event-driven invalidation, Request ID tracing, Error sanitization, Sensitive data redaction, Request validation handler, Form validation, HTML responsive mobile
- **Faza 11 (R4):** COMPLETATA — 27 bug fixes: B1-B27 (6 CRIT + 13 HIGH + 8 MED) — bilant crash, schema mismatch, CAEN chain, synthesis quality, reports data, cache race, delta dimensions
- **Faza 12 (R5):** COMPLETATA — 25 deep research fixes: C1-C25 (4 CRIT + 16 HIGH + 5 MED) — delta dead, SEAP bonus, TOC accuracy, settings phantom, cache invalidation, batch safety, PDF/HTML fixes
- **Faza 13 (R6):** COMPLETATA — 21 items: D1-D21 (1 CRIT + 12 HIGH + 7 MED) + 4 N-items (financial ratios, charts, exec summary, company page)
- **Faza 14 (R7):** COMPLETATA — 15 items: E1-E13 + EP1-EP3 + ER1-ER2 — calitate rapoarte, surse noi (BPI insolventa, ANAF inactivi/risc fiscal), anti-halucination, template-uri, raport comparativ PDF, sparkline trend, Excel Trend sheet
- **Faza 15 (R8):** COMPLETATA — 21 items: F1-F21 (3 CRIT + 9 HIGH + 8 MED + 1 LOW) — WS bug fix, HTML tables/bold/numbered lists, version unify, PRAGMA optimize, dead deps cleanup, silent except→logger.debug, anti-hallucination skip, DRY providers, split verification (1248→982 LOC), BPI robust, compare PDF narrative, teste html/orchestrator/pdf, PDF markdown tables
- **Faza 16 (R9):** COMPLETATA — 41 items in 5 BLOC-uri: BPI false positive fix + 11 teste, anti-hallucination hardening (completeness gate, prompt, competitor detection) + 14 teste, HTML/PDF edge cases (separator, XSS, column norm, truncation) + 7 teste, Compare PDF ratii financiare + narrative, dead code cleanup + scoring tests + datetime migration
- **Faza 17 (R10):** COMPLETATA — Audit Full 90/100 + R10 unificat: unused deps removed (python-dotenv, jinja2), ALL datetime.utcnow migrated (29 locations, 0 warnings), WS auth token, scoring constants extracted, README.md, 15 router tests, comment cleanup, DB except fix
- **Faza 18 (R11):** COMPLETATA — 40 imbunatatiri din /imbunatatiri: scoring confidence power-law fix, zombie detection, dynamic completeness, monitoring critical combos, provider circuit breaker, L1 cache, DRY scoring compare, token pre-check, SQLite cache 64MB, dashboard trends, breadcrumbs, wizard progress, ETA progress, batch CSV preview, global search Ctrl+K, compare CSV export, report metadata, company actions (monitor/compare/similar), settings test all, api.ts timeout+errors, notifications center (CRUD+migration), favorites, risk movers endpoint, company timeline, email report send, PDF encoding unicodedata, HTML warnings gradient, .env backup
- **Faza 19 (R12):** COMPLETATA — 17 items R2 fix+completare: notifications create integration (job_service+monitoring), circuit breaker wired in synthesis (Groq/Gemini/Cerebras/Mistral), AbortController fix retry, L1 cache threading lock, email field_validator, zombie exclude inactive, CSV header detection, ETA progress guard, monitoring loading state, Notification Bell UI (poll 60s+dropdown+mark read), Favorites UI (star+filter), Risk Movers Widget, Timeline UI (CompanyDetail), Email Send Modal (ReportView), circuit_breaker.py module (circular import fix)
- **Faza 20 (R13):** COMPLETATA — 39 items din RECOMANDARI_IMBUNATATIRI_R3: P0(#31 .env.bak gitignore, #32 datetime UTC 4 loc, #2 memory leak _in_flight, #1 agent timeout individual, #21+26 input validation+extra=forbid), P1(#33 DB transactions, #34 report /data endpoint, #35 22x bare except→logger, #7 scoring Why reasons, #3 HTTPException→RISError, #4 api.ts endpoints, #5 WS agent_start/complete, #15 FTS5 search, #22 SSRF prevention, #24 path traversal hardening, #25 pip-audit script, #36 settings auth+security.py), P2(#37 tsconfig strict, #38 stats cache lock, #39 is_favorite fix, #40 DB indexes, #41 conditional sleep, #42 config validation, #9 concurrent fallback synthesis, #6 cache L1/LRU, #8 GlobalSearch rapoarte+actiuni, #10 scoring volatilitate per industrie, #11 companies sort+filter, #14 dashboard skeleton, #16 useOptimistic favorites, #17 report delta endpoint+UI, #18 PDF markdown helper, #19 SQL window functions score trend, #23 dead code cleanup, #29 accessibility ARIA, #30 token budget single-build), P3(#12 toast dedup, #13 favorites endpoint dedicat)
- **Audit R14 (2026-04-05):** EFECTUAT — scor 82/100 (delta -8 vs R10 90/100). Plan: 99_Plan_vs_Audit/RECOMANDARI_IMBUNATATIRI_R4.md (F0-F6, 28 items). Probleme critice: API key Gemini in logs, 47 fisiere necomise. Scor tinta dupa F0-F5: 90/100.
- **Audit R15 (2026-04-06):** EFECTUAT — scor 86/100 (+4 vs R14). Plan unificat: RECOMANDARI_IMBUNATATIRI_R5.md (53 items din 3 surse). 184 pytest PASSED, 0 failures. TypeScript: 0 erori.
- **Faza R5 (2026-04-06):** COMPLETATA — 47/53 items implementate (F0 9/9 + F1 10/10 + F2 15/15 + F3 11/13 + F4 4/6). 13 feature-uri noi: webhook, quick-score, tags+note, compare templates, sector CAEN, ICS export, batch preview, health status, CLI script, browser notifications, watermark config, key takeaways, score sparkline.
- **Feedback Loop:** ACTIV — RIS_TEST.bat, logs/ris_summary.log, ris_runtime.log, ris_frontend.log (5 componente), ISSUES.md, session startup protocol, G1-G8 complete
- **Git:** https://github.com/RolandPetrila/Sistem-Inteligent-Analize.git | 182 teste (171 pytest + 11 vitest)
- **12 pagini frontend** (adaugat CompanyDetail /company/:id)
- **Planificari detaliate:** ROLAND_PLANIFICARI_MODULE.md (R4 + R5 + R6 + R7 = 88 items total)
- **Deep Research:** 99_Deep_Research/ (2 rapoarte complete cu roadmap)
- **Spec complet:** SPEC_INTELLIGENCE_SYSTEM_V2.md
- **42 REST endpoints + 1 WebSocket + 12 pagini frontend + 8 formate raport + diagnostic + audit + request tracing + notifications + favorites + timeline**

## Feedback Loop (Session Protocol)
La FIECARE sesiune noua, Claude citeste automat:
1. `logs/ris_summary.log` — sumar per-analiza (CUI, status, score, erori)
2. `logs/ris_runtime.log` — erori de startup/runtime (WARNING+)
3. `ISSUES.md` — probleme raportate manual de utilizator
4. `TEST_RESULTS.log` — ultimul run RIS_TEST.bat (pytest + vitest)

Fisiere feedback loop:
- `RIS_TEST.bat` — dublu-click: ruleaza toate testele, salveaza in TEST_RESULTS.log
- `ISSUES.md` — utilizatorul noteaza minim: "ce am facut + ce s-a intamplat"
- `backend/services/job_logger.py` — logging automat per-job + summary consolidat
- `logs/ris_summary.log` — 1 linie per analiza (append automat la fiecare job finalizat)
- `logs/ris_runtime.log` — erori WARNING+ din backend (rotatie 5MB, retentie 7 zile)

## Stack
- Backend: Python 3.13 + FastAPI + SQLite (aiosqlite, WAL mode)
- Frontend: React 19 + Vite + TypeScript + Tailwind CSS
- AI: Claude CLI (Opus) + Groq (Llama 4 Scout) + Mistral (Small 3) + Gemini (2.5 Flash) + Cerebras (Qwen 3 235B) — 5-level fallback + smart routing
- ONRC: openapi.ro (100 req/luna gratuit, date structurate)
- Licitatii: SEAP e-licitatie.ro API (contracte publice)
- Search: Tavily API (1000 req/luna gratuit)
- PDF: fpdf2 (nu WeasyPrint — evitam GTK pe Windows)
- Notificari: Telegram Bot API (configurat)
- Statistici: INS TEMPO API (date oficiale per CAEN)

## Key Files
- `backend/main.py` — FastAPI entry point + WebSocket + lifespan + SecurityHeaders + CSP + scheduler
- `backend/config.py` — Settings din .env (pydantic-settings)
- `backend/database.py` — SQLite connection + migrations
- `backend/models.py` — Pydantic models + ANALYSIS_TYPES_META (9 tipuri)
- `backend/http_client.py` — httpx AsyncClient singleton (connection pool) + pool metrics
- `backend/routers/` — API routes (jobs, reports, companies, analysis, settings, compare, monitoring, batch)
- `backend/migrations/001_initial.sql` — Schema DB completa
- `backend/agents/base.py` — BaseAgent abstract (retry, timeout, logging)
- `backend/agents/state.py` — AnalysisState TypedDict + routing logic
- `backend/agents/agent_official.py` — Agent 1: ANAF + ANAF Bilant + BNR + Tavily + openapi.ro + CAEN + AI pre-processing
- `backend/agents/agent_verification.py` — Agent 4: trust labels + scoring 0-100 + cross-validation + due diligence + early warnings + actionariat + benchmark + relations
- `backend/agents/agent_synthesis.py` — Agent 5: Claude/Groq/Mistral/Gemini/Cerebras + smart routing + context awareness + dynamic word count
- `backend/agents/orchestrator.py` — LangGraph state machine + timing metrics + error boundaries
- `backend/errors.py` — Structured error codes (ErrorCode enum + RISError exception)
- `backend/migrations/002_phase8.sql` — Phase 8 schema: monitoring_audit, score_history, compare_history
- `backend/agents/tools/bpi_client.py` — BPI insolventa (buletinul.ro + Tavily fallback)
- `backend/agents/tools/anaf_client.py` — ANAF REST API v9 (TVA, stare, adresa, inactivi, risc fiscal)
- `backend/agents/tools/anaf_bilant_client.py` — ANAF Bilant API (CA, profit, angajati, multi-an)
- `backend/agents/tools/bnr_client.py` — BNR XML cursuri valutare
- `backend/agents/tools/tavily_client.py` — Tavily search cu quota tracking
- `backend/agents/tools/cui_validator.py` — Validare CUI cu cifra de control MOD 11
- `backend/agents/tools/openapi_client.py` — openapi.ro REST client (ONRC + asociati + administratori + CAEN)
- `backend/agents/tools/seap_client.py` — SEAP e-licitatie.ro (licitatii + achizitii directe)
- `backend/agents/tools/caen_context.py` — Context CAEN: 122 coduri + 96 sectiuni + benchmark + INS TEMPO live
- `backend/services/job_service.py` — Job execution + WS progress
- `backend/services/cache_service.py` — Cache cu TTL per sursa
- `backend/services/notification.py` — Telegram + Email notifications
- `backend/services/monitoring_service.py` — Verificare periodica firme + alerte Telegram
- `backend/services/scheduler.py` — Scheduler automat: monitoring la 6h + backup DB zilnic + rotatie 7 zile
- `backend/services/delta_service.py` — Comparatie raport nou vs anterior
- `backend/reports/generator.py` — Report orchestrator (PDF + DOCX + HTML + Excel + PPTX + 1-Pager)
- `backend/reports/pdf_generator.py` — PDF cu fpdf2, sanitize latin-1
- `backend/reports/docx_generator.py` — DOCX cu python-docx
- `backend/reports/html_generator.py` — HTML single-file dark theme + Chart.js grafice
- `backend/reports/excel_generator.py` — Excel cu openpyxl (4 sheet-uri + grafice native)
- `backend/reports/pptx_generator.py` — PowerPoint 7 slide-uri (python-pptx)
- `backend/reports/one_pager_generator.py` — PDF executiv 1-pager (scor, checklist, riscuri, benchmark)
- `backend/reports/compare_generator.py` — PDF comparativ 2 firme side-by-side
- `backend/routers/compare.py` — POST /api/compare + POST /api/compare/sector
- `backend/routers/monitoring.py` — CRUD alerte monitorizare + check-now
- `backend/routers/batch.py` — Batch analysis CSV (upload, progress, ZIP download)
- `frontend/src/App.tsx` — React Router + Layout (11 pagini)
- `frontend/src/main.tsx` — Entry point + ToastProvider + ErrorBoundary
- `frontend/src/components/Toast.tsx` — Toast notifications (success/error/warning/info)
- `frontend/src/components/ErrorBoundary.tsx` — Error boundary cu mesaj util + reload
- `frontend/src/components/Layout.tsx` — Sidebar nav (11 items)
- `frontend/src/pages/Dashboard.tsx` — Stats + trend chart + integrations + quick actions
- `frontend/src/pages/NewAnalysis.tsx` — Wizard 4 pasi + CUI validator instant
- `frontend/src/pages/BatchAnalysis.tsx` — Upload CSV + progress + ZIP download
- `frontend/src/pages/Companies.tsx` — Lista companii + Export CSV CRM
- `frontend/src/pages/Monitoring.tsx` — Monitorizare firme cu toast notifications
- `frontend/src/pages/CompanyDetail.tsx` — N4: Pagina per firma cu profil, rapoarte, scor history, re-analiza
- `frontend/src/pages/` — AnalysisProgress, ReportsList, ReportView, CompareCompanies, Settings
- `frontend/src/hooks/useWebSocket.ts` — WebSocket cu reconnect + ping/pong
- `frontend/src/lib/api.ts` — API client complet (toate endpoint-urile)
- `frontend/src/lib/cui-validator.ts` — Validare CUI MOD 11 in browser

## ANAF APIs
- **ANAF TVA/Stare (v9):** `POST https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva`
  - Returneaza 404 HTTP dar cu JSON valid (found/notFound) — NU face raise_for_status()
  - Rate limit: 1 req/2 sec
- **ANAF Bilant:** `GET https://webservicesp.anaf.ro/bilant?an={year}&cui={cui}`
  - Date financiare oficiale: CA, profit, angajati, capitaluri
  - Disponibil 2014-2024, gratuit
  - Indicatorii vin in `data["i"]` cu `indicator` code + `val_indicator` + `val_den_indicator`
  - Formatul indicatorilor difera intre firme mari/mici — parsam dupa val_den_indicator text

## Scoring System (Phase 8B enhanced)
- Scor numeric 0-100 pe 6 dimensiuni (ponderat):
  - Financiar (30%): CA, profit, trend growth, volatility index (CV), solvency ratio
  - Juridic (20%): litigii, insolventa
  - Fiscal (15%): inactiv ANAF, TVA, split TVA
  - Operational (15%): angajati, vechime, age-adjusted (startup tolerance), angajati trend
  - Reputational (10%): prezenta online (nuantat per nr categorii web)
  - Piata (10%): competitie, SEAP bonus, benchmark comparison bonus
- Mapare culori: >= 70 Verde, >= 40 Galben, < 40 Rosu
- Due Diligence Checklist: 10 verificari DA/NU/INDISPONIBIL
- Early Warning Signals: scadere CA >30%, pierdere 2 ani, reducere angajati >50%
- Benchmark CAEN: comparatie firma vs media sector (CA, angajati)
- Score History: stocat in DB per company (score_history table) pentru delta temporal
- Solvency Stress Matrix: 3x3 grid (Profit Margin x Equity Ratio) cu 9 zone risc
- Early Warning Confidence: 0-100 per avertisment (freshness + cross-source + extreme values)

## Conventii
- Limba UI: Romana
- Limba cod: Engleza (variabile, functii, comentarii tehnice)
- Port backend: 8001
- Port frontend: 5173
- Database: ./data/ris.db (WAL mode)
- Outputs: ./outputs/[job_id]/
- Backups: ./backups/ris_YYYY-MM-DD.db (rotatie 7 zile)
- .env obligatoriu (.env.example ca referinta)
- fpdf2 pt PDF (NU WeasyPrint)
- Synthesis: subprocess `claude --print --model claude-opus-4-6 --effort max`

## Decizii tehnice confirmate
1. Synthesis via Claude Code CLI subprocess ($0, calitate maxima)
2. Groq (Llama 4 Scout) ca fallback rapid (gratuit)
3. Gemini 2.5 Flash ca fallback autonom (gratuit)
4. Cerebras (Qwen 3 235B) ca fallback final (gratuit, 1M tokeni/zi)
5. Mistral Small 3 ca fallback european (1B tokeni/luna gratuit)
6. fpdf2 pentru PDF (zero dependinte native Windows)
7. TypeScript pentru frontend
8. Dark theme (#1a1a2e, accent albastru/violet)
9. LangGraph cu conditional_edges pt routing
10. DB separata pt LangGraph checkpoints (checkpoints.db)
11. Implementare faza cu faza cu test real intre faze
12. ANAF Bilant API pentru date financiare oficiale (nu estimate)
13. CUI validation MOD 11 inainte de API calls
14. Scoring numeric 0-100 multi-dimensional (nu doar 3 culori)
15. Cross-validare multi-sursa cu confidence scoring
16. httpx singleton cu connection pool (nu clienti noi per request)
17. AI Smart Routing: sectiuni scurte → Groq, lungi → Claude
18. Prompt optimization per provider (narativ/structurat/european/analitic)
19. Scheduler asyncio (fara dependinte externe) pt monitoring + backup
20. React 19 cu auto-memoizare
21. Request ID tracing (X-Request-ID) pe toate requesturile
22. Error sanitization — stack traces nu ajung la client
23. Cache LRU 100MB cu evictie automata
24. Batch parallel processing (2 CUI simultan cu semaphore)
25. Prompt injection hardening (sanitize backticks, control chars)
26. Solvency Stress Matrix 3x3 (profit margin x equity ratio)

## Documentatie — Fisiere de tinut sincronizate
La finalul fiecarei sesiuni de lucru, actualizeaza:
- `CLAUDE.md` — status faze, key files, decizii
- `TODO_ROLAND.md` — status items, ce ramane de facut
- `FUNCTII_SISTEM.md` — inventar complet functionalitati
- `AUDIT_REPORT.md` — doar daca s-au facut modificari majore
- Memory files — project_ris_status.md, reference_api_keys.md

## Comenzi
```bash
# Start complet (dublu-click)
START_RIS.vbs

# Stop complet (dublu-click)
STOP_RIS.vbs

# Manual
cd C:\Proiecte\Sistem_Inteligent_Analize
python -m backend.main          # Backend pe 8001
cd frontend && npm run dev      # Frontend pe 5173
```
