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

## Jurnal execuție

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
