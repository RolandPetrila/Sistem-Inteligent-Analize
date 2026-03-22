# RIS — Planificari Extindere Module (Runda 4 + Runda 5)

> Deep-dive pe cod sursa post-Faza 10F. Focus: bug-uri critice, data quality pipeline, calitate raport, reliability.
> Metoda: 6 agenti paraleli deep research + sequential thinking + filtrare stricta ROI.
> Reguli: free tier only, single user, DOAR imbunatatiri cu impact semnificativ pe calitatea functionarii.
> R4 generat: 2026-03-22 | 27 items din 90+ findings
> R5 generat: 2026-03-22 | 25 items din 61 findings (filtrare stricta HIGH ROI)

---

## Faze implementate (completate)

| Faza | Ce s-a implementat |
|------|--------------------|
| 1-7E | Fundatie completa: 8 surse date, 5 agenti AI, scoring 6D, 7 formate raport, LangGraph, cache, monitoring, batch, tests |
| 8A-8E | Gzip, ErrorCode 55+, cache stats, trend scoring, volatility CV, solvency, dynamic word count, ZIP pack, smart severity, audit log |
| 9A-9E | Parallel fetch, error boundaries 5/5, cash flow proxy, confidence scoring, pagination, watermark, TOC, alert dedup, batch resume |
| 10A-10F | 51 P1 features: solvency matrix, prompt hardening, parallel Agent 2+3, request dedup, cache LRU 100MB, batch parallel 2-CUI, request ID tracing, error sanitization, form validation, HTML responsive |

---

## Harta Module — Evolutie R1 -> R2 -> R3 -> R4 -> R5

| # | Modul | R1 % | R2 % | R3 % | R4 target | R5 target | Status |
|---|-------|------|------|------|-----------|-----------|--------|
| 1 | **Dashboard** | 45% | 58% | 78% | 78% | 78% | - |
| 2 | **Colectare Date (Agent 1)** | 62% | 68% | 92% | 97% | 99% | [ ] R5 PROPUS |
| 3 | **Verificare & Scoring (Agent 4)** | 67% | 82% | 98% | 99% | 100% | [ ] R5 PROPUS |
| 4 | **Sinteza AI (Agent 5)** | 62% | 78% | 97% | 99% | 99% | - (R4 acoperit) |
| 5 | **Orchestrator** | 67% | 75% | 95% | 97% | 97% | - (R4 acoperit) |
| 6 | **Rapoarte** | 62% | 72% | 92% | 97% | 99% | [ ] R5 PROPUS |
| 7 | **Comparator & Delta** | 57% | 60% | 85% | 90% | 97% | [ ] R5 PROPUS |
| 8 | **Batch Analysis** | 52% | 65% | 90% | 95% | 98% | [ ] R5 PROPUS |
| 9 | **Monitoring & Alerte** | 57% | 62% | 85% | 95% | 95% | - (R4 acoperit) |
| 10 | **Cache & Performance** | 72% | 78% | 95% | 97% | 99% | [ ] R5 PROPUS |
| 11 | **Securitate & API** | 68% | 75% | 94% | 96% | 99% | [ ] R5 PROPUS |
| 12 | **Frontend UI** | 62% | 62% | 88% | 92% | 97% | [ ] R5 PROPUS |

**Media exploatare:** R1=61% -> R2=70% -> R3=91% -> R4=96% -> R5 target=97%

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
| 1 | B1 | **CAEN din ANAF API v9 nu se extrage** — campul `cod_caen` exista in `date_generale` dar NU e parsat | anaf_client.py | S | HIGH |
| 2 | B2 | [x] **openapi_client "found" field lipseste** — VERIFICAT: found prezent in toate path-urile | openapi_client.py | S | CRIT |
| 3 | B3 | **Litigation = same reference as insolvency** — pointer, nu copie | agent_official.py:199-204 | S | HIGH |
| 4 | B4 | **SEAP valute mixte sumate fara conversie** | seap_client.py:117-122 | M | MED |

## R4 — 3. Verificare & Scoring (Agent 4)

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 5 | B5 | [x] **Actionariat `[]` falsy → INCOMPLETE gresit** — fix: check available flag only | completeness.py:46 | S | CRIT |
| 6 | B6 | [x] **Market `{}` truthy → PASS gresit** — fix: check actual SEAP contracts | completeness.py:111 | S | CRIT |
| 7 | B7 | **Confidence nefolosita in scor final** | scoring.py:403-421 | M | HIGH |
| 8 | B8 | **Risk factors duplicate** | scoring.py:489-502 | S | MED |

## R4 — 4. Sinteza AI (Agent 5)

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 9 | B9 | **Provider order gresit pt fast route** | agent_synthesis.py:59-107 | S | HIGH |
| 10 | B10 | **JSON context limits statice si prea mici** | agent_synthesis.py:147-149 | M | HIGH |
| 11 | B11 | **Hallucination detection pasiva** — returneaza text cu nota sistem | agent_synthesis.py:245-275 | M | HIGH |
| 12 | B12 | **Degradation fallback = JSON dump** | agent_synthesis.py:519-543 | M | HIGH |

