# PLAN — Verificare E2E toate fluxurile implementate (2026-07-12)

## Context

Ultima verificare E2E (sesiunea trecută) a acoperit UN singur flux: `FULL_COMPANY_PROFILE`
pe 1 firmă (CUI 26313362), prin API-ul live, cu inspectarea raportului real generat.
A găsit și reparat 1 bug real (SEAP `Referer` lipsă → istoric achiziții mereu gol).

Cerința curentă: verificare E2E pe **toate fluxurile implementate**, nu doar unul.

## Descoperire preliminară (înainte de orice test) — IMPORTANT

`grep .env`: `SYNTHESIS_MODE=autonomous` (nu `claude_code`).
Decizia tehnică #1 din CLAUDE.md spune sinteza ar trebui să ruleze via Claude Code CLI
subprocess (Opus, "$0, calitate maxima"), cu Groq/Gemini/Cerebras/Mistral ca _fallback_.
În modul `autonomous`, CLI-ul Claude nu e folosit deloc — toate rapoartele generate acum
folosesc direct fallback-urile. Efect direct asupra "analizelor în profunzime" — merită
clarificat cu tine explicit (vezi întrebarea de mai jos), NU schimb nimic fără decizia ta.

## Constrângeri / riscuri reale (nu teoretice)

- **Tavily**: 8/1000 cote folosite luna asta (verificat live la 2026-07-12) — headroom mare.
- **openapi.ro**: 100/lună, NEverificat câte s-au consumat — verific înainte de Tier 1.
- **Telegram real**: `test/{service}` cu `service=telegram` + orice alertă de monitoring
  reală declanșată de `check-now` TRIMIT mesaj Telegram efectiv.
- **Email real**: `POST /reports/{id}/send-email` trimite email efectiv dacă SMTP e configurat.
- **`/api/update` + `/api/restart`**: NU le retrigger live în acest plan — au fost deja
  verificate funcțional în sesiunea anterioară (PID schimbat, mecanism confirmat). Repornirea
  serviciului acum ar întrerupe testarea în desfășurare. Verificare = code review, nu execuție.
- **Scheduler background** (monitoring 6h, backup zilnic, auto-update 10min, log cleanup):
  verificare prin `logs/ris_runtime.log` / `ris_summary.log` (au rulat deja de la ultimul
  restart), NU force-trigger separat.

## Metodologie

Ca și data trecută: **NU** scripturi izolate cu cache rece. Driving prin API-ul live al
serviciului de producție (`localhost:8001`), poll status real, inspectare output REAL
(`outputs/{job_id}/*`, `reports.full_data` din `data/ris.db`), nu presupuneri din cod.
Reutilizez CUI-uri deja cunoscute (26313362 Mosslein, 49104500, 43978110 — cache cald pe
sursele de bază ANAF/BNR/ONRC) ca să nu irosesc cotă nou pe firme noi fără motiv.

## TIER 1 — Fluxul central "analiză în profunzime" (prioritate maximă)

- [ ] Verific consum openapi.ro curent (câte din 100/lună)
- [ ] Rulez cel puțin 3 din cele 9 `AnalysisType` (nu doar FULL_COMPANY_PROFILE) pe
      CUI cunoscut, confirm că fiecare tip produce secțiuni/focus DISTINCTE (nu același
      raport generic indiferent de tip) — asta e testul real al „profunzimii"
      Tipuri: FULL_COMPANY_PROFILE (deja făcut), PARTNER_RISK_ASSESSMENT, TENDER_OPPORTUNITIES
- [ ] Verific toate cele 8 formate de raport pe un job din cele de mai sus
      (PDF, DOCX, HTML, Excel, PPTX, 1-pager, ZIP, share link public)
- [ ] Verific WebSocket progress (evenimente agent_start/complete reale în timpul jobului)
- [ ] Verific diagnostics endpoint (`/jobs/{id}/diagnostics`) reflectă status real per sursă
- [ ] Verific `retry-source` pe o sursă căzută (dacă apare uneori)
- [ ] Clarific + documentez SYNTHESIS_MODE (vezi întrebare user)

## TIER 2 — Fluxuri secundare implementate (smoke E2E, cotă redusă)

- [ ] Batch: preview CSV → create → progress → resume → download ZIP (CSV mic, 2-3 CUI cunoscute)
- [ ] Compare: 2 firme side-by-side (PDF) + compare/sector + compare templates CRUD
- [ ] Monitoring: create alert → check-now (pe firmă fără schimbări recente, risc mic de
      alertă falsă) → toggle → suppress → audit-log → history → health
