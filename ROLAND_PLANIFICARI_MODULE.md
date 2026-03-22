# RIS — Planificari Extindere Module (Runda 4)

> Deep-dive pe cod sursa post-Faza 10F. Focus: bug-uri critice, data quality pipeline, calitate raport, reliability.
> Metoda: 6 agenti paraleli deep research + sequential thinking + filtrare stricta ROI.
> Reguli: free tier only, single user, DOAR imbunatatiri cu impact semnificativ pe calitatea functionarii.
> Generat: 2026-03-22 | Runda: 4 (post-Faza 10A-10F) | 27 items selectate din 90+ findings

---

## Faze implementate (completate)

| Faza | Ce s-a implementat |
|------|--------------------|
| 1-7E | Fundatie completa: 8 surse date, 5 agenti AI, scoring 6D, 7 formate raport, LangGraph, cache, monitoring, batch, tests |
| 8A-8E | Gzip, ErrorCode 55+, cache stats, trend scoring, volatility CV, solvency, dynamic word count, ZIP pack, smart severity, audit log |
| 9A-9E | Parallel fetch, error boundaries 5/5, cash flow proxy, confidence scoring, pagination, watermark, TOC, alert dedup, batch resume |
| 10A-10F | 51 P1 features: solvency matrix, prompt hardening, parallel Agent 2+3, request dedup, cache LRU 100MB, batch parallel 2-CUI, request ID tracing, error sanitization, form validation, HTML responsive |

---

## Harta Module — Evolutie R1 -> R2 -> R3 -> R4

| # | Modul | R1 % | R2 % | R3 % | R4 target | Status |
|---|-------|------|------|------|-----------|--------|
| 1 | **Dashboard** | 45% | 58% | 78% | 78% (no changes) | - |
| 2 | **Colectare Date (Agent 1)** | 62% | 68% | 92% | 97% | [ ] R4 PROPUS |
| 3 | **Verificare & Scoring (Agent 4)** | 67% | 82% | 98% | 99% | [ ] R4 PROPUS |
| 4 | **Sinteza AI (Agent 5)** | 62% | 78% | 97% | 99% | [ ] R4 PROPUS |
| 5 | **Orchestrator** | 67% | 75% | 95% | 97% | [ ] R4 PROPUS |
| 6 | **Rapoarte** | 62% | 72% | 92% | 97% | [ ] R4 PROPUS |
| 7 | **Comparator & Delta** | 57% | 60% | 85% | 90% | [ ] R4 PROPUS |
| 8 | **Batch Analysis** | 52% | 65% | 90% | 95% | [ ] R4 PROPUS |
| 9 | **Monitoring & Alerte** | 57% | 62% | 85% | 95% | [ ] R4 PROPUS |
| 10 | **Cache & Performance** | 72% | 78% | 95% | 97% | [ ] R4 PROPUS |
| 11 | **Securitate & API** | 68% | 75% | 94% | 96% | [ ] R4 PROPUS |
| 12 | **Frontend UI** | 62% | 62% | 88% | 92% | [ ] R4 PROPUS |

**Media exploatare:** R1=61% -> R2=70% -> R3=91% -> R4 target=94%

---

## Legenda

- **CRIT** = Bug critic — crash sau date corupte, FIX OBLIGATORIU
- **HIGH** = Impact major pe calitatea raportului sau fiabilitate
- **MED** = Imbunatatire semnificativa, fara urgenta critica
- **Efort:** S (~30 min) | M (~1-2h) | L (~3h+)

---

## 2. Colectare Date (Agent 1 — Official Data)

