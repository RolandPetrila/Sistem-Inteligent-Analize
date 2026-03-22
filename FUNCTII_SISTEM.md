# RIS — Inventar Complet Functionalitati

Data actualizare: 2026-03-22 | Versiune: 5.1 | Faze 1-9E + 10A-10F complete

---

## Backend — 37 REST Endpoints + 1 WebSocket

### Jobs API
| Metoda | Endpoint | Descriere |
|--------|----------|-----------|
| POST | /api/jobs | Creeaza job nou (rate limited: 5/min) |
| GET | /api/jobs | Lista joburi (filtru status, paginare) |
| GET | /api/jobs/{id} | Detalii job |
| POST | /api/jobs/{id}/start | Porneste executia |
| POST | /api/jobs/{id}/cancel | Anuleaza job |
| GET | /api/jobs/{id}/diagnostics | Diagnostic completitudine + surse per job (7E) |
| GET | /api/jobs/diagnostics/latest | Diagnostic ultimul job completat (7E) |
| POST | /api/jobs/{id}/retry-source/{source} | Re-ruleaza o sursa esuata: anaf/openapi/bilant/bnr/seap (7E) |
| WS | /ws/jobs/{id} | WebSocket progress real-time |

### Reports API
| Metoda | Endpoint | Descriere |
|--------|----------|-----------|
| GET | /api/reports | Lista rapoarte (filtru tip, firma, paginare) |
| GET | /api/reports/{id} | Detalii raport + full_data JSON |
| GET | /api/reports/{id}/download/{format} | Download PDF/DOCX/Excel/HTML/PPTX |
| GET | /api/reports/{id}/download/one_pager | Download raport executiv 1-pager PDF |

### Companies API
| Metoda | Endpoint | Descriere |
|--------|----------|-----------|
| GET | /api/companies | Lista companii (search, filtru judet/CAEN) |
| GET | /api/companies/{id} | Detalii companie + rapoarte |
| GET | /api/companies/export/csv | Export CSV CRM-ready (toate companiile) |

### Analysis API
| Metoda | Endpoint | Descriere |
|--------|----------|-----------|
| GET | /api/analysis/types | Lista tipuri analiza (9 tipuri) |
| GET | /api/analysis/types/{type} | Detalii tip analiza |
| POST | /api/analysis/parse-query | NLP: parseaza cerere in limba naturala |

### Compare API
| Metoda | Endpoint | Descriere |
|--------|----------|-----------|
| POST | /api/compare | Compara 2-5 firme side-by-side |
| POST | /api/compare/sector | Raport sector CAEN (agregate din DB) |

### Monitoring API
| Metoda | Endpoint | Descriere |
|--------|----------|-----------|
| GET | /api/monitoring | Lista alerte monitorizare |
| POST | /api/monitoring | Creeaza alerta noua |
| PUT | /api/monitoring/{id}/toggle | Activeaza/dezactiveaza alerta |
| DELETE | /api/monitoring/{id} | Sterge alerta |
| POST | /api/monitoring/check-now | Verificare manuala toate alertele |

### Batch API
| Metoda | Endpoint | Descriere |
|--------|----------|-----------|
| POST | /api/batch | Upload CSV + start batch analysis |
| GET | /api/batch/{id} | Status batch (progress, completed, failed) |
| GET | /api/batch/{id}/download | Download ZIP cu toate rapoartele |
| POST | /api/batch/{id}/resume | Re-ruleaza doar CUI-urile FAILED din batch (9E) |

### System API
| Metoda | Endpoint | Descriere |
|--------|----------|-----------|
| GET | /api/health | Health check simplu |
| GET | /api/health/deep | Health deep (DB, ANAF, Tavily, disk, AI providers) |
| GET | /api/stats | Statistici globale (cached 30s) |
| GET | /api/stats/trend | Analize per luna ultimele 6 luni |
| GET | /api/cache/stats | Statistici cache: entries, expired, size_mb, per sursa (8A) |
| GET | /api/settings | Configurare curenta |
| PUT | /api/settings | Salveaza setari |
| POST | /api/settings/test-telegram | Test notificare Telegram |
| GET | /api/monitoring/health | Health status monitorizare: last check, failed count, next scheduled (10E) |

---

## Agenti AI (5)

| Agent | Rol | Surse |
|-------|-----|-------|
| Agent 1 (Official) | Extrage date oficiale | ANAF, ANAF Bilant, BNR, openapi.ro, Tavily, SEAP, INS TEMPO |
| Agent 2 (Web) | Web intelligence | Tavily search (stiri, recenzii) |
| Agent 3 (Market) | Analiza piata | Tavily search (competitori, sector) |
| Agent 4 (Verification) | Verificare + scoring | Cross-validare, scoring 0-100, due diligence, early warnings, benchmark, relations |
| Agent 5 (Synthesis) | Generare text narativ | Claude CLI / Groq / Mistral / Gemini / Cerebras (smart routing) |

