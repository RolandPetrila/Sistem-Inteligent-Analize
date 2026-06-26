# RIS — Recomandări Îmbunătățiri & Completări (2026-06-26)

**Sursă:** `/imbunatatiri` (3 agenți discovery paraleli pe cod real) · **Total:** 32 recomandări (23 safe)
**Temă centrală:** _backend-ul calculează și colectează mult mai mult decât expune_ — endpoint-uri construite dar neconectate + date bogate pierdute înainte de rapoarte.

## Status aplicare

| Categorie                                                    | Nr  | Stare                            |
| ------------------------------------------------------------ | --- | -------------------------------- |
| **Aplicate acum (safe, high-value)**                         | 8   | ✅ commituite + verificate       |
| **Amânate — safe, vetate (follow-up)**                       | ~15 | 📋 gata de aplicat, în acest doc |
| **Strategice — necesită pagini/refactor (NU auto-aplicate)** | ~8  | 🔭 prezentate, decizia ta        |

---

## ✅ PARTEA 0 — APLICATE ACUM (commit IMB)

| #   | Titlu                                                                                                                                                                                     | Fișier                                      | Impact   |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | -------- |
| B1  | **Propagă semnalele OSINT Monitorul Oficial** (`historical_flags`) în `verified_data` → ajung în synthesis + full_data. Erau pierdute complet.                                            | `agent_verification.py`                     | **Mare** |
| B2  | **Scoruri predictive faliment** (Altman/Piotroski/Beneish/Zmijewski) persistate în `verified['predictive_scores']` → intră în promptul AI + full_data (înainte: doar endpoint on-demand). | `agent_verification.py`                     | **Mare** |
| B3  | `COMPANY_COLS` — constantă DRY pentru proiecția companies repetată 3× (sursa exactă a clasei schema-drift F1).                                                                            | `companies.py`                              | Mic      |
| B4  | F9 — `require_api_key` pe `/settings/test-telegram` + `/test/{service}`.                                                                                                                  | `settings.py`                               | Mic      |
| B5  | F13 — `resume_batch` SELECT 11 → 3 coloane (verificat: doar acelea folosite).                                                                                                             | `batch.py`                                  | Mic      |
| F1  | **Fix handoff rupt** — `CompareCompanies` citește `?cui=` din „Compară" (CompanyDetail) și pre-completează firma.                                                                         | `CompareCompanies.tsx`                      | Mediu    |
| F3  | CTA „Pornește analiza" în empty-state Companii.                                                                                                                                           | `Companies.tsx`                             | Mic      |
| F4  | A11y — `role=progressbar`+`aria-valuenow` pe barele de progres + `aria-live=polite` pe jurnal.                                                                                            | `AnalysisProgress.tsx`, `BatchAnalysis.tsx` | Mic      |

---

## 📋 PARTEA I — AMÂNATE, SAFE (vetate, gata de follow-up, ordine ROI)

1. **[P2] Wire score-trend în CompanyDetail** — `GET /companies/{id}/score-trend` (window functions, delta) construit dar 0 consumeri UI.
2. **[P2] ReportsList: filtru report_type + search + CTA empty** — `listReports` acceptă deja `report_type`.
3. **[P2] Conectează FTS5 search** — `GET /companies/search/fts` (tabel întreținut) — 0 consumeri UI.
4. **[P2] quick-score în UI** — `POST /analysis/quick-score` (≤20 CUI, fără AI) — 0 consumeri.
5. **[P2] Audit-log monitorizare în UI** — `GET /monitoring/{id}/audit-log` — 0 consumeri.
6. **[P2] Regenerare per-secțiune** — `POST /jobs/{id}/section/{key}/regenerate` — 0 consumeri.
7. **[P2] F19-scoped retry** — `anaf_bilant_client` + `bpi_client` cu `with_retry` (surse esențiale, GET idempotent).
8. **[P2] Raport evoluție multi-an PDF** — verifică expunerea `timeline-report/pdf` în CompanyDetail.
9. **[P3] Export .ics licitații** în ReportView.
10. **[P3] F10** — `list_reports` `Path.exists()` blocant → `asyncio.to_thread` (impact local marginal).
11. **[P3] Logging structurat report_service** (0 apeluri logger).
12. **[P3] Monitoring: skeleton + buton Reîncearcă.**
13. **[P3] CompareCompanies: comunică limita PDF 2-firme.**
14. **[P3] Teste router** resume/share/funding.
15. **[P4] Docstrings** pe `list_reports`/`get_report`.

---

## 🔭 PARTEA II — STRATEGICE (pagini noi / refactor — decizia ta)

1. **[P1] Randează câmpurile bogate în rapoarte** (`relations`, `actionariat`, `benchmark`, `anomalies`, `cross_validation`, `aegrm`) — calculate dar **0/0/0** în HTML/PDF/DOCX. Cel mai mare gap de livrabil; începe cu `html_generator.py`. **Mare.**
2. **[P1] Cablează `funding_programs`** — modul construit+testat+whitelisted, dar `match_programs` neapelat → secțiune mereu goală. **Mare.**
3. **[P1] Pagină Sector CAEN** — `GET /compare/sector/{caen}/dashboard` gata, 0 UI. **Mare.**
4. **[P1] Monitorizare dincolo de ANAF** — check insolvență BPI + scădere CA >30% în `run_monitoring_check`. **Mare.**
5. **[P2] Pagină OCR** — `POST /documents/ocr` (Mistral) gata, 0 UI. **Mediu.**
6. **[P2] Bulk-select Companii** (Compară/Monitorizare selectate). **Mare.**
7. **[P2] BatchAnalysis: persistă batch_id + resume după reload.** **Mediu.**
8. **[P3] F19-full** — `with_retry` pe toți cei ~10 clienți rămași.

---

## 🐞 OBSERVAȚIE /debug (runtime)

`AEGRM [Errno 11001] getaddrinfo failed` — hostname-ul AEGRM nu se rezolvă (endpoint probabil mort/schimbat); eșuează constant dar **gestionat grațios** (jobul termină DONE). Verifică URL-ul AEGRM sau marchează sursa indisponibilă.

## NOTE IMPLEMENTARE

1. **Constrângeri:** free-only, UI română, local single-user, fără refactor masiv, păstrează pattern-urile existente.
2. **Pattern surfacing:** multe câștiguri = _doar wiring_ (endpoint există → conectează UI), nu cod nou.
3. **Dependență:** PARTEA II #1 (render rich fields) face vizibile în PDF datele pe care B1/B2 (aplicate) le pun deja în `full_data`.
4. **Ce NU se schimbă:** schema DB, fluxul LangGraph, generatoarele (doar adăugări de secțiuni), cei 5 provideri AI.
