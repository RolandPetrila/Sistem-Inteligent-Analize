# PLAN CONTINUARE — ReportView Regenereaza + validare rich-fields (2026-06-27)

> **Status:** IN_PROGRESS (pending) — task pentru sesiune nouă (context curat).
> **Premisă:** sesiunea Wave A–F (2026-06-26) e COMPLETĂ și pushed (10 commits `6eaab00`→`e5e99e3`). Vezi memory `project_ris_status.md`.
> **Cum pornești:** rulează `/onboard`, apoi citește acest fișier + `project_ris_next_actions.md`.

---

## Ce s-a făcut deja (NU reface)

Wave A–F: F10/F21/F19/F3 hygiene; F15 funding cablat; PII#4 monitoring BPI+CA (cu fix tranziție); F6 network cache+N+1; **rich-fields randate în HTML+PDF+DOCX** (predictive/benchmark/actionariat/relations/aegrm/historical/funding) — verificat E2E pe job real (CUI 49104500, HTML 38KB + DOCX + PDF 20.8KB); api.ts +6 metode; CompanyDetail score-trend+timeline PDF; ReportsList filtre; Monitoring audit-log+retry; ReportView .ics; Compare notice + bulk-compare multi-CUI; 3 pagini noi (`/sector`, `/ocr`, `/quick-tools`); Companies bulk-select; Batch persist; fix `/analysis/quick-score`. **372 pytest, tsc+build clean, vitest full exit 0 (pool threads).**

---

## TASK 1 (PRIMARY) — ReportView "Regenereaza" funcțional

**Problema (de ce e inactiv acum):**

1. Backend `regenerate_section` (`backend/routers/jobs.py:287`) e **STUB** — întoarce `{"status":"queued", "note":...}` și NU re-rulează sinteza.
2. `report_sections` **NU e persistat** în `reports.full_data` — `job_service.py:270` (INSERT) și `:307` (UPDATE delta) salvează `json.dumps(verified_data)`, fără `report_sections`.
   → ReportView arată butoanele "Regenereaza" doar dacă `full_data.report_sections` există (acum nu) → butoane invizibile.

**Pași:**

- [ ] **1a. Persistă report_sections în full_data.** În funcția de salvare din `backend/services/job_service.py`, ÎNAINTE de INSERT (~linia 262): `verified_data["report_sections"] = report_sections`.
  - ⚠️ Confirmă că `report_sections` e în scope acolo. Este output-ul Agent 5 (sinteză), pasat la `backend/reports/generator.py`. Dacă NU e parametru al funcției de salvare → thread-uiește-l prin lanțul orchestrator → job_service. (`job_service.py:171` are deja cheia `"report_sections": None` într-un state dict — verifică dacă e populată.)
  - Aplică-l ȘI înainte de UPDATE-ul delta (`:307-308`) ca să nu se piardă la rescriere.
- [ ] **1b. Implementează regenerarea reală** în `jobs.py:287`. Înlocuiește stub-ul: încarcă `full_data["report_sections"][section_key]` + contextul `verified_data`, re-rulează sinteza pentru ACEA secțiune (instanțiază `SynthesisAgent` / metodă per-secțiune din `backend/agents/agent_synthesis.py`), actualizează `full_data["report_sections"][section_key]`, `UPDATE reports SET full_data=?`. Returnează conținutul nou (ReportView îl poate afișa).
- [ ] **1c. Frontend** — deja cablat (`ReportView.tsx`, `api.regenerateSection`). Doar verifică că butoanele apar după 1a și afișează rezultatul din 1b.

**Caveats (schimbare de comportament storage — testează regresii!):**

- `full_data` crește (report_sections poate fi mare). OK pentru SQLite single-user, dar verifică `get_report` / `get_report_data`.
- `report_sections` = cheie nouă top-level → NU e în `ALLOWED_SECTIONS` (`report_service.py:131`) deci `GET /reports/{id}/data?section=report_sections` o respinge (corect, nu o adăuga).
- `delta_service.compute_delta` lucrează pe verified_data — ignoră chei necunoscute, dar **rulează un test de delta** după.

**Acceptance:** rulează un job real → `GET /reports/{id}/data` arată `report_sections` în full_data → ReportView afișează butoanele → click "Regenereaza" pe `executive_summary` → secțiunea se schimbă (conținut nou) fără 500. + un test router pentru regenerate (asertează că re-scrie secțiunea).

---

## TASK 2 (SECONDARY) — validare aegrm + historical_flags pe date reale

Randarea acestor 2 câmpuri e testată synthetic + unit, dar firma E2E (CUI 49104500) n-avea date AEGRM/Monitorul Oficial. Rulează o analiză pe o firmă cu **insolvență BPI** sau **semnale Monitorul Oficial** (cesiuni/dizolvări) și confirmă secțiunea "Garantii & Istoric (OSINT)" în HTML+PDF+DOCX. (AEGRM = DNS dead; historical_flags via Tavily/Monitorul mai probabil să aibă date.)

---

## DEFERRED (P3 — intenționat sărit, NU implementa fără analiză quotă)

- **F19-full**: `with_retry` pe `tavily_client` / `monitorul_oficial_client` — retry pe surse limitate de quotă = risc epuizare quotă Tavily. F19 esențial (anaf_bilant + bpi, GET idempotent) e deja făcut în Wave A.

---

## Gotchas OBLIGATORII (altfel pierzi timp)

- **vitest**: rulează `npx vitest run --pool=threads` (pool default `forks` = HANG ~10min pe acest Windows; un fișier ~6s cu threads). Vezi memory `ris-build-test-gotchas`.
- **Formatter PostToolUse (autoflake)** stripează importurile noi dacă usage-ul nu există încă în fișier la momentul edit-ului → adaugă importul DUPĂ ce există usage-ul SAU re-verifică `ruff check <fișiere> --select F821,F401` după orice batch care adaugă importuri.
- **Schema-drift** (memory `project_ris_schema_drift_gotcha`): migrări DOAR în `database.py run_migrations()`, niciodată scattered în handlere.
- **Reguli proiect**: FREE only, UI română, cod engleză; commit+push după fiecare unitate logică; root curat (planuri → `99_Plan_vs_Audit/`); restart serviciu după modificări backend (`tools/RIS-Backend.exe restart`) + smoke live.

## Validare finală (înainte de „done")

```
python -m pytest -q                                  # backend
cd frontend && npx tsc -b && npx vite build           # types + build
cd frontend && npx vitest run --pool=threads          # frontend tests
tools/RIS-Backend.exe restart                          # deploy backend
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/health
```