- [ ] Companii: search/fts, risk-movers, favorites, tags, note, network, timeline,
      timeline-report(+pdf), score-trend, predictive, export/csv, auto-reanalyze
- [ ] NLQ: `/api/ask` + `parse-query`
- [ ] Quick tools: quick-score, VIES check
- [ ] OCR: upload document test (caut/generez fixture minimal)
- [ ] Reports: delta, export ics, share (public token access neautentificat)
- [ ] Settings: `test/{service}` pentru groq/gemini/mistral/cerebras (fără tavily/telegram —
      side-effect real, cer confirmare separat)

## TIER 3 — Verificare prin code review, NU execuție live

- [ ] `/api/update`, `/api/restart` — cod + log din verificarea anterioară (PID)
- [ ] Scheduler background (monitoring/backup/auto-update/log-cleanup) — inspectare
      `logs/ris_runtime.log` pentru dovadă că au rulat

## Jurnal execuție (index)

1. SYNTHESIS_MODE — investigat, NU comutat (jos)
2. TIER 1 AnalysisType — BUG Cerebras găsit + reparat (jos)
3. **TIER 2 compare/sector — BUG companies.caen_code/county mereu NULL — GĂSIT + REPARAT** (jos)
4. Tier 1 rest (formate raport, WS, diagnostics) — TOATE VERIFICATE OK
5. Tier 2 compare (2 firme, report PDF, sector, templates) — TOATE OK dupa fix #3

### SYNTHESIS_MODE — investigat, NU comutat (blocant real găsit)

- `claude.exe` e pe PATH machine-wide (`C:\Users\ALIENWARE\.local\bin` e în PATH de Machine) — deci binarul s-ar găsi.
- DAR: WinSW (`tools/RIS-Backend.xml`) nu are `<serviceaccount>` → serviciul rulează ca **SYSTEM**.
- `C:\Windows\System32\config\systemprofile\.claude` → **nu există** (testat `Test-Path`).
- `C:\Users\ALIENWARE\.claude` + `.claude.json` → **există** (auth-ul e doar la user).
- Test empiric: `claude --print` cu `USERPROFILE`/`HOME` redirectate spre un folder gol
  → eșuează în **6.3s** cu `Not logged in · Please run /login`, exit code 1 (NU hang 180s).
- Concluzie: flip-ul simplu pe `claude_code` NU ar activa Opus — codul (`_generate_with_claude`)
  ar primi `returncode != 0` rapid și ar cădea pe fallback oricum (per logica proprie din
  `synthesis_providers.py:60-67`), doar cu ~6s latență inutilă adăugată per secțiune × N secțiuni.
- Opțiuni reale (de decis cu userul, NU aplicate acum): (1) rulează serviciul ca user ALIENWARE
  în loc de SYSTEM (ar rezolva simultan și issue-ul `git dubious ownership` din updater, dar e
  schimbare de infra HIGH risk — cere confirmare separată), (2) auth CLI via `ANTHROPIC_API_KEY`
  în env-ul serviciului (schimbă costul din "$0 subscription" în billing per-token — contrazice
  decizia tehnică #1), (3) las autonomous (Groq/Gemini/Cerebras/Mistral) cum e acum.
- **Nu am modificat `.env`** — rămâne `SYNTHESIS_MODE=autonomous`, decizie lăsată userului.

### TIER 1 — 3 AnalysisType diferite pe CUI 26313362 — BUG REAL GĂSIT + REPARAT

- Job PARTNER_RISK_ASSESSMENT + TENDER_OPPORTUNITIES rulate (pe lângă FULL_COMPANY_PROFILE
  deja verificat sesiunea trecută) → CONFIRMAT: fiecare tip produce set DIFERIT de secțiuni
  (5 pt PARTNER_RISK: executive_summary/company_profile/financial_analysis/risk_assessment/
  recommendations; 4 pt TENDER_OPP: executive_summary/company_profile/opportunities/
  recommendations) — analysis_type chiar direcționează structura raportului, nu e generic.
- DAR: în ambele joburi, secțiunile-cheie (`financial_analysis`, `risk_assessment`,
  `recommendations`) erau degradate la stub/fallback sau complet "Indisponibil (toti
  providerii AI au esuat)". Root cause din `logs/ris_runtime.log` (reprodus identic în
  2026-06-26 ȘI 2026-07-12 — bug persistent, nu fluke de concurență):
  1. **Cerebras 100% down**: `HTTP 404 model_not_found` pe FIECARE apel — modelul
     `qwen-3-235b-a22b-instruct-2507` a fost retras din catalogul Cerebras (confirmat live
     `GET /v1/models` → doar `gemma-4-31b`, `zai-glm-4.7`, `gpt-oss-120b` disponibile).
  2. **Groq 429 rate-limited** în burst (3/3 eșecuri → circuit breaker deschis 30 min).
  3. Cu Cerebras mort + Groq limitat, lanțul de 5 fallback-uri (Claude CLI/Gemini/Groq/
     Mistral/Cerebras) ajungea efectiv la 2 provideri utilizabili (Gemini+Mistral) — dacă
     și aceștia erau ocupați/lenți, secțiunea pica complet.
