# RIS — Planificari Extindere Module (Runda 4 + Runda 5 + Runda 6)

> Deep-dive pe cod sursa post-Faza 10F. Focus: bug-uri critice, data quality pipeline, calitate raport, reliability.
> Metoda: 6 agenti paraleli deep research + sequential thinking + filtrare stricta ROI.
> Reguli: free tier only, single user, DOAR imbunatatiri cu impact semnificativ pe calitatea functionarii.
> R4 generat: 2026-03-22 | 27 items din 90+ findings — COMPLET IMPLEMENTAT
> R5 generat: 2026-03-22 | 25 items din 61 findings (filtrare stricta HIGH ROI) — COMPLET IMPLEMENTAT
> R6 generat: 2026-03-23 | 21 items din 52 findings (post R4+R5, verificat pe cod real)

---

## Faze implementate (completate)

| Faza | Ce s-a implementat |
|------|--------------------|
| 1-7E | Fundatie completa: 8 surse date, 5 agenti AI, scoring 6D, 7 formate raport, LangGraph, cache, monitoring, batch, tests |
| 8A-8E | Gzip, ErrorCode 55+, cache stats, trend scoring, volatility CV, solvency, dynamic word count, ZIP pack, smart severity, audit log |
| 9A-9E | Parallel fetch, error boundaries 5/5, cash flow proxy, confidence scoring, pagination, watermark, TOC, alert dedup, batch resume |
| 10A-10F | 51 P1 features: solvency matrix, prompt hardening, parallel Agent 2+3, request dedup, cache LRU 100MB, batch parallel 2-CUI, request ID tracing, error sanitization, form validation, HTML responsive |

---

## Harta Module — Evolutie R1 -> R2 -> R3 -> R4 -> R5 -> R6

| # | Modul | R1 % | R2 % | R3 % | R4 | R5 | R6 target | Status |
|---|-------|------|------|------|-----|-----|-----------|--------|
| 1 | **Dashboard** | 45% | 58% | 78% | 78% | 78% | 78% | - (stabil) |
| 2 | **Colectare Date (Agent 1)** | 62% | 68% | 92% | 97% | 99% | 100% | [ ] R6 PROPUS |
| 3 | **Verificare & Scoring (Agent 4)** | 67% | 82% | 98% | 99% | 100% | 100% | [ ] R6 PROPUS |
| 4 | **Sinteza AI (Agent 5)** | 62% | 78% | 97% | 99% | 99% | 100% | [ ] R6 PROPUS |
| 5 | **Orchestrator** | 67% | 75% | 95% | 97% | 97% | 97% | - (stabil) |
| 6 | **Rapoarte** | 62% | 72% | 92% | 97% | 99% | 100% | [ ] R6 PROPUS |
| 7 | **Comparator & Delta** | 57% | 60% | 85% | 90% | 97% | 97% | - (stabil) |
| 8 | **Batch Analysis** | 52% | 65% | 90% | 95% | 98% | 99% | [ ] R6 PROPUS |
| 9 | **Monitoring & Alerte** | 57% | 62% | 85% | 95% | 95% | 98% | [ ] R6 PROPUS |
| 10 | **Cache & Performance** | 72% | 78% | 95% | 97% | 99% | 100% | [ ] R6 PROPUS |
| 11 | **Securitate & Config** | 68% | 75% | 94% | 96% | 99% | 100% | [ ] R6 PROPUS |
| 12 | **Frontend UI** | 62% | 62% | 88% | 92% | 97% | 99% | [ ] R6 PROPUS |

**Media exploatare:** R1=61% -> R2=70% -> R3=91% -> R4=96% -> R5=97% -> R6 target=99.3%

---

## Legenda

- **CRIT** = Bug critic — crash, date corupte, functionalitate complet nefunctionala
- **HIGH** = Impact major pe calitatea raportului, date gresite, sau fiabilitate
- **MED** = Imbunatatire vizibila pe calitate output, fara urgenta critica
- **Efort:** S (~30 min) | M (~1-2h) | L (~3h+)

---

# ======================================
# RUNDA 4 — 27 items (post-Faza 10F)
# ======================================

## R4 — 2. Colectare Date (Agent 1)

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 1 | B1 | [x] **CAEN din ANAF API v9 nu se extrage** — fix: extract cod_CAEN from date_generale | anaf_client.py | S | HIGH |
| 2 | B2 | [x] **openapi_client "found" field lipseste** — VERIFICAT: found prezent in toate path-urile | openapi_client.py | S | CRIT |
| 3 | B3 | [x] **Litigation = same reference as insolvency** — fix: deep copy dict | agent_official.py:199-204 | S | HIGH |
| 4 | B4 | [x] **SEAP valute mixte sumate fara conversie** — fix: EUR→RON conversion at approx rate | seap_client.py:116-128 | M | MED |

