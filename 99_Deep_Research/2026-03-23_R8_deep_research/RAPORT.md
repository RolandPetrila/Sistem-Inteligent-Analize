# Deep Research Report — Roland Intelligence System (RIS) — R8
Data: 2026-03-23 18:00 | Stack: Python 3.13 + FastAPI + React 19 | Agenti: 6 + audit manual | Timp: ~15 min

## Scor General

| Aspect | Scor | Vizual |
|--------|------|--------|
| Securitate | 8/10 | ████████░░ |
| Calitate Cod | 6/10 | ██████░░░░ |
| Arhitectura | 8/10 | ████████░░ |
| Testare | 5/10 | █████░░░░░ |
| Performanta | 7/10 | ███████░░░ |
| Documentatie | 8/10 | ████████░░ |
| Dependente | 7/10 | ███████░░░ |
| Deploy Ready | 6/10 | ██████░░░░ |
**TOTAL: 55/80**

## Metrici Proiect (masurate)

| Metrica | Valoare | Cum am masurat |
|---------|---------|---------------|
| Backend Python LOC | 13,363 | find + wc -l |
| Frontend TS/TSX LOC | 4,175 | find + wc -l |
| Total LOC | 17,538 | suma |
| Fisiere backend .py | 58 | find count |
| Fisiere frontend .ts/.tsx | 25 | find count |
| Fisiere test | 7 (6 py + 1 ts) | glob |
| Total teste | 88 (77 pytest + 11 vitest) | grep "def test_" / "it(" count |
| DB size | 748 KB | du -sh |
| Frontend bundle (gzip) | 80 KB (index) + ~30 KB (pages) | npx vite build |
| Build time | 56.73s | npx vite build |
| API endpoints | ~40 | grep @router count |
| Frontend pagini | 11 (+ 404) | App.tsx routes |
| Formate raport | 7 (PDF+DOCX+HTML+Excel+PPTX+1Pager+ZIP) | CLAUDE.md |
| Git commits | 20 | git log |
| Fragile code #1 | scoring.py (8 modif) | git log --name-only |
| Fragile code #2 | html_generator.py (6 modif) | git log --name-only |

## Gasiri Critice (actiune imediata)

### F1. BUG: WebSocket manager — list.discard() pe lista [CERT]
- **Fisier:** `backend/main.py:51`
- **ROI:** 10 | **Impact:** CRITICAL | **Efort:** 5 min | **Risc:** LOW
- **Problema:** `self.active[job_id]` este initializat ca `list` (linia 29: `= []`, linia 30: `.append()`), dar linia 51 apeleaza `.discard(ws)` — metoda de `set`, nu de `list`.
- **Root cause:** Probabil codul a fost scris initial cu `set`, apoi schimbat la `list` fara actualizarea tuturor referintelor.
- **Impact:** `AttributeError: 'list' object has no attribute 'discard'` cand se detecteaza WebSocket-uri moarte in `broadcast()`. Dead connections NU sunt curatate.
- **Fix:** Schimba `self.active[job_id].discard(ws)` in `self.active[job_id].remove(ws)` sau transforma `active` in `dict[str, set[WebSocket]]`.

### F2. HTML _render_content() nu parseaza tabele markdown [CERT]
- **Fisier:** `backend/reports/html_generator.py:21-50`
- **ROI:** 9 | **Impact:** HIGH | **Efort:** 2h | **Risc:** MEDIUM
- **Problema:** Cand AI genereaza tabele markdown (`| Col | Col |`), acestea sunt randate ca `<p>| Col | Col |</p>` in loc de `<table>`. Confirmat in Mosslein_4.html liniile 328-335 (sectiunea Ratii Financiare).
- **Root cause:** `_render_content()` nu are niciun handler pentru linii care incep cu `|`.
- **Impact:** Tabelele financiare (ratii, benchmark, comparatii) sunt ilizibile in raportul HTML.
- **Fix:** Adauga parser de tabele markdown: detecteaza linii `| ... |`, parseaza header/separator/rows, genereaza `<table class="md-table">`.