---

## Functionalitati Faza 6 (toate noi)

### 6A — Performance
- Lazy imports (fpdf2, openpyxl, pptx — import doar la generare)
- CORS Tailscale (acces de pe Android via 100.* IP range)
- httpx singleton (1 client cu connection pool, nu 8 clienti noi)
- Cache cleanup la startup
- Health check deep (/api/health/deep — DB, ANAF, Tavily, disk, AI)
- Stats cache 30s

### 6B — Documentare Extinsa
- Due Diligence Checklist (10 verificari DA/NU in raport)
- Profil Actionariat (asociati + administratori din openapi.ro)
- Early Warning Signals (scadere CA >30%, pierdere 2 ani, reducere angajati >50%)
- Export CRM CSV (buton in Companies, descarca toate firmele)
- Raport Executiv 1-Pager PDF (scor, dimensiuni, checklist, riscuri, benchmark)
- Context CAEN (122 coduri + 96 sectiuni + descriere + nr firme)
- Benchmark Financiar CAEN (CA firma vs media sector, ratio, pozitie)
- Batch Analysis CSV (upload CSV, analiza serie, ZIP rapoarte)

### 6C — UX Polish
- Toast Notifications (notificari vizuale — inlocuieste console.error)
- Error Boundaries React (pagina crapa → mesaj util + buton reload)
- Dashboard grafice trend (bare SVG — analize/luna 6 luni)
- Validare CUI in browser (MOD 11 instant, feedback verde/rosu)
- Prompt optimization per provider (Claude=narativ, Groq=structurat, Mistral=european)
- CSP headers (Content-Security-Policy permite Chart.js CDN + WebSocket)

### 6D — Advanced
- Scheduler Monitoring (asyncio loop, verificare la 6h, Telegram alerts automat)
- INS TEMPO Integration live (nr firme + CA medie din API oficial)
- Auto-backup DB (zilnic backups/ris_YYYY-MM-DD.db, rotatie 7 zile)
- Sector Report (POST /api/compare/sector — agregate firme per CAEN)
- Matricea Relatii (detectie one-person, virtual office, flags)
- AI Smart Routing (sectiuni scurte → Groq rapid, lungi → Claude calitate)
- AI Pre-processing (clasificare 5 categorii + sentiment pozitiv/negativ/neutru)
- React 19 (auto-memoizare, -38% JS payload)

---

## Functionalitati Faza 7 (Data Quality, Securitate, Testare, Calitate)

### 7A — Data Quality & Diagnosticare
- SEAP routing fix (FULL_COMPANY_PROFILE include Agent 3/Market la nivel 2)
- ONRC structurat integrat in Verification (CAEN, asociati, administratori, capital)
- Completeness check 17 verificari (profil, financiar, CAEN, SEAP, litigii)
- Anti-halucinare: campuri lipsa transmise explicit in prompt AI
- Sectiune "Diagnostic Completitudine" vizibila in raportul HTML
- Sistem logging complet per job: logs/job_{id}.log

### 7B — Quick Wins Securitate
- PATH TRAVERSAL fix pe 3 endpoint-uri download (resolve() + startswith)
- requirements.txt actualizat cu versiuni reale
- PRAGMA synchronous=NORMAL + mmap_size=256MB (SQLite performance)
- sqlite3.backup() in loc de shutil.copy2 (backup sigur)
- Toast pe catch-uri goale (5 locuri fixate in frontend)
- Route 404 catch-all cu pagina "Pagina nu a fost gasita"
- uvicorn reload conditionat (RIS_ENV)
- Warning la startup daca secret key = default

### 7C — Securitate & Stabilitate
- Batch progress persistent in DB (supravietuieste restart server)
- Rate limiting custom: 5 req/min jobs, 2 req/min batch, per IP
- API key auth optional (X-RIS-Key header, activat cand RIS_API_KEY setat)
- CSP hardened: eliminat unsafe-eval + CDN din script-src
- Cache SEAP cu TTL 30 zile
- Few-shot examples in 4 prompturi AI (executive, financial, risk, recommendations)

### 7D — Testare & Refactorizare
- 28 pytest tests (CUI validator, scoring, completeness, rate limiter)
- 11 vitest tests (CUI validator frontend)
- Split agent_verification.py → scoring.py + completeness.py (submodule)
- React.lazy() pe toate 10 paginile + Suspense + 404 route
- Retry logic shared (with_retry) integrat in ANAF + openapi.ro