## R4 — 3. Verificare & Scoring (Agent 4)

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 5 | B5 | [x] **Actionariat `[]` falsy → INCOMPLETE gresit** — fix: check available flag only | completeness.py:46 | S | CRIT |
| 6 | B6 | [x] **Market `{}` truthy → PASS gresit** — fix: check actual SEAP contracts | completeness.py:111 | S | CRIT |
| 7 | B7 | [x] **Confidence nefolosita in scor final** — fix: apply confidence weighting to dimension scores | scoring.py:403-421 | M | HIGH |
| 8 | B8 | [x] **Risk factors duplicate** — fix: dedup by text before return | scoring.py:518-524 | S | MED |

## R4 — 4. Sinteza AI (Agent 5)

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 9 | B9 | [x] **Provider order gresit pt fast route** — fix: fast=Groq→Cerebras→Mistral→Gemini, quality=Claude→Gemini→Groq→Mistral | agent_synthesis.py:59-107 | S | HIGH |
| 10 | B10 | [x] **JSON context limits statice si prea mici** — fix: dynamic limits (Claude 50K, Groq/Mistral/Cerebras 20K, Gemini 80K) | agent_synthesis.py:139-150 | M | HIGH |
| 11 | B11 | [x] **Hallucination detection pasiva** — fix: strip suspicious %%, replace invented CUI | agent_synthesis.py:263-276 | M | HIGH |
| 12 | B12 | [x] **Degradation fallback = JSON dump** — fix: readable key-value format instead of raw JSON | agent_synthesis.py:537-560 | M | HIGH |

## R4 — 5. Orchestrator

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 13 | B13 | [x] **`years` nedefinita → crash bilant multi-an** — fix: years → years_desc | anaf_bilant_client.py:146 | S | CRIT |
| 14 | B14 | [x] **Early warnings neconectate la recomandari** — fix: added early_warnings instruction to recommendations prompt | section_prompts.py:105 | M | HIGH |

## R4 — 6. Rapoarte

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 15 | B15 | [x] **PDF/DOCX ignora due_diligence + early_warnings** — fix: added structured DD checklist + EW sections to both generators | pdf_generator.py, docx_generator.py, generator.py | M | HIGH |
| 16 | B16 | [x] **Excel CAGR crash pe firma < 2 ani** — fix: handle negative CA with simple growth rate | excel_generator.py:324-371 | S | HIGH |
| 17 | B17 | [x] **PPTX fara trend financiar** — fix: added trend multi-an section on Slide 3 | pptx_generator.py:123-137 | M | MED |

## R4 — 7-12 (Celelalte module)

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 18 | B18 | [x] Compare year hardcodat — fix: `date.today().year - 1` instead of hardcoded -2 | compare.py:45 | S | MED |
| 19 | B19 | [x] Delta doar pe scor total, fara dimensiuni — fix: added dimension-level scoring delta with ±3 threshold | delta_service.py | M | MED |
| 20 | B20 | [x] gather() exception = batch RUNNING forever — fix: return_exceptions=True | batch.py:389 | S | CRIT |
| 21 | B21 | [x] Stuck batch = concurrent limit blocat — fix: auto-timeout RUNNING batches > 4h before checking limit | batch.py:110-127 | M | HIGH |
| 22 | B22 | [x] Schema mismatch: `triggered_at` vs `created_at` — fix: created_at → triggered_at | monitoring_service.py | S | CRIT |
| 23 | B23 | [x] Firma radiata = silentios ignorata — fix: triggers RED alert + Telegram when CUI not found | monitoring_service.py:134-155 | M | HIGH |
| 24 | B24 | [x] get_or_fetch race condition — fix: per-key asyncio.Lock with double-check-locking | cache_service.py | M | MED |
| 25 | B25 | [x] WebSocket broadcast exception swallowing — fix: track dead connections and remove from active | main.py | S | MED |
| 26 | B26 | [x] Retry-source fara UI — fix: added 5 source retry buttons to AnalysisProgress page | AnalysisProgress.tsx:163-198 | M | HIGH |
| 27 | B27 | [x] Companies search reset nu reseteaza paginare — fix: added "Sterge" button resetting search+pagination | Companies.tsx | S | MED |

---

# ============================================
# RUNDA 5 — 25 items (deep research 6 agenti)
# ============================================

> Metoda R5: 6 agenti paraleli de deep research pe TOATE modulele (61 findings brute).
> Filtru aplicat: DOAR items cu impact DIRECT si SEMNIFICATIV pe calitatea functionarii.
> Exclus: cosmetic, refactoring, naming, items deja in R4, ROI scazut.
> Data: 2026-03-22

---

## R5 — 2. Colectare Date (Agent 1)

