# Roland Intelligence System (RIS)

## Overview

Sistem local de Business Intelligence care ruleaza pe Windows 10. Extrage automat date din surse publice romanesti (ANAF, ONRC, SEAP, etc.), le proceseaza prin agenti AI si produce rapoarte profesionale.

## Context critic (evita sa repeti greseli din sesiuni anterioare)

- CSP-ul aplicatiei (`script-src 'self'`, fara `unsafe-inline`) blocheaza SILENTIOS orice
  `<script>` inline sau `onclick="..."` — orice UI noua trebuie JS extern same-origin +
  `addEventListener`. Testeaza mereu prin deschidere reala in browser, nu doar "fisierul e valid".
- `autoflake` (hook PostToolUse) sterge importuri neutilizate imediat dupa Edit — adauga
  usage-ul INAINTE de import, in edit-uri separate.
- Repo public pe GitHub — nu presupune ca orice date reale de firme terte pot fi publicate
  fara verificare.
- **`RIS_API_KEY` e ACTIV din 2026-07-12** — toate `/api/*` cer header `X-RIS-Key` (exceptii:
  `/api/health`, `/api/health/deep`, `/api/frontend-log`, `/api/reports/public/*`). Frontend-ul
  trimite cheia automat DOAR daca a fost construit dupa ce `frontend/.env` (`VITE_RIS_API_KEY`,
  gitignored, valoare IDENTICA cu `RIS_API_KEY` din `.env` root) exista — `npm run build` fara
  acest fisier produce un build care primeste 401 pe orice apel API. Dupa orice schimbare a
  cheii: actualizeaza AMBELE `.env`-uri, apoi rebuild frontend, apoi restart serviciu.
- **Testele verzi nu dovedesc ca feature-ul ruleaza** (lectie 2026-07-15, clasa de bug inchisa
  atunci: Comparator scor fix 70, tabul Grafice mort, 4 modele faliment moarte, 4 chei
  frontend moarte). In RIS, fixture-urile au codificat aceeasi presupunere gresita ca si codul
  (ex. `aegrm` testat cu chei `"guarantees"`/`"descriere"` care nu exista in produs — clientul
  real emite `details`) — testul si codul se confirmau reciproc. **Verifica forma REALA a
  datelor la producator (DB / client), nu in fixture-uri existente.** Corolar: codul mort
  aduna bug-uri latente care se activeaza exact cand il reinvii. Corolar 2: verificarea live
  prinde ce e RUPT, nu ce e plauzibil-si-fals.
- **JOB LIVE INAINTE DE PUSH, la orice fix care poate reinvia o cale moarta** (regula scrisa
  2026-07-15 dupa ce a fost incalcata si s-a pushat o regresie). Fix-ul `9324e0a` (orbire la
  pierderi) avea 566 pytest verzi + golden identic + **intrarea** verificata live + diff citit
  linie cu linie — si prima firma reala pe pierdere a **crapat jobul complet**: fix-ul reinviase
  calea "firma pe pierdere", pe care zacea `', '.join(<lista de ANI int>)` (`early_warnings.py:58`,
  reparat in `84fc37a`). Avertismentul "Pierdere consecutiva 2+ ani" (HIGH, listat mai jos ca
  functie de baza) **nu rulase NICIODATA**. **Testele nu pot prinde asta prin constructie** — calea
  n-a existat niciodata ca sa fie testata. **"Am verificat intrarea" NU inseamna "am verificat".**
  A treia confirmare a corolarului de mai sus, prima declansata de noi insine.
- **Firme de test cu rol** (verificat live 2026-07-15): **TAROM CUI 477647** = declansator pt calea
  "pierdere" (5 ani consecutivi pe pierdere 2019-2023 + capitaluri proprii NEGATIVE + redresare
  reala pe profit in 2024 — testeaza si istoricul si revenirea). **MEGA IMAGE 6719278** = date
  bogate. **MOSSLEIN 26313362** = control profitabil. **"Identic pe firma curata" NU e succes** —
  o cablare rupta da acelasi rezultat.
- **`.get(cheie, default)` pe raspunsuri de la surse externe MASCHEAZA absenta** — nu poti distinge
  "API-ul n-a trimis campul" de "entitatea n-are date". Asa a stat ascuns ani de zile faptul ca
  openapi.ro **nu livreaza NICIODATA** `asociati`/`administratori` (clientul face `.get("asociati", [])`)
  -> `network_client.py` intreg (Toxic PageRank, Conflict Interese, Reteaua de Firme, migrarea 008)
  **n-a rulat niciodata cu date reale**. La orice client de sursa: verifica setul de chei REAL emis,
  nu ce zice documentatia. Comentariul "ANAF are formate diferite pt firme mari vs mici" era, tot
  asa, **fals** — infirmat empiric 2026-07-15 (OMV Petrom si o firma mica primesc acelasi set I1-I20).
- ~~**Google Maps e MORT din ~2026-07**~~ **[FALS — INFIRMAT 2026-07-16 cu date de PRODUCTIE.
  Google Maps FUNCTIONEAZA. NU e nicio actiune de facut la Google Cloud Console.]** Dovada: joburi
  reale 2026-07-16 — TAROM `found=True rating=3.3 (767 recenzii)`, CIP INSPECTION `found=True
rating=5 (349 recenzii)`. Dimensiunea reputational **nu** rula "doar pe web_presence".
  **`AUDIT_FUNCTII.html` avea DREPTATE**; textul de mai sus (care il acuza ca "minte pasiv") era el
  minciuna. **CAUZA — GOTCHA MAJOR, se repeta:** `GOOGLE_CLOUD_API_KEY` din **env var-ul userului**
  DIFERA de cel din `.env`, iar `pydantic-settings` citeste env var-ul **INAINTEA** lui `.env`.
  Un test din shell foloseste cheia VECHE -> `request_denied` -> concluzia falsa "API mort".
  ~~Serviciul ruleaza ca **SYSTEM** -> nu vede env var-ul userului -> foloseste `.env` (cheia BUNA).~~
  **[FALS — INFIRMAT 2026-07-24 prin masurare. Serviciul ruleaza sub contul `.\ALIENWARE`, NU ca
  LocalSystem: `sc qc RIS-Backend` -> `SERVICE_START_NAME : .\ALIENWARE`; procesul de pe :8001
  (PID copil al serviciului) primea `TELEGRAM_CHAT_ID` din env var-ul USERULUI. Deci serviciul
  mostenea mediul userului, iar env var-ul castiga SI in productie, nu doar in shell.]**
  Concluzia despre Maps ramane valida (statea pe dovada directa de productie, nu pe aceasta premisa);
  se schimba EXPLICATIA: shell-ul care dadea `request_denied` avea blocul de mediu VECHI, nu o cheie
  diferita de a productiei. **Lectia: o premisa scrisa ca "verificata" a propagat intr-o regula de
  lucru si a supravietuit pentru ca nimeni n-a masurat contul serviciului.**
- ~~**4 chei difera intre shell si productie**~~ **[STALE — remasurat 2026-07-24: din 38 de chei
  in `.env`, **16** au omonim in env vars User; **4 diverg**, dar NU aceleasi 4:
  `DEEPSEEK_API_KEY` (env var GOL -> stergea cheia reala), `GOOGLE_AI_API_KEY`, `TELEGRAM_CHAT_ID`,
  `XAI_API_KEY`. **`GOOGLE_CLOUD_API_KEY` nu mai diverge.** Nu te baza pe lista — remasoara:
  `scratchpad/env_shadow_audit.py` compara pe hash, fara sa afiseze valori.]**
  **REPARAT STRUCTURAL (2026-07-24):** `Settings.settings_customise_sources` inverseaza ordinea ->
  **`.env` bate env var-ul** in RIS. Env vars-urile NU s-au sters din Windows: sunt sistemul central
  de chei al masinii (`~/.api-keys`), folosit de alte proiecte — s-a eliminat clasa de bug, nu
  instanta, si doar pentru RIS. `RIS_ENV` (setat de WinSW) e neatins: se citeste cu `os.environ.get`,
  nu prin Settings. Regresie: `tests/test_config_source_priority.py`.
  Regula ramane valabila ca disciplina: nu declara NICIO sursa "moarta" pe baza unui test din shell —
  confirma in `reports.full_data` (joburi reale) sau prin `POST /api/settings/test/{service}` (ruleaza
  IN serviciu). Cand ping-ul live si CLAUDE.md se contrazic, **productia castiga**.

- **`git stash` e GLOBAL pe repo** — cu agenti paraleli, ferestrele de non-vacuitate se falsifica
  reciproc (dovedit 2026-07-17). Metoda sigura: `git show HEAD:fisier > backup` (sau backup din
  working tree daca fisierul are deja modificari necomise) -> suprascrie -> testeaza -> restaureaza
  -> verifica **sha256 identic**.
- **TESTELE POT STRICA PRODUCTIA.** `test_update_settings` facea `PUT /api/settings` pe endpointul
  REAL -> rescria `.env`-ul de productie la fiecare `RIS_TEST.bat`. Exista acum o **garda** in
  `tests/conftest.py` (hash `.env` inainte/dupa suita) care PICA mecanic daca se repeta.