- **FIX APLICAT**: `backend/agents/synthesis_providers.py` — model Cerebras schimbat la
  `gpt-oss-120b` (testat live înainte de commit: 200 OK, text RO coerent). Commit `4371d61`,
  push, service restart (WinSW), verificat prin apel DIRECT la `_generate_with_cerebras()`
  în procesul aplicației (nu doar curl extern): `Cerebras OK: 28 words`.
- **Verificare finală**: job PARTNER_RISK_ASSESSMENT re-rulat DUPĂ fix pe același CUI —
  toate 5 secțiuni acum text narativ complet (financial_analysis 278→3353 chars,
  risk_assessment 301→2300 chars, recommendations "Indisponibil"→2761 chars text real).
- Impact: acesta e motivul cel mai probabil din spatele senzației "analizele nu sunt
  suficient de profunde" — nu (doar) SYNTHESIS_MODE, ci un fallback provider mort de facto
  de cel puțin 2-3 luni (dovadă log 2026-06-26) care degrada exact secțiunile cele mai
  substanțiale ale rapoartelor sub sarcină/rate-limit.

### TIER 1 rest — formate raport / WS / diagnostics / share — TOATE OK

- 6 formate download (PDF/DOCX/HTML/Excel/PPTX/1-Pager) → toate HTTP 200, dimensiuni reale.
  ("zip" NU e format valid per-raport — corectat presupunere proprie din plan; ZIP exista
  doar la nivel de batch. Nu e bug.)
- Share link public (`/reports/{id}/share` → `/reports/public/{token}`) → HTTP 200 FĂRĂ auth,
  conținut real (37KB).
- Diagnostics (`/jobs/{id}/diagnostics`) → completeness gate real (88/100, 2 gap-uri reale
  cu motiv explicit), nu placeholder.
- WebSocket (`/ws/jobs/{id}`) → testat cu script real (`websockets` lib), evenimente complete:
  progress(0→5→10) → agent_start/complete (official 19.9s, verification 0.8s, synthesis
  9.4s) → job_complete cu report_id + formats. 10 evenimente, toate corecte.

### TIER 2 compare — BUG REAL #2: companies.caen_code / county mereu NULL

- `POST /api/compare/sector {"caen_section":"36"}` → returna `companies: []`, `total_in_db: 0`
  deși Mosslein (CAEN 3600, secțiunea 36) fusese analizat de 13 ori.
- Root cause (`backend/services/job_service.py` upsert companii): INSERT-ul original seta
  DOAR `id/cui/name/county(hardcodat None!)/analysis_count` — niciodată `caen_code` sau
  `caen_description`, și nicio UPDATE ulterioară nu le completa (spre deosebire de
  `latest_ca`, care avea deja acest pattern de auto-update). Confirmat pe TOATE cele 7
  firme din DB: `caen_code IS NULL` și `county IS NULL` peste tot, deși datele erau
  disponibile corect în `verified_data["company"]["caen_code"]["value"]` la fiecare job.
- Impact real: `/sector` (SectorDashboard, pagină întreagă), `POST /compare/sector`, și
  filtrul `?caen=` din `GET /api/companies` erau **silențios goale pentru orice firmă**,
  indiferent câte analize reale rulau — o funcționalitate întreagă (context de sector, parte
  din "analiză în profunzime") nu a funcționat niciodată în producție.
- **FIX**: extrage `caen_code`/`judet`/`caen_description` din `verified_data["company"]`
  (aceeași sursă OFICIAL-trust folosită la randarea raportului) și le persistă pe INSERT +
  UPDATE `COALESCE` (auto-refresh la fiecare re-analiză). Backfill manual rulat pe cele 7
  firme existente din `reports.full_data` (6/7 recuperate complet, 1 fără CAEN disponibil
  în raportul stocat). Commit `7913791`, push, restart, 440 pytest PASSED.