**Status post-10F:** 8 surse cu asyncio.gather paralel. Cache hit/miss. Data freshness. Error boundaries 5/5. Retry 3x exponential. CUI early return. Tavily quota pre-check. ANAF year-range smart.
**Probleme gasite R4 deep research:** CAEN chain complet rupt (3 bug-uri inlantuite), litigation = pointer insolvency, SEAP valute mixte.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 1 | B1 | **CAEN din ANAF API v9 nu se extrage** — campul `cod_caen` exista in raspunsul `date_generale` dar NU e parsat in result dict. ~15% firme pierd CAEN din sursa primara | anaf_client.py | S | HIGH |
| 2 | B2 | **openapi_client "found" field lipseste** — return dict nu are `"found": True`. Agent 4 face `onrc_s.get("found")` → False → CAEN fallback chain rupt, actionariat skipat | openapi_client.py | S | CRIT |
| 3 | B3 | **Litigation = same reference as insolvency** — `official_data["litigation"] = official_data["insolvency"]` (pointer, nu copie). Agent 4 trateaza separat dar ambele pointeaza la aceleasi date | agent_official.py:199-204 | S | HIGH |
| 4 | B4 | **SEAP valute mixte sumate fara conversie** — contracte in RON + EUR sumate direct in `total_value`. Solutie: conversie cu BNR rate deja disponibil in pipeline | seap_client.py:117-122 | M | MED |

**Total: 4 (1 CRIT, 2 HIGH, 1 MED)**

---

## 3. Verificare & Scoring (Agent 4)

**Status post-10F:** Scor 0-100 pe 6D cu trend, volatility, solvency, cash flow, confidence, anomaly loop, benchmark, score history DB.
**Probleme gasite R4 deep research:** 2 bug-uri logice in completeness, confidence nefolosita in ponderea finala, risk factors duplicate.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 5 | B5 | **Actionariat logic bug** — `if actionariat.get("asociati") or ...` dar empty list `[]` e falsy in Python. Firma cu admin unic (valid) marcata INCOMPLETE. Fix: check `actionariat.get("available")` separat | completeness.py:46 | S | CRIT |
| 6 | B6 | **Market check {} truthy bug** — `if market_verified:` dar empty dict `{}` e truthy. Firma fara market data e marcata "PASS". Fix: check `if market_verified and any(market_verified.values())` | completeness.py:111 | S | CRIT |
| 7 | B7 | **Confidence nefolosita in scor final** — confidence per dimensiune (0.0-1.0) e calculata dar `total_score` NU e ponderat cu ea. Firma cu financiar 85 + confidence 0.2 = identic cu 85 + confidence 1.0 | scoring.py:403-421 | M | HIGH |
| 8 | B8 | **Risk factors duplicate** — `risk_factors.append()` fara dedup. Acelasi risc detectat in multiple locuri = inflat in raport. Fix: hash-based dedup inainte de return | scoring.py:489-502 | S | MED |

**Total: 4 (2 CRIT, 1 HIGH, 1 MED)**

---

## 4. Sinteza AI (Agent 5)

**Status post-10F:** 5 provideri fallback cu routing per sectiune. Dynamic word count. Context awareness. Anti-halucinare. Provider-specific styles. Anomaly injection. Token budget. Output validation.
**Probleme gasite R4 deep research:** Provider order gresit pt narativ, JSON truncation distruge context, hallucination detection pasiva, degradation = JSON dump.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 9 | B9 | **Provider order gresit pt "fast" route** — Groq e primul dar genereaza bullet-points, nu narativ. Rezumat executiv cu Groq = lista, nu paragraf. Fix: Mistral->Gemini->Groq->Claude pt fast | agent_synthesis.py:59-107 | S | HIGH |
| 10 | B10 | **JSON context limits statice si prea mici** — Groq primeste max 4K chars din 20K verified_data = vede 20% din date. AI genereaza pe baza incompleta. Fix: limita adaptiva per provider + extractie campuri relevante per sectiune | agent_synthesis.py:147-149 | M | HIGH |
| 11 | B11 | **Hallucination detection pasiva** — `_validate_output()` detecteaza probleme (% suspecte, word count mic) dar RETURNEAZA TEXTUL CU NOTA in loc sa regenereze. Raport profesional NU ar trebui sa contina "[Nota sistem]" | agent_synthesis.py:245-275 | M | HIGH |
| 12 | B12 | **Degradation fallback = JSON dump** — Cand TOTI providerii esueaza, Tier 3 = `json dump` in raport. Distruge credibilitatea. Fix: template narativ pre-renderat cu date injectate, NICIODATA JSON raw | agent_synthesis.py:519-543 | M | HIGH |

**Total: 4 (0 CRIT, 4 HIGH)**

---

## 5. Orchestrator

