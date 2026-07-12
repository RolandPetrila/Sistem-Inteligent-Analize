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