- **Verificare finală live**: `compare/sector {"caen_section":"36"}` → acum returnează
  Mosslein cu date complete; `GET /api/companies?caen=3600` → filtrează corect (1/7 firme).

### Re-test sub sarcină concurentă (cerut de advisor) — fix Cerebras confirmat, dar NU 100% elimină riscul

- Rulate 2 joburi PARTNER_RISK_ASSESSMENT concurente (CUI 49104500 + 43978110) — aceleași
  condiții care cauzau degradarea originală.
- Rezultat: 9/10 secțiuni OK (vs. 3-4/9 degradate înainte de fix) — îmbunătățire mare.
- DAR: 1 secțiune (`financial_analysis`, job A) tot a degradat la stub — de data asta pentru
  că **Groq ȘI Cerebras** au primit 429 (rate-limit) simultan în acest run. Cerebras acum
  participă real în lanț (nu mai e mort structural), dar sub burst concurent tot se poate
  epuiza împreună cu Groq. Nu mai e "provider complet mort" (bug de config, reparat), ci
  "fereastră de risc rezidual la concurență mare" (limitare arhitecturală: nu exista
  retry/backoff dedicat pe 429, doar circuit-breaker care marchează esec dupa 3 lovituri).
- **Nu am extins fix-ul la retry/backoff pe 429** — ar fi o schimbare de comportament mai
  mare in pipeline-ul de sinteza (afecteaza toate sectiunile/toti providerii), nu doar o
  corectie de config gresit. Recomandare pentru sesiune viitoare, nu aplicata acum.

### CA discrepancy warning — FALSE POSITIVE in coherence checker (timeboxed, nu e bug de date)

- Log: `Numeric coherence warnings: Discrepanta CA detectata intre sectiuni: 1.4M vs 20.0M RON`.
- Verificat continutul real (executive_summary, job TENDER_OPPORTUNITIES): "14.15M RON" =
  cifra de afaceri REALA a firmei; "peste 20M RON" = valoarea TOTALA a oportunitatilor de
  licitatii deschise gasite (SICAP) — doua metrici DIFERITE, ambele corecte in context, nu
  o eroare de date. Checker-ul de coerenta numerica (Faza 10B) are un fals-pozitiv cand
  raportul discuta legitim 2 sume monetare diferite (CA firma vs. valoare oportunitati
  externe) — nu distinge intre ele, doar cauta orice 2 tipare "X.XM RON" in text.
  Severitate mica (doar log warning intern, nu ajunge in raportul afisat userului) — notat,
  nu reparat acum (in afara scope-ului acestei verificari E2E).

### Restul Tier 2 — TOATE VERIFICATE OK (fara alte bug-uri noi)

- Batch: preview → create real (2 CUI) → progress → DONE 2/2 → download ZIP (14 fisiere:
  7 formate × 2 firme + sumar CSV). OK.
- Monitoring: create → list → toggle → toggle back → audit-log → health → history →
  check-now (real, 0 alerte declansate) → suppress → delete (cleanup). Toate OK.
- Companii: fts search, risk-movers, favorites, tags, note, network, timeline, predictive,
  export/csv, auto-reanalyze — toate OK. (network/timeline goale pt Mosslein — plauzibil,
  nu au fost gasite date OSINT/relatii, nu neaparat bug.)
- NLQ: `/api/ask` (raspuns structurat inteligent, date reale) + `parse-query` (95%
  confidence, extras corect analysis_type + CUI). OK.
- Quick tools: `quick-score` (batch 2 CUI, date reale ANAF+Bilant) + VIES (validare TVA
  live, date reale UE). OK.
- OCR: upload imagine test → text extras corect (Mistral). OK.
- Reports: `delta` (corect "prima analiza" pt tip nou de raport), `list`. OK.
- Settings: test groq/gemini (OK dinainte) — vezi bug separat mai jos pt mistral/cerebras.
- **Efecte reale aprobate**: Telegram test → trimis cu succes. Email test → esuat CORECT
  cu mesaj clar (`GMAIL_USER`/`GMAIL_APP_PASSWORD` goale in `.env` — gap de configurare
  cunoscut dinainte, NU bug de cod).

### BUG REAL #3: score-trend — company_id: int (ar fi trebuit str, UUID)