### 7E — Calitate Analiza Avansata
- CAEN fallback din ANAF Bilant (daca openapi.ro + ANAF n-au CAEN)
- Retry cu backoff pe TOATE sursele: ANAF, openapi.ro, BNR, SEAP
- Completeness gate <50%: WARNING inject in prompt sinteza
- Anti-halucinare prompts pe competition, opportunities, SWOT
- GET /api/jobs/{id}/diagnostics (completeness, risk, log tail)
- GET /api/jobs/diagnostics/latest (ultimul job)
- POST /api/jobs/{id}/retry-source/{source} (re-run sursa individuala)

---

## Functionalitati Faza 8 (Extindere Module)

### 8A — Infrastructure & Performance
- GZip Middleware (compresia raspunsurilor HTTP > 1000 bytes)
- Coduri eroare structurate: ErrorCode enum cu 25+ coduri specifice (ANAF_TIMEOUT, CUI_INVALID, etc.)
- RISError exception class cu cod, mesaj, detalii
- API Cache-Control headers per endpoint (stats=30s, types=immutable, companies=5min)
- GET /api/cache/stats (total entries, expired, size_mb, by source)
- Cache cleanup periodic la 12h (scheduler)
- Migratie DB: monitoring_audit, score_history, compare_history (002_phase8.sql)

### 8B — Scoring & Intelligence
- Trend scoring: CA growth factor cu bonus/penalizare graduala (>50%=+15, >20%=+10, <-30%=-20)
- Volatility Index: coeficient de variatie (CV) pe CA multi-an; CV>0.5=-10pts, CV>0.3=-5pts
- Solvency Ratio: capitaluri_proprii/CA; capital negativ=-15pts, <5%=-10pts
- Age-Adjusted Scoring: startup <2 ani cu pierderi = toleranta (+5), firma >10 ani cu pierderi = regres (-10)
- Angajati trend: reducere >50% = HIGH risk factor (-15pts)
- Reputational nuantat: categorii web prezenta (1=60, 2=70, 3+=80)
- Market enhanced: bonus SEAP contracte, bonus benchmark CAEN

### 8C — Synthesis & Reports
- Dynamic Word Count: ajusteaza target cuvinte per sectiune bazat pe complexitate date
- Context Awareness Injection: summary structurat per tip sectiune injectat in prompt AI
- Provider Routing per Section: SECTION_PROVIDER_PREFERENCE (fast/quality per sectiune)
- ZIP Auto-Pack: toate formatele generate impachetate automat in raport_{CUI}_{date}.zip

### 8D — Orchestrator & Comparator
- Error Boundaries: Agent 2 (Web) si Agent 3 (Market) — erori catchuite, pipeline continua
- Orchestrator Timing Metrics: _agent_metrics per nod (secunde executie)
- Compare cu cache ANAF+Bilant (reduce API calls duplicate)
- Compare scoring aliniat cu formula Agent 4
- Compare persistence: rezultate salvate in compare_history
- Batch retry logic: max 2 retries cu backoff exponential (3s * attempt)
- Rich Summary CSV: CUI, Denumire, CAEN, CA, Profit Net, Angajati, Scor, Culoare

### 8E — Monitoring & UX
- Smart Alert Severity: RED (inactiv, radiat), YELLOW (TVA, split TVA), GREEN (reactivare)
- Audit Log: monitoring_audit table (alert_id, change_type, old/new, severity, timestamp)
- Expanded delta detection: stare, inactiv, TVA, split TVA
- Score History: score_history table (tracking numeric_score + dimensions per firma in timp)
- Telegram messages cu severity icons (RED/YELLOW/GREEN)

### Tabele DB noi (Faza 8)
| Tabel | Scop |
|-------|------|
| monitoring_audit | Log auditabil schimbari detectate la monitoring |
| score_history | Istoric scor per firma (trend temporal) |
| compare_history | Persistenta rezultate comparatii |

---

## Functionalitati Faza 9 (Performance, Intelligence, UX, Reports, Monitoring)

### 9A — Performance & Robustness
- Parallel source fetching: asyncio.gather in Agent 1 (2 grupe paralele: ANAF+openapi+Bilant+BNR, apoi BPI+Litigation)
- Error boundaries 5/5 agenti: try/except in orchestrator.py wrapping fiecare agent cu fallback data
- Request size limit 10MB: RequestSizeLimitMiddleware in main.py
- Cache hit/miss tracking: _hit_miss dict in cache_service.py, expus via /api/cache/stats
- Data freshness tracking: data_freshness dict in agent_official.py (latest_year, data_age_years, fresh)