**Probleme noi gasite:** pierdere_neta ignorata in trend, bilant fara retry per-an, completeness formula incorecta, source names nu match.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 1 | C1 | [x] **_calculate_trends ignora pierdere_neta** — fix: use pierdere_neta as negative profit | anaf_bilant_client.py:165 | S | HIGH |
| 2 | C2 | [x] **get_bilant() fara retry per-an** — fix: retry once on 5xx/timeout per-year request | anaf_bilant_client.py:31 | S | HIGH |
| 3 | C3 | [x] **Completeness score formula gresita** — fix: denominator changed to `max(5, 1)` matching the 5 field checks in numerator | agent_official.py:312-314 | S | MED |

---

## R5 — 3. Verificare & Scoring (Agent 4)

**Probleme noi gasite:** SEAP bonus mort din cauza wrapping, solvency matrix null safety, scor de la CRIT.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 4 | C4 | [x] **SEAP bonus niciodata aplicat** — fix: unwrap _make_field .value before checking | scoring.py:338-340 | S | CRIT |
| 5 | C5 | [x] **Solvency matrix null safety** — fix: flag missing profit/equity as INDETERMINAT, apply score penalty | scoring.py:149-151 | S | HIGH |

---

## R5 — 6. Rapoarte

**Probleme noi gasite:** TOC page numbers gresite, POSITIVE factors invizibile, N/A = NERECOMANDAT, PDF truncation, silent paragraph drop.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 6 | C6 | [x] **PDF TOC page numbers mereu gresite** — fix: replaced manual TOC with fpdf2 insert_toc_placeholder (auto-tracked page numbers) | pdf_generator.py:106-122 | M | HIGH |
| 7 | C7 | [x] **POSITIVE factors invizibile** — fix: add POSITIVE to severity color maps in Excel+PPTX | excel/pptx/one_pager generators | S | HIGH |
| 8 | C8 | [x] **One-pager: N/A scor → "NERECOMANDAT"** — fix: unknown score_color → "INSUFICIENT DATE" | one_pager_generator.py:73 | S | HIGH |
| 9 | C9 | [x] **PDF truncheaza cuvinte > 60 caractere** — fix: hyphenated break `w[:55] + "-" + w[55:110]` instead of silent truncation | pdf_generator.py:164 | S | MED |
| 10 | C10 | [x] **PDF sterge paragrafe silentios la eroare render** — fix: renders "[paragraf nerandat]" placeholder instead of silent pass | pdf_generator.py:180-182 | S | MED |
| 11 | C11 | [x] **HTML: `<li>` fara `<ul>` wrapper** — fix: `in_list` state tracking, proper `<ul>` open/close transitions | html_generator.py:30-31 | S | MED |

---

## R5 — 7. Comparator & Delta

**Problema critica:** Delta compara raport cu SINE INSUSI — functionalitate complet moarta.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 12 | C12 | [x] **Delta compara raportul cu sine insusi** — fix: rows[0]→rows[1], len<1→len<2 | delta_service.py:23-34 / job_service.py:218,256 | S | CRIT |

---

## R5 — 8. Batch Analysis

**Probleme noi gasite:** _run_batch fara safety net, resume pierde rezultate anterioare, analysis_type gresit.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 13 | C13 | [x] **_run_batch fara top-level try/except** — fix: wrapped in try/except, sets ERROR status on failure | batch.py:340-348 | S | HIGH |
| 14 | C14 | [x] **Batch resume pierde rezultate precedente** — fix: loads existing results from progress before appending | batch.py:365-370 | M | HIGH |
| 15 | C15 | [x] **BatchAnalysis trimite COMPANY_PROFILE in loc de FULL_COMPANY_PROFILE** — fix: changed to FULL_COMPANY_PROFILE matching backend routing | BatchAnalysis.tsx:32 | S | MED |

---

## R5 — 10. Cache & Performance

**Problema critica:** invalidate_company nu sterge nimic real.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 16 | C16 | [x] **invalidate_company nu sterge cache-ul real** — fix: enumerate all possible key variants (bilant_CUI_YEAR, fin_CUI, etc) for each source | cache_service.py:183-210 | M | HIGH |
| 17 | C17 | [x] **Compare sleeps 2s chiar si pe cache hit** — VERIFICAT: sleep already inside cache miss block | compare.py:58,80 | S | HIGH |

---

## R5 — 11. Securitate & API

**Probleme noi gasite:** diagnostic endpoint mort, structured errors dead code, retry-source leak, cancel_job corupe DONE, settings refresh.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 18 | C18 | [x] **get_latest_diagnostics foloseste 'COMPLETED' in loc de 'DONE'** — fix: COMPLETED → DONE | jobs.py:22 | S | CRIT |
| 19 | C19 | [x] **retry-source leaks raw exception str(e)** — fix: sanitize to first 100 chars, wrap in safe message | jobs.py:260-266 | S | HIGH |
| 20 | C20 | [x] **cancel_job nu verifica status curent** — fix: block cancel on DONE/ERROR/FAILED | jobs.py:269-279 | S | HIGH |
| 21 | C21 | [x] **Settings .env scris dar in-memory settings nu se reincarca** — fix: _reload_settings() updates in-memory attrs after write | settings.py:140-170 | M | HIGH |