## R4 — 5. Orchestrator

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 13 | B13 | [x] **`years` nedefinita → crash bilant multi-an** — fix: years → years_desc | anaf_bilant_client.py:146 | S | CRIT |
| 14 | B14 | **Early warnings neconectate la recomandari** | orchestrator.py + section_prompts | M | HIGH |

## R4 — 6. Rapoarte

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 15 | B15 | **PDF/DOCX ignora due_diligence + early_warnings** | pdf_generator.py, docx_generator.py | M | HIGH |
| 16 | B16 | **Excel CAGR crash pe firma < 2 ani** | excel_generator.py:324-371 | S | HIGH |
| 17 | B17 | **PPTX fara trend financiar** | pptx_generator.py | M | MED |

## R4 — 7-12 (Celelalte module)

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 18 | B18 | Compare year hardcodat | compare.py:45 | S | MED |
| 19 | B19 | Delta doar pe scor total, fara dimensiuni | delta_service.py | M | MED |
| 20 | B20 | [x] gather() exception = batch RUNNING forever — fix: return_exceptions=True | batch.py:389 | S | CRIT |
| 21 | B21 | Stuck batch = concurrent limit blocat | batch.py:110 + scheduler.py | M | HIGH |
| 22 | B22 | [x] Schema mismatch: `triggered_at` vs `created_at` — fix: created_at → triggered_at | monitoring_service.py | S | CRIT |
| 23 | B23 | Firma radiata = silentios ignorata | monitoring_service.py:136 | M | HIGH |
| 24 | B24 | get_or_fetch race condition | cache_service.py | M | MED |
| 25 | B25 | WebSocket broadcast exception swallowing | main.py | S | MED |
| 26 | B26 | Retry-source fara UI | AnalysisProgress.tsx | M | HIGH |
| 27 | B27 | Companies search reset nu reseteaza paginare | Companies.tsx | S | MED |

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
| 1 | C1 | **_calculate_trends ignora pierdere_neta** — Ani cu pierdere apar ca "date lipsa", nu ca profit negativ. Trend-ul financiar incomplet/gresit pt firme cu ani de pierdere | anaf_bilant_client.py:165 | S | HIGH |
| 2 | C2 | **get_bilant() fara retry per-an** — 2 erori tranziente consecutive trigger early-stop, bilant multi-an se opreste prematur. Firma cu 5 ani date primeste doar 2 | anaf_bilant_client.py:31 | S | HIGH |
| 3 | C3 | **Completeness score formula gresita** — Numitor = len(expected_sources)+2, dar numaratorul = field checks. Mixeaza doua unitati diferite, score mereu supra-estimat | agent_official.py:312-314 | S | MED |

---

## R5 — 3. Verificare & Scoring (Agent 4)

**Probleme noi gasite:** SEAP bonus mort din cauza wrapping, solvency matrix null safety, scor de la CRIT.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 4 | C4 | **SEAP bonus niciodata aplicat** — `_verify_market()` wrapeaza in `_make_field()`, scoring cauta `total_contracts` la nivel top dar il gaseste sub `.value`. Bonus +10 piata e cod mort. Toate firmele cu SEAP sunt sub-evaluate | scoring.py:338-340 | S | CRIT |
| 5 | C5 | **Solvency matrix null safety** — `profit_val = None` trece prin comparatii fara eroare. `None < 0` = False in Python, deci profit necunoscut = clasificat "Sanatos". Firma fara date profit = falsa siguranta | scoring.py:149-151 | S | HIGH |

---

## R5 — 6. Rapoarte

**Probleme noi gasite:** TOC page numbers gresite, POSITIVE factors invizibile, N/A = NERECOMANDAT, PDF truncation, silent paragraph drop.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 6 | C6 | **PDF TOC page numbers mereu gresite** — Presupune 1 pagina per sectiune, dar text lung = 3-4 pagini. Dupa prima sectiune lunga, TOT restul TOC pointeaza pagini gresite | pdf_generator.py:119-126 | M | HIGH |
| 7 | C7 | **POSITIVE factors invizibile** — scoring.py emite severity "POSITIVE" dar Excel/PPTX/1-Pager au doar maps pt HIGH/MEDIUM/LOW. Rapoartele apar mai negative decat sunt — vesti bune (crestere CA) nu apar nicaieri | excel/pptx/one_pager generators | S | HIGH |
| 8 | C8 | **One-pager: N/A scor → "NERECOMANDAT"** — Agent 4 eroare → scor "N/A" → label "NERECOMANDAT". Firma fara date suficiente primeste eticheta negativa in loc de "INSUFICIENT DATE" | one_pager_generator.py:73 | S | HIGH |
| 9 | C9 | **PDF truncheaza cuvinte > 60 caractere** — `w[:60]` taie URLs, termeni lungi, fara marker. Output corupt silentios in raportul PDF | pdf_generator.py:164 | S | MED |
| 10 | C10 | **PDF sterge paragrafe silentios la eroare render** — `except Exception: pass` in multi_cell. Paragraf intreg disparut, fara log, fara placeholder | pdf_generator.py:180-182 | S | MED |
| 11 | C11 | **HTML: `<li>` fara `<ul>` wrapper** — Bullet-uri fara lista HTML valida. Formatare stricata in browser, invalid pentru screen readers | html_generator.py:30-31 | S | MED |