### 9B — Scoring & Intelligence
- Cash flow proxy: marja negativa + capital negativ = stress detection in scoring.py
- Anomaly feedback loop: anomalii Agent 4 injectate in prompturile Agent 5 synthesis via orchestrator.py
- Confidence scoring: 0-1 per dimensiune bazat pe puncte de date reale in scoring.py
- Provider capacity awareness: limite JSON per provider (Claude 15K, Groq 4K, etc.) in agent_synthesis.py, auto-truncate

### 9C — Frontend UX Polish
- Pagination: Companies.tsx + ReportsList.tsx cu PAGE_SIZE 20, offset support, navigare pagini
- API key masking: Eye/EyeOff toggle pe campuri parola in Settings.tsx
- Responsive mobile sidebar: hamburger menu, drawer overlay, backdrop in Layout.tsx
- ApiError class: code, status, retryAfter fields in api.ts
- Rate limit 429 handler: parse Retry-After header in api.ts request()
- Error codes in toast: error_code extras din raspunsurile API

### 9D — Reports & Export
- Watermark CONFIDENTIAL: text diagonal in PDF (RISPdf header), CSS fixed overlay in HTML
- TOC PDF: pagina Cuprins cu titluri sectiuni si numere pagina
- TOC DOCX: Word TOC field (OxmlElement w:fldChar) auto-updatable la deschidere

### 9E — Monitoring & Batch
- Alert dedup 24h: _is_duplicate_alert() in monitoring_service.py verifica monitoring_audit ultimele 24h
- Batch resume: POST /api/batch/{id}/resume re-ruleaza doar CUI-urile cu status FAILED

---

## Functionalitati Faza 10 (R3 Module Upgrades — 51 P1 features)

### 10E — Security & Observability
- Request ID Tracing (X-Request-ID header pe fiecare request)
- Error Message Sanitization (stack traces nu ajung la client)
- Sensitive Data Redaction in logs (CUI mascat: 123***)
- Request Validation Handler (422 structurat cu field errors)

---

## Frontend — 11 Pagini

| Pagina | Ruta | Descriere |
|--------|------|-----------|
| Dashboard | / | Stats, trend chart, integrari, actiuni rapide |
| Analiza Noua | /new-analysis | Wizard 4 pasi + chatbot NLP + CUI validator |
| Progress Analiza | /analysis/:id | WebSocket real-time, logs, link raport |
| Rapoarte | /reports | Lista rapoarte, download (6 formate) |
| Vizualizare Raport | /report/:id | Full data, sectiuni, surse, download |
| Companii | /companies | Lista + search + export CSV CRM |
| Comparator | /compare | Comparatie 2-5 firme side-by-side |
| Monitorizare | /monitoring | Alerte, toggle, check-now, Telegram |
| Batch Analysis | /batch | Upload CSV, progress, download ZIP |
| Configurare | /settings | API keys, Telegram, Gmail, synthesis mode |

---

## Formate Raport (7)

| Format | Generator | Detalii |
|--------|-----------|---------|
| PDF | fpdf2 | Multi-pagina, titlu, sectiuni, surse, disclaimer |
| DOCX | python-docx | Headere, paragrafe, stiluri |
| HTML | Custom | Single-file, dark theme, Chart.js grafice |
| Excel | openpyxl | 4 sheet-uri, grafice native |
| PPTX | python-pptx | 7 slide-uri prezentare |
| 1-Pager PDF | fpdf2 | O pagina: scor, dimensiuni, checklist, riscuri, benchmark |
| ZIP Auto-Pack | zipfile | Toate formatele generate intr-un singur raport_{CUI}_{date}.zip (8C) |

---

## Surse Date (10+)

| Sursa | Nivel | Status |
|-------|-------|--------|
| ANAF TVA/Stare v9 | 1 (Oficial) | Activ |
| ANAF Bilant | 1 (Oficial) | Activ |
| BNR Cursuri | 1 (Oficial) | Activ |
| openapi.ro (ONRC) | 1 (Oficial) | Activ (100 req/luna) |
| SEAP e-licitatie.ro | 1 (Oficial) | Activ |
| INS TEMPO | 1 (Oficial) | Activ (optional) |
| Tavily Search | 3 (Estimat) | Activ (1000 req/luna) |
| Groq AI | - | Activ (gratuit) |
| Mistral AI | - | Activ (1B tokeni/luna) |
| Gemini AI | - | Activ (gratuit) |
| Cerebras AI | - | Activ (1M tokeni/zi) |
| Claude CLI | - | Activ (local) |
| Telegram | - | Activ |