### F3. Inline **bold** nu e stripat in list items [CERT]
- **Fisier:** `backend/reports/html_generator.py:40`
- **ROI:** 8 | **Impact:** HIGH | **Efort:** 30 min | **Risc:** LOW
- **Problema:** List items ca `- **Descriere**: Text...` sunt randate ca `<li>**Descriere**: Text...</li>` cu asteriscurile raw. Confirmat in Mosslein_4.html liniile 361-362.
- **Root cause:** Linia 40 face doar `_escape(line[2:])` fara a procesa inline markdown.
- **Impact:** Raportul HTML arata neprofesional cu `**text**` literal in loc de **bold**.
- **Fix:** Dupa `_escape()`, aplica regex: `re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)`.

## Gasiri Importante (HIGH)

### F4. Version mismatch in health endpoints [CERT]
- **Fisier:** `backend/main.py:278` si `backend/main.py:292`
- **ROI:** 8 | **Impact:** MEDIUM | **Efort:** 5 min | **Risc:** LOW
- **Problema:** `/api/health` returneaza `"version": "3.0.0"` dar `/api/health/deep` returneaza `"version": "1.1.0"`.
- **Fix:** Unifica la o constanta `RIS_VERSION = "3.0.0"` in config.py.

### F5. Numbered list support lipseste in _render_content() [CERT]
- **Fisier:** `backend/reports/html_generator.py:21-50`
- **ROI:** 7 | **Impact:** MEDIUM | **Efort:** 30 min | **Risc:** LOW
- **Problema:** AI genereaza frecvent `1. Item`, `2. Item` — nu sunt convertite in `<ol>`. Randate ca `<p>`.
- **Fix:** Detecteaza pattern `^\d+\.\s` si genereaza `<ol>/<li>`.