---

## R5 — 12. Frontend UI

**Probleme noi gasite:** Settings fara error check, polling leak, WS reconnect leak, api.ts schemas gresite, monitoring fara error handling.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 22 | C22 | [x] **Settings save nu verifica res.ok** — fix: check res.ok, throw on failure | Settings.tsx:67-71 | S | CRIT |
| 23 | C23 | [x] **Batch polling interval nu se curata la unmount** — fix: useRef + useEffect cleanup | BatchAnalysis.tsx:24-30 | S | HIGH |
| 24 | C24 | [x] **api.compareCompanies + api.createMonitoring schema gresita** — fix: cui_list, caen_section, company_id match backend | api.ts:143-177 | S | HIGH |
| 25 | C25 | [x] **Monitoring toggle/delete + CompareCompanies score 0** — fix: try/catch + toast, riskColor checks null explicitly | Monitoring.tsx:62-75, CompareCompanies.tsx:34-39 | S | HIGH |

---

## Rezumat General R5

| # | Modul | CRIT | HIGH | MED | Total |
|---|-------|------|------|-----|-------|
| 2 | Colectare Date (Agent 1) | 0 | 2 | 1 | 3 |
| 3 | Verificare & Scoring (Agent 4) | 1 | 1 | 0 | 2 |
| 6 | Rapoarte | 0 | 3 | 3 | 6 |
| 7 | Comparator & Delta | 1 | 0 | 0 | 1 |
| 8 | Batch Analysis | 0 | 2 | 1 | 3 |
| 10 | Cache & Performance | 0 | 2 | 0 | 2 |
| 11 | Securitate & API | 1 | 3 | 0 | 4 |
| 12 | Frontend UI | 1 | 3 | 0 | 4 |
| | **TOTAL R5** | **4** | **16** | **5** | **25** |

**Combinat R4+R5: 52 items total (10 CRIT, 29 HIGH, 13 MED)**

---

## Top 10 Quick Wins R5 (Impact maxim, efort minim)

| Ord | Cod | Modul | Ce fixeaza | Efort | Sev |
|-----|-----|-------|-----------|-------|-----|
| 1 | C12 | Delta | Delta compara cu sine insusi — intreaga functie moarta | S | CRIT |
| 2 | C4 | Scoring | SEAP bonus cod mort — piata sub-evaluata sistematic | S | CRIT |
| 3 | C18 | API | diagnostics/latest mereu gol — 'COMPLETED' vs 'DONE' | S | CRIT |
| 4 | C22 | Frontend | Settings "Salvat!" fara verificare server | S | CRIT |
| 5 | C5 | Scoring | Solvency null → "Sanatos" fals | S | HIGH |
| 6 | C7 | Rapoarte | POSITIVE factors invizibile in rapoarte | S | HIGH |
| 7 | C8 | Rapoarte | N/A scor → "NERECOMANDAT" (eticheta gresita) | S | HIGH |
| 8 | C17 | Cache | Compare sleeps pe cache hit (20s inutil) | S | HIGH |
| 9 | C19 | API | retry-source leak raw exceptions | S | HIGH |
| 10 | C20 | API | cancel_job corupe DONE → FAILED | S | HIGH |

**Timp estimat Top 10 R5:** ~5h (toate S)

---

## REGULI DE EXECUTIE CERINTE (R4 + R5)

### Workflow implementare per cerinta

```
1. SELECTIE
   - Alege cerinta: R4 CRIT intai → R4 HIGH → R5 CRIT → R5 HIGH → MED
   - Verifica: "Ce modul afecteaza?" → citeste codul sursa INAINTE
   - Confirma: cerinta inca e relevanta? (nu s-a implementat intre timp)

2. PRE-IMPLEMENTARE
   [ ] Citeste TOATE fisierele afectate (backend + frontend)
   [ ] Identifica functiile exacte de modificat/adaugat
   [ ] Verifica dependinte cross-module (vezi sectiunea dependinte)
   [ ] Estimeaza impactul: LOW / MEDIUM / HIGH
   [ ] Daca HIGH: declara fisiere afectate + asteapta confirmare

3. IMPLEMENTARE
   [ ] Cod complet: import-uri, error handling, tipuri
   [ ] Respecta conventii: cod in engleza, UI in romana
   [ ] Nu introduce vulnerabilitati (OWASP top 10)
   [ ] Pastreaza backward compatibility (nu rupe endpoints existente)
   [ ] Fiecare functie noua: docstring 1-linie in cod

4. TESTARE
   [ ] Test manual functional (ruleaza analiza pe CUI real)
   [ ] Test automated daca exista suite (pytest / vitest)
   [ ] Verifica: celelalte module nu sunt afectate negativ
   [ ] Pt bug-uri CRIT: verifica fix-ul rezolva problema EXACT
   [ ] Pt data quality: verifica datele apar corect in raportul generat

5. DOCUMENTARE
   [ ] Bifeaza cerinta [ ] → [x] in ROLAND_PLANIFICARI_MODULE.md
   [ ] Actualizeaza FUNCTII_SISTEM.md daca functie/endpoint NOU
   [ ] CLAUDE.md — status faza + key files + decizii
   [ ] TODO_ROLAND.md la finalul sesiunii
   [ ] Memory files daca decizie tehnica noua

6. GIT
   [ ] git add [fisierele modificate] (NU git add -A)
   [ ] git commit cu mesaj descriptiv per fix sau grup logic
   [ ] git push origin main
   [ ] Verifica: pytest + vitest trec INAINTE de push

7. CONFIRMARE
   [ ] Afiseaza: CE s-a implementat + CE fisiere modificate
   [ ] Test real: ruleaza analiza completa (CUI 26313362 = MOSSLEIN)
```

