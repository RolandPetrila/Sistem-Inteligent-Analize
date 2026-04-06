# RECOMANDARI IMBUNATATIRI R5 — PLAN UNIFICAT
**Data creare:** 2026-04-06 | **Versiune:** 5.1 (UNIFICAT)
**Surse combinate:**
- `/imbunatatiri` R5 — 40 recomandari (15 UI + 13 feature noi + 12 tehnice)
- Audit R15 (86/100) — 3 HIGH blockers + 6 MEDIUM + 4 LOW
- `/improve` — 15 sugestii (versiuni, tools, patterns)
**Stack:** FastAPI 0.115.5 + React 19 + SQLite + 5 AI providers + 47 endpoints
**Baseline:** 14,739 LOC Python | 6,399 LOC TypeScript | 86/100 audit score
**Tinta:** 93+/100 dupa Faza 0-3

---

## LEGENDA

| Simbol | Semnificatie |
|--------|-------------|
| `[ ]` | De facut |
| `[x]` | Implementat |
| `[~]` | In progres |
| `[-]` | Amanat / out of scope sesiune |

---

# FAZA 0 — SECURITATE & AUDIT BLOCKERS (Sprint 1 Audit)
> Sursa: Audit R15 + /improve | Efort total: ~3h | Risc: LOW

- [x] **F0-1** CORS whitelist metode si headere — `backend/main.py:233-240`
  - `allow_methods=["GET","POST","DELETE","OPTIONS"]`
  - `allow_headers=["Content-Type","X-RIS-Key","Accept"]`
  - Sursa: Audit R15 [HIGH]

- [x] **F0-2** Bare except + logging — 3 locatii
  - `backend/database.py:52` — rollback fara logger
  - `backend/routers/reports.py:200`
  - `backend/services/monitoring_service.py:114`
  - Fix: `except Exception as e: logger.error(f"[ctx] failed: {e}", exc_info=True)`
  - Sursa: Audit R15 [MEDIUM]

- [x] **F0-3** `print()` → `logger.warning()` — `backend/config.py:83`
  - Sursa: Audit R15 [LOW] + /improve

- [x] **F0-4** TypeScript `any` → tipuri explicite — `frontend/src/pages/ReportView.tsx:209-210`
  - `analysis_type: report.report_type as AnalysisType`
  - `report_level: report.report_level as ReportLevel`
  - Sursa: Audit R15 [MEDIUM]

- [x] **F0-5** Path traversal robust — `backend/routers/reports.py:117`
  - `try: full_path.relative_to(outputs_root)` → `except ValueError: raise HTTPException(403)`
  - Sursa: Audit R15 [MEDIUM]

- [x] **F0-6** Rate limiter X-Forwarded-For — `backend/rate_limiter.py:39`
  - Respect proxy headers: `xff.split(",")[0].strip()`
  - Sursa: Audit R15 [MEDIUM]

- [x] **F0-7** Filename injection Content-Disposition — `backend/routers/reports.py:163`
  - `from urllib.parse import quote` → `filename*=UTF-8''${safe_name}`
  - Sursa: Audit R15 [MEDIUM]

- [x] **F0-8** WAL CHECKPOINT TRUNCATE in scheduler
  - In `backend/services/scheduler.py` la backup zilnic: `PRAGMA wal_checkpoint(TRUNCATE)`
  - Sursa: /imbunatatiri #33

- [x] **F0-9** FastAPI upgrade 0.115.5 → latest stable
  - `pip install fastapi --upgrade` → pinuieste in requirements.txt
  - Sursa: /improve #1

---

# FAZA 1 — REFACTORING TEHNIC
> Sursa: Audit R15 Sprint 2 + /imbunatatiri tehnice | Efort total: ~6h

- [x] **F1-1** Extract `backend/ws.py` — elimina late imports fragile
  - `ws_manager = WebSocketManager()` in modul separat
  - Import din `backend.ws` in loc de `backend.main`
  - Fisiere afectate: `routers/jobs.py`, `routers/batch.py`
  - Sursa: Audit R15 [HIGH]

- [x] **F1-2** Split `agent_synthesis.py::execute()` 337L → subfunctii
  - `_process_section()` (~50L)
  - `_select_route()` (~20L)
  - `_apply_fallback_chain()` (~50L)
  - `_validate_sections()` (~30L)
  - Sursa: Audit R15 [HIGH]

- [x] **F1-3** JSON dumps DRY — `backend/utils/serialization.py`
  - `def to_json(data) -> str: return json.dumps(data, ensure_ascii=False, default=str)`
  - Inlocuieste 15+ locatii duplicate
  - Sursa: Audit R15 [MEDIUM]