- **Surse „moarte confirmate" — 2 din 3 erau GRESITE (re-verificat din browser 2026-07-24, sesiune
  extensie).** Din INS TEMPO + buletinul.ro + RNPM/AEGRM, toate marcate „moarte, confirmat repetat":
  **INS TEMPO e VIU** (era „offline/timeout" — fals; shell-ul pe portul 8077 nu e dovada — instanta
  noua a „shell != productie"). Contract REST captat:
  `POST http://statistici.insse.ro:8077/tempo-ins/matrix/INT101W` (200) — intreprinderi active pe
  **clase CAEN Rev.2** (4 cifre, 589 optiuni); baza e `/tempo-ins/`, **NU** `/tempo-online/` (ala e
  doar frontendul). **buletinul.ro MORT si in browser** (DNS inexistent, nu blocaj — concluzia veche
  corecta, dar re-atribuita cu metoda, nu lasata „confirmat repetat" fara data). **RNPM/AEGRM VIU dar
  BLOCAT de reCAPTCHA v2 per-cerere, validat server-side** (categorie noua: nici mort, nici
  automatizabil legitim — **NU** scraping cu CAPTCHA-solving). **CONVENTIE (nenegociabila de acum):**
  orice premisa de tip „sursa moarta"/„blocat pe X" primeste **data + metoda + punct de observatie**
  si EXPIRA — altfel devine o regula care minte (al treilea caz dupa premisa „SYSTEM" si Google Maps;
  toate verificate o data, dintr-un singur punct, scrise ca fapt, niciodata re-testate).
- **`caen_context.py` — benchmark-ul de CIFRA DE AFACERI nu are sursa corecta la nivel de clasa CAEN**
  (masurat 2026-07-24; in coada dupa Pasul 4, NU „quick win"). `CAEN_BENCHMARK` (linia ~189) e cheiat
  pe **DIVIZIUNE** (2 cifre): „media CAEN 45 = 1.500.000 RON" include si dealerii auto, dar se afiseaza
  pentru clasa 4520. Calea live `INT101B` (linia ~346) e **diviziune Rev.1** SI suprascrie eticheta din
  „estimare" in „date oficiale" (liniile ~320-326) — a repara doar conectivitatea ar transforma o
  estimare prudenta intr-o afirmatie autoritara pe alta clasificare. **INS nu publica CA sub nivel de
  SECTIUNE** (INT104, confirmat din meniu) -> `media_sector` pe CA la nivel de clasa e imposibila din
  INS. Migrarea la INT101W e valida DOAR pt **numarul de firme** (context, nu verdict); verdictele „sub
  percentila 25" pe CA se ELIMINA, nu se califica (nu plasezi o firma in percentila unei populatii care
  nu exista ca data). Fix de onestitate separabil de migrare: eticheta „diviziune", nu clasa.
- **`WinError 206` ("linie de comanda prea lunga") se ridica in Python ca `FileNotFoundError`.**
  A produs mesajul "Claude CLI not found" pentru un executabil care exista. **Cand un mesaj de
  eroare contrazice realitatea verificata, mesajul minte — nu realitatea.** Windows taie linia de
  comanda la ~32.767 caractere; prompturile lungi se paseaza prin `input=`/stdin, nu ca argument.
- **`claude_cli` din `/api/health/deep` e VACUU** — compara `synthesis_mode == "claude_code"`, nu
  stie nimic despre CLI. Dovada reala = linia `SYNTHESIS | ... | provider=X` din job log
  (`log_synthesis`, cablata 2026-07-17).
- **`elapsed_ms` din `SYNTHESIS` e TOTAL PE CASCADA, atribuit castigatorului.**
  `provider=cerebras | 183542ms` = "Claude a incercat 180s, a fost taiat, cerebras a raspuns instant"
  — NU "cerebras e lent".
- **Claude Opus SCRIE ACUM raportul — cauza #5 REPARATA + verificat live 2026-07-18** (job TAROM
  `328981d8`): 4/4 sectiuni quality `provider=claude` (executive_summary/financial_analysis/
  risk_assessment/recommendations), 264-324s fiecare, toate 8 formatele. **Root cause #5:** timeout
  per-sectiune hardcodat 180s < durata reala Claude (masurat: `--effort max`=252s, `high`=143s pe
  prompt ~46k) -> Claude cadea MEREU pe fallback tacut. PLUS timeout global 600s ANULA `execute()` si
  ARUNCA sectiunile deja scrise (`base.py::run` -> `asyncio.wait_for`) -> `0 sections` -> `Formats: none`.
  **Fix:** (a) timeout per-sectiune + effort + plafon global CONFIGURABILE in `.env`
  (`SYNTHESIS_EFFORT`/`SYNTHESIS_CLAUDE_TIMEOUT`/`SYNTHESIS_TOTAL_TIMEOUT`, default max/360/2400);
  (b) `execute()` gestioneaza un DEADLINE INTERN si randeaza determinist sectiunile ramase daca il
  depaseste -> o sectiune lenta nu mai poate zero-iza raportul (test regresie
  `test_synthesis_partial_preservation.py`); (c) subprocesul `claude --print` ELIMINA
  `ANTHROPIC_API_KEY` din mediu -> $0 GARANTAT prin Max, niciodata API (serviciul mostenea env
  var-ul Windows al userului). **Harta pasilor per provider:** `python tools/render_job_map.py [job_id]`
  -> `outputs/<job_id>/execution_map.html`. Ghid: `docs/GHID_UTILIZARE_RIS.md`.

## Cum se citeste "COMPLETATA" mai jos (citeste asta INAINTE de Status)

**"COMPLETATA" in istoricul de mai jos a insemnat: cod scris + teste verzi + commit.
NU a insemnat: "am vazut feature-ul ruland pe date reale".**

Pe **2026-07-15** am gasit **15 feature-uri marcate COMPLETATE care nu rulasera NICIODATA** — nici
macar o data, pentru nicio firma. Printre ele: toate 4 modelele predictive de faliment (marcate livrate
pe 2026-04-08), scorul din Comparator (70 constant pentru orice firma), tabul "Grafice", bara de pozitie
in sector, banner-ul de date incomplete, sectiunea de competitie (gate pe o cheie scrisa in zero locuri).

**Cauza, confirmata cu dovada:** fixture-urile de test codificau ACEEASI presupunere gresita ca si codul
(dovada: `aegrm` testat cu forma `"guarantees"`/`"descriere"`, care NU exista in produs — clientul emite
`details`; un test vitest facea literalmente `expect(45 < 50).toBe(true)`, fara sa randeze componenta).
Testul si codul se confirmau reciproc; niciunul nu fusese confruntat cu producatorul real. **Testele nu
au ratat bug-urile — le-au codificat.**

**Deci: nu trata nicio intrare de mai jos ca dovada ca ceva functioneaza.** Verifica la producatorul
real (DB / clientul sursei) inainte de a construi peste. Intrarile marcate `[NEADEVARAT LA DATA ACEEA]`
au fost corectate retroactiv pe 2026-07-15 — restul n-au fost re-verificate una cate una.

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
- **Faza 20 (R13):** COMPLETATA — 39 items din RECOMANDARI_IMBUNATATIRI_R3: P0(#31 .env.bak gitignore, #32 datetime UTC 4 loc, #2 memory leak \_in_flight, #1 agent timeout individual, #21+26 input validation+extra=forbid), P1(#33 DB transactions, #34 report /data endpoint, #35 22x bare except→logger, #7 scoring Why reasons, #3 HTTPException→RISError, #4 api.ts endpoints, #5 WS agent_start/complete, #15 FTS5 search, #22 SSRF prevention, #24 path traversal hardening, #25 pip-audit script, #36 settings auth+security.py), P2(#37 tsconfig strict, #38 stats cache lock, #39 is_favorite fix, #40 DB indexes, #41 conditional sleep, #42 config validation, #9 concurrent fallback synthesis, #6 cache L1/LRU, #8 GlobalSearch rapoarte+actiuni, #10 scoring volatilitate per industrie, #11 companies sort+filter, #14 dashboard skeleton, #16 useOptimistic favorites, #17 report delta endpoint+UI, #18 PDF markdown helper, #19 SQL window functions score trend, #23 dead code cleanup, #29 accessibility ARIA, #30 token budget single-build), P3(#12 toast dedup, #13 favorites endpoint dedicat)
- **Audit R14 (2026-04-05):** EFECTUAT — scor 82/100 (delta -8 vs R10 90/100). Plan: 99_Plan_vs_Audit/RECOMANDARI_IMBUNATATIRI_R4.md (F0-F6, 28 items). Probleme critice: API key Gemini in logs, 47 fisiere necomise. Scor tinta dupa F0-F5: 90/100.
- **Audit R15 (2026-04-06):** EFECTUAT — scor 86/100 (+4 vs R14). Plan unificat: RECOMANDARI_IMBUNATATIRI_R5.md (53 items din 3 surse). 184 pytest PASSED, 0 failures. TypeScript: 0 erori.
- **Faza R5 (2026-04-06):** COMPLETATA — 47/53 items implementate (F0 9/9 + F1 10/10 + F2 15/15 + F3 11/13 + F4 4/6). 13 feature-uri noi: webhook, quick-score, tags+note, compare templates, sector CAEN, ICS export, batch preview, health status, CLI script, browser notifications, watermark config, key takeaways, score sparkline.
- **Faza R6 (2026-04-07):** COMPLETATA PARTIAL — ~45/65 items implementate din RECOMANDARI_IMBUNATATIRI_R6.md.
- **Hotfix (2026-04-08):** INVALID_CONCURRENT_GRAPH_UPDATE pe `_agent_metrics` — fix in `state.py:68` (`Annotated[dict | None, _merge_dicts]`), ReportView null-safety `sources ?? []`. Commits: dc0d408, 69ae807. **ATENTIE: repornire serviciu obligatorie dupa deploy.** F0-3 (job_service split), F1-2/F1-3/F1-4/F1-5 (retea firme + SQL migration 008), F2-1..F2-4 (Altman/Piotroski/Beneish/Zmijewski + wrapper), F3-3/F3-4/F3-6/F3-8 (trust scoring/anomalii/coherence/quota), F4-1/F4-2/F4-3/F4-4 (monitoring escalation/sync/audit-log/suppress), F5-1 (funding programs JSON+module), F6-1/F6-3/F6-5/F6-8 (risk badge/completeness warning/localStorage draft/dedup dashboard), F7-1/F7-2 (N+1 fix/CSV streaming), F8-5 (29 teste modele predictive) **[NEADEVARAT LA DATA ACEEA — corectat 2026-07-15: cele 4 modele (F2-1..F2-4) erau 100% MOARTE de la aceasta data pana pe 2026-07-15 (`active_totale`/`datorii_totale` nu erau propagate in `verified["financial"]`, deci toate returnau INDISPONIBIL). Cele 29 de teste treceau verzi pentru ca pasau dict-uri sintetice direct in functii, ocolind cablarea reala — sunt exemplul-etalon de test vacuu]**. Provideri noi: GitHub Models, Fireworks AI, SambaNova. 213 pytest PASSED.
- **Gemini Analysis Sprint (2026-04-08):** 3 imbunatatiri din analiza Gemini CLI — commit 7a2e70d. (A) Agentic Reflexion: `_reflexion_check()` in SynthesisAgent detecteaza contradictii tone vs scor in sectiuni critice si corecteaza via Groq. (B) Dynamic CA percentile scoring dual-path: PRIMAR = CA real din `companies.latest_ca` (stocat dupa fiecare analiza), FALLBACK = score_history proxy. Coloana `latest_ca` adaugata idempotent in database.py. (C) Scheduler log cleanup: `_run_log_cleanup_safe()` sterge log-urile rotite mai vechi de 7 zile. 365 pytest PASSED.
- **Sprint R7 (2026-04-09):** COMPLETAT — 18 items din RECOMANDARI_IMBUNATATIRI_R7.md (A1-A5, B1-B5, C1-C4, E3): raport unic RIS-YYYY-XXXX, risk badge numeric, AEGRM garanții, NLQ chatbot, Knowledge Graph (@xyflow), share link HTML, mobile search, dark/light theme, TanStack Query, split componente (ReportView 910→644, CompanyDetail 1009→826), ARIA + type hints, Mistral OCR. 365 pytest PASSED, 0 erori TypeScript.
- **Sprint R8 (2026-04-09):** COMPLETAT — 9 items din RECOMANDARI_IMBUNATATIRI_R8.md (G1-G8 + D1): Process Pool asyncio.to_thread + asyncio.gather (6 formate concurent), TanStack Query Dashboard+Companies+RiskMovers+TrendChart (3/3 pagini migrate), WCAG 2.2 (sidebar focus-visible, contrast text-gray-400, aria-modal GlobalSearch), i18n English (i18n.py + PDF/HTML lang param), ONRC local dataset (migration 009 + import script + agent lookup), Monitorul Oficial crawler (Tavily+scrape, scoring penalty juridic), Prometheus /metrics endpoint, PostgreSQL feasibility (documentat), XGBoost faliment (research doar). 365 pytest PASSED, 0 erori TypeScript.
- **Gemini Audit Sprint (2026-04-11):** COMPLETAT — validare audit Gemini (10 claims verificate: 6 false/deja-facute/overkill respinse, 3 valide implementate) + simplificari cod. (1) Secret key persistence: `config.py` auto-genereaza+persista in `data/.secret_key` (gitignored); hard-fail in `RIS_ENV=production` daca APP_SECRET_KEY lipseste. (2) `main.py` refactor 659→486 LOC: extras `backend/middlewares.py` (5 classes: RequestId, RequestLogging, RequestSizeLimit, ApiKey, SecurityHeaders + `_redact_sensitive` + `register_middlewares`) si `backend/static_serving.py` (mount_frontend_dist). (3) WCAG 2.2 NetworkGraph: `aria-label` pe nodes + edges + `role=application` pe container + `nodesFocusable` + keyboard nav. (4) Simplificari: `_is_private_ip` dedup, benchmark `_position()` helper, key_takeaways provider loop, cleanup variabile nefolosite (`p90_score`, `profit_net`, `risk_content`). Respinse (contrazic context/deja-done): PostgreSQL migration, Dockerfile, PDF Celery (deja G1), GDPR backup T>30 (deja 7 zile), SQLi in migrations (fals — static .sql files), Elasticsearch/Loki (overkill). 365 pytest PASSED, 0 erori TypeScript.
- **Fortify ULTRA + Restante + /imbunatatiri (2026-06-26):** COMPLETAT — 5 commits (`e3a314b`, `605063b`, `82064d2`, `9a33912`, `a42be72`). **FIX CRITIC F1:** 5 coloane fantomă pe `companies` (is_active/risk_score/last_risk_score_numeric/tag/note) → `GET /api/companies` + `/{id}` dădeau **HTTP 500 LIVE** → ALTER idempotent în `run_migrations()` + populare scor la finalul jobului (ca `latest_ca`) + backfill din reports/score_history → filtru `?risk_score=` + sort `score_desc` funcționale. **F5:** migrări consolidate în `run_migrations()` (single source of truth — eliminat ALTER-uri scattered din handlere/scheduler, cauza-rădăcină schema-drift). **F2:** `/api/ask` reparat (color+numeric denormalizat). **F4:** `Companies.tsx` isError. **Restante:** F18 (12× B904→0), F8 (SSRF mort), F7 (logging WARNING), F23 (urllib3 pin), react-router 7.4→7.18 (npm 13→0 vulns). **F26:** test anti-regresie schema `tests/test_companies_schema.py` (run_migrations real vs query-urile companies — a prins un bug fresh-install: `connect()` indexa înainte de crearea tabelelor → mutat în `run_migrations`; F11/F12 = false positives). **/imbunatatiri:** 8/32 safe aplicate (B1 osint_historical + B2 scoruri predictive Altman/Piotroski/Beneish/Zmijewski în `verified_data`, B3 COMPANY_COLS DRY, B4 settings auth, B5 batch trim, F1 fix handoff `?cui=`, F3 empty CTA, F4 a11y). Doc: `99_Plan_vs_Audit/RECOMANDARI_IMBUNATATIRI_2026-06-26.md` (~15 deferred-safe + ~8 strategice; temă: backend colectează > expune). **366 pytest PASSED**, tsc + build clean. Snapshot: `~/.claude/context-snapshots/Sistem_Inteligent_Analize-checkpoint-2026-06-26/`.
- **Fortify Remediere ULTRA — Wave A–F (2026-06-26):** COMPLETAT — execuție autonomă a recomandărilor neimplementate din `.claude-outputs` (fortify 06-25 + /imbunatatiri 06-26), 8 commits (`6eaab00`→`d0878a2`). **A (hygiene):** F10 `list_reports` `asyncio.to_thread` (stat off event-loop), F21 closure bind (B023), F19 `with_retry` pe anaf_bilant+bpi, F3 `.env.bak` mutate în `%LOCALAPPDATA%/RIS/env-backups` + șterse din repo, logging structurat report_service. **B (backend):** F15 `funding_programs` cablat în `agent_verification` → `verified['funding_programs']`; PII#4 monitoring BPI insolvență + scădere CA>30% (free-only via `check_insolvency(use_tavily_fallback=False)` — fără consum quota Tavily); F6 `network_client` cache in-memory TTL 5min (invalidat la `store_administrators`) + batch N+1 prin `cui_to_info`. **C (rapoarte):** randare câmpuri bogate `predictive_scores`/`benchmark`/`actionariat`/`relations`/`aegrm`/`historical_flags`/`funding` în HTML+PDF+DOCX (erau 0/0/0 — cel mai mare gap de livrabil) — verificat E2E pe job real (CUI 49104500). **D (UI):** api.ts +6 metode (searchFts/quickScore/getMonitoringAuditLog/regenerateSection/exportIcs/downloadTimelineReportPdf); CompanyDetail score-trend + timeline PDF; ReportsList filtru tip+search; Monitoring audit-log+retry; ReportView .ics + regenerare secțiuni; Compare notice 2-firme; **fix `/analysis/quick-score`** (importa clase inexistente `ANAFBilantClient/ANAFClient` → `get_anaf_data`+`get_bilant`, chei corecte). **E (pagini noi):** `/sector` SectorDashboard, `/ocr` OcrPage (Mistral), `/quick-tools` QuickTools (FTS+quick-score); Companies bulk-select (compară/monitorizează selectate); BatchAnalysis persist+resume localStorage. **F:** test regresie rich-fields (`test_html_generator::TestRichFields`), F27 teste migrate (QueryClientProvider) committed. **370 pytest PASSED**, tsc+build clean, ReportView vitest 5/5 (pool threads). Deferred (P3): F19-full (retry tavily/monitorul = risc epuizare quota). 9 subagenți (5 wiring UI + 4 pagini).
- **TASK 1 — ReportView „Regenereaza" FUNCȚIONAL (2026-06-27):** COMPLETAT — (1) `report_sections` persistat în `full_data` (`job_service._save_job_results` din `final_state`, înainte de INSERT; delta-ul re-dump-uiește același dict — `delta_service` îl ignoră, citește doar financial/risk_score/company); (2) `regenerate_section` (`jobs.py`) implementat real — reconstituie `verified_data` (exclude report_sections/key_takeaways/delta), `get_sections_for_analysis` validează **dinamic** key-ul (nu set hardcodat cu `market_position` fantomă), `synthesis_agent.generate_section()` (extras din `execute()`, pipeline IDENTIC) re-rulează DOAR secțiunea, `UPDATE reports.full_data`, return `{section:{title,content,word_count}}`; plafon server `asyncio.wait_for(210s)` + client timeout extins 220s pentru quality-route Claude. (3) `api.ts` tip retur nou + `request()` cu `timeoutMs` per-apel; `ReportView.handleRegenerateSection` aplică secțiunea în state. **NU** atins `ALLOWED_SECTIONS`. **Smoke LIVE PASS** (CUI 49104500, job real DONE 18s): report_sections persistat (8 secțiuni) → regen fast `company_profile` 200/8.0s/260w + quality `executive_summary` 200/17.3s/434w, conținut schimbat + persistat (matches_regen=True), 0×500. tsc+build clean, vitest ReportView 5/5 (threads). Commit `386e02f`.
- **TASK 2 (SECONDARY) — COMPLETAT (2026-06-27):** validare randare `aegrm`/`historical_flags`. **Insight (advisor):** livrabilul = secțiunea „Garantii & Istoric (OSINT)" în **HTML+PDF+DOCX**, dar calea **populată** rulase doar prin HTML (`TestRichFields` e html-only); PDF+DOCX populat **nu rulase niciodată** cu date (firmele reale curate). Adăugat `TestRichFieldsPdf` + `test_..._rich_fields_aegrm_historical` cu **diacritice** (ă/ț/ș/î/â) → calea latin-1 PDF (`_sanitize` cu `errors="replace"`) **nu aruncă** pe text OSINT diacritic (modul de eșec prezis, acum păzit). Calea **empty** validată LIVE pe 2 firme reale (49104500 + 43978110: secțiune omisă în HTML+DOCX, 7 formate curate). **Date reale populate LIVE = imposibil:** AEGRM DNS-dead + firmele user curate (0 semnale Monitorul Oficial) — blocaj de DATE, nu de cod. **BUG găsit + REPARAT (advisor adversarial):** cei 3 renderi citeau `fl.get("type")` (slug) + `detail`/`date`, dar `osint_client` emite `{type, label, severity, snippet}` → pe **date reale** randa slug-ul (`cesiune_parti_sociale`) și pierdea descrierea. Fix: HTML+PDF+DOCX preferă `label`→`type` și `snippet`→`detail` (fallback = backward-compat); fixture-uri aliniate la shape-ul REAL osint + test regresie HTML (label uman + snippet). **378 pytest** (+3 generator). Deferred P3: F19-full (risc quotă). **Gotchas confirmate:** vitest `--pool=threads` + fișiere EXPLICIT (bare full-run se blochează); autoflake stripează importuri noi (re-verifică F821/F401).
- **Surse externe FREE noi (2026-07-12):** 3 valuri, 4 commits (`b1cecd2`→`6b6832d`), plan `99_Plan_vs_Audit/PLAN_SURSE_FREE_2026-07-11.md`, decizii verificate la sursă în memory `project_ris_free_sources_decisions`. **(1) VIES** (`vies_client.py`) — validare TVA intracomunitar UE (partener/contraparte): REST `.../vies/rest-api/check-vat-number` + fallback SOAP, `POST /api/analysis/vies` + `api.ts checkVies` + card QuickTools. Fără cheie, comercial OK. **(2) Sancțiuni** (`sanctions_client.py`) — screening OFAC SDN + UE FSF + ONU (~53k intrări, follow-redirects), cache local 24h (gitignored) + pre-warm scheduler; `screen()` conservator (egalitate set-token normalizat + prag single-token≥8, anti-fals-pozitiv); cablat `agent_verification._screen_sanctions` (firmă+admini+asociați, timeout 45s); secțiune „Screening Sanctiuni" în HTML+PDF+DOCX. **NU acoperă PEP** (OpenSanctions CC BY-NC = plătit comercial). **(3) Eurostat** (`eurostat_client.py`) — benchmark sector UE (`sbs_ovw_act`, JSON-stat 2.0, `lastTimePeriod=1`), mapare CAEN→NACE + extractor JSON-stat, nr. firme + angajați/firmă RO vs UE27; secțiune „Benchmark Sector UE" în HTML+PDF+DOCX. **414 pytest** (+36), smoke LIVE toate 3, tsc+build clean. Bonus: reparat `test_funding_programs` fragil la dată. **Excluse (verificat la sursă):** Termene.ro (1.200/an), OpenSanctions/OpenCorporates/D&B/IBISWorld (plătit), RBR/UBO (blocat legal CJEU C-37/20 + L.86/2025), RNPM (web-only), dump ONRC 674MB (deferred, volum mic).
- **Licitatii/Contracte (2026-07-12):** commits `a30bf4b`+`06988f0`+`48e35c4`, plan `99_Plan_vs_Audit/PLAN_INTEGRARE_LICITATII_2026-07-12.md`. **Istoric achizitii publice SEAP** expus in raport (Angle B — RIS deja colecta `get_contracts_won` pe CUI + scora, dar nu randa; secțiune „Istoric Achizitii Publice (SICAP)" in HTML/PDF/DOCX). **Angle A — licitatii deschise pe sector** (`caen_cpv_map.py` mapare orientativa CAEN→CPV + `seap_client.search_open_tenders` via SICAP `GetCNoticeList`, filtrare locala pe prefix CPV, cache 6h; sectiune „Oportunitati de Contracte (SICAP)"). **Decizie:** NU se integreaza TENDERS-RO (proiect separat Next.js/Supabase) — symbiote e mecanism gresit; istoricul e deja in RIS via SEAP; matching GO/NO_GO TENDERS = Faza 2 firm-scoped. **Hardening review adversarial** (`48e35c4`): gate completitudine sanctiuni + Eurostat zecimale + VIES SOAP/GB + subset matching. **435 pytest.**
- **Auto-update local + versiune (2026-07-12, commits `0f79926`→`aef9ade`):** RIS = LOCAL, FĂRĂ Vercel/Supabase. Updater propriu („Vercel local"): `backend/services/updater.py` verifică git remote la 10min → `git pull --ff-only` + `npm build` + restart automat, cu safeguards (tree curat, build verificat, rollback la fail). `GET /api/version` (build git + update_available), `POST /api/update` (manual), `POST /api/restart`. Versiune afișată în header (`VersionBadge`, badge „la zi"/„actualizare disponibilă"). **Starter = iconița desktop (PWA Chrome către :8001)**; backend = serviciu Windows `RIS-Backend` (WinSW, auto-start la boot). **Restart:** Method B self-exit `os._exit(1)` → WinSW `onfailure=restart` (VERIFICAT live, PID schimbat). Serviciul rulează ca **SYSTEM** → git cu `-c safe.directory=*`. Dezactivare: `AUTO_UPDATE_ENABLED=false` în `.env`. **Utilizatorul dă doar refresh în PWA.**
- **Verificare E2E completa toate fluxurile — TOATE 9 AnalysisType (2026-07-12, commits `4371d61`→`3b67cb7`):** COMPLETATA — testare directa pe serviciul LIVE (joburi reale, nu scripturi izolate). Plan complet: `99_Plan_vs_Audit/PLAN_E2E_VERIFICARE_2026-07-12.md`. **10 bug-uri reale gasite + reparate:** (1) Cerebras — model retras din catalogul vendorului, mort ~2-3 luni → migrat `gpt-oss-120b`; (2) `companies.caen_code`/`county` niciodata populate → `/sector`+`compare/sector`+filtrul `?caen=` goale silentios pt orice firma → fix + backfill; (3) `score-trend` — `company_id: int` vs schema UUID TEXT → HTTP 422 garantat → `str`; (4) `timeline-report/pdf` — crash Unicode 100% reproductibil → fix; (5) `export/ics` — cheie JSON inexistenta → fix; (6) `settings test/{service}` — Mistral+Cerebras netestabile → adaugate; (7) sectiunea "opportunities" nu stia de `tender_opportunities` (gasit adversarial, advisor) → fix, verificat 350→3080 caractere; (8) aceeasi sectiune nu stia nici de `funding_programs` → fix; (9, **cel mai sever**) MARKET_ENTRY_ANALYSIS + LEAD_GENERATION + CUSTOM_REPORT nu extrageau CUI din campul lor de intrare (n-au camp "cui" dedicat) → **0/16 completitudine GARANTAT pt orice utilizator real** pe 3/9 tipuri → fix generalizat (extrage CUI din orice camp text); (10) `KeyError('anaf')` — crash cand ANAF nu returneaza date, afecteaza toate 9 tipurile in conditii rare. **3 feature-uri promise dar NEIMPLEMENTATE** (semnalate, nu construite): COMPETITION_ANALYSIS+MARKET_ENTRY_ANALYSIS nu au nicio colectare reala de date despre competitori; LEAD_GENERATION nu cauta/lista firme candidate; CUSTOM_REPORT ignora complet cererea libera a userului (template fix). **1 inconsistenta documentata**: job completat cu succes (fisiere scrise) dar status DB "PAUSED" (handler recovery la un restart cu cauza neclara). **SYNTHESIS_MODE=autonomous investigat, NU comutat:** serviciul ruleaza ca SYSTEM, Claude CLI auth exista doar in profilul userului → switch simplu ar cadea tacut pe fallback (confirmat empiric) — 3 optiuni documentate, decizie lasata userului. Degradare sub concurenta mult redusa dar NU eliminata (retry/backoff pe 429 neaplicat). 440 pytest PASSED, 0 erori TypeScript, toate fix-urile verificate live.
- **LEAD_GENERATION — feature lipsa implementat (2026-07-12, commits `950113c`→`33af688`):** COMPLETAT — cautare firme candidate pe tabela proprie `companies` (nu ONRC bulk, gol pe aceasta masina) + parsare AI (Groq) a criteriilor din `ideal_client` text liber. `backend/agents/tools/lead_search.py` (nou): `parse_lead_criteria()` + `search_candidate_companies()` (filtrare judet/CAEN + prioritate: crestere/licitatii/probleme). Sectiune noua `lead_candidates` in raport. **Bug serios reparat dupa 4 runde de testare live:** AI-ul amesteca CUI-ul firmei solicitante cu CUI-urile firmelor candidate — 3 incercari pe calea AI (prompt mai strict, route "quality", izolare completa context/JSON — verificat direct ca prompt-ul era curat) NU au oprit halucinarea. **Fix real:** sectiunea randata 100% determinist in Python (`_render_lead_candidates_content`), zero apel AI — CUI/CAEN/scor vin direct din date, imposibil de halucinat. Bug cosmetic conex reparat: randererul markdown strip-uie indentarea, deci un item numerotat + sub-bullet indentat rupea numerotarea vizuala (toate firmele aparea "1.") → consolidat fiecare candidat pe un singur rand. **Verificare suplimentara:** spot-check fidelitate numerica pe fix-urile #7/#8 din sweep-ul E2E (opportunities/funding) — cifre transcrise corect, fara probleme noi. 440 pytest PASSED. Memory: `project_ris_lead_generation_deterministic` — lectie generalizabila (date per-entitate = randare determinista, nu LLM).
- **Audit follow-up A+B+C+D (2026-07-12):** COMPLETAT — implementate recomandarile din `AUDIT_FUNCTII.html`. **(A)** `backend/agents/tools/connectivity.py` nou — `PING_REGISTRY` cu 15 functii `ping_*` (pattern generic, nu 15 elif), dispatch din `POST /api/settings/test/{service}` existent. Verificat LIVE: 11/15 OK (ANAF TVA/Bilant, BNR, openapi.ro, SEAP, Monitorul Oficial, Sanctiuni, Eurostat, Brave, Jina, Google Maps), 4 gasite picate real — **BPI/buletinul.ro DNS-dead**, **INS TEMPO timeout**, **AEGRM tot DNS-dead** (confirmat, ca la 2026-06-27), **Portal Just: `zeep` neinstalat** in acest mediu. **(B)** `POST /api/settings/test/email` + `/test/webhook` (webhook reutilizeaza `_send_webhook_if_configured` din `job_service.py`, acum cu rezultat structurat). **(C) FINDING DE SECURITATE CONFIRMAT + REPARAT:** `RIS_API_KEY` lipsea complet din `.env` → backend pe `0.0.0.0:8001` fara NICIO autentificare pe `/api/*` (verificat live: 200 fara header). Frontend nu trimitea deloc `X-RIS-Key`. Fix (ales de user dintre 3 optiuni): cheie noua generata, `.env` + `frontend/.env` (`VITE_RIS_API_KEY`, gitignored), `api.ts`+`ChatInput.tsx`+`ReportView.tsx` trimit automat header-ul, `/api/reports/public/*` exceptat explicit (share link extern), `tests/conftest.py` izoleaza pytest de cheia locala. Verificat live: 401 fara cheie / 200 cu cheie / PWA functionala in browser (0 erori consola). **(D)** `AUDIT_FUNCTII.html` regenerat (0 necuratate) cu butoane live pt toate sursele noi. 440 pytest PASSED, 29 vitest PASSED (+ fix mic bug preexistent `getVersion` lipsa din mock `Dashboard.test.tsx`). `Companies.test.tsx` are un hang preexistent confirmat si pe baseline — semnalat, neinvestigat (afara scop). Memory: `project_ris_audit_dashboard_ping_registry`.
- **Portal Just reparat COMPLET (2026-07-13):** dupa `pip install zeep` (ceruta de user), retestarea a scos la iveala ca `backend/agents/tools/just_client.py` **nu functionase niciodata cu succes** — 3 bug-uri suprapuse, niciodata verificate contra serviciului real: (1) parametri SOAP gresiti (`instanta=0` presupunea "toate instantele" — nu exista, `institutie` e camp obligatoriu cu 246 valori posibile); (2) fix aprobat de user: mapare judet firma → Tribunalul judetului + Curtea de Apel regionala (circumscriptii verificate cu WebFetch, nu din memorie); (3) `_parse_dosare` verifica atribute (`numarDosar`, `calitate` flat) care nu exista pe raspunsul real (shape real: `numar`, `parti.DosarParte[]` cu `{nume, calitateParte}`) — ar fi raportat tot 0 dosare chiar cu parametrii corectati. Verificat cu date reale: cautare "Popescu" pe Cluj → 242 dosare gasite si parsate corect. `tests/test_just_client.py` rescris (mock-ul vechi testa un shape fictiv). `requirements.txt`: zeep 4.3.1→4.3.3 (versiunea testata live). 443 pytest PASSED.
- **Audit complet 88/88 endpoint-uri + 15/15 pagini verificate vizual (2026-07-13):** userul a cerut citirea completa a ce a ramas netestat din `AUDIT_FUNCTII.html` + continuarea executiei. **88/88 endpoint-uri REST+WS** (de la 56/88) testate live, inclusiv toate 14 ramase cu efecte reale (companies/import, chat, jobs/cancel+retry-source, batch/resume, settings PUT, tags, notifications, note, frontend-log, restart, update) — executate cu payload-uri no-op/idempotente unde a fost posibil. **GASIT:** `/metrics` raspunde 200 dar cu `{"error":"prometheus-client not installed"}` — endpoint neconectat real. **15/15 pagini frontend verificate vizual in browser real** (Chrome, nu doar curl). **4 bug-uri UI/backend reale gasite + reparate**: (1) badge scor risc pe `/companies` afisa mereu "N/A" — camp inexistent `last_score` + lipsea din `COMPANY_COLS`; (2) pe `/company/:id`, cardurile "Analize"/"Prima Analiza"/CAEN erau goale — `COMPANY_COLS` nu includea `analysis_count`/`first_analyzed_at`/`caen_description`/`city`; (3) `POST /api/companies/{id}/chat` citea `full_data.get("verified_data")` — cheie care NU EXISTA NICIODATA, deci contextul de scor/CA era mereu gol de la scriere; (4) `POST /api/companies/import` — INSERT cu coloane fantoma `created_at`/`updated_at` (HTTP 500 garantat). **Gotcha reconfirmat:** service worker-ul PWA serveste bundle vechi dupa rebuild — tab nou (nu doar hard-refresh) necesar pt verificare vizuala reala.
- **BUG CRITIC gasit prin analiza E2E reala (2026-07-13):** la cererea userului ("incepe o analiza completa cu toate functiile, remediaza direct"), o rulare reala `FULL_COMPANY_PROFILE` nivel 3 a picat cu `'NoneType' object has no attribute 'get'`. Root cause reala: `cannot access local variable 'litigation'` in `backend/agents/verification/scoring.py` — variabila era asignata DOAR in ramura Portal Just SOAP indisponibil, dar folosita neconditionat mai jos. **Bug complet LATENT pana azi**: cat timp Portal Just a fost mereu picat, ramura "SOAP disponibil" nu rulase niciodata — propriul fix de azi la Portal Just a expus acest crash pre-existent, care ar fi afectat ORICE analiza pt orice firma odata ce sursa raspunde cu succes. Fix + verificare cu re-rulare completa: DONE 100%, completeness 16/16, risc Verde 84.5/100, toate formatele + randare browser OK. **Lectie:** un fix care repara o sursa anterior mereu-picata poate expune bug-uri latente in codul din aval care presupunea implicit ca acea ramura nu ruleaza — doar o rulare E2E reala (nu teste izolate) prinde asta. 443 pytest, tsc clean, 6 commits. Memory: `project_ris_audit_dashboard_ping_registry`.
- **Audit complet 18 domenii (2026-07-13):** `/audit complet` — 9 agenti paraleli, 63 findinguri (4 CRITICA, 10 HIGH, 25 MEDIUM, 24 LOW). Raport complet: `.claude-outputs/audit/2026-07-13_021900/audit_report.md` (+ `audit_score.json`, ambele **gitignored, local-only**). Scor 73/100 (delta -18 vs auditul 2026-04-10, metodologie diferita — vezi nota din raport, NU e regresie de cod). **4 CRITICA de reparat prima data:** (1) `official_data["cui"]`/`["company_name"]` setate DOAR daca ANAF reuseste (`agent_official.py:145-156`) → job DONE fara legatura la `companies` daca ANAF pica dar alte surse merg; (2) `requirements.txt` `fpdf2>=2.9.0` — versiune INEXISTENTA pe PyPI (ultima reala 2.8.7) → orice instalare fresh esueaza, confirmat inclusiv ca blocheaza `pip-audit` insusi; (3) Starlette 0.41.3 (transitiv `fastapi==0.115.5`) — 7 avize reale confirmate live cu `pip-audit`, incl. CVE-2026-48818 (leak NTLM prin `StaticFiles` pe Windows, serviciul ruleaza ca SYSTEM) si CVE-2026-48817 — fix necesita upgrade fastapi pt starlette>=1.1.0; (4) `calculate_risk_score` — 807 linii, complexitate ciclomatica 167 (`scoring.py:160-967`). **2 findinguri suplimentare descoperite prin verificare independenta** (nu doar din raportul agentilor): `python-multipart==0.0.22` folosit real (upload CSV/OCR) dar absent din requirements.txt, 4 CVE reale; serviciul Windows ruleaza pe Python global fara venv dedicat (confirmat `tools/RIS-Backend.xml` == `sys.executable`). Mod `complet` = doar raportare, ZERO auto-fix aplicat.
- **Remediere completa 4 CRITICA din audit (2026-07-13, commits `1d8d0bd`→`c9352d3`):** toate 4 CRITICA din auditul de mai sus REPARATE + verificate live, in aceeasi sesiune. **#1** `fpdf2>=2.9.0` (versiune inexistenta) → `>=2.8.0,<3.0.0`. **#2** `official_data["cui"]`/`["company_name"]` mutate NECONDITIONAT dupa blocul ANAF in `agent_official.py` (nu mai depind de succesul ANAF) — verificat: firma legata corect in `companies` chiar cu alte surse esuate. **#3** fastapi `0.115.5→0.139.0` + starlette pinat explicit la `1.3.1` (repara TOATE cele 8 avize, nu doar cele din 1.1.0) + `python-multipart==0.0.31` declarat (folosit real, era absent din requirements.txt — 5 CVE). Metoda de upgrade dep major: snapshot `pip freeze` → dry-run gate (orice pachet-tinta miscat peste cele 3 asteptate = semnal de risc; aici doar `annotated-doc`, leaf nou, anyio/pydantic neatinse) → install → `pip check` → pytest → restart → smoke pe suprafata REALA de regresie (multipart FormParser + WebSocket, neacoperita de TestClient) — batch CSV + OCR 3MB + WS auth/ping-pong toate OK, zero regresie. Verificat vizual in browser (tab nou): PWA + `/audit.html` + toate bundle-urile `/assets/*` servite 200 pe starlette nou (suprafata exact atinsa de CVE-2026-48818/StaticFiles). Side-effect gasit (nu reparat, deferred M25): `gradio` (pachet nelegat de RIS pe Python global) cere `starlette<1.0`, acum in conflict — intareste finding-ul "fara venv dedicat". **#4** (cel mai mare) refactor `calculate_risk_score`: 807 linii/complexitate 167 → orchestrator de 5 linii-complexitate + 9 functii mici (`_score_financiar/_juridic/_fiscal/_operational/_reputational/_piata` + `_compute_confidence/_detect_zombie_and_anomalies/_build_early_warnings`), cu `*Facts` dataclass explicite (nu variabile libere partajate — cauza bug-ului `litigation` de acum 2 zile). Executat DUPA `/plan` dedicat (userul a cerut sa nu se atinga cod inainte de plan) + Pas 0 obligatoriu: golden snapshot pe 6 fixture-uri SINTETICE acoperind ramuri netestate (coverage `scoring.py` 39%→77%, doar din golden), inclusiv un caz adversarial "everything triggers" (zombie+insolventa+BPI+Portal Just SOAP+AEGRM+Monitorul Oficial simultan) si unul de cuplare mixta a confidence-ului — cerute explicit de user dupa ce a identificat ca bug-urile clasei `litigation` nu sunt vizibile in scorul final, ci in blocurile derivate. Executat in etape (dimensiuni simple → financiar/operational cuplate → consumatori agregati ULTIMII), golden re-verificat dupa FIECARE etapa, fiecare etapa adusa userului pt review inainte de commit. Pastrat (nu reparat) un quirk pre-existent documentat in cod: total_score se calculeaza inainte de zombie detection, deci override-ul zombie nu se reflecta in total_score — decizie business separata, deferred. **Verificare finala end-to-end pe job real live** (CUI 26313362, DONE 100%): scor 87.3/Verde plauzibil, solvency_matrix corect (Sanatos+Solid→RISC MINIM), toate 6 dimensiuni + toate cheile contractului de retur prezente, persistenta confirmata in `companies.risk_score`/`last_risk_score_numeric` + `score_history`, toate 7 fisiere de raport generate pe disc. 450 pytest PASSED (443+7 golden), ~~`ruff check` all clean~~ **[FALS — corectat 2026-07-15: `ruff check backend/` avea 17 erori si atunci (auditul din 2026-07-14 le-a confirmat identic); azi 10, dupa curatarea reziduului]**. Plan: `99_Plan_vs_Audit/PLAN_REFACTOR_SCORING_2026-07-13.md`. Ramase din audit: 10 HIGH + 25 MEDIUM + 24 LOW — de planificat impreuna (grupate, nu unul cate unul — unele se ating intre ele, ex. prag culoare scor duplicat in 12+ fisiere).
- **HIGH #8 + #10 din audit reparate + verificate live (2026-07-13, commits `478a16c`, `cce6abd`):** #6 (avize starlette) si #7 (python-multipart) din audit erau DEJA rezolvate de CRITICA #3 — raman 8 HIGH reale, atacate ca grup de "quick-wins user-facing". **HIGH #8** (notificari/webhook arata mereu "Firma: N/A"): 2 bug-uri suprapuse, gasite prin verificare live (nu presupunere din audit) — (1) `job_service.py` citea `verified_data.get("company_name")`/`.get("cui")` ca chei TOP-LEVEL, care NU EXISTA NICIODATA (verificat: nicio asignare in tot `agent_verification.py`); calea reala e `verified["company"]["denumire"/"cui"]["value"]`, acelasi pattern deja folosit in acelasi fisier. (2) Chiar dupa fix-ul #1, notificarea TOT nu aparea (0 randuri `job_complete` in toata istoria DB) — cauza: `_sev = "success" if _score >= 70 ...` compara STRING-ul de culoare ("Verde") cu un numar → `TypeError`, INGHITITA silentios de un `except...logger.debug`. Ridicat temporar la `logger.exception`, capturat traceback-ul real, reparat (severitate din culoare direct), apoi `except` mutat la `logger.warning` (NU inapoi la debug — un except care inghite tacut a ascuns bug-ul asta). Verificat live: notificare reala cu `title="Analiza finalizata: CFL SOLUTION S.R.L."`. **HIGH #10** (WS `agent_complete` fara `status` → UI arata "finalizat (undefined)"): adaugat `status` ("success"/"error") la toate 5 puncte de emisie din `orchestrator.py` (official/verification/synthesis urmaresc statusul prin variabila, reflecta error boundary; web/market hardcodat "success" — broadcast-ul lor exista doar pe calea de succes). Verificat live prin WebSocket real: toate 5 mesaje `agent_complete` cu `status='success'` prezent. **Gasit adiacent, NU reparat (semnalat explicit, in afara scope):** ramurile except de la `web`/`market` nu trimit deloc `agent_complete` pe eroare — frontend nu primeste niciun semnal de finalizare pt Agent 2/3 daca acestea pica. 450 pytest PASSED dupa fiecare fix. Raman: 8 HIGH reale (2 rezolvate) + 25 MEDIUM + 24 LOW — de planificat grupat.
- **HIGH #4 + #5 (Grup C — securitate) din audit reparate + verificate live (2026-07-13, commits `951fb3a`, urmatorul):** **HIGH #4** (`RIS_API_KEY` fail-open fara garda): acelasi pattern deja existent pt `APP_SECRET_KEY` in `config.py` — daca cheia e goala/lipsa la boot, WARNING zgomotos + hard-fail DOAR in `RIS_ENV=production`; plus log UNIC (nu per-request) in `ApiKeyMiddleware.__init__` cand fail-open-ul e activ. Cu cheia setata (cazul curent) — zero schimbare de comportament, verificat live (`/api/companies` fara cheie 401, cu cheie 200, neschimbat). Teste noi `tests/test_security_gates.py` (6 teste, construiesc `Settings`/`ApiKeyMiddleware` direct — NU golesc `.env`-ul real). **Observatie minora (nu reparata):** rularea `pytest` produce 1 warning real in `logs/ris_runtime.log` per proces (fixture-ul `conftest.py` seteaza `ris_api_key=""` pt izolare teste, iar noul log din `__init__` se declanseaza o data pe `app`-ul global partajat de `TestClient`) — zgomot de log, nu problema de securitate. **HIGH #5** (`/metrics` + `/audit.html`/`.js` neprotejate, nu-s sub `/api/`): `/metrics` adaugat explicit in `ApiKeyMiddleware` (machine-facing, gate-uit desi azi e stub `prometheus-client not installed`, pt cand devine functional). `/audit.html` + `/audit.js` devin LOCALHOST-ONLY (decizia userului): servite doar daca `request.client.host` e loopback (127.0.0.1/::1), altfel `404` (nu `403`, ca sa nu confirme existenta). Verificat live: `/metrics` fara cheie→401, cu cheie→200; `/audit.html` via 127.0.0.1→200, via IP Tailscale masinii (100.80.18.55)→404, `/api/companies` via Tailscale CU cheie ramane 200 (PWA de pe telefon neafectat — restrictia e STRICT pe `/audit.html`/`.js`); confirmat vizual in browser ca `http://localhost:8001/audit.html` inca se incarca. Documentat in `START_PWA.md`. 456 pytest PASSED (450+6 noi). Raman: 6 HIGH reale + 25 MEDIUM + 24 LOW — urmeaza DRY #2+#3.
- **Grup DRY #3 (rich-fields) din audit reparat + verificat (2026-07-14, commit `27a7df3`):** extras `backend/reports/rich_fields.py::build_rich_fields_model(verified)` — centralizeaza gate-urile de prezenta + unwrap `.get("value")` (aegrm/seap) + normalizarea `historical_flags` (label-peste-type-peste-title-peste-category, snippet-peste-detail-peste-description-peste-text — zona cu 2 bug-uri deja reparate 2026-06-27, triplicata independent in html/pdf/docx_generator). Gate de subset INAINTE de extractie: confirmat ca toate 3 randereaza acelasi 9 grupuri cu conditii identice. 2 divergente FINE gasite si LASATE per-renderer (nu unificate silentios): (1) HTML omite sectiunea actionariat daca ramane goala dupa `act_ok=True` cu date lipsa, PDF/DOCX nu au acest guard (reachable, edge case real); (2) fallback-ul label/detail era mai larg in HTML (`category`/`text`) — verificat la sursa (`osint_client.py`) ca acele chei nu sunt NICIODATA emise azi, deci canonicalizarea in model pe lantul superset e garantat behavior-preserving. Randarea (markup, culori, trunchiere 240 vs 200) ramane neschimbata per format. Gate de acceptanta: diff before/after via `git stash` pe fixture cu toate 9 grupuri populate, extras ca text din toate 3 formate (HTML string, DOCX python-docx, PDF `pdfplumber`) — IDENTIC in toate 3. `tests/test_rich_fields.py` nou (10 teste normalizare+gate-uri) + test de continut DOCX nou (nu doar "nu arunca"). 467 pytest PASSED (456+11).
- **Grup DRY #2 (get_risk_color) — extractie completa (2026-07-14, commit `de67c91`):** dupa inventarul complet (25 situri: 11 backend + 14 frontend, ZERO divergenta de prag/operator — toate `>=70`/`>=40`), Opus a dat GO pt extractie ("DOAR pragul se centralizeaza, nuantele NU se unifica"). Backend: `risk_bucket(score)` in `scoring.py` (backed de `COLOR_MAP`, care era exportat dar folosit nicaieri — acum e sursa reala, nu mai decorativa; motorul insusi il apeleaza la linia 1130 in loc sa re-hardcodeze). Migrati: `excel_generator._risk_fill` + duplicarea interna din Trend sheet, `pptx_generator._risk_color` (ramura numerica), `agent_synthesis._reflexion_check`. SQL CASE WHEN din `compare.py` ramas inline (SQL nu importa Python) + comentariu cross-reference. `quick-score` (analysis.py) si `completeness_score` (alta metrica) NEATINSE, explicit in afara scope. Frontend: `frontend/src/lib/risk.ts::getRiskBucket()` oglinda TS, migrate toate site-urile de recompute independent (Companies.tsx, ReportView.tsx+ReportHeader.tsx, CompareCompanies.tsx, SectorDashboard.tsx, CompanyDetail.tsx x3) — fiecare site isi PASTREAZA reprezentarea exacta (hex/Tailwind -400/-500/clasa custom risk-*), doar logica de prag inlocuita, per decizia explicita a userului de a NU unifica nuantele. Verificare: teste de granita noi (70/69.99/40/39.99) in ambele limbaje + coverage noua pt excel/pptx (zero teste existau inainte pe aceste functii) + tsc/build frontend curate + live spot-check dupa restart serviciu (tab nou): Companii/CompanyDetail/ReportView/Comparator arata culorile identic cu inainte pe firme reale, inclusiv un caz live care a nimerit exact granita 70→Verde in Comparator. 483 pytest PASSED (467+16).
- **Refactor #1 (AgentOfficial.execute) — COMPLET, Pas 0 + Faza A + B + C + D (2026-07-14, commits `26e379e`, `0aaccbd`, `d2556e3`, `a596d71`, `246ae7f`):** PLAN scris + APROBAT de Opus inainte de orice cod (harta reala ~20 blocuri secventiale vs 6 presupuse de audit, consumatori verificati direct — `agent_verification.py` primeste `official_data` intreg la ~15 functii interne). **Pas 0:** test de caracterizare (`tests/test_agent_official_characterization.py`) — golden snapshot pe INTREG dict-ul de retur, 6 fixture-uri. **Dovada de non-vacuitate:** re-cuplat temporar regresia CRITICA #2 → testul a picat pe 2 fixture-uri → revertit complet (git diff gol). **Descoperire adiacenta:** `tavily_quota_ok` gateaza SI legal-merged SI OSINT historical-flags (acelasi flag) — quota epuizata pierde silentios si semnalele OSINT (semnalat, NU reparat). **Faza A:** 7 functii pure per-sursa extrase (`_process_anaf_result`, `_process_openapi_result`, `_process_bilant_result`, `_process_bnr_result`, `_process_bpi_result`, `_process_aegrm_result`, `_derive_anaf_fiscal_risk`). **Faza B:** 4 functii cu side-effects/dependinte de ordine extrase (`_store_administrators_sideeffect` — citeste `openapi_source` brut, nu `official_data`; `_fetch_portal_just` — depinde de onrc_structured/onrc_local; `_fetch_google_maps` — pastreaza bug-ul preexistent `address` mort, neatins; `_fetch_monitorul_oficial_partea_iv`). **Faza C:** 4 functii fallback guardate de stare extrase (`_fetch_onrc_fallback`, `_fetch_financial_fallback`, `_check_tavily_quota` — pastreaza cuplarea cu OSINT, `_fetch_legal_merged_and_split`). **Faza D (ultima):** 5 functii consumatori agregati extrase (`_build_web_intelligence` — Brave+Jina+clasificare; `_resolve_caen_context` — fallback 3 trepte onrc_structured→anaf→financial_official, returneaza `caen_code`; `_compute_data_freshness`; `_compute_diagnostics` — returneaza `(ok_count, total_count)` inghetate ca in original; `_fetch_osint_historical` — ULTIMUL, dupa diagnostics, quirk-ul "diagnostics inainte de OSINT source-append" pastrat exact). Fiecare faza: ZERO reordonare (apel de metoda in ACEEASI pozitie textuala), commit separat, golden re-verificat IDENTIC dupa fiecare. **Gotcha autoflake reconfirmat** in Faza D: split-ul edit inline→apel-de-metoda vs adaugare-definitie-metoda a lasat temporar 4 importuri neutilizate (`get_caen_context`, `brave_available`, `brave_search`, `enrich_tavily_results`), sterse de hook-ul PostToolUse intre cele 2 edit-uri — prins imediat la golden, reparat intr-un singur edit ulterior. **Complexitate `execute()`: 81 → 15** (radon cc) — dovada ca refactorul si-a atins scopul. **E2E LIVE final** (CUI 26313362, dupa restart serviciu real): DONE 100% in 58s, completeness 94% (15/16), scor 87.3/Verde IDENTIC cu rularile anterioare din `score_history` (behavior-preserving confirmat), toate 7 formate raport scrise pe disc, linkage confirmat `companies`+`score_history`. 490 pytest PASSED (483+7), ~~ruff check curat (1 finding preexistent in `_fetch_insolvency`)~~ **[FALS — corectat 2026-07-15: erau 17 erori reale; afirmatia a fost preluata si repetata in brief-urile ulterioare fara sa fie verificata]**. **Refactor #1 INCHIS** — raman HIGH #9 (feature competitie) + 25 MEDIUM + 24 LOW din audit.
- **Chei moarte frontend + reziduu ruff reparate (2026-07-15):** clasa sistemica "cod care citeste chei pe care nimic nu le scrie" — inchisa in 2 valuri anterioare (Comparator, Grafice, 4 modele faliment) + acest val: 4 chei frontend moarte in `ReportView`/`ReportHeader`/`Dashboard` (verificate direct in `data/ris.db reports.full_data`, NU din fixture-uri): (1) "Pozitie in Sector" citea `data.risk.sector_position`/`data.benchmark.percentile` (inexistente) — real e `risk_score.sector_position`, dict per-metrica cu bucket categorial (`"P90+"`/`"P75-P90"`/...), NU un procentil numeric — randat ca etichete oneste, nu bara falsa; (2) banner "Date insuficiente" citea `report.completeness_score`/`.failed_sources` (zero coloana DB, niciodata existente) — real e `full_data.agent_diagnostics.completeness_score`/`.missing_sources`; (3) badge "LOW DATA" pe Dashboard citea `job.completeness_score` (coloana inexistenta pe `jobs`, ar necesita join nou) — cod mort STERS (R-MINIMAL); (4) badge "vs anterior" din antet citea `fullData.delta_info`/`.previous_report_id` (niciodata scrise) — inlocuit cu fetch real `GET /reports/{id}/delta` (`has_delta`), acelasi endpoint deja folosit de tabul "Modificari". Teste vitest vechi pe completeness erau VACUE (`expect(45 < 50).toBe(true)`, nu randau componenta) — rescrise sa randeze real componenta cu forma corecta de date. **`ruff check backend/` 17→10 erori:** 4 F841 + 3 B007 erau reziduu (variabile calculate corect inlocuite/nefolosite din refactor anterior, sterse) — 2 F841 raman NEATINSE, sunt bug-uri reale gasite si NEREPARATE intentionat (raportate, nu corectate): `one_pager_generator.py:52` (`cui = meta.get("company_name", "")` — cheie/dict gresite, CUI-ul real nu apare niciodata in header-ul PDF 1-pager), `pptx_generator.py:182` (`icon` calculat per severitate anomalie, niciodata randat pe slide). 830 pytest PASSED, tsc+build frontend curate.
- **Feedback Loop:** ACTIV — RIS_TEST.bat, logs/ris_summary.log, ris_runtime.log, ris_frontend.log (5 componente), ISSUES.md, session startup protocol
- **Git:** https://github.com/RolandPetrila/Sistem-Inteligent-Analize.git | **734 pytest** + vitest (8 fisiere/69 teste, `Companies.test.tsx` reparat 2026-07-16 — nu mai e exclus) | `ruff check backend/`: **All checks passed (0 erori)** de la 2026-07-16 (cele 2 F841 raportate anterior — `one_pager` CUI + `pptx` icon — REPARATE ca A5/B3; zip-urile capata `strict=True` cu garda reala, nu doar suprimare)
- **Sesiune 2026-07-16 (32 commit-uri, rundele 4-8, mod AUTONOM Opus-advisor + Sonnet-subagenti):** vezi snapshot `~/.claude/context-snapshots/Sistem_Inteligent_Analize-checkpoint-2026-07-16/`. Clasa "cod care citeste ce nimic nu scrie la celalalt capat" — 23 instante in 2 zile, la GRANITA, niciun test nu o traverseaza. Reparate: orbire la pierderi (+mina armata `early_warnings`), regula anomalie moarta pe toate firmele (ISO vs `%d.%m.%Y`), FIX #10 volatilitate pe sector 100% mort (benzi 2-cifre vs clase 4-cifre), bucla infinita `/companies` (bug productie, nu "flaky"), batch ERROR spinner infinit, `RIS_TEST.bat` rupt din ziua crearii (em-dash), dashboard audit rupt de fastapi 0.139, quota Tavily randata onest, divergenta 6D-vs-modele ca fapt. Refactoare: `_score_financiar` 95→4, `execute` in curs. Reguli noi: **job live inainte de push la cale reinviata**, **dovada non-vacuitate obligatorie** (test pica pe cod vechi), **agentii NU comit — comite Opus serializat** (race pe index). `demoanaf.ro` respins (fara ToS). Piotroski F2/F3→None (D5).
- **Sesiune 2026-07-18 (4 commits `24d2c05`→`aa431fe`, mod Opus-advisor):** vezi snapshot `~/.claude/context-snapshots/Sistem_Inteligent_Analize-checkpoint-2026-07-18/`. **Claude Opus scrie EFECTIV raportul** (cauza #5 timeout reparata + verificat live job TAROM `328981d8`: 4/4 quality `provider=claude`; effort/timeout in `.env`; env-strip `ANTHROPIC_API_KEY` = $0 Max; DEADLINE INTERN pastreaza munca partiala). Regenerare sectiune reparata (cap 210s→`synthesis_claude_timeout+120`, verificat 321s). **Dashboard Health Status reparat** (marca fals FAIL `ai_providers`/`http_pool` — dict-uri sanatoase; verificat live healthy). **Verificare conexiuni LIVE centralizata:** `tools/preflight_check.py` (CLI) + `GET /api/settings/preflight` (concurent ~8s) + componenta `PreflightCheck` pe Analiza Noua (verificat in browser real: "GATA DE EXECUTIE 18/18"). `tools/render_job_map.py` (harta pasilor per provider→HTML). `docs/GHID_UTILIZARE_RIS.md` (ghid). Startere desktop personale: `Deschide RIS.vbs`, `Verifica conexiuni RIS.vbs`. Ramas (deferat): progres WS per-sectiune. 833 pytest.
- **Sesiune 2026-07-24/25 (4 commits `8987621`→`07e1355`, LOCALE NEPUSHATE, mod Opus-advisor):** remediere Val 1 din audit extern Opus (`99_Plan_vs_Audit/AUDIT_BRIEF_RIS_CLAUDE_AI_CHAT.md` → verificat prin `VERIFICARE_AUDIT_BRIEF_2026-07-24.md`, plan `PLAN_REMEDIERE_2026-07-24.md` — toate 3 UNTRACKED intentionat: repo public + date firma terta). Snapshot: `~/.claude/context-snapshots/Sistem_Inteligent_Analize-checkpoint-2026-07-25/`. **(1) SEAP `93fa5de` — cel mai grav:** contractele erau ale ALTOR firme in FIECARE raport (`spiCuiSupplier` = cheie ignorata tacit → lista nationala; service auto raporta 296M RON = 804× CA). Reparat: rezolutie CUI→id intern via `searchSuppliers` + filtrare `winnerId` (CA) / `supplierId` (DA — **nume diferite, fara simetrie**), doar `sysDirectAcquisitionState.id==7` = castigat, `seap_status()` 3 stari, canar dublu. **6 campuri moarte** gasite prin masurarea setului real de chei (4/7 pe CA goale dintotdeauna). Vezi memory `project_ris_seap_attribution`. **(2) config `739f52f`:** `.env` BATE acum env var in RIS (`settings_customise_sources`) — **corectat faptul FALS "serviciul = SYSTEM"** (e `.\ALIENWARE`; env var-ul umbrea `.env` SI in productie → 403 Telegram tacut luni). Env vars NEsterse (sistem central chei). **(3) monitoring `8987621`:** canal in-app + `is_active` degatate de Telegram (erau in `if changes and telegram_notify`); ramura RED "firma disparuta ANAF" nu crea notificare in-app; `send_telegram_detailed` + coloane `last_delivery_*` + garda chat_id=bot. **(4) `07e1355`:** semantica `verified` 3 stari (nu figureaza = RASPUNS, nu esec) + marcaj `score_history` (`methodology_version` v2, delta suprimat peste granita in ambele sensuri). Verificat LIVE job `38f9020a` CUI 9901265: toate criteriile trec (Piata fara bonus, completitudine 100% SEAP-nu-e-gap, 0 "competenta dovedita", narativ mentioneaza corect absenta). **886 pytest**, ruff+tsc clean. **Ramas:** decizii Roland (push + rotire token Telegram) + Pas 3 validare CUI + Pas 4 wizard.
- **16 pagini frontend** (adaugat SectorDashboard /sector, OcrPage /ocr, QuickTools /quick-tools)
- **Planificari detaliate:** ROLAND_PLANIFICARI_MODULE.md (R4 + R5 + R6 + R7 + R8 = 97 items total)
- **Deep Research:** 99_Deep_Research/ (2 rapoarte complete cu roadmap)
- **Spec complet:** SPEC_INTELLIGENCE_SYSTEM_V2.md
- **89+ REST endpoints + 1 WebSocket + 16 pagini frontend + 8 formate raport (cu câmpuri bogate randate) + diagnostic + audit + request tracing + notifications + favorites + timeline + OCR UI + /metrics**

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
- AI: Claude CLI (Opus) + Groq (Llama 4 Scout) + Mistral (Small 3) + Gemini (2.5 Flash) + Cerebras (gpt-oss-120b, migrat de la Qwen 3 235B retras din catalog 2026-07-12) — 5-level fallback + smart routing
- ONRC: openapi.ro (100 req/luna gratuit, date structurate)
- Licitatii: SEAP e-licitatie.ro API (contracte publice)
- Search: Tavily API (1000 req/luna gratuit)
- PDF: fpdf2 (nu WeasyPrint — evitam GTK pe Windows)
- Notificari: Telegram Bot API (configurat)
- Statistici: INS TEMPO API (date oficiale per CAEN)

## Key Files

- `backend/main.py` — FastAPI entry point + lifespan + routers + exception handlers + WebSocket (486 LOC dupa refactor Gemini-audit)
- `backend/middlewares.py` — 5 middleware classes (RequestId, RequestLogging, RequestSizeLimit, ApiKey, SecurityHeaders) + `register_middlewares()`
- `backend/static_serving.py` — `mount_frontend_dist()` pentru servit `frontend/dist` (Tailscale/PWA mode)
- `backend/config.py` — Settings din .env (pydantic-settings) + secret key persistence (`data/.secret_key`)
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
- `backend/agents/tools/monitorul_oficial_client.py` — G2: Monitorul Oficial Partea IV (cesiuni, dizolvari, radieri) + scoring penalty
- `backend/agents/tools/connectivity.py` — PING_REGISTRY: test conectivitate pt 15 surse externe fara endpoint dedicat (dispatch din POST /api/settings/test/{service})
- `backend/reports/i18n.py` — G5: i18n traduceri ro/en pentru rapoarte PDF/HTML
- `backend/migrations/009_onrc_local.sql` — D1: tabel ONRC local dataset din data.gov.ro
- `tools/import_onrc.py` — D1: script import CSV ONRC in SQLite (~660MB active + ~392MB radiate)
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
- `frontend/src/App.tsx` — React Router + Layout (16 pagini, lazy)
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
- `frontend/src/pages/SectorDashboard.tsx` — Pagina Sector CAEN (/sector): stats + top firme din `getSectorDashboard`
- `frontend/src/pages/OcrPage.tsx` — Pagina OCR Mistral (/ocr): upload PDF/imagine → text extras
- `frontend/src/pages/QuickTools.tsx` — Instrumente Rapide (/quick-tools): cautare FTS + quick-score bulk (fara AI)
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
- Port frontend: 5173 (dev) / 8001 (productie — dist/ servit de backend)
- Database: ./data/ris.db (WAL mode)
- Outputs: ./outputs/[job_id]/
- Backups: ./backups/ris_YYYY-MM-DD.db (rotatie 7 zile)
- .env obligatoriu (.env.example ca referinta)
- fpdf2 pt PDF (NU WeasyPrint)
- Synthesis: subprocess `claude --print --model claude-opus-4-8 --effort {SYNTHESIS_EFFORT}` (default max), timeout `SYNTHESIS_CLAUDE_TIMEOUT` (360s), fara `ANTHROPIC_API_KEY` in mediu ($0 Max)

## Structura folder principal (ROOT) — REGULA STRICTA

Folderul principal `C:\Proiecte\Sistem_Inteligent_Analize\` trebuie sa ramana curat.
Fisierele permise in root sunt NUMAI:

| Fisier                          | Motiv                                                                                                      |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `CLAUDE.md`                     | Instructiuni Claude — obligatoriu in root                                                                  |
| `ISSUES.md`                     | Feedback loop utilizator                                                                                   |
| `TODO_ROLAND.md`                | Task list activ                                                                                            |
| `README.md`                     | Documentatie principala proiect                                                                            |
| `requirements.txt`              | Dependente Python — obligatoriu in root                                                                    |
| `pyproject.toml`                | Configurare Python tools                                                                                   |
| `.env` / `.env.example`         | Config mediu — obligatoriu in root                                                                         |
| `.gitignore` / `.gitattributes` | Config git — obligatoriu in root                                                                           |
| `RIS.vbs`                       | Launcher unic (dublu-click pornire)                                                                        |
| `RIS_TEST.bat`                  | Runner teste (pytest + vitest)                                                                             |
| `ris_icon.ico`                  | Iconita aplicatie (folosita de shortcut desktop)                                                           |
| `START_PWA.md`                  | Documentatie pornire + Tailscale + PWA                                                                     |
| `AUDIT_FUNCTII.html`            | Dashboard live audit functii — vezi sectiunea "Audit Functii" mai jos. Exceptie explicita user 2026-07-12. |
| `AUDIT_FUNCTII.js`              | JS extern pentru dashboard-ul de mai sus (CSP `script-src 'self'` interzice inline).                       |

**TOATE celelalte fisiere se plaseaza in subfoldere:**

- Planificari, audit-uri, executoare → `99_Plan_vs_Audit/`
- Rapoarte de cercetare, deep research → `99_Deep_Research/`
- Documentatie tehnica, spec-uri, prompturi → `docs/`
- Scripturi utilitare, tools, iconite → `tools/`
- Teste backend/frontend → `tests/`
- Outputuri Claude, audituri automate → `.claude-outputs/`

**La creare fisier nou: intreaba-te "in ce subfolder apartine?" inainte de a-l pune in root.**
**Nu crea fisiere .bat, .vbs, .ps1 noi in root fara confirmare explicita.**

## Audit Functii — regula obligatorie de mentinere (adaugata 2026-07-12)

`AUDIT_FUNCTII.html` (+ `AUDIT_FUNCTII.js`) e dashboard-ul LIVE de audit al tuturor
functiilor testabile din RIS: cele 88 endpoint-uri REST+WebSocket, 9 tipuri de analiza,
5 provideri AI, 18 integrari surse externe, 3 canale de notificare, 7 task-uri scheduler,
8 formate raport, 15 pagini frontend. Servit de backend la `/audit.html` + `/audit.js`
(same-origin — evita CORS si respecta CSP-ul `script-src 'self'` existent, care blocheaza
silentios orice `<script>` inline sau `onclick="..."`).

**REGULA: dupa ORICE endpoint/functie noua adaugata in `backend/routers/*.py`,
`backend/main.py`, sau orice integrare noua de sursa externa/provider/task scheduler:**

1. Ruleaza `python tools/generate_audit_dashboard.py` — lista de endpoint-uri se
   extrage AUTOMAT prin introspectia `backend.main.app.routes` (nu poate ramane
   in urma codului la nivel de existenta). Orice endpoint nou aparut fara metadate
   apare automat marcat "NECURATAT" in dashboard si listat in output-ul scriptului.
2. Adauga o intrare in `CURATED_ENDPOINTS` (in acelasi script) cu categoria,
   `tested: False` (pana se verifica live macar o data), o nota, si `live_safe`
   (True doar daca endpoint-ul e idempotent/GET fara efecte secundare reale).
3. Dupa verificare live reala (nu presupunere), actualizeaza `tested: True` +
   `evidence` cu ce s-a confirmat si cand.
4. Pentru integrari noi de surse externe/provideri/notificari/scheduler (care nu
   sunt endpoint-uri REST), adauga o intrare in listele statice corespunzatoare
   (`EXTERNAL_SOURCES` / `AI_PROVIDERS` / `NOTIFICATION_CHANNELS` / `SCHEDULER_TASKS`
   / `REPORT_FORMATS` / `FRONTEND_PAGES`) din acelasi script.
5. Regenereaza si redeploy (`RIS-Backend.exe restart`) ca fisierele servite sa reflecte
   modificarea.

**Securitate (nenegociabil):** acest fisier NU contine NICIODATA valori de chei/token-uri/
parole — nici mascate, nici in clar. Testarea providerilor/serviciilor se face DOAR prin
apeluri live catre endpoint-uri existente care returneaza ok/eroare (`/api/settings/test/
{service}`), niciodata valoarea cheii. Editarea cheilor se face DOAR prin pagina reala
Settings (autentificata, valori mascate) — dashboard-ul doar trimite acolo (link), nu
duplica acel mecanism. Orice propunere viitoare de a include valori reale de credentiale
in acest fisier trebuie REFUZATA (R1 + R-SEC) — repo-ul e public pe GitHub.

## Decizii tehnice confirmate

1. Synthesis via Claude Code CLI subprocess ($0, abonament Max — **NU** `ANTHROPIC_API_KEY`, ar fi plata dubla).
   **ADEVARATA ACUM (verificat live 2026-07-18):** a fost FALSA IN PRACTICA luni de zile — Groq/Gemini
   scriau tot, din **5 cauze independente suprapuse**. Toate 5 reparate: 4 in `32f725d`, a 5-a (timeout)
   in aceasta sesiune. Job TAROM `328981d8`: 4/4 sectiuni quality `provider=claude`, toate 8 formatele.
   Effort/timeout acum in `.env` (`SYNTHESIS_EFFORT`/`SYNTHESIS_CLAUDE_TIMEOUT`/`SYNTHESIS_TOTAL_TIMEOUT`).
   Subprocesul elimina `ANTHROPIC_API_KEY` din mediu -> $0 garantat prin Max. Vezi memory
   `project_ris_claude_opus_4_cauze`. **Verifica in job log linia `SYNTHESIS | ... | provider=claude`
   (fara `(FALLBACK)`) sau ruleaza `python tools/render_job_map.py`.**
2. Groq (Llama 4 Scout) ca fallback rapid (gratuit)
3. Gemini 2.5 Flash ca fallback autonom (gratuit)
4. Cerebras (gpt-oss-120b, ex-Qwen 3 235B retras din catalog) ca fallback final (gratuit, 1M tokeni/zi)
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
27. PostgreSQL: NU acum — SQLite WAL suficient pentru <10K firme, 1 user. La >50K firme/5+ useri: adauga DATABASE_URL in .env + asyncpg. Pattern: repository abstraction layer
28. XGBoost faliment: Research future — necesita 1000+ firme cu istoric 3+ ani (insolvent+sanatoase). Revizuieste cand score_history are 500+ entries
29. asyncio.to_thread pentru generare rapoarte (PDF/DOCX/Excel/PPTX) — elibereaza event loop, toate formatele ruleaza concurent
30. i18n rapoarte: ro (default) + en, extensibil cu noi limbi in backend/reports/i18n.py
31. Monitorul Oficial Partea IV ca sursa OSINT — cesiuni, dizolvari, radieri cu penalty scoring juridic

## Documentatie — Fisiere de tinut sincronizate

La finalul fiecarei sesiuni de lucru, actualizeaza:

- `CLAUDE.md` — status faze, key files, decizii
- `TODO_ROLAND.md` — status items, ce ramane de facut
- `docs/FUNCTII_SISTEM.md` — inventar complet functionalitati
- `99_Plan_vs_Audit/AUDIT_REPORT.md` — doar daca s-au facut modificari majore
- Memory files — project_ris_status.md, reference_api_keys.md

## Regula Commit Obligatoriu

**Dupa ORICE modificare in fisierele proiectului → commit + push imediat.**

```bash
git add fisier1 fisier2 ...   # DOAR fisierele modificate in sesiunea curenta
git commit -m "tip: descriere"
git push origin main
```

Nu lasa modificari uncommitted la finalul sesiunii.

## Comenzi

```bash
# Start (dublu-click, zero ferestre, serviciu Windows)
RIS.vbs

# Serviciu Windows — gestionare manuala
sc start RIS-Backend
sc stop RIS-Backend
sc query RIS-Backend
tools\RIS-Backend.exe restart   # WinSW restart

# Frontend build (necesar dupa modificari UI, pentru Tailscale/PWA)
cd frontend && npm run build    # dist/ servit de backend pe 8001

# Rebuild iconita
python tools\create_icon.py

# Teste
RIS_TEST.bat                    # pytest + vitest

# Dev mode (doar development, nu productie)
python -m backend.main          # Backend pe 8001
cd frontend && npm run dev      # Frontend pe 5173 (dev cu HMR)
```