### F6. Missing PRAGMA temp_store=MEMORY si optimize la close [CERT]
- **Fisier:** `backend/database.py:15-23` (connect) si `backend/database.py:27-29` (close)
- **ROI:** 7 | **Impact:** MEDIUM | **Efort:** 15 min | **Risc:** LOW
- **Problema:** `PRAGMA temp_store=MEMORY` lipseste (ar tine temp tables in RAM — mai rapid). `PRAGMA optimize` nu e apelat la close (recomandat de SQLite docs).
- **Sursa:** [SQLite Performance Tuning](https://phiresky.github.io/blog/2020/sqlite-performance-tuning/)
- **Fix:** Adauga `await self._db.execute("PRAGMA temp_store=MEMORY")` in connect() si `await self._db.execute("PRAGMA optimize")` in close().

### F7. playwright in requirements.txt — dependenta nefolosita [PROBABIL]
- **Fisier:** `requirements.txt:17`
- **ROI:** 7 | **Impact:** LOW | **Efort:** 5 min | **Risc:** LOW
- **Problema:** `playwright==1.58.0` e listata dar niciun import `playwright` nu exista in backend/.
- **Verificare:** `grep -r "playwright\|from playwright" backend/` — 0 rezultate.
- **Impact:** Dependenta grea (~50MB), incetineste install.
- **Fix:** Sterge din requirements.txt daca confirmat nefolosit.

### F8. matplotlib posibil nefolosita [PROBABIL]
- **Fisier:** `requirements.txt:26`
- **ROI:** 6 | **Impact:** LOW | **Efort:** 15 min | **Risc:** LOW
- **Problema:** `matplotlib==3.10.7` — de verificat daca se foloseste. Chart.js e folosit in frontend HTML, openpyxl are grafice native Excel.
- **Fix:** Grep `import matplotlib` — daca 0 rezultate, sterge.

### F9. 9 blocuri except Exception: pass — erori inghitite silentios [CERT]
- **Fisiere:** database.py:66, monitoring.py:113+124, jobs.py:193, batch.py:125, caen_context.py:340+364, agent_official.py:229, compare.py:118, job_service.py:34
- **ROI:** 6 | **Impact:** MEDIUM | **Efort:** 1h | **Risc:** LOW
- **Problema:** Erorile sunt inghitite complet — debugging imposibil cand ceva nu merge.
- **Fix:** Inlocuieste `pass` cu `logger.debug(f"... {e}")` pentru fiecare. Pastreaza comportamentul (nu crash), dar logheaza.

### F10. Anti-hallucination inca flaggeaza financial_analysis [CERT]
- **Fisier:** `backend/agents/agent_synthesis.py:555-605`
- **ROI:** 6 | **Impact:** MEDIUM | **Efort:** 30 min | **Risc:** LOW
- **Problema:** In Mosslein_4, sectiunea `financial_analysis` are inca "[Nota: Verificati cifrele...]" (linia 353). Threshold-ul de 3 discrepante e aproape de limita.
- **Fix:** Ajusteaza: skip numere din tabelul de ratii (care sunt calculate, nu raw data). Adauga pattern skip pentru "ROE", "ROA", "Marja".

### F11. Lipseste .env.example [CERT]
- **Fisier:** (nu exista)
- **ROI:** 6 | **Impact:** MEDIUM | **Efort:** 15 min | **Risc:** LOW
- **Problema:** Noul utilizator nu stie ce variabile trebuie setate. config.py le defineste dar nu exista template.
- **Fix:** Genereaza `.env.example` din toate campurile Settings.

### F12. Dependenta beautifulsoup4 — verificare utilizare [PROBABIL]
- **Fisier:** `requirements.txt:18`
- **ROI:** 5 | **Impact:** LOW | **Efort:** 10 min | **Risc:** LOW
- **Problema:** `beautifulsoup4==4.13.4` — de verificat daca se foloseste.

## Imbunatatiri Sugerate (MEDIUM, ROI descrescator)

### F13. Split agent_verification.py (1248 LOC) [CERT]
- **Fisier:** `backend/agents/agent_verification.py`
- **ROI:** 5 | **Impact:** MEDIUM | **Efort:** 3h | **Risc:** MEDIUM
- **Problema:** Al doilea cel mai mare fisier. Contine scoring, completeness, due diligence, early warnings, actionariat, benchmark — prea multe responsabilitati.
- **Nota:** Deja exista `backend/agents/verification/scoring.py` (618 LOC) — split partial facut.
- **Fix:** Extrage: due_diligence.py (~200 LOC), early_warnings.py (~150 LOC), completeness.py (~200 LOC).

### F14. DRY: Extract provider call pattern din synthesis [CERT]
- **Fisier:** `backend/agents/agent_synthesis.py:394-551`
- **ROI:** 5 | **Impact:** MEDIUM | **Efort:** 2h | **Risc:** MEDIUM
- **Problema:** `_generate_with_groq`, `_generate_with_mistral`, `_generate_with_gemini`, `_generate_with_cerebras` sunt ~30 linii aproape identice (URL, payload format, response parsing). Doar URL, model name, si auth header difera.
- **Fix:** Extrage `_generate_with_openai_compat(provider, url, model, api_key, prompt)` si elimina duplicarea.

### F15. Teste: html_generator _render_content() [CERT]
- **Fisier:** (nou) `tests/test_html_generator.py`
- **ROI:** 5 | **Impact:** MEDIUM | **Efort:** 2h | **Risc:** LOW
- **Problema:** `_render_content()` nu are niciun test. E fisierul cu cele mai multe modificari (6 commits) si bug-uri recurente.
- **Fix:** Teste pentru: headers ##/###, list items, **bold**, tables |, trust labels, edge cases.

### F16. Teste: orchestrator flow [PROBABIL]
- **Fisier:** (nou) `tests/test_orchestrator.py`
- **ROI:** 4 | **Impact:** MEDIUM | **Efort:** 3h | **Risc:** LOW
- **Problema:** Orchestrator-ul (graful LangGraph) nu are teste. E codul central al pipeline-ului.

### F17. Teste: pdf_generator sanitize [CERT]
- **Fisier:** (nou) `tests/test_pdf_generator.py`
- **ROI:** 4 | **Impact:** LOW | **Efort:** 1h | **Risc:** LOW
- **Problema:** Functia `_sanitize` (latin-1 encoding) nu are teste — risc de caractere romanesti trunchiates.

### F18. Compare PDF: concluzii mai detaliate [CERT]
- **Fisier:** `backend/reports/compare_generator.py:194-213`
- **ROI:** 4 | **Impact:** MEDIUM | **Efort:** 2h | **Risc:** LOW
- **Problema:** Concluziile sunt simpliste: "Cifra Afaceri: X este superior (N vs M)". Lipsesc: diferenta procentuala, interpretare (de ex. "cu 23% mai mare"), recomandare.
- **Fix:** Adauga calcul procentual si narrative interpretativa.

### F19. BPI client robustete [CERT]
- **Fisier:** `backend/agents/tools/bpi_client.py:43-73`
- **ROI:** 4 | **Impact:** MEDIUM | **Efort:** 2h | **Risc:** MEDIUM
- **Problema:** `_check_buletinul_ro()` cauta keywords in `resp.text.lower()` — orice pagina cu cuvantul "insolventa" (chiar in meniu/footer) va returna `found: True`. False positives posibile.
- **Fix:** Cauta keywords doar in body-ul principal, sau verifica ca CUI apare langa keyword.

### F20. fpdf2 + mistletoe pentru tabele in PDF [NEVERIFICAT]
- **ROI:** 3 | **Impact:** MEDIUM | **Efort:** 4h | **Risc:** MEDIUM
- **Sursa:** [fpdf2 Combine With Markdown](https://py-pdf.github.io/fpdf2/CombineWithMarkdown.html)
- **Problema:** PDF-ul probabil are aceleasi probleme cu tabelele markdown ca HTML-ul.
- **Fix:** Foloseste `mistletoe` sa converteasca markdown sections → HTML, apoi fpdf2 `write_html()`.

## Audit Granular

### Per-Endpoint Backend

| Endpoint | Fisier:Linie | Probleme | Certitudine |
|----------|-------------|----------|-------------|
| GET /api/health | main.py:276 | Version hardcodat "3.0.0" | [CERT] |
| GET /api/health/deep | main.py:289 | Version "1.1.0" (mismatch) | [CERT] |
| GET /api/stats | main.py:356 | Global mutable `_stats_cache` — OK pt single-worker | [CERT] |
| WS /ws/jobs/{id} | main.py:394 | Broadcast .discard() bug | [CERT] |
| GET /api/reports | reports.py:14 | f-string SQL cu params ? — OK | [CERT] |
| GET /api/jobs | jobs.py:* | f-string SQL cu params ? — OK | [CERT] |
| GET /api/companies | companies.py:* | f-string SQL cu params ? — OK | [CERT] |
| POST /api/batch | batch.py:* | except:pass pe cleanup — silent | [CERT] |
| POST /api/compare | compare.py:* | except:pass pe history save — silent | [CERT] |
| POST /api/monitoring | monitoring.py:* | 2x except:pass — silent failures | [CERT] |

### Per-Pagina Frontend

| Pagina | Fisier | Probleme | Certitudine |
|--------|--------|----------|-------------|
| Dashboard | Dashboard.tsx | OK — stats + trend chart | [CERT] |
| NewAnalysis | NewAnalysis.tsx | OK — CUI validator + templates | [CERT] |
| ReportView | ReportView.tsx | OK — re-analyze button (E13) | [CERT] |
| CompanyDetail | CompanyDetail.tsx | OK — largest page (8.68KB) | [CERT] |
| BatchAnalysis | BatchAnalysis.tsx | No file type validation client-side | [PROBABIL] |
| Settings | Settings.tsx | API key masking OK (eye toggle) | [CERT] |

### AI Prompt Audit

| Sectiune | Specific? | Format? | Anti-haluc? | Few-shot? | Sugestie |
|----------|-----------|---------|-------------|-----------|----------|
| executive_summary | DA | DA | DA | DA | OK — complet |
| company_profile | DA | DA | DA | DA | OK — complet |
| financial_analysis | DA | DA (tabel ratii) | DA | DA | Tabelul de ratii NU se randeaza in HTML |
| risk_assessment | DA | DA | DA | DA | OK |
| competition | DA | DA (tabel) | DA | DA | Tabelul NU se randeaza (F2) |
| opportunities | DA | DA | DA | DA | OK |
| swot | DA | DA | DA | DA | OK |
| recommendations | DA | DA | DA (B14) | DA | OK |

### Surse Externe Audit

| Client API | Fisier | Error handling? | Rate limit? | Cache? | Retry? |
|-----------|--------|----------------|------------|--------|--------|
| ANAF TVA | anaf_client.py | DA (404 OK) | DA (2s delay) | DA | DA |
| ANAF Bilant | anaf_bilant_client.py | DA | DA (2s delay) | DA | DA |
| BNR | bnr_client.py | DA | - | DA | DA |
| openapi.ro | openapi_client.py | DA | DA (quota) | DA | DA |
| Tavily | tavily_client.py | DA | DA (quota tracking) | DA | DA |
| SEAP | seap_client.py | DA | DA | DA | DA |
| BPI | bpi_client.py | DA | - | DA (Tavily) | DA (2-tier) |
| INS TEMPO | caen_context.py | DA | - | DA | except:pass |

## Dead Code Identificat

| Tip | Locatie | Detalii | Certitudine |
|-----|---------|---------|-------------|
| Dependenta | requirements.txt:17 | playwright — 0 importuri | [PROBABIL] |
| Dependenta | requirements.txt:26 | matplotlib — de verificat | [PROBABIL] |
| Metoda | agent_synthesis.py:785 | `_extract_raw_for_section` — duplicata de `_extract_raw_dict_for_section` (linia 811) | [PROBABIL] |

## Dependency Map

```
[main.py] --imports--> [config.py, database.py, http_client.py]
    |
    +--routers--> [jobs, reports, companies, analysis, settings, compare, monitoring, batch]
    |                  |
    |                  +--all use--> [database.py, config.py]
    |
    +--lifespan--> [cache_service, scheduler]

[orchestrator.py] --imports--> [agent_official, agent_verification, agent_synthesis]
    |                              |            |                    |
    |                              +--tools-->  [anaf_client, bnr_client, tavily_client,
    |                              |            openapi_client, seap_client, caen_context,
    |                              |            anaf_bilant_client, bpi_client, cui_validator]
    |                              |
    |                              +--verification--> [scoring.py, completeness]
    |
    +--reports--> [generator.py]
                      |
                      +--> [pdf_gen, docx_gen, html_gen, excel_gen, pptx_gen, one_pager, compare_gen]
```

## Cross-Platform Issues

| Config | Windows (dev) | Observatie |
|--------|--------------|------------|
| subprocess.CREATE_NO_WINDOW | DA (agent_synthesis.py:355) | Corect — sys.platform check |
| Path separators | Path() folosit consistent | OK |
| Encoding utf-8 | Setat explicit in subprocess | OK |
| fpdf2 latin-1 | _sanitize() in pdf_generator | OK dar fara teste (F17) |

## Provider/Tool Scan

| Tool curent | Alternativa | Free? | Avantaj | Recomandare |
|------------|------------|-------|---------|-------------|
| fpdf2 (PDF) | + mistletoe (md→html→pdf) | DA | Tabele markdown native | [UPGRADE RECOMANDAT] |
| openpyxl (Excel) | - | - | - | [NU MERITA SCHIMBAREA] |
| Chart.js (HTML) | - | - | - | [NU MERITA SCHIMBAREA] |
| sqlite/aiosqlite | - | - | - | [NU MERITA SCHIMBAREA] |
| LangGraph | - | - | - | [NU MERITA SCHIMBAREA] |
| BPI via Tavily fallback | Lista firme direct API | DA | Mai precis decat keyword scan | [ALTERNATIVA INTERESANTA] |

## Best Practices Comparison

| Practica | Status proiect | Recomandare | Prioritate |
|----------|---------------|-------------|-----------|
| Parameterized SQL | DA — toate query-urile | - | - |
| Error sanitization | DA — stack traces ascunse | - | - |
| Request ID tracing | DA — X-Request-ID | - | - |
| CORS restrictiv | DA — regex pattern | - | - |
| Rate limiting | DA — API key + semaphore | - | - |
| Security headers | DA — CSP, X-Frame, etc. | - | - |
| Code splitting | DA — React.lazy 11 pages | - | - |
| DB WAL mode | DA | Adauga temp_store=MEMORY | MEDIUM |
| .env.example | NU | Creeaza din config.py | HIGH |
| Multi-worker | NU (uvicorn singur) | - | LOW (app local) |
| Gunicorn manager | NU | - | LOW (app local) |
| PRAGMA optimize | NU | Adauga la close() | MEDIUM |

## Fragile Code Hotspots

| Fisier | Nr modif (50 commits) | Cauza | Recomandare |
|--------|----------------------|-------|-------------|
| scoring.py | 8 | Logica scoring mereu ajustata | Stabilizeaza cu teste |
| html_generator.py | 6 | Bug-uri markdown rendering | Adauga teste + table parser |
| excel_generator.py | 6 | Noi sheet-uri + grafice | OK — feature additions |
| agent_synthesis.py | 6 | Provider routing + anti-haluc | DRY provider calls |
| batch.py | 5 | Safety + retry logic | OK — hardening |
| pdf_generator.py | 5 | Sanitize + watermark | Adauga teste |

## Metrici Actuale vs Target

| Metrica | Actual (masurat) | Target recomandat | Cum masori |
|---------|-----------------|-------------------|-----------|
| Frontend bundle gzip | 80 KB (index) | < 100 KB | npx vite build |
| DB size | 748 KB | < 50 MB | du -sh |
| Test files coverage | 7/83 fisiere (8%) | > 30% | glob count |
| Test count | 88 | > 120 | pytest + vitest |
| Silent except:pass | 9 | 0 | grep count |
| Largest file (py) | 1,248 LOC | < 500 LOC | wc -l |
| Dead deps | 2 (playwright, matplotlib?) | 0 | grep imports |
| API version consistency | 2 diferite | 1 | grep "version" |

## Roadmap Imbunatatiri R8

### SESIUNEA 1 — Quick Wins + Bug Fix (ROI > 7, ~2h)
```
[F1] FIX BUG: main.py:51 list.discard() → list.remove()
     Efort: 5 min | Impact: CRITICAL | Depinde de: nimic

[F4] FIX: Version consistency health endpoints
     Efort: 5 min | Impact: MEDIUM | Depinde de: nimic

[F7] CLEAN: Sterge playwright din requirements.txt (dupa grep confirm)
     Efort: 5 min | Impact: LOW | Depinde de: nimic

[F8] CLEAN: Verifica matplotlib, sterge daca nefolosit
     Efort: 15 min | Impact: LOW | Depinde de: nimic

[F6] PERF: Adauga PRAGMA temp_store=MEMORY + optimize la close
     Efort: 15 min | Impact: MEDIUM | Depinde de: nimic

[F11] DOC: Creeaza .env.example
     Efort: 15 min | Impact: MEDIUM | Depinde de: nimic

[F3] FIX: Inline **bold** stripping in _render_content() list items
     Efort: 30 min | Impact: HIGH | Depinde de: nimic

[F5] ADD: Numbered list support (1. 2. 3.) in _render_content()
     Efort: 30 min | Impact: MEDIUM | Depinde de: nimic
```

### SESIUNEA 2 — HTML Table Rendering + Anti-Hallucination (~3h)
```
[F15] TEST: Scrie teste pentru html_generator _render_content()
      Efort: 2h | Impact: MEDIUM | Depinde de: F3, F5 (dupa ce se adauga features)

[F2] FIX: Markdown table parsing in _render_content()
     Efort: 2h | Impact: HIGH | Depinde de: F15 (test-first!)

[F10] FIX: Anti-hallucination — skip ratii financiare calculate
      Efort: 30 min | Impact: MEDIUM | Depinde de: nimic

[F9] FIX: Adauga logger.debug in cele 9 except:pass blocks
     Efort: 1h | Impact: MEDIUM | Depinde de: nimic
```

### SESIUNEA 3 — Cod Quality + Robustete (~4h)
```
[F14] REFACTOR: DRY provider calls in agent_synthesis.py
      Efort: 2h | Impact: MEDIUM | Depinde de: nimic

[F19] ROBUST: BPI client — cauta keyword aproape de CUI, nu in toata pagina
      Efort: 2h | Impact: MEDIUM | Depinde de: nimic

[F18] IMPROVE: Compare PDF concluzii cu procente si narrative
      Efort: 2h | Impact: MEDIUM | Depinde de: nimic

[F13] REFACTOR: Split agent_verification.py (extrage due_diligence, early_warnings)
      Efort: 3h | Impact: MEDIUM | Depinde de: nimic
```

### VIITOR (nice to have, ROI < 4):
```
[F16] TEST: orchestrator flow (mock agents)
      Efort: 3h | Depinde de: F13

[F17] TEST: pdf_generator _sanitize
      Efort: 1h | Depinde de: nimic

[F20] IMPROVE: fpdf2 + mistletoe pentru tabele in PDF
      Efort: 4h | Depinde de: F2 (HTML tables first)
```

## Ce Am Omis / Ce Poate Fi Incorect

1. **Nu am putut rula backend-ul** — import time si performanta runtime nu sunt masurate real
2. **Agentii de explorare** pot gasi probleme suplimentare cand termina (6 agenti in background)
3. **playwright** si **matplotlib** — marcate [PROBABIL] dead code; pot fi folosite in scripturi auxiliare neincluse in backend/
4. **beautifulsoup4** — probabil folosit de BPI sau alt client dar nu am confirmat
5. **Test coverage real** (statement/branch) nu a fost masurat — nu am putut rula pytest --cov
6. **Securitate CSRF** — FastAPI nu are CSRF built-in, dar fiind SPA cu API key auth, riscul e LOW
7. **Performance sub sarcina** — nu am testat concurrent requests, doar static analysis

## Snapshot JSON

```json
{
  "snapshot_date": "2026-03-23",
  "project": "Roland Intelligence System (RIS)",
  "stack": "Python 3.13 + FastAPI + React 19 + SQLite",
  "phase": "Post-R7 (Faza 14 completa)",
  "metrics": {
    "backend_import_time_s": null,
    "frontend_bundle_kb_gzip": 80,
    "db_size_kb": 748,
    "total_endpoints": 40,
    "total_pages": 11,
    "total_loc_backend": 13363,
    "total_loc_frontend": 4175,
    "total_loc": 17538,
    "db_tables": null,
    "test_files": 7,
    "test_count": 88,
    "backend_files": 58,
    "frontend_files": 25,
    "report_formats": 7,
    "ai_providers": 5,
    "data_sources": 10,
    "git_commits": 20
  },
  "scores": {
    "security": 8,
    "code_quality": 6,
    "architecture": 8,
    "testing": 5,
    "performance": 7,
    "documentation": 8,
    "dependencies": 7,
    "deploy_ready": 6,
    "total": 55
  },
  "issues": {
    "critical": 3,
    "high": 9,
    "medium": 8,
    "low": 1
  },
  "improvements_proposed": 21
}
```