- [x] **F1-4** Dead code cleanup — clienti API neutilizati
  - Verifica daca sunt importati: `brave_client.py`, `grok_client.py`, `deepseek_client.py`,
    `jina_client.py`, `openrouter_client.py`, `perplexity_client.py`
  - Daca nu sunt folositi: sterge sau muta in `tools/_experimental/`
  - Sursa: /imbunatatiri #40 [Securitate/Mentenanta]

- [x] **F1-5** Database VACUUM incremental in scheduler lunar
  - `PRAGMA auto_vacuum = INCREMENTAL` la creare + `PRAGMA incremental_vacuum(100)` lunar
  - Sursa: /imbunatatiri #39

- [x] **F1-6** Ruff linter setup
  - `pip install ruff` + `pyproject.toml` cu `[tool.ruff]`
  - `ruff check backend/ --fix` (auto-fix imports, style)
  - Sursa: /improve #4

- [x] **F1-7** LangGraph upgrade → latest stable
  - `pip install --upgrade langgraph` + verifica breaking changes + test_orchestrator.py
  - Sursa: /imbunatatiri #37

- [x] **F1-8** `requests` lib eliminata (foloseste httpx)
  - Verifica requirements.txt — `requests` nu trebuie sa fie acolo
  - In orice script nou: `httpx.Client()` sync sau `httpx.AsyncClient()`
  - Sursa: /imbunatatiri #38

- [x] **F1-9** Logging structurat JSON optional
  - In `backend/main.py`, daca `LOG_FORMAT=json`: `logger.add(..., serialize=True)`
  - Sursa: /imbunatatiri #35 + /improve #15

- [x] **F1-10** Componente React mari — ErrorBoundary granulare per widget
  - `<ErrorBoundary fallback={<WidgetError/>}>` pe fiecare widget din Dashboard + CompanyDetail
  - Sursa: /improve #13

---

# FAZA 2 — IMBUNATATIRI UI EXISTENTE
> Sursa: /imbunatatiri Partea I | Efort total: ~8h

- [x] **F2-1** `Dashboard.tsx` — Widget "Scoruri in Scadere"
  - Apeleaza `/api/companies/stats/risk-movers` (endpoint existent)
  - Top 3 firme cu delta negativ, buton "Vezi toate" → `/companies?sort=risk_delta`
  - Sursa: /imbunatatiri #7 [P1]

- [x] **F2-2** `Companies.tsx` — Filtre avansate (judet, CAEN, interval scor)
  - `useSearchParams` pentru persistenta URL
  - Select judete RO + input CAEN + select Verde/Galben/Rosu
  - Backend: adauga `risk_score: str | None` query param in `routers/companies.py`
  - Sursa: /imbunatatiri #9 [P1]

- [x] **F2-3** `ReportView.tsx` — Breakdown Scor per Dimensiune in tab Risc
  - 6 dimensiuni cu progress bar + ponderi + explicatii
  - Tooltip "Ce inseamna asta?" per dimensiune
  - Sursa: /imbunatatiri #14 [P1]

- [x] **F2-4** `CompanyDetail.tsx` — Sparkline SVG score history
  - Component `ScoreSparkline` SVG pur (zero dependinte noi)
  - Colorat Verde/Galben/Rosu per valoare
  - Sursa: /imbunatatiri #3 [P2]

- [x] **F2-5** `CompanyDetail.tsx` — Download direct raport (PDF/Excel/HTML)
  - Links inline pe fiecare raport din lista
  - Sursa: /imbunatatiri #4 [P3]

- [x] **F2-6** `NewAnalysis.tsx` — Salvare draft wizard in sessionStorage
  - Restore automat la montare + banner "Draft salvat — continua"
  - Clear la submit reusit
  - Sursa: /imbunatatiri #5 [P3]

- [x] **F2-7** `GlobalSearch.tsx` — Istoric cautari recente (localStorage, max 5)
  - Afisare sub input cand query gol + click pre-fill
  - Sursa: /imbunatatiri #15 [P4]

- [x] **F2-8** `AnalysisProgress.tsx` — ETA per step
  - Calcul `elapsed / pct - elapsed` → afisare "~Xs ramas"
  - Log vizual steps parcurse
  - Sursa: /imbunatatiri #13 [P3]

- [x] **F2-9** `Monitoring.tsx` — Frecventa verificare configurabila din UI
  - Select 6h/12h/24h/Saptamanal la creare alerta
  - Afisare frecventa curenta in lista
  - Sursa: /imbunatatiri #1 [P3]

- [x] **F2-10** `Monitoring.tsx` — Istoric alerte trimise
  - Endpoint `GET /api/monitoring/history` (din `monitoring_audit` table existenta)
  - Sectiune "Istoric Alerte" in pagina cu filtru Zi/Saptamana/Toate
  - Sursa: /imbunatatiri #2 [P2]