### Reguli stricte

1. **CRIT inainte de HIGH inainte de MED** — Nu sari la MED daca CRIT sau HIGH neimplementate
2. **Bug fix = test imediat** — Dupa fix CRIT, ruleaza test care demonstreaza fix-ul
3. **Cross-module: identifica INAINTE** — C4 (SEAP wrap) afecteaza scoring pt ORICE firma cu contracte
4. **Nu modifica module netestate** — Daca nu ai pytest/vitest pe modul, adauga test INAINTE
5. **O cerinta = un commit logic** — Nu amesteca module diferite in acelasi commit
6. **Git push dupa fiecare sesiune** — Codul trebuie versionat pe GitHub la final

### Ordinea recomandata per sesiune

```
Sesiune 1 (R4 CRITICAL bugs — PRIORITAR):
   B13 + B22 + B2 + B5 + B6 + B20
   = 6 CRIT din R4, toate S, ~3h cu testare

Sesiune 2 (R5 CRITICAL bugs):
   C12 + C4 + C18 + C22
   = 4 CRIT din R5, toate S, ~2h cu testare

Sesiune 3 (R4 Data quality HIGH):
   B1 + B3 + B9 + B16 + B7
   = 5 HIGH din R4, ~3h total

Sesiune 4 (R5 Quick wins HIGH):
   C5 + C7 + C8 + C17 + C19 + C20 + C1 + C2
   = 8 items S din R5, ~4h total

Sesiune 5 (R4 Synthesis + Reports HIGH):
   B10 + B11 + B12 + B15
   = 4 HIGH din R4, ~4h total

Sesiune 6 (R5 Reports + Batch + Frontend HIGH):
   C6 + C13 + C14 + C21 + C23 + C24 + C25
   = 7 items din R5, ~4h total

Sesiune 7 (Remaining HIGH + MED):
   B21 + B23 + B14 + C16 + B26
   = 5 items restante HIGH, ~3h total

Sesiune 8 (MED polish):
   C3 + C9 + C10 + C11 + C15 + B4 + B8 + B17 + B18 + B19 + B24 + B25 + B27
   = 13 MED items, ~6h total

Dupa fiecare sesiune:
   python -m pytest tests/ -v --tb=short
   cd frontend && npx vitest run
   git add + commit + push
```

---

## PROTOCOL ACTUALIZARE DOCUMENTATIE

### Ce fisiere se actualizeaza si cand

| Fisier | Cand | Ce se modifica |
|--------|------|----------------|
| `ROLAND_PLANIFICARI_MODULE.md` | Dupa FIECARE cerinta | Bifeaza `[ ]` → `[x]` |
| `FUNCTII_SISTEM.md` | Daca functie/endpoint NOU | Adauga in inventar |
| `CLAUDE.md` | La finalul sesiunii | Status faze, key files, decizii |
| `TODO_ROLAND.md` | La finalul sesiunii | Status, ce ramane |
| `AUDIT_REPORT.md` | Doar la schimbari MAJORE | Entry cu data |
| Memory files | Daca decizie tehnica noua | project_ris_decisions.md |

### Checklist documentatie (la final sesiune)

```
[ ] ROLAND_PLANIFICARI_MODULE.md — Cerinta bifata [x]?
[ ] FUNCTII_SISTEM.md — Functie noua listata?
[ ] CLAUDE.md — Faza curenta actualizata?
[ ] TODO_ROLAND.md — Status actualizat?
[ ] git push origin main — Cod pe GitHub?
[ ] pytest + vitest — Toate testele trec?
```

---

## PROTOCOL TEST FUNCTIONALITATE

### Test rapid per cerinta (obligatoriu)