**Status post-10F:** LangGraph state machine cu timing metrics, error boundaries 5/5, request dedup, state checkpoints, parallel Agent 2+3.
**Probleme gasite R4 deep research:** variabila nedefinita crash, early warnings neconectate la recomandari.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 13 | B13 | **anaf_bilant_client variabila `years` nedefinita** — `"years_requested": years` dar variabila `years` nu exista in scope. Runtime NameError la orice bilant multi-an. Fix: `list(range(start_year, end_year + 1))` | anaf_bilant_client.py:146 | S | CRIT |
| 14 | B14 | **Early warnings neconectate la recomandari** — Agent 4 detecteaza "CA -35% YoY" dar sectiunea Recomandari e generata independent, fara obligatia de a adresa warning-urile. Fix: inject warnings in prompt recomandari cu "TREBUIE sa adresezi aceste semnale" | orchestrator.py + section_prompts | M | HIGH |

**Total: 2 (1 CRIT, 1 HIGH)**

---

## 6. Rapoarte (7 Generatoare)

**Status post-10F:** PDF+DOCX+HTML+Excel+PPTX+1-Pager+ZIP. Watermark, TOC, Chart.js, bookmarks, CAGR, responsive.
**Probleme gasite R4 deep research:** ~45% din verified_data NU ajunge in PDF/DOCX, Excel CAGR crash pe startups, PPTX fara trend.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 15 | B15 | **PDF/DOCX ignora due_diligence + early_warnings** — Date calculate de Agent 4 dar NU afisate. 1-Pager le are, PDF/DOCX nu. Adauga sectiuni: checklist 10 items + semnale alarma dupa risk assessment | pdf_generator.py, docx_generator.py | M | HIGH |
| 16 | B16 | **Excel CAGR crash pe firma < 2 ani** — `n_years = ca_years_count - 1` poate fi 0, CAGR division by zero. ROE fara null check pe profit_latest. Fix: guard clauses + "N/A startup" | excel_generator.py:324-371 | S | HIGH |
| 17 | B17 | **PPTX fara trend financiar** — Slide "Date Financiare" are 6 campuri statice. `trend_financiar` multi-an exista dar nu e vizualizat. Adauga slide cu tabel CA/Profit/Angajati pe 3-5 ani | pptx_generator.py | M | MED |

**Total: 3 (0 CRIT, 2 HIGH, 1 MED)**

---

## 7. Comparator & Delta

**Status post-10F:** Compare 2-5 firme, financial ratios, sector percentile, chart.js format, anomaly flags, time-series 5 rapoarte.
**Probleme gasite R4 deep research:** an hardcodat, delta doar pe scor total fara dimensiuni.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 18 | B18 | **Compare year hardcodat** — `last_year = date.today().year - 2` mereu. In martie 2026 = 2024 fix. Dar unele firme au bilant doar 2023. Fix: try year-1, fallback year-2, fallback year-3 | compare.py:45 | S | MED |
| 19 | B19 | **Delta doar pe scor total, fara dimensiuni** — Delta detecteaza schimbare scor 72→58 dar NU spune de ce (financiar -20 vs operational +5). Adauga breakdown per dimensiune in delta | delta_service.py | M | MED |

**Total: 2 (0 CRIT, 0 HIGH, 2 MED)**

---

## 8. Batch Analysis

**Status post-10F:** CSV upload, pre-validare, retry 2x, progress DB, resume, parallel 2-CUI, queue max 2, checkpoint per CUI.
**Probleme gasite R4 deep research:** gather exception = batch mort, stuck batch = concurrent limit blocat.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 20 | B20 | **gather() exception = batch RUNNING forever** — `return_exceptions=False` + no try/except pe gather. O exceptie in 1 CUI = intregul batch moare, status ramane RUNNING. Fix: try/except pe gather + per-CUI exception handling | batch.py:389 | S | CRIT |
| 21 | B21 | **Stuck batch = concurrent limit blocat** — Batch crash → status RUNNING → `COUNT(*) >= 2` → user blocat permanent. Fix: auto-cancel batch-uri RUNNING > 4h la startup | batch.py:110 + scheduler.py | M | HIGH |

**Total: 2 (1 CRIT, 1 HIGH)**

---

## 9. Monitoring & Alerte