- `GET /companies/{company_id}/score-trend` → HTTP 422 mereu pt orice apel real (frontend-ul
  trimite UUID string, ruta declara `company_id: int`). `score_history.company_id` +
  `companies.id` sunt `TEXT` (UUID) peste tot in schema si cod — feature complet
  nefunctional de la introducere (CompanyDetail score trend / sparkline).
- Fix: `company_id: int` → `company_id: str`. Commit `fff2feb`. Verificat live: 200 OK,
  date reale (istoric scoruri + delta calculat corect via LAG window function).

### BUG REAL #4: timeline-report/pdf — crash 100% reproductibil pe caracter Unicode

- `GET /companies/{cui}/timeline-report/pdf` → HTTP 500 mereu. Traceback:
  `FPDFUnicodeEncodingException` — caracterul em-dash "—" in `TimelinePdf.header()`
  (apelat automat de fpdf la fiecare `add_page()`) trimis direct la fontul Helvetica
  (latin-1), fara sa treaca prin helper-ul local `_sanitize()` deja folosit consecvent
  in restul continutului fisierului. Acelasi risc latent la fallback-ul `"year"` lipsa.
- Fix: ambele locuri infasurate cu `_sanitize()`. Commit `fff2feb`. Verificat live:
  200 OK, PDF valid (2.4KB).

### BUG REAL #5: export/ics — cheie JSON gresita, feature mort de la introducere

- `GET /reports/{id}/export/ics` → HTTP 404 "Nu exista licitatii" chiar si pe raportul
  TENDER_OPPORTUNITIES cu 15 licitatii deschise reale confirmate (deadline-uri, CPV-uri,
  autoritati contractante). Cauza: citea `data["market"]["seap_tenders"]` — cheie
  niciodata scrisa nicaieri in cod (grep confirmat 0 rezultate). Datele reale sunt in
  `data["tender_opportunities"]["opportunities"]` (Angle A v2), cu campuri
  `deadline`/`title`/`authority`/`value`/`notice_no` in loc de `deadline_date`/`id`.
- Fix: cale + campuri corectate. Commit `9a069d2`. Verificat live: 200 OK, .ics valid
  cu 15 evenimente reale (deadline-uri corecte, UID stabil din notice_no).

### BUG REAL #6: settings test/{service} — Mistral + Cerebras netestabile