```
1. Porneste RIS: dublu-click START_RIS.vbs
2. Deschide http://localhost:5173/new-analysis
3. CUI test: 26313362 (MOSSLEIN S.R.L.)
4. Tip: FULL_COMPANY_PROFILE | Nivel: STANDARD (2)
5. Asteapta finalizare (~2-3 min)
6. Verifica raportul HTML:
   [ ] CAEN code prezent (B1, B2)
   [ ] Scor SEAP bonus aplicat (C4)
   [ ] Text narativ fluid, nu bullets (B9)
   [ ] Fara "[Nota sistem]" in text (B11)
   [ ] Fara JSON raw in raport (B12)
   [ ] TOC cu numere corecte (C6)
   [ ] POSITIVE factors vizibile (C7)
7. Verifica PDF descarcat:
   [ ] Fara cuvinte trunchiate la 60 chars (C9)
   [ ] Toate paragrafele prezente (C10)
8. Verifica logs/:
   [ ] Fara NameError/crash (B13)
   [ ] Delta cu changes != empty (C12)
```

### Test automated (la finalul sesiunii)

```bash
cd C:\Proiecte\Sistem_Inteligent_Analize
python -m pytest tests/ -v --tb=short
cd frontend && npx vitest run --reporter=verbose
```

### Test API specific (dupa C18, C19, C20)

```bash
# C18: diagnostics/latest trebuie sa returneze date
curl http://localhost:8001/api/jobs/diagnostics/latest

# C20: cancel pe job DONE trebuie respins
curl -X POST http://localhost:8001/api/jobs/{DONE_JOB_ID}/cancel
# Asteptat: 400 "Job deja finalizat", NU 200
```

---

## DEPENDINTE CROSS-MODULE

```
R4 Dependencies:
   B2 (openapi found) --> B5 (completeness) --> B7 (confidence)
   B13 (bilant years) --> B16 (Excel CAGR) --> B15 (PDF/DOCX data)
   B22 (schema fix) --> monitoring dedup + throttling
   B9 (provider order) --> B10 (context) --> B11/B12

R5 Dependencies:
   C4 (SEAP unwrap) --> scoring market dimension pt TOATE firmele
   C12 (delta fix) --> anomaly flags --> monitoring alerts
   C18 (DONE query) --> diagnostics endpoint functionality
   C22 (Settings check) --> C21 (settings refresh) — fix C22 first, then C21

R4→R5 Dependencies:
   B13 (years fix) --> C1 (pierdere_neta in trends) — B13 INAINTE de C1
   B2 (openapi found) --> C4 (SEAP unwrap) — B2 INAINTE de C4
```

**Regula:** Implementeaza in ordinea dependintelor. Nu sari peste un CRIT care e dependinta pt alt item.

---

# ============================================
# RUNDA 6 — 21 items (post R4+R5 implementation)
# ============================================

> Metoda R6: 6 agenti paraleli deep research pe cod ACTUALIZAT (post 52 fix-uri R4+R5).
> Filtru aplicat: DOAR items cu impact DIRECT pe calitatea functionarii. Verificat pe cod real.
> Eliminat: duplicate R4/R5, false alarms, cosmetic, LOW ROI.
> Data: 2026-03-23 | 52 findings brute → 21 filtrate

---

## R6 — 2. Colectare Date (Agent 1)

**Probleme noi gasite:** SEAP EUR hardcoded, JSON parsing fara try/except pe 2 clienti API, BNR namespace suspect, INS TEMPO pierde float values.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 1 | D1 | [ ] **SEAP EUR rate hardcoded 5.0** — fix: use BNR rates from state, fallback 4.97 | seap_client.py:118 | M | HIGH |
| 2 | D2 | [ ] **ANAF Bilant JSON parse fara try/except** — fix: wrap response.json() in try/except, return found=False on error | anaf_bilant_client.py:49-55 | S | HIGH |
| 3 | D3 | [ ] **OpenAPI.ro JSON parse fara try/except** — fix: idem, wrap response.json() in try/except | openapi_client.py:45 | S | HIGH |
| 4 | D4 | [ ] **BNR XML namespace posibil incorect** — fix: verifica cu BNR XML real, fallback pe `{uri}Body` notation | bnr_client.py:34 | S | MED |
| 5 | D5 | [ ] **INS TEMPO filter pierde float values** — `str(v).isdigit()` skip "123.5" → fix: `int(float(val))` | caen_context.py:296-302 | S | MED |

---

## R6 — 3. Verificare & Scoring (Agent 4)

**Problema noua:** Score 50 din confidence weighting pare "risk mediu" cand e de fapt "date insuficiente".

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 6 | D6 | [ ] **Confidence implicit: scor 50 = "date lipsa" nu "risk mediu"** — fix: flag `data_available=False` pe dimensiuni cu confidence < 0.4, afiseaza "[Date insuficiente]" in raport | scoring.py:403-409 | M | HIGH |

---

## R6 — 4. Sinteza AI (Agent 5)