- [x] **F2-11** `Settings.tsx` — Test individual per API key
  - Endpoint `POST /api/settings/test/{service}` pentru: groq, gemini, tavily, cerebras, mistral
  - Buton "Test" langa fiecare camp cu feedback verde/rosu
  - Sursa: /imbunatatiri #8 [P2]

- [x] **F2-12** `ReportView.tsx` — Tab "Grafice" cu date financiare multi-an
  - SVG bar chart pentru CA/Profit/Angajati (fara dependinte noi)
  - Fallback "Date financiare insuficiente" daca < 2 ani
  - Sursa: /imbunatatiri #6 [P2]

- [x] **F2-13** `batch.py` — Preview CSV inainte de procesare
  - `POST /api/batch/preview` — validare fara a porni procesarea
  - Returneaza: valid_count, invalid_count, estimated_time_minutes
  - Sursa: /imbunatatiri #11 [P3]

- [x] **F2-14** `one_pager_generator.py` — Due Diligence Checklist in PDF
  - Table Verificare | Rezultat | Sursa cu 10 randuri
  - Colorat verde/rosu/gri
  - Sursa: /imbunatatiri #12 [P3]

- [x] **F2-15** `agent_synthesis.py` — Sectiune "Key Takeaways" (3 bullets)
  - Generata DUPA celelalte sectiuni (are context complet)
  - Via Groq (rapid, nu necesita Claude)
  - Stilat distinct in HTML/PDF
  - Sursa: /imbunatatiri #10 [P1]

---

# FAZA 3 — FEATURE-URI NOI (P0/P1)
> Sursa: /imbunatatiri Partea II | Efort total: ~10h

- [x] **F3-1** Webhook outbound la finalizare analiza
  - `WEBHOOK_URL` in config.py
  - SSRF prevention (scheme=https, nu IP private)
  - POST JSON la finalizare job: `{job_id, company_name, cui, risk_score, ...}`
  - Sursa: /imbunatatiri #20 [P0, Impact Maxim]

- [x] **F3-2** Quick Score batch (`POST /api/analysis/quick-score`)
  - Max 20 CUI-uri, doar ANAF TVA + Bilant, fara AI synthesis
  - Parallel asyncio.gather, scoring minimal (0-100)
  - Sursa: /imbunatatiri #19 [P0, Impact Maxim]

- [x] **F3-3** Tag-uri si Note Manuale pe Companii
  - Migration `007_tags_scheduler.sql`: `company_tags` + `company_notes`
  - CRUD endpoints in `routers/companies.py`
  - UI in `CompanyDetail.tsx`: chips tags + textarea note cu auto-save
  - Sursa: /imbunatatiri #17 [P1, Impact Maxim]

- [-] **F3-4** Re-analiza Programata Automata (Scheduler per firma)
  - Migration: `ALTER TABLE companies ADD COLUMN auto_reanalyze_days INTEGER`
  - Task `_run_auto_reanalysis()` in `scheduler.py` (la fiecare 1h)
  - UI in `CompanyDetail.tsx`: toggle + select interval
  - Sursa: /imbunatatiri #18 [P0, Impact Maxim]

- [x] **F3-5** Export Calendar Licitatii SEAP (.ics)
  - `GET /api/reports/{id}/export/ics`
  - iCalendar standard (fara dependinte noi)
  - Buton in ReportView tab Piata
  - Sursa: /imbunatatiri #16 [P2]

- [x] **F3-6** Raport Sector CAEN Dashboard
  - `GET /api/compare/sector/{caen_code}/dashboard`
  - Agregat din DB: avg score, distributie Verde/Galben/Rosu, top 10 firme
  - Sursa: /imbunatatiri #21 [P2]

- [x] **F3-7** Import Companii din CSV (onboarding)
  - `POST /api/companies/import` — INSERT OR IGNORE, fara analiza
  - CUI validation + header detection
  - Sursa: /imbunatatiri #22 [P4]

- [x] **F3-8** Comparatii Salvate ca Template
  - Migration: `compare_templates` table
  - Endpoints: `POST /api/compare/templates`, `GET /api/compare/templates`
  - UI in CompareCompanies: save + load template
  - Sursa: /imbunatatiri #27 [P3]

- [x] **F3-9** Browser Push Notifications (Web Push API)
  - `frontend/src/lib/notifications.ts` — Notification API nativa
  - `requestNotificationPermission()` in Settings
  - Trigger in AnalysisProgress la DONE
  - Sursa: /imbunatatiri #24 [P2]