- Descoperit imediat dupa fix-ul Cerebras (#Tier1): endpoint-ul de test conectivitate
  suporta doar groq/gemini/tavily/telegram — Mistral si Cerebras (2 din 5 provideri
  activi in lantul de sinteza) nu puteau fi verificati nici din UI, nici din API.
  Exact genul de gol care a lasat bug-ul Cerebras (#Tier1) nedetectat luni de zile.
- Fix: adaugate ambele, reutilizand `_PROVIDERS` din `synthesis_providers.py` (sursa
  unica, evita alt drift). Commit `41ab809`. Verificat live: ambele HTTP 200.
- Observatie NErezolvata (semnalata, nu fixata): `MISTRAL_API_KEY`/`CEREBRAS_API_KEY`
  nu apar deloc in formularul Settings.tsx (doar 7 campuri: Tavily/Gemini/Synthesis mode/
  Telegram x2/Gmail x2) — decizie de scop UI mai mare, las-o userului.

### Tier 3 — verificat prin checkpoint DB (mai bun decat grep pe log)

- `logs/ris_runtime.log` e filtrat WARNING+ (documentat in CLAUDE.md) — grep pe "scheduler"
  a dat 0 rezultate fals-ingrijorator (loguru scrie INFO doar in sink-ul de fisier, nu si
  in stdout-ul capturat de WinSW). Dovada reala: tabela `scheduler_state` — toate 7 task-uri
  (backup/log_cleanup/monitoring/cache_cleanup/auto_reanalyze/sanctions_refresh/auto_update)
  au timestamp recent + status "OK". `auto_update` a rulat la 14:42 UTC azi (dupa commiturile
  mele), confirmand ca bucla de verificare la 10 min chiar functioneaza in productie.
- `/api/update` + `/api/restart`: NU re-testate live (ar fi intrerupt sesiunea) — mecanismul
  a fost deja verificat live in sesiunea anterioara (PID schimbat dupa self-exit + WinSW
  onfailure). Cod nemodificat de atunci.

### BUG REAL #7 (gasit de advisor, verificare adversariala) — sectiunea "opportunities" nu stia de Angle A v2

- Job TENDER_OPPORTUNITIES avea 15 licitatii SICAP REALE in `tender_opportunities.opportunities`
  (confirmat separat la fix-ul export/ics), dar sectiunea narativa "Oportunitati" — sectiunea
  CENTRALA pentru acest tip de analiza — tot cadea pe fallback "date insuficiente". Trecuse
  initial drept "comportament corect anti-halucinare" pana la re-verificare adversariala.
- Root cause: `_has_sufficient_data("opportunities")` verifica doar `market.seap.total_contracts`
  (Angle B, contracte CASTIGATE) + `web_presence.opportunities` (camp nescris niciodata) — nu
  stia de cheia noua `tender_opportunities` (Angle A v2). Chiar daca gate-ul trecea,
  `section_data_map["opportunities"]` nu includea `tender_opportunities` in promptul AI.
- Fix: gate + context map actualizate. Commit `d3e8dd1`. **Verificat live pe job nou**:
  sectiunea trece de la ~350 caractere fallback la 3080 caractere text narativ real, cu
  licitatii concrete (titlu, valoare, deadline, eligibilitate CAEN).
- **Bonus descoperire, NU reparata (feature lipsa, nu bug de wiring)**: gate-ul pentru
  sectiunea "competition" verifica `web_presence.competitors` — camp care nu e scris
  NICAIERI in cod (grep confirmat in agent_official.py + agent_verification.py). Tipul de
  analiza `COMPETITION_ANALYSIS` nu are, de fapt, nicio colectare reala de date despre
  competitori — sectiunea cade mereu pe fallback, structural, nu ocazional. Nu e o cheie
  gresita de reparat (ca #5/#7), ci o functionalitate niciodata implementata. NEVERIFICAT
  live (nu am rulat un job COMPETITION_ANALYSIS) — semnalat, nu construit acum.

## Onestitate asupra scope-ului acoperit (limite reale ale acestei verificari)

- **6 din 9 AnalysisType NU au fost rulate deloc**: COMPETITION_ANALYSIS, FUNDING_OPPORTUNITIES,
  MARKET_ENTRY_ANALYSIS, LEAD_GENERATION, MONITORING_SETUP, CUSTOM_REPORT. Am confirmat ca
  fiecare tip produce un set diferit de sectiuni — deci cele 6 netestate pot avea propriile
  bug-uri de wiring specifice tipului (ca #7, gasit doar prin testarea efectiva a TENDER_
  OPPORTUNITIES). "Toate fluxurile" NU a fost atins literal — doar un esantion reprezentativ.
- **Degradarea sub sarcina concurenta NU e 100% eliminata**, doar mult redusa: re-testul cu 2
  joburi simultane a aratat 1/10 sectiuni tot picand ("ALL providers failed") cand Groq+Cerebras
  au fost rate-limitate simultan. Batch analysis (feature reala, folosita) ruleaza exact in
  acest regim de concurenta — deci riscul e activ, nu doar teoretic. Fix real ar necesita
  retry/backoff pe 429, nu doar modelul Cerebras corect — neaplicat acum (scope mai mare).
- **Toata verificarea a fost la nivel de API** (curl / apeluri directe), NU prin browser. Fix-urile
  care ating UI-ul (score-trend afisat in CompanyDetail, sector dashboard) sunt verificate ca
  API-ul raspunde corect cu date reale, dar NU am deschis efectiv paginile in browser sa confirm
  ca frontend-ul le randeaza corect vizual.

## Sumar final

**7 bug-uri reale gasite si reparate** (toate live-verificate, 440 pytest PASSED la fiecare
pas, 0 erori TypeScript): Cerebras model retras din catalog, `companies.caen_code`/`county`
niciodata populate (rupea /sector), `score-trend` type mismatch, `timeline-report/pdf` crash
Unicode, `export/ics` cheie gresita, `settings test/{service}` incomplet, sectiunea
"opportunities" nu stia de Angle A v2 (gasit prin verificare adversariala advisor — cel mai
relevant pt plangerea initiala a userului). Plus 1 finding nefixat intentionat (SYNTHESIS_MODE
— decizie lasata userului), 1 feature lipsa descoperita dar neconstruita (competition analysis
nu colecteaza deloc date reale despre competitori), 2 observatii minore (coherence-checker
fals-pozitiv, Settings.tsx nu expune toti providerii), si 3 limite oneste de scop (6/9
AnalysisType netestate, degradare sub concurenta redusa dar nu eliminata, verificare doar la
nivel API nu si vizual in browser). Artefacte de test curatate de pe firma reala (Mosslein).