**Status post-10F:** CRUD alerte, scheduler 6h, smart severity, audit log, dedup 24h, throttling, Telegram retry 3x, health endpoint.
**Probleme gasite R4 deep research:** schema mismatch = dedup dezactivat, firma radiata = no alert.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 22 | B22 | **Schema mismatch: `triggered_at` vs `created_at`** — monitoring_audit tabel are coloana `triggered_at` dar TOATE query-urile folosesc `created_at`. Rezultat: dedup DEZACTIVAT, throttling DEZACTIVAT, user primit alerte DUPLICATE la fiecare check | monitoring_service.py + monitoring.py | S | CRIT |
| 23 | B23 | **Firma radiata = silentios ignorata** — ANAF returneaza `found=False` pt firma radiata. Cod seteaza `changed=False, error="CUI not found"` → NO alert. User NU afla ca firma a fost radiata | monitoring_service.py:136 | M | HIGH |

**Total: 2 (1 CRIT, 1 HIGH)**

---

## 10. Cache & Performance

**Status post-10F:** SQLite cache cu TTL, hit/miss tracking, LRU 100MB, schema versioning, event-driven invalidation, HTTP pool metrics.
**Probleme gasite R4 deep research:** race condition in get_or_fetch.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 24 | B24 | **get_or_fetch race condition** — 2 requesturi simultane pt acelasi CUI: ambele fac cache miss, ambele apeleaza ANAF (2x). Fix: asyncio.Lock per cache_key inainte de fetch | cache_service.py | M | MED |

**Total: 1 (0 CRIT, 0 HIGH, 1 MED)**

---

## 11. Securitate & API

**Status post-10F:** SecurityHeaders, CSP, ApiKeyMiddleware, Gzip, CORS, RequestLogging+Redaction, RequestID, ErrorSanitization, RequestValidation, Rate limiter.
**Probleme gasite R4 deep research:** WebSocket broadcast swallows exceptions.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 25 | B25 | **WebSocket broadcast exception swallowing** — `except Exception: pass` in ws.send_text(). Client deconectat → mesaj pierdut, conexiune moarta ramane in lista, memory leak. Fix: log + remove dead ws din active list | main.py (WSManager) | S | MED |

**Total: 1 (0 CRIT, 0 HIGH, 1 MED)**

---

## 12. Frontend UI

**Status post-10F:** React 19, 11 pagini lazy, pagination, API key masking, responsive sidebar, form validation Zod, CUI validator, search debouncing, retry button.
**Probleme gasite R4 deep research:** retry-source UI lipseste (endpoint exista), search+pagination bug.

### Imbunatatiri R4

| # | Cod | Ce rezolva concret | Locatie | Efort | Sev |
|---|-----|-------------------|---------|-------|-----|
| 26 | B26 | **Retry-source fara UI** — Endpoint `POST /jobs/{id}/retry-source/{source}` exista din 7E dar NU are buton in AnalysisProgress. User nu stie ca poate reincerca o sursa esuata individual | AnalysisProgress.tsx | M | HIGH |
| 27 | B27 | **Companies search reset nu reseteaza paginare** — User cauta "Acme" (3 rezultate, page 1). Sterge search → ramane pe page=2 care e gol. Fix: `setPage(0)` in useEffect pe search | Companies.tsx | S | MED |

**Total: 2 (0 CRIT, 1 HIGH, 1 MED)**

---

## Rezumat General (Runda 4)

| # | Modul | CRIT | HIGH | MED | Total | R3% | R4% | Delta |
|---|-------|------|------|-----|-------|-----|-----|-------|
| 2 | Colectare Date (Agent 1) | 1 | 2 | 1 | 4 | 92% | 97% | +5% |
| 3 | Verificare & Scoring (Agent 4) | 2 | 1 | 1 | 4 | 98% | 99% | +1% |
| 4 | Sinteza AI (Agent 5) | 0 | 4 | 0 | 4 | 97% | 99% | +2% |
| 5 | Orchestrator | 1 | 1 | 0 | 2 | 95% | 97% | +2% |
| 6 | Rapoarte | 0 | 2 | 1 | 3 | 92% | 97% | +5% |
| 7 | Comparator & Delta | 0 | 0 | 2 | 2 | 85% | 90% | +5% |
| 8 | Batch Analysis | 1 | 1 | 0 | 2 | 90% | 95% | +5% |
| 9 | Monitoring & Alerte | 1 | 1 | 0 | 2 | 85% | 95% | +10% |
| 10 | Cache & Performance | 0 | 0 | 1 | 1 | 95% | 97% | +2% |
| 11 | Securitate & API | 0 | 0 | 1 | 1 | 94% | 96% | +2% |
| 12 | Frontend UI | 0 | 1 | 1 | 2 | 88% | 92% | +4% |
| | **TOTAL** | **6** | **13** | **8** | **27** | **91%** | **96%** | **+5%** |