---

## R5 — 7. Comparator & Delta

**Problema critica:** Delta compara raport cu SINE INSUSI — functionalitate complet moarta.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 12 | C12 | **Delta compara raportul cu sine insusi** — `compute_delta` e apelat DUPA INSERT in DB. Query LIMIT 2 returneaza raportul tocmai inserat ca `rows[0]`. Compara date identice → delta MEREU gol. Intreaga functionalitate delta (anomaly flags, CA_DROP, PROFIT_TO_LOSS) e cod mort | delta_service.py:23-34 / job_service.py:218,256 | S | CRIT |

---

## R5 — 8. Batch Analysis

**Probleme noi gasite:** _run_batch fara safety net, resume pierde rezultate anterioare, analysis_type gresit.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 13 | C13 | **_run_batch fara top-level try/except** — Exceptie in DB/ZIP/progress (NU in gather) = task moare silentios, batch ramane RUNNING forever. Distinct de B20 (gather-specific) | batch.py:332 | S | HIGH |
| 14 | C14 | **Batch resume pierde rezultate precedente** — resume creeaza `results = []` fresh, suprascrie progresul. ZIP-ul final contine DOAR CUI-urile reincercate, nu batch-ul complet | batch.py:186-229 | M | HIGH |
| 15 | C15 | **BatchAnalysis trimite COMPANY_PROFILE in loc de FULL_COMPANY_PROFILE** — Backend are routing pe FULL_COMPANY_PROFILE (state.py:72), batch trimite alt string → Agent 3 (Market/SEAP) skipat in batch | BatchAnalysis.tsx:32 | S | MED |

---

## R5 — 10. Cache & Performance

**Problema critica:** invalidate_company nu sterge nimic real.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 16 | C16 | **invalidate_company nu sterge cache-ul real** — Foloseste hash(cui) dar cache keys reale sunt hash("bilant_CUI_YEAR"), hash("fin_CUI"), etc. DELETE by exact key nu gaseste nimic. Cache invalidation e 95% nefunctionala | cache_service.py:183-193 | M | HIGH |
| 17 | C17 | **Compare sleeps 2s chiar si pe cache hit** — `asyncio.sleep(2)` e INAUNTRU loop-ului dar AFARA de if-ul de cache miss. 5 firme = 20s sleep inutil pe date deja cached | compare.py:58,80 | S | HIGH |

---

## R5 — 11. Securitate & API

**Probleme noi gasite:** diagnostic endpoint mort, structured errors dead code, retry-source leak, cancel_job corupe DONE, settings refresh.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 18 | C18 | **get_latest_diagnostics foloseste 'COMPLETED' in loc de 'DONE'** — Endpoint-ul /api/jobs/diagnostics/latest returneaza MEREU "Niciun job completat". Complet nefunctional de la implementare | jobs.py:22 | S | CRIT |
| 19 | C19 | **retry-source leaks raw exception str(e)** — `except Exception as e: return {"error": str(e)}` trimite stack trace / paths / potential API keys catre client. Bypass-eaza error sanitization | jobs.py:260-266 | S | HIGH |
| 20 | C20 | **cancel_job nu verifica status curent** — Poate seta DONE → FAILED. Rapoarte completate corupt retroactiv, statisticile gresite | jobs.py:269-279 | S | HIGH |
| 21 | C21 | **Settings .env scris dar in-memory settings nu se reincarca** — User salveaza API keys din UI, vede "Salvat!", dar runtime-ul continua cu valorile vechi pana la restart | settings.py:123-140 + config.py:66 | M | HIGH |

---

## R5 — 12. Frontend UI

**Probleme noi gasite:** Settings fara error check, polling leak, WS reconnect leak, api.ts schemas gresite, monitoring fara error handling.

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 22 | C22 | **Settings save nu verifica res.ok** — `fetch()` fara check status HTTP. Server 400/500 → user vede "Salvat!" → crede ca setarile sunt active | Settings.tsx:67-71 | S | CRIT |
| 23 | C23 | **Batch polling interval + WS reconnect timer nu se curata la unmount** — setInterval ramas activ dupa navigare = toast-uri pe pagini gresite, WS orfane acumulate, memory leak | BatchAnalysis.tsx:49-67, useWebSocket.ts:57 | S | HIGH |
| 24 | C24 | **api.compareCompanies + api.createMonitoring schema gresita** — `{cuis}` in loc de `{cui_list}`, `{cui,company_name}` in loc de `{company_id,alert_type}`. Functii API complet nefunctionale | api.ts:146,175 | S | HIGH |
| 25 | C25 | **Monitoring toggle/delete + CompareCompanies score 0** — Toggle/delete fara try/catch (eroare silentioasa), scor 0 afisat ca "date lipsa" (gri) in loc de rosu | Monitoring.tsx:62-70, CompareCompanies.tsx:35 | S | HIGH |

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