**Probleme noi gasite:** Token budget Groq gresit, Gemini JSON limit prea mic, hallucination regex false positive pe ani, Level 1 skip sectiuni.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 7 | D7 | [x] **Groq _PROVIDER_MAX_CONTEXT = 6000** — fix: 131000 (Llama 4 Scout actual context) | agent_synthesis.py:756 | S | HIGH |
| 8 | D8 | [x] **Gemini JSON limit 80K chars** — fix: 400000 chars + token budget 1M | agent_synthesis.py:144 | S | HIGH |
| 9 | D9 | [x] **Hallucination regex `\d{4,}%` detecteaza "2024%" ca suspect** — fix: exclude `20\d{2}%` pattern | agent_synthesis.py:266 | S | HIGH |
| 10 | D10 | [ ] **Prompt word_count=0 Level 1 skip competition+opportunities** — raport RAPID nu contine competitori/oportunitati. Fix: minim 150 cuvinte | section_prompts.py:73,82 | S | MED |

---

## R6 — 6. Rapoarte

**Probleme noi gasite:** Early Warnings complet absent din HTML, Excel KPI fara scoring dimensiuni, PPTX crash pe null, Due Diligence absent din Excel.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 11 | D11 | [ ] **Early Warnings absent din HTML report** — PDF/DOCX/Excel le au, HTML NU. Fix: sectiune dedicata cu severity colors | html_generator.py | M | HIGH |
| 12 | D12 | [ ] **Excel KPI sheet fara scor pe dimensiuni** — Sheet 5 (KPI) are doar 4 metrics, lipsesc scorurile 6D. Fix: adauga sectiune "Score pe Dimensiuni" | excel_generator.py:276+ | M | HIGH |
| 13 | D13 | [ ] **PPTX risk_score None → crash AttributeError** — `risk_score.get()` fara isinstance check. Fix: `risk_score = ... or {}` + isinstance guard | pptx_generator.py:152 | S | HIGH |
| 14 | D14 | [ ] **Due Diligence checklist absent din Excel** — PDF/DOCX il au, Excel NU. Fix: Sheet 6 "Due Diligence" cu checklist DA/NU | excel_generator.py | M | MED |

---

## R6 — 8. Batch Analysis

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 15 | D15 | [ ] **Batch CSV summary fara CAEN description** — coloana "CAEN" are doar cod, nu descriere sector. Fix: adauga coloana CAEN_Descriere | batch.py:268-305 | S | MED |

---

## R6 — 9. Monitoring & Alerte

**Problema critica:** B22 (R4) a fixat WHERE dar NU ORDER BY — dedup+throttle inca broken.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 16 | D16 | [x] **ORDER BY created_at pe tabel cu triggered_at** — fix: ORDER BY triggered_at in both queries | monitoring_service.py:69,89 | S | CRIT |

---

## R6 — 10. Cache & Performance

**Probleme noi gasite:** Tavily bypaseaza complet cache_service, _fetch_locks cresc nelimitat.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 17 | D17 | [x] **Tavily INSERT direct in DB bypaseaza LRU + stats + schema_version** — fix: uses cache_service.set() | tavily_client.py:42-46 | S | HIGH |
| 18 | D18 | [x] **_fetch_locks dict creste nelimitat → memory leak** — fix: OrderedDict max 500 + popitem eviction | cache_service.py:161 | S | HIGH |

---

## R6 — 11. Securitate & Config

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 19 | D19 | [ ] **Config secret key hardcoded "change-me-to-random-string"** — orice deploy fara .env = secret public. Fix: generate random key on startup daca nu e setat, log warning | config.py:35 | S | MED |

---

## R6 — 12. Frontend UI

**Probleme noi gasite:** WebSocket reconnect leak, 429 retry incomplet.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 20 | D20 | [x] **WebSocket reconnect setTimeout fara cleanup** — fix: reconnectTimeoutRef + clearTimeout on unmount | useWebSocket.ts:57 | S | HIGH |
| 21 | D21 | [ ] **429 Rate Limit: toast "reincercati" dar nu reexecuta automat** — ApiError cu retryAfter dar nicio logica de auto-retry. Fix: retry wrapper cu exponential backoff in api.ts | api.ts:10-16 | M | MED |

---

## Rezumat General R6

| # | Modul | CRIT | HIGH | MED | Total |
|---|-------|------|------|-----|-------|
| 2 | Colectare Date (Agent 1) | 0 | 2 | 2 | 4 |
| 3 | Verificare & Scoring (Agent 4) | 0 | 1 | 0 | 1 |
| 4 | Sinteza AI (Agent 5) | 0 | 3 | 1 | 4 |
| 6 | Rapoarte | 0 | 3 | 1 | 4 |
| 8 | Batch Analysis | 0 | 0 | 1 | 1 |
| 9 | Monitoring & Alerte | 1 | 0 | 0 | 1 |
| 10 | Cache & Performance | 0 | 2 | 0 | 2 |
| 11 | Securitate & Config | 0 | 0 | 1 | 1 |
| 12 | Frontend UI | 0 | 1 | 1 | 2 |
| | **TOTAL R6** | **1** | **12** | **7** | **20** |