---

## Top 10 Quick Wins R4 (Impact maxim, efort minim)

| Ord | Cod | Modul | Ce fixeaza | Efort | Sev |
|-----|-----|-------|-----------|-------|-----|
| 1 | B13 | Orchestrator | `years` nedefinita → crash bilant multi-an | S | CRIT |
| 2 | B22 | Monitoring | `triggered_at` vs `created_at` → dedup dezactivat | S | CRIT |
| 3 | B2 | Agent 1 | openapi "found" lipseste → CAEN chain rupt | S | CRIT |
| 4 | B5 | Agent 4 | Actionariat `[]` falsy → completeness gresit | S | CRIT |
| 5 | B6 | Agent 4 | Market `{}` truthy → completeness inflat | S | CRIT |
| 6 | B20 | Batch | gather() no try/except → batch mort forever | S | CRIT |
| 7 | B1 | Agent 1 | CAEN din ANAF API v9 ne-extras | S | HIGH |
| 8 | B9 | Agent 5 | Groq first in fast route → narativ slab | S | HIGH |
| 9 | B16 | Rapoarte | Excel CAGR division by zero pe startups | S | HIGH |
| 10 | B3 | Agent 1 | Litigation = pointer insolvency (nu copie) | S | HIGH |

**Timp estimat Top 10:** ~5h (toate sunt S = ~30 min fiecare)

---

## REGULI DE EXECUTIE CERINTE

### Workflow implementare per cerinta

```
1. SELECTIE
   - Alege cerinta din tabelul modulului (CRIT intai, apoi HIGH, apoi MED)
   - Verifica: "Ce modul afecteaza?" -> citeste codul sursa INAINTE
   - Confirma: cerinta inca e relevanta? (nu s-a implementat intre timp)

2. PRE-IMPLEMENTARE
   [ ] Citeste TOATE fisierele afectate (backend + frontend)
   [ ] Identifica functiile exacte de modificat/adaugat
   [ ] Verifica dependinte cross-module (vezi sectiunea module)
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

5. DOCUMENTARE (vezi Protocol Documentatie mai jos)
   [ ] Actualizeaza CLAUDE.md (status faza, key files daca fisier nou)
   [ ] Bifeaza cerinta [x] in ROLAND_PLANIFICARI_MODULE.md
   [ ] Actualizeaza FUNCTII_SISTEM.md daca functie/endpoint NOU
   [ ] Memory files daca decizie tehnica noua
   [ ] TODO_ROLAND.md la finalul sesiunii

6. CONFIRMARE
   [ ] Afiseaza: CE s-a implementat + CE fisiere modificate
   [ ] Test real: ruleaza analiza completa (CUI 26313362 = MOSSLEIN)
   [ ] Marcheaza cerinta [x] in fisierul de planificari
```

### Reguli stricte

1. **CRIT inainte de HIGH inainte de MED** — Nu sari la MED daca CRIT sau HIGH neimplementate
2. **Bug fix = test imediat** — Dupa fix CRIT, ruleaza test care demonstreaza fix-ul
3. **Cross-module: identifica INAINTE** — B2 (openapi) afecteaza B5 (completeness) si B7 (confidence)
4. **Nu modifica module netestate** — Daca nu ai pytest/vitest pe modul, adauga test INAINTE
5. **O cerinta = un commit logic** — Nu amesteca B22 (monitoring schema) cu B9 (synthesis routing)

### Ordinea recomandata per sesiune