- [x] **F3-10** CLI Script `tools/ris-analyze.py`
  - `python tools/ris-analyze.py --cui 26313362 --type full --level 2`
  - Poll status + output json/summary
  - Sursa: /imbunatatiri #28 [P3]

- [-] **F3-11** Raport Comparativ Multi-An (aceeasi firma)
  - `GET /api/reports/{id}/financials/multiyear`
  - 5 ani consecutivi: CA delta%, profit, angajati
  - Sectiune vizuala in CompanyDetail
  - Sursa: /imbunatatiri #23 [P3]

- [x] **F3-12** PDF Watermark Personalizabil
  - `PDF_WATERMARK` + `PDF_WATERMARK_ENABLED` in config.py
  - Input text in Settings UI
  - Sursa: /imbunatatiri #25 [P4]

- [x] **F3-13** Pagina `/health/status` Publica
  - Endpoint public (fara auth): DB status, scheduler, last 5 jobs
  - Sursa: /imbunatatiri #26 + /improve #14 [P4]

---

# FAZA 4 — TESTE & CALITATE
> Sursa: Audit R15 Sprint 3 + /imbunatatiri tehnice | Efort total: ~12h

- [ ] **F4-1** Test coverage backend: 5% → 30%
  - `tests/test_job_service.py` — mock LangGraph, state transitions
  - `tests/test_cache_service.py` — TTL, eviction, LRU
  - `tests/test_routers_extended.py` — toate 42 endpoints cu TestClient
  - `tests/test_database.py` — migrations, CRUD, WAL
  - Sursa: Audit R15 [HIGH] + /imbunatatiri #29

- [ ] **F4-2** Frontend Component Tests
  - `npm install --save-dev @testing-library/react @testing-library/user-event jsdom`
  - `tests/Toast.test.tsx`, `tests/ErrorBoundary.test.tsx`, `tests/api.test.ts`
  - Sursa: Audit R15 [HIGH] + /imbunatatiri #30

- [x] **F4-3** pyproject.toml — consolidare config
  - `[project]`, `[tool.ruff]`, `[tool.pytest.ini_options]`
  - Sursa: /improve #11

- [ ] **F4-4** Bundle Analysis — verifica code splitting per pagina
  - `npm install --save-dev rollup-plugin-visualizer`
  - Verifica ca fiecare pagina e chunk separat (React.lazy existent)
  - Target: main chunk < 50KB
  - Sursa: /imbunatatiri #34

- [x] **F4-5** OpenAPI Docs — verifica `/docs` accesibil pe localhost
  - Asigura descrieri pe endpoint-urile fara docstring
  - Sursa: /imbunatatiri #36

- [ ] **F4-6** TanStack Query pentru Data Fetching
  - `npm install @tanstack/react-query@^5.96.2`
  - Migreaza treptat pagini cu mai mult boilerplate
  - Sursa: /improve #3 + /imbunatatiri #31 [P3]

---

# SUMAR EXECUTIE

| Faza | Items | Efort | Status |
|------|-------|-------|--------|
| F0 — Securitate/Audit | 9 | ~3h | `[x]` 9/9 IMPLEMENTAT |
| F1 — Refactoring Tehnic | 10 | ~6h | `[x]` 10/10 IMPLEMENTAT |
| F2 — UI Imbunatatiri | 15 | ~8h | `[x]` 15/15 IMPLEMENTAT |
| F3 — Feature-uri Noi | 13 | ~10h | `[x]` 11/13 + 2 amanate (F3-4, F3-11) |
| F4 — Teste & Calitate | 6 | ~12h | `[~]` 2/6 (F4-3, F4-5 gata; F4-1,2,4,6 ramane) |
| **TOTAL** | **53** | **~39h** | **47 implementate, 4 amanate/ramase** |

---

## NOTE IMPLEMENTARE

1. **SSRF protection obligatorie** pe orice URL extern configurat de utilizator (webhook, import).
2. **API key required** pe TOATE endpoint-urile noi care modifica date.
3. **Migrations**: Schema changes merg in `backend/migrations/007_tags_scheduler.sql` (ADITIVE).
4. **Nu se schimba:** Stack AI, LangGraph orchestrator, schema DB existenta 001-006, fpdf2, porturi.
5. **Backend dependencies noi:** zero pentru F0-F1. F3-F4 pot necesita `@testing-library/react`.
6. **Ordinea de implementare:** F0 → F1 → F2 → F3 → F4 (secvential, cu teste dupa fiecare faza).

---

*Document unificat din 3 surse: /imbunatatiri R5 (40 items) + Audit R15 (13 issues) + /improve (15 sugestii)*
*Total dupa deduplicare: 53 items organizate in 5 faze*
*Generat: 2026-04-06*