**Combinat R4+R5+R6: 72 items total (11 CRIT, 41 HIGH, 20 MED)**

---

## Top 10 Quick Wins R6 (Impact maxim, efort minim)

| Ord | Cod | Modul | Ce fixeaza | Efort | Sev |
|-----|-----|-------|-----------|-------|-----|
| 1 | D16 | Monitoring | ORDER BY created_at → triggered_at (dedup broken) | S | CRIT |
| 2 | D7 | Synthesis | Groq token budget 6K → 131K (routing gresit) | S | HIGH |
| 3 | D8 | Synthesis | Gemini JSON limit 80K → 400K (data trunchiate) | S | HIGH |
| 4 | D9 | Synthesis | Hallucination regex: "2024%" = false positive | S | HIGH |
| 5 | D17 | Cache | Tavily bypaseaza LRU + stats + schema_version | S | HIGH |
| 6 | D18 | Cache | _fetch_locks unbounded → memory leak | S | HIGH |
| 7 | D20 | Frontend | WebSocket reconnect setTimeout leak | S | HIGH |
| 8 | D2 | Agent 1 | ANAF Bilant JSON parse fara try/except | S | HIGH |
| 9 | D3 | Agent 1 | OpenAPI.ro JSON parse fara try/except | S | HIGH |
| 10 | D13 | Rapoarte | PPTX risk_score null → crash | S | HIGH |

**Timp estimat Top 10 R6:** ~4h (toate S)

---

## REGULI DE EXECUTIE R6

### Workflow identic cu R4/R5 (vezi sectiunea "REGULI DE EXECUTIE CERINTE")

### Ordinea recomandata per sesiune R6

```
Sesiune 1 (R6 CRITICAL + Quick Wins HIGH):
   D16 + D7 + D8 + D9 + D17 + D18 + D20
   = 1 CRIT + 6 HIGH, toate S, ~3h cu testare

Sesiune 2 (R6 Data Quality + Reports HIGH):
   D1 + D2 + D3 + D6 + D11 + D12 + D13
   = 7 items (5 HIGH + 2 HIGH), ~4h total

Sesiune 3 (R6 MED polish):
   D4 + D5 + D10 + D14 + D15 + D19 + D21
   = 7 MED items, ~3h total

Dupa fiecare sesiune:
   python -m pytest tests/ -v --tb=short
   cd frontend && npx vitest run
   git add + commit + push
```

---

## DEPENDINTE CROSS-MODULE R6

```
R6 Dependencies:
   D16 (monitoring ORDER BY) → dedup + throttle pt TOATE alertele
   D7 + D8 (token/JSON limits) → synthesis quality pt ORICE raport
   D17 (Tavily via cache_service) → D18 (LRU enforcement acum include Tavily)
   D6 (confidence flag) → D11 (Early Warnings HTML) — D6 INAINTE de D11
   D1 (SEAP EUR via BNR) → depinde de BNR rates functional (D4 verifica)

R5→R6 Dependencies:
   C4 (SEAP unwrap) → D1 (SEAP EUR conversion) — C4 deja implementat
   C18 (DONE query fix) → D16 (monitoring column) — C18 deja implementat
```

---

## PROTOCOL TEST R6

### Test rapid per cerinta (obligatoriu)

```
1. Porneste RIS: dublu-click START_RIS.vbs
2. Deschide http://localhost:5173/new-analysis
3. CUI test: 26313362 (MOSSLEIN S.R.L.)
4. Tip: FULL_COMPANY_PROFILE | Nivel: STANDARD (2)
5. Asteapta finalizare (~2-3 min)
6. Verifica raportul HTML:
   [ ] Early Warnings prezente cu severity colors (D11)
   [ ] Fara "[procent neverificat]" pe ani 2022-2025 (D9)
   [ ] Dimensiuni scor vizibile (D6 confidence flag)
7. Verifica Excel descarcat:
   [ ] Sheet KPI contine dimensiuni scoring (D12)
   [ ] Sheet Due Diligence prezent (D14)
8. Verifica PPTX descarcat:
   [ ] Nu crash pe Slide 4 (D13)
9. Verifica monitoring:
   [ ] Dedup functioneaza — nu duplicateaza alerte in 24h (D16)
10. Verifica logs/:
   [ ] Fara JSONDecodeError crash (D2, D3)
```

### Test automated (la finalul sesiunii)

```bash
cd C:\Proiecte\Sistem_Inteligent_Analize
python -m pytest tests/ -v --tb=short
cd frontend && npx vitest run --reporter=verbose
```