```
Sesiune tipica (~2-3h):

Sesiune 1 (CRITICAL bugs): B13 + B22 + B2 + B5 + B6 + B20
   = 6 bug-uri critice, toate efort S, ~3h total cu testare

Sesiune 2 (Data quality): B1 + B3 + B9 + B16 + B7
   = 5 HIGH items, ~3h total

Sesiune 3 (Synthesis + Reports): B10 + B11 + B12 + B15
   = 4 HIGH items pt calitate raport, ~4h total

Sesiune 4 (Reliability): B21 + B23 + B14 + B8 + B24 + B25
   = 6 items MED-HIGH, ~3h total

Sesiune 5 (Polish): B26 + B27 + B4 + B17 + B18 + B19
   = 6 items MED, ~3h total

Dupa fiecare sesiune: pytest + vitest + analiza CUI 26313362
```

---

## PROTOCOL ACTUALIZARE DOCUMENTATIE

### Ce fisiere se actualizeaza si cand

| Fisier | Cand se actualizeaza | Ce se modifica |
|--------|---------------------|----------------|
| `CLAUDE.md` | La finalul FIECAREI sesiuni cu implementari | Status faze, key files (daca fisier nou), decizii tehnice |
| `ROLAND_PLANIFICARI_MODULE.md` | Dupa FIECARE cerinta implementata | Bifeaza `[ ]` -> `[x]`, actualizeaza R4% |
| `FUNCTII_SISTEM.md` | Daca functie/endpoint NOU adaugat | Adauga in inventar cu descriere + parametri |
| `TODO_ROLAND.md` | La finalul sesiunii | Status items, ce ramane, ce e nou |
| `AUDIT_REPORT.md` | Doar la modificari MAJORE (security, scoring) | Adauga entry cu data + descriere |
| Memory files | Daca decizie tehnica noua confirmata | project_ris_decisions.md / project_ris_status.md |

### Ordinea actualizare

```
1. ROLAND_PLANIFICARI_MODULE.md  -> bifeaza cerinta [x]
2. FUNCTII_SISTEM.md             -> adauga functie noua (daca exista)
3. CLAUDE.md                     -> status faza + key files + decizii
4. TODO_ROLAND.md                -> ce s-a facut + ce ramane
5. Memory files                  -> daca decizie/status nou
6. AUDIT_REPORT.md               -> doar la schimbari critice
```

### Checklist documentatie

```
[ ] CLAUDE.md — Faza curenta actualizata?
[ ] CLAUDE.md — Key files lista completa?
[ ] CLAUDE.md — Numar REST endpoints corect?
[ ] ROLAND_PLANIFICARI_MODULE.md — Cerinta bifata [x]?
[ ] FUNCTII_SISTEM.md — Functie noua listata?
[ ] TODO_ROLAND.md — Status actualizat?
[ ] Memory — Decizie noua salvata?
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
6. Verifica in raportul HTML:
   [ ] CAEN code prezent (B1, B2)
   [ ] Actionariat corect (B5)
   [ ] Due diligence checklist (B15)
   [ ] Scor completitudine > 70% (B6)
   [ ] Text narativ fluid, nu bullets (B9)
   [ ] Fara "[Nota sistem]" in text (B11)
   [ ] Fara JSON raw in raport (B12)
7. Verifica in logs/:
   [ ] Fara NameError/crash (B13)
   [ ] Surse cu status OK/FAIL (nu crash)
```

### Test automated (la finalul sesiunii)

```bash
# Backend tests
cd C:\Proiecte\Sistem_Inteligent_Analize
python -m pytest tests/ -v --tb=short

# Frontend tests
cd frontend
npx vitest run --reporter=verbose
```

### Test monitoring (dupa B22)

```
1. Adauga alerta pe firma de test
2. Ruleaza POST /api/monitoring/check-now
3. Verifica: NU se trimit alerte duplicate
4. Verifica: log monitoring_audit are triggered_at (nu created_at)
```

---

## DEPENDINTE CROSS-MODULE

```
B2 (openapi found) --> B5 (completeness actionariat)
                   --> B7 (confidence scoring)
                   --> B1 (CAEN extraction chain)

B13 (bilant years) --> B16 (Excel CAGR)
                   --> B15 (PDF/DOCX financial data)

B22 (schema fix)   --> monitoring dedup
                   --> monitoring throttling
                   --> monitoring health endpoint

B9 (provider order) --> B10 (JSON context)
                    --> B11 (hallucination)
                    --> B12 (degradation fallback)
```

**Implicatie:** B2 trebuie implementat INAINTE de B5 si B7. B9 inainte de B10-B12.
