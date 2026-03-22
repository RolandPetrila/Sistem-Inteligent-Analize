# Deep Research Report — Roland Intelligence System (RIS)
Data: 2026-03-21 15:00 | Stack: Python 3.13 + FastAPI + React 19 + Vite + TS + SQLite | Agenti: 6 | Timp: ~15 min

---

## Scor General

| Aspect | Scor | Vizual | Delta vs anterior |
|--------|------|--------|-------------------|
| Securitate | 6/10 | ██████░░░░ | = (6) |
| Calitate Cod | 7/10 | ███████░░░ | = (7) |
| Arhitectura | 8/10 | ████████░░ | = (8) |
| Testare | 1/10 | █░░░░░░░░░ | = (1) |
| Performanta | 6/10 | ██████░░░░ | +1 (era 5) |
| Documentatie | 9/10 | █████████░ | = (9) |
| Dependente | 6/10 | ██████░░░░ | -2 (era 8) |
| Deploy Ready | 4/10 | ████░░░░░░ | = (4) |
| **TOTAL** | **47/80** | | **-1** (era 48) |

**Nota:** Scorul dependente a scazut de la 8 la 6 din cauza descoperirii ca requirements.txt NU corespunde cu pachetele instalate (divergenta majora langgraph 0.3.30 vs 1.1.3).

---

## Metrici Proiect (masurate)

| Metrica | Valoare | Delta vs anterior | Cum am masurat |
|---------|---------|-------------------|----------------|
| Backend import time | 9.39s | -3.56s (era 12.95s) | `python -c "import..."` |
| - fastapi | 3.56s | -1.44s | idem |
| - fpdf2 | 2.84s | -0.43s | idem |
| - httpx | 0.63s | -0.56s | idem |
| - openpyxl | 1.27s | -0.46s | idem |
| - pptx | 0.71s | -0.09s | idem |
| - docx | 0.33s | NOU masurat | idem |
| - aiosqlite | 0.04s | -0.01s | idem |
| Frontend bundle JS | 308.47 KB | +68KB (era 240KB) | `npx vite build` |
| Frontend bundle gzip | 92.48 KB gzip | = | `npx vite build` |
| Frontend CSS | 24.18 KB | +3KB (era 21KB) | `npx vite build` |
| DB size | 112 KB | = | `du -sh data/*.db` |
| Data dir | 1.6 MB | NOU | `du -sh data/` |
| Backup size | 112 KB | NOU | `du -sh backups/*.db` |
| Total endpoints | 33 | +3 (era 30) | `grep @router` |
| Total pagini | 10 | = | `App.tsx routes` |
| Total LOC backend | 7662 | = | `wc -l` |
| Total LOC frontend | 3085 | = | `wc -l` |
| DB tables | 9 | = | `sqlite_master` |
| DB rows total | 64 | NOU | `SELECT COUNT(*)` |
| Test files | 0 | = | `find` |
| TODO/FIXME/HACK | 0 | = | `grep` |
| console.log in frontend | 0 | -11 (era 11) | `grep` |
| npm vulnerabilities | 0 | = | `npm audit` |
| except Exception blocks | 44 in 18 files | NOU | `grep` |
| httpx singleton usage | CORECT | = | `grep` |
| Lazy imports reports | DA (in generator.py) | = | `grep` |
| React.lazy() | 0 instante | = | `grep` |
| Chunks JS | 1 (monolitic) | = | `npx vite build` |

---

## SQLite PRAGMA Status

| PRAGMA | Actual | Recomandat (WAL best practices 2026) | Status |
|--------|--------|---------------------------------------|--------|
| journal_mode | WAL | WAL | OK |
| busy_timeout | 5000 | 5000 | OK |
| foreign_keys | ON | ON | OK |
| cache_size | -20000 (20MB) | -2000 sau -20000 | OK |
| synchronous | 2 (FULL) | 1 (NORMAL) | SUBOPTIMAL |
| mmap_size | 0 (dezactivat) | 30000000000 | LIPSA |

---

## Gasiri Critice (actiune imediata)

### [CRITICAL] [ROI: 10] PATH TRAVERSAL in download report — `backend/routers/reports.py:140` [CERT]
**Problema:** Endpoint-ul de download primeste `file_path` din baza de date si il serveste FARA validare ca e in directorul `outputs/`:
```python
full_path = Path(file_path)  # ← Nu verifica ca e in outputs/!
if not full_path.exists():
    raise HTTPException(404)
return FileResponse(full_path)
```
**Root cause:** `file_path` vine din DB. Daca DB e compromisa sau un bug scrie un path gresit, se poate citi orice fisier de pe disk.
**Impact:** File disclosure — orice fisier accesibil user-ului Windows poate fi descarcat.
**Fix:** Adauga validare path:
```python
full_path = Path(file_path).resolve()
base = Path(settings.outputs_dir).resolve()
if not str(full_path).startswith(str(base)):
    raise HTTPException(403, "Access denied")
```
**Efort:** MIC (15 min) | **Risc:** LOW

### [CRITICAL] [ROI: 10] requirements.txt divergent de installed — `requirements.txt` [CERT]
**Problema:** requirements.txt specifica versiuni care NU corespund cu pachetele instalate:
- `langgraph==0.3.30` in req vs `1.1.3` instalat (MAJOR version mismatch!)
- `fastapi==0.115.12` in req vs `0.115.5` instalat
- `pydantic==2.11.1` in req vs `2.9.2` instalat
- `pydantic-settings==2.8.1` in req vs `2.13.1` instalat
- `fpdf2==2.8.3` in req vs `2.8.7` instalat
- `aiosqlite==0.21.0` in req vs `0.22.1` instalat

**Root cause:** requirements.txt a fost editat manual cu versiuni "dorite" fara `pip freeze`.
**Impact:** Oricine face `pip install -r requirements.txt` primeste un mediu DIFERIT de cel functional. Deploy pe alta masina = crash garantat (mai ales langgraph 0.3 vs 1.1 — API complet diferit).
**Fix:** Ruleaza `pip freeze > requirements.txt` si verifica rezultatul.
**Efort:** MIC (5 min) | **Risc:** LOW (reversibil)

### [CRITICAL] [ROI: 9] backups/ nu e in .gitignore — `.gitignore` [CERT]
**Problema:** Directorul `backups/` contine copii ale bazei de date (`ris_2026-03-21.db`) dar NU este exclus din `.gitignore`.
**Root cause:** La adaugarea feature-ului backup automat, .gitignore nu a fost actualizat.
**Impact:** La un eventual `git add .` sau `git init`, backup-urile DB (cu date potentiale ale firmelor analizate) ar fi comise in repository.
**Fix:** Adauga `backups/` in `.gitignore`.
**Efort:** MIC (1 min) | **Risc:** LOW

---

## Gasiri Importante (HIGH)

### [HIGH] [ROI: 9] Batch progress in-memory — pierdut la restart — `backend/routers/batch.py:25` [CERT]
**Problema:** Batch progress e stocat in dict in-memory: `_batch_progress: dict[str, dict] = {}`. Daca serverul restarteaza in timpul unui batch de 50 CUI-uri, progress-ul se pierde complet.
**Root cause:** Design initial rapid, fara persistenta.
**Impact:** UX deteriorata — utilizatorul pierde tracking pe batch-uri lungi (10-30 min).
**Fix:** Muta batch progress in tabelul DB (adauga `batch_jobs` table sau extinde `jobs`).
**Efort:** MIC (30 min) | **Risc:** LOW

### [HIGH] [ROI: 9] SQLite backup nesigur — `backend/services/scheduler.py:109` [CERT]
**Problema:** Backup-ul DB foloseste `shutil.copy2()` pe un fisier SQLite activ. SQLite poate fi in mijlocul unui write, ceea ce produce un backup corupt.
**Root cause:** Metoda simpla aleasa initial. SQLite are un API dedicat de backup (`VACUUM INTO` sau `sqlite3.backup()`).
**Fix:** Inlocuieste `shutil.copy2(db_path, backup_path)` cu:
```python
import sqlite3
src = sqlite3.connect(str(db_path))
dst = sqlite3.connect(str(backup_path))
src.backup(dst)
dst.close()
src.close()
```
**Efort:** MIC (30 min) | **Risc:** LOW

### [HIGH] [ROI: 8] 0 teste automate — tot proiectul [CERT]
**Problema:** Zero fisiere de test in backend si frontend (doar 2 fisiere frontend sunt Playwright empty stubs). Orice modificare poate introduce regresii nedetectate.
**Root cause:** Focus pe feature delivery rapid, testare manuala.
**Impact:** La refactorizare (ex: splitul agent_verification.py), nu exista nicio retea de siguranta.
**Fix:** Prioritar: teste pe rutele critice (POST /jobs, scoring logic, CUI validator, ANAF client mock).
**Efort:** MARE (8-16h pentru coverage minim ~40%) | **Risc:** LOW

### [HIGH] [ROI: 7] agent_verification.py — 1063 linii [CERT]
**Problema:** Cel mai mare fisier din proiect. Contine scoring logic + due diligence + early warnings + actionariat + benchmark + cross-validation — toate in acelasi fisier.
**Root cause:** Feature-uri adaugate incremental in aceeasi clasa.
**Impact:** Dificil de intretinut, dificil de testat individual, risc de regresii la modificari.
**Fix:** Separa in module: `scoring.py`, `due_diligence.py`, `early_warnings.py`, `benchmark.py`.
**Efort:** MEDIU (2-4h) | **Risc:** MEDIUM (necesita teste inainte!)

### [HIGH] [ROI: 7] Fara rate limiting pe API — `backend/main.py` [CERT]
**Problema:** Endpoint-urile API nu au rate limiting. Un script rau-intentionat poate trimite mii de request-uri/secunda.
**Root cause:** App local, initial fara nevoie de protectie.
**Impact:** DoS local, consum resurse, potential flood ANAF API (care are propriul rate limit).
**Fix:** Adauga `slowapi` (wrapper peste `limits`) pe endpoint-urile POST.
**Efort:** MIC (1h) | **Risc:** LOW

### [HIGH] [ROI: 6] Fara autentificare — toate endpoint-urile [CERT]
**Problema:** Orice client din retea (inclusiv Tailscale) poate accesa/modifica/sterge date fara autorizare.
**Root cause:** Design initial = "doar local".
**Impact:** Cu CORS deschis pentru Tailscale (100.x.x.x), orice dispozitiv din reteaua Tailscale are acces total.
**Fix:** Minim: API key simplu in header (`X-RIS-Key`) verificat cu middleware. Sau: basic auth.
**Efort:** MEDIU (2-3h) | **Risc:** MEDIUM

---

## Gasiri MEDIUM (imbunatatiri recomandate)

### [MEDIUM] [ROI: 7] SEAP client fara cache — `backend/agents/tools/seap_client.py` [CERT]
**Problema:** Spre deosebire de celelalte 5 clienti API (ANAF, BNR, Tavily, openapi, ANAF Bilant) care folosesc `cache_service`, SEAP client NU cacheaza rezultatele. Fiecare re-analiza a aceluiasi CUI face call-uri noi la SEAP.
**Root cause:** Omisiune la implementare cache.
**Impact:** Request-uri inutile la SEAP (rate limit strict, 3s delay per call).
**Fix:** Adauga `cache_service.get_or_fetch(key=f"seap_{cui}", source="seap_active", ...)` cu TTL 2h.
**Efort:** MIC (15 min) | **Risc:** LOW

### [MEDIUM] [ROI: 7] compare.py si monitoring bypass cache — `routers/compare.py:48,66` [CERT]
**Problema:** Routerele compare.py si monitoring_service.py apeleaza direct `get_anaf_data()` si `get_bilant()` fara a trece prin `cache_service`. Datele nu sunt reutilizate din cache.
**Root cause:** Routerele au fost adaugate separat de agent pipeline-ul care foloseste cache.
**Impact:** Latenta +500ms-1s per request daca datele sunt deja in cache.
**Fix:** Inlocuieste apelurile directe cu `cache_service.get_or_fetch()`.
**Efort:** MIC (30 min) | **Risc:** LOW

### [MEDIUM] [ROI: 6] AI prompts fara few-shot examples — `backend/prompts/` [CERT]
**Problema:** Niciunul din cele 7 section prompts si system prompt nu contine un exemplu de output dorit (few-shot). Groq si Gemini pot genera format inconsistent (bullets vs paragrafe).
**Root cause:** Prompturi scrise pentru Claude care respecta instructiunile bine, dar alte modele variaza.
**Impact:** Inconsistenta format output intre provideri AI.
**Fix:** Adauga 2-3 linii exemplu de output dorit in fiecare section prompt.
**Efort:** MEDIU (1h) | **Risc:** LOW

### [MEDIUM] [ROI: 7] Frontend: pages folosesc fetch() direct in loc de api.ts — multiple pagini [CERT]
**Problema:** api.ts ofera un wrapper centralizat cu error handling, dar 5 pagini folosesc `fetch()` direct:
- `CompareCompanies.tsx:69` — `fetch("/api/compare")`
- `Dashboard.tsx:40,295` — `fetch("/api/settings")`, `fetch("/api/stats/trend")`
- `BatchAnalysis.tsx:32,51` — `fetch("/api/batch...")`
- `Monitoring.tsx:35,36,52,63,68,75` — 6 direct fetches
- `Settings.tsx:51,64,81` — 3 direct fetches

**Root cause:** Endpoint-uri adaugate in faze ulterioare fara extinderea api.ts.
**Impact:** Error handling inconsistent. Unele catch-uri sunt goale (`catch {}`), altele nu verifica `res.ok`.
**Fix:** Extinde `api.ts` cu metodele lipsa (compare, batch, monitoring, stats/trend) si refactorizeaza paginile.
**Efort:** MEDIU (2h) | **Risc:** LOW

### [MEDIUM] [ROI: 6] Silent error swallowing in catch blocks — multiple fisiere frontend [CERT]
**Problema:** Mai multe catch blocks nu afiseaza toast sau log:
- `Dashboard.tsx:298` — `.catch(() => {})`
- `NewAnalysis.tsx:70` — `.catch(() => {})`
- `Dashboard.tsx:40` — `.catch(() => null)`
- `BatchAnalysis.tsx:62,78` — `catch {}` fara toast
- `Settings.tsx:71,84` — `catch {}` fara toast

**Root cause:** Quick error suppression la development.
**Impact:** Utilizatorul nu afla ca ceva a esuat.
**Fix:** Inlocuieste cu toast de eroare in fiecare catch.
**Efort:** MIC (30 min) | **Risc:** LOW

### [MEDIUM] [ROI: 6] SQLite PRAGMA synchronous=FULL — `backend/database.py:18-21` [CERT]
**Problema:** In WAL mode, synchronous=NORMAL e recomandat (safe + performant). FULL adauga fsync-uri inutile.
**Root cause:** PRAGMA synchronous nu e setat explicit, default = FULL.
**Impact:** Write-uri mai lente cu ~20-30% fara beneficiu de safety suplimentar in WAL mode.
**Fix:** Adauga `await self._db.execute("PRAGMA synchronous=NORMAL")` dupa WAL mode.
**Efort:** MIC (5 min) | **Risc:** LOW

### [MEDIUM] [ROI: 5] React.lazy() absent — monolitic 308KB — `frontend/src/App.tsx` [CERT]
**Problema:** Toate cele 10 pagini sunt importate eager in App.tsx. Un singur chunk JS de 308KB (92KB gzip).
**Root cause:** React.lazy nu a fost implementat.
**Impact:** Initial load descarca tot codul chiar daca utilizatorul acceseaza doar Dashboard-ul. La 92KB gzip nu e critic, dar e o imbunatatire simpla.
**Fix:** Inlocuieste importurile statice cu `React.lazy()` + `<Suspense>` in App.tsx.
**Efort:** MIC (30 min) | **Risc:** LOW

### [MEDIUM] [ROI: 5] CSP cu unsafe-inline si unsafe-eval — `backend/main.py:105-106` [CERT]
**Problema:** Content-Security-Policy include `'unsafe-inline' 'unsafe-eval'` pe script-src, ceea ce anuleaza practic protectia CSP impotriva XSS.
**Root cause:** Chart.js (CDN) si inline styles necesita aceste exceptii.
**Impact:** CSP nu protejeaza contra script injection. Pentru app local, riscul e redus.
**Fix:** Migra Chart.js din CDN in bundle (npm install chart.js), elimina unsafe-eval.
**Efort:** MEDIU (1-2h) | **Risc:** MEDIUM

### [MEDIUM] [ROI: 5] Default secret key — `backend/config.py:32` [CERT]
**Problema:** `app_secret_key: str = "change-me-to-random-string"` — daca .env nu seteaza, ramane default-ul.
**Root cause:** Default hardcodat pt development.
**Impact:** Predictibil. Daca se adauga JWT/sessions, cheia e compromisa.
**Fix:** Genereaza random la init sau fa campul obligatoriu (fara default).
**Efort:** MIC (15 min) | **Risc:** LOW

### [MEDIUM] [ROI: 4] Lipsa route 404 catch-all — `frontend/src/App.tsx` [CERT]
**Problema:** Nu exista `<Route path="*" element={<NotFound />} />`. Navigare la URL invalid = pagina goala.
**Root cause:** Omisiune la implementare routes.
**Fix:** Adauga o componenta NotFound simpla si o ruta catch-all.
**Efort:** MIC (15 min) | **Risc:** LOW

### [MEDIUM] [ROI: 4] uvicorn reload=True in __main__ — `backend/main.py:276` [CERT]
**Problema:** `reload=True` e hardcodat in blocul `if __name__ == "__main__"`. In productie, reload monitorizeaza fisiere si consuma CPU.
**Root cause:** Setare de development lasata in cod.
**Fix:** Conditioneaza de `settings.log_level == "DEBUG"` sau un flag explicit.
**Efort:** MIC (5 min) | **Risc:** LOW

---

## Gasiri LOW (nice to have)

### [LOW] [ROI: 3] mmap_size=0 — `backend/database.py` [CERT]
**Problema:** PRAGMA mmap_size nu e setat. Memory-mapped I/O e dezactivat.
**Impact:** Reads mai lente pe baze de date mari. La 112KB actual, impact zero.
**Fix:** Adauga `PRAGMA mmap_size=268435456` (256MB) — va conta cand DB creste.
**Efort:** MIC (5 min) | **Risc:** LOW

### [LOW] [ROI: 3] X-XSS-Protection deprecated — `backend/main.py:101` [CERT]
**Problema:** Header-ul X-XSS-Protection e deprecated in browsere moderne si poate cauza side-effects.
**Impact:** Nul practic. Browserele il ignora.
**Fix:** Inlocuieste cu nothing sau pastreaza (nu dauneaza).
**Efort:** MIC (2 min) | **Risc:** LOW

### [LOW] [ROI: 2] tsconfig noUnusedLocals=false — `frontend/tsconfig.json:15-16` [PROBABIL]
**Problema:** noUnusedLocals si noUnusedParameters sunt dezactivate, permitand dead code in TypeScript.
**Impact:** Cosmetic — dead code ramane nedetectat.
**Fix:** Seteaza pe `true`, repara erorile de compilare.
**Efort:** MIC (30 min) | **Risc:** LOW

---

## Audit Granular

### Per-Endpoint Backend

| Endpoint | Fisier:Linie | Probleme | Certitudine |
|----------|-------------|----------|-------------|
| POST /api/jobs | jobs.py:18 | - | OK [CERT] |
| GET /api/jobs | jobs.py:44 | f-string SQL (safe — param ?); cod duplicat JSON parse | [CERT] |
| GET /api/jobs/{id} | jobs.py:92 | Cod duplicat JSON parse cu list_jobs | [CERT] |
| POST /api/jobs/{id}/start | jobs.py:120 | asyncio.create_task fire-and-forget (erori pierdute) | [CERT] |
| POST /api/jobs/{id}/cancel | jobs.py:136 | Nu verifica daca job-ul chiar ruleaza | [PROBABIL] |
| GET /api/reports | reports.py:13 | f-string SQL (safe) | [CERT] |
| GET /api/reports/{id} | reports.py:68 | - | OK [CERT] |
| GET /api/reports/{id}/download/{fmt} | reports.py:126 | Path din DB fara validare in outputs/ | [CERT] |
| GET /api/reports/{id}/download/one_pager | reports.py:108 | - | OK [CERT] |
| GET /api/health | main.py:134 | - | OK [CERT] |
| GET /api/health/deep | main.py:140 | - | OK [CERT] |
| GET /api/stats | main.py:204 | Module-level globals pt cache | [CERT] |
| GET /api/stats/trend | main.py:232 | - | OK [CERT] |
| WS /ws/jobs/{id} | main.py:243 | json.loads fara validare (crash = WS disconnect, OK) | [CERT] |
| POST /api/compare | compare.py | Direct fetch fara api.ts | [CERT] |
| POST /api/compare/sector | compare.py | Idem | [CERT] |
| CRUD /api/monitoring | monitoring.py | 5 endpoints, toate fara auth | [CERT] |
| POST /api/batch | batch.py | File upload fara size limit | [PROBABIL] |
| GET /api/batch/{id} | batch.py | - | OK [CERT] |
| GET /api/batch/{id}/download | batch.py | - | OK [CERT] |
| GET /api/companies | companies.py | f-string SQL (safe) | [CERT] |
| GET /api/companies/export/csv | companies.py | - | OK [CERT] |
| GET /api/analysis/types | analysis.py | - | OK [CERT] |
| POST /api/analysis/parse-query | analysis.py | - | OK [CERT] |
| GET /api/settings | settings.py | Expune config non-secret | [CERT] |
| PUT /api/settings | settings.py | Modifica .env fara auth | [CERT] |
| POST /api/settings/test-telegram | settings.py | Trimite mesaj fara auth | [CERT] |

### Per-Pagina Frontend

| Pagina | Fisier | LOC | Probleme | Certitudine |
|--------|--------|-----|----------|-------------|
| Dashboard | Dashboard.tsx | 336 | fetch direct (nu api.ts); catch(() => {}) silent | [CERT] |
| NewAnalysis | NewAnalysis.tsx | 346 | catch(() => {}) pe startJob | [CERT] |
| AnalysisProgress | AnalysisProgress.tsx | 227 | Foloseste api wrapper corect | OK [CERT] |
| ReportsList | ReportsList.tsx | 117 | OK — toast pe erori | OK [CERT] |
| ReportView | ReportView.tsx | 335 | OK — toast pe erori | OK [CERT] |
| Companies | Companies.tsx | 117 | OK — toast pe erori | OK [CERT] |
| CompareCompanies | CompareCompanies.tsx | 213 | fetch direct; error handling custom | [CERT] |
| Monitoring | Monitoring.tsx | 174 | 6x fetch direct; 3x catch {} fara toast | [CERT] |
| BatchAnalysis | BatchAnalysis.tsx | 235 | fetch direct; catch {} fara toast | [CERT] |
| Settings | Settings.tsx | 214 | fetch direct; catch {} fara toast | [CERT] |

### AI Prompts Audit

| Locatie | Scop | Specific? | Format? | Anti-haluc? | Provider-aware? | Few-shot? |
|---------|------|-----------|---------|-------------|-----------------|-----------|
| agent_synthesis.py | Generare sectiuni raport | DA | DA (word limit) | Partial ("fara introduceri") | DA (stil per provider) | NU |
| agent_verification.py | Scoring + verificari | DA | DA (structura fixa) | DA (INDISPONIBIL pt lipsa) | N/A (nu e LLM call) | N/A |
| agent_official.py | Pre-procesare date AI | [NEVERIFICAT] | [NEVERIFICAT] | [NEVERIFICAT] | [NEVERIFICAT] | [NEVERIFICAT] |

### Surse Externe API Audit

| Client API | Fisier | Error handling? | Rate limit? | Cache? | Retry? | Timeout? |
|-----------|--------|----------------|------------|--------|--------|----------|
| ANAF TVA | anaf_client.py | DA (found/notFound) | DA (2s delay) | Via cache_service | NU explicit | DA (httpx 30s) |
| ANAF Bilant | anaf_bilant_client.py | DA | DA (2s delay) | Via cache_service | NU explicit | DA (httpx 30s) |
| BNR | bnr_client.py | [NEVERIFICAT] | N/A (XML static) | Via cache_service | NU | DA (httpx 30s) |
| Tavily | tavily_client.py | DA + quota tracking | N/A (quota-based) | Via cache_service | NU | DA |
| openapi.ro | openapi_client.py | DA | N/A (100/luna) | Via cache_service | NU | DA (httpx 30s) |
| SEAP | seap_client.py | DA | DA (3s delay) | Via cache_service | NU | DA (httpx 30s) |

**Observatie:** Clientii API au retry logic via `BaseAgent.fetch_with_retry()` (3 retries, backoff [2, 5, 15]s), dar doar cand sunt apelati din pipeline-ul de agenti. Apelurile directe din routers (compare.py, monitoring) NU beneficiaza de retry.

---

## Dead Code Identificat

| Tip | Locatie | Detalii | Certitudine |
|-----|---------|---------|-------------|
| Hook nefolosit | `frontend/src/hooks/useApi.ts` | Definit dar neimportat in nicio pagina — pages folosesc fetch direct | [CERT] |
| API wrapper mort | `frontend/src/lib/api.ts` | `api.getSettings()`, `api.updateSettings()`, `api.testTelegram()` definite dar Settings.tsx foloseste fetch direct | [CERT] |
| API wrapper mort | `frontend/src/lib/api.ts` | `api.health()` definit dar neapelat nicaieri in frontend | [CERT] |
| Endpoint neapelat | `POST /api/compare/sector` | Backend definit dar frontend nu il apeleaza | [CERT] |
| DB table | `markets` | 0 rows, posibil nefolosit (MARKET_ENTRY_ANALYSIS poate sa nu-l populeze) | [PROBABIL] |
| DB table | `report_deltas` | 0 rows, posibil nefolosit | [PROBABIL] |
| Frontend spec stubs | `frontend/test-results/` in .gitignore | Playwright menționat dar 0 teste reale | [CERT] |
| Playwright dep | `requirements.txt:18` | playwright==1.51.0 instalat dar posibil nefolosit in runtime | [PROBABIL] |

---

## Dependency Map

```
backend/main.py
  ├── config.py (settings)
  ├── database.py (db singleton)
  ├── http_client.py (httpx singleton)
  ├── services/scheduler.py
  │     ├── services/monitoring_service.py
  │     └── database.py
  ├── services/cache_service.py
  └── routers/
        ├── jobs.py → services/job_service.py → agents/orchestrator.py
        │                                         ├── agents/agent_official.py
        │                                         │     └── agents/tools/ (anaf, bnr, tavily, openapi, seap, cui)
        │                                         ├── agents/agent_verification.py
        │                                         └── agents/agent_synthesis.py
        ├── reports.py
        ├── companies.py
        ├── analysis.py → models.py (ANALYSIS_TYPES_META)
        ├── settings.py → config.py
        ├── compare.py → agents/tools/ (direct)
        ├── monitoring.py → services/monitoring_service.py
        └── batch.py → services/job_service.py

frontend/src/
  ├── main.tsx (ToastProvider + ErrorBoundary + Router)
  ├── App.tsx (Routes → 10 pages)
  ├── lib/api.ts (fetch wrapper — PARTIAL coverage)
  ├── lib/types.ts (TypeScript types)
  ├── lib/cui-validator.ts (MOD 11)
  ├── hooks/useWebSocket.ts
  ├── components/ (Layout, Toast, ErrorBoundary, ChatInput)
  └── pages/ (10 pages)
```

**Circular dependencies:** NICIUNA detectata [CERT]

---

## Cross-Platform Issues

| Config | Windows (dev) | Mobile/Tailscale | Problema | Fix |
|--------|--------------|------------------|----------|-----|
| CORS | localhost:5173 | 100.x.x.x:8001 | CORS regex acopera ambele | OK [CERT] |
| Vite proxy | /api → 8001 | N/A (acces direct) | Proxy doar in dev | OK [CERT] |
| File paths | Windows backslash | N/A | Path() normalizeaza | OK [CERT] |
| SQLite WAL | OK | OK | WAL mode e cross-platform | OK [CERT] |
| subprocess claude | Windows CREATE_NO_WINDOW | N/A | Flag conditionat de platform | OK [CERT] |

---

## Provider/Tool Scan

| Tool curent | Versiune | Alternativa | Free? | Avantaj | Recomandare |
|-------------|----------|-------------|-------|---------|-------------|
| fpdf2 | 2.8.7 | reportlab | Partial | Mai matur, tabele avansate | NU MERITA SCHIMBAREA |
| openpyxl | 3.1.5 | xlsxwriter | DA | Mai rapid la write | NU MERITA SCHIMBAREA |
| httpx | 0.28.1 | aiohttp | DA | Matur, dar httpx e mai modern | NU MERITA SCHIMBAREA |
| LangGraph | 1.1.3 | CrewAI | DA | Diferit paradigm | NU MERITA SCHIMBAREA |
| loguru | 0.7.3 | structlog | DA | Structured logging | ALTERNATIVA INTERESANTA |
| Tailwind | 3.4.17 | Tailwind 4.x | DA | CSS-first, mai mic | UPGRADE RECOMANDAT (cand stabil) |
| Vite | 6.4.1 | - | DA | Ultima versiune | OK |
| React | 19.2.4 | - | DA | Ultima versiune | OK |

---

## Best Practices Comparison (2026)

| Practica | Status Proiect | Recomandare | Prioritate |
|----------|---------------|-------------|------------|
| Parameterized SQL queries | DA (?) | OK — corect implementat | - |
| .env pentru secrets | DA | OK | - |
| CORS restrictiv | DA (regex) | OK | - |
| Security headers | DA (CSP, X-Frame, etc.) | CSP are unsafe-inline/eval | MEDIUM |
| Rate limiting API | NU | Adauga slowapi | HIGH |
| Authentication | NU | Adauga minim API key | HIGH |
| WAL mode SQLite | DA | Adauga synchronous=NORMAL | MEDIUM |
| Connection pool HTTP | DA (httpx singleton) | OK — corect implementat | - |
| Lazy imports | DA (reports) | OK | - |
| Code splitting React | NU | React.lazy() pe pagini | MEDIUM |
| Error boundaries | DA | OK | - |
| Toast notifications | DA (partial) | Extinde la toate catch-urile | MEDIUM |
| Automated tests | NU (0 teste) | Adauga pytest + vitest | HIGH |
| CI/CD pipeline | NU | Adauga GitHub Actions | LOW |
| Structured logging | PARTIAL (loguru) | OK pentru acum | - |
| DB migrations | DA (SQL files) | OK | - |
| Backup automatizat | DA (scheduler) | Fix shutil.copy2 → sqlite3.backup | HIGH |
| Health check | DA (simplu + deep) | OK | - |
| Dependency pinning | PARTIAL (requirements.txt divergent!) | Fix urgent: pip freeze | CRITICAL |

---

## Fragile Code Hotspots

| Fisier | LOC | Cauza | Recomandare |
|--------|-----|-------|-------------|
| agent_verification.py | 1063 | 6+ responsabilitati in 1 fisier | Split in module separate |
| caen_context.py | 361 | Date statice + logica mixed | Separa datele in JSON extern |
| agent_synthesis.py | 357 | 5 provideri AI in 1 fisier | Acceptabil (pattern strategy) |
| NewAnalysis.tsx | 346 | Wizard 4 pasi in 1 componenta | Split in sub-componente per pas |
| Dashboard.tsx | 336 | Multiple sectiuni + API calls | Split in sub-componente |

---

## Metrici Actuale vs Target

| Metrica | Actual (masurat) | Target recomandat | Status | Cum masori |
|---------|-----------------|-------------------|--------|-----------|
| Backend cold start | 9.39s | < 5s | SLOW | `python -c "import..."` |
| Frontend bundle gzip | 92.48 KB | < 150KB | OK | `npx vite build` |
| Frontend chunks | 1 | 3-5 (lazy) | IMPROVABLE | `npx vite build` |
| DB size | 112 KB | < 100MB | OK | `du -sh` |
| Endpoints fara test | 33/33 (100%) | < 20% | FAIL | manual count |
| except Exception blocks | 44 | < 20 (cu logging) | NEEDS REVIEW | `grep` |
| Files > 300 LOC | 5 backend + 3 frontend | < 3 total | HIGH | `wc -l` |
| PRAGMA synchronous | FULL | NORMAL | SUBOPTIMAL | `PRAGMA synchronous` |
| React.lazy pages | 0/10 | 8+/10 | LIPSA | `grep React.lazy` |
| API coverage in api.ts | ~60% | 100% | PARTIAL | manual audit |

---

## Roadmap Imbunatatiri

### SAPTAMANA 1 — Quick Wins (ROI > 7, Efort MIC)

```
[QW1] Fix requirements.txt — pip freeze > requirements.txt
      Fisier: requirements.txt
      Efort: 5 min | Impact: CRITICAL | ROI: 10
      Depinde de: nimic

[QW2] Adauga backups/ in .gitignore
      Fisier: .gitignore
      Efort: 1 min | Impact: CRITICAL | ROI: 9
      Depinde de: nimic

[QW3] PRAGMA synchronous=NORMAL + mmap_size
      Fisier: backend/database.py:21
      Efort: 5 min | Impact: MEDIUM | ROI: 6
      Depinde de: nimic

[QW4] Fix backup cu sqlite3.backup()
      Fisier: backend/services/scheduler.py:109
      Efort: 30 min | Impact: HIGH | ROI: 9
      Depinde de: nimic

[QW5] Fix silent catch blocks in frontend (7 locuri)
      Fisiere: Dashboard.tsx, NewAnalysis.tsx, BatchAnalysis.tsx, Monitoring.tsx, Settings.tsx
      Efort: 30 min | Impact: MEDIUM | ROI: 7
      Depinde de: nimic

[QW6] Adauga route 404 catch-all
      Fisier: frontend/src/App.tsx
      Efort: 15 min | Impact: MEDIUM | ROI: 4
      Depinde de: nimic

[QW7] uvicorn reload conditionat
      Fisier: backend/main.py:276
      Efort: 5 min | Impact: LOW | ROI: 4
      Depinde de: nimic

[QW8] Default secret key → obligatoriu
      Fisier: backend/config.py:32
      Efort: 15 min | Impact: MEDIUM | ROI: 5
      Depinde de: nimic
```
Toate independente — pot fi executate in orice ordine.

### SAPTAMANA 2 — Securitate & Stabilitate

```
[S1] Adauga rate limiting (slowapi) pe POST endpoints
     Efort: 1h | Impact: HIGH | ROI: 7
     Depinde de: nimic

[S2] Adauga API key simplu pentru autentificare
     Efort: 2-3h | Impact: HIGH | ROI: 6
     Depinde de: nimic (dar recomandat DUPA QW1-QW8)

[S3] Extinde api.ts cu toate endpoint-urile lipsa
     Efort: 2h | Impact: MEDIUM | ROI: 7
     Depinde de: nimic

[S4] Migra Chart.js din CDN in bundle + elimina unsafe-eval din CSP
     Efort: 1-2h | Impact: MEDIUM | ROI: 5
     Depinde de: nimic
```

### SAPTAMANA 3-4 — Testare & Refactorizare

```
[T1] Adauga pytest — teste pe CUI validator, ANAF client mock, scoring logic
     Efort: 4-8h | Impact: HIGH | ROI: 8
     Depinde de: nimic (dar INAINTE de A1!)

[T2] Adauga vitest — teste pe CUI validator frontend, api.ts
     Efort: 2-4h | Impact: MEDIUM | ROI: 5
     Depinde de: nimic

[A1] Split agent_verification.py in 4 module
     Efort: 2-4h | Impact: MEDIUM | ROI: 7
     Depinde de: T1 (teste INAINTE de refactorizare!)

[A2] React.lazy() pe 8+ pagini
     Efort: 30 min | Impact: MEDIUM | ROI: 5
     Depinde de: nimic

[A3] Adauga retry logic in clientii API externi (ANAF, Tavily, openapi)
     Efort: 2h | Impact: MEDIUM | ROI: 4
     Depinde de: T1
```

### VIITOR (nice to have, ROI < 3)

```
[V1] Split NewAnalysis.tsx in sub-componente per wizard step
     Efort: MARE | Impact: LOW | Doar daca se adauga noi pasi wizard

[V2] Structured logging cu structlog
     Efort: MARE | Impact: LOW | Doar daca se adauga monitoring extern

[V3] tsconfig strict (noUnusedLocals/Params)
     Efort: MIC | Impact: LOW | Cosmetic

[V4] CI/CD cu GitHub Actions
     Efort: MARE | Impact: MEDIUM | Doar daca se adauga deployment automat
```

**IMPORTANT:** Dependintele sunt OBLIGATORII. Nu executa A1 (refactorizare) inainte de T1 (teste).

---

## Ce Am Omis / Ce Poate Fi Incorect

1. **[NEVERIFICAT] React 19 Compiler** — npm packages sunt la 19.2.4 dar nu am verificat daca React Compiler e activat in vite.config.ts (plugin-ul react() poate sa-l activeze automat sau nu).
2. **[NEVERIFICAT] .env actual** — nu citesc secrets — daca API keys sunt corecte si active.
3. **[PROBABIL] Dead code markets/report_deltas tables** — tabele cu 0 rows pot fi populate de anumite tipuri de analiza pe care nu le-am testat.
4. **[NEVERIFICAT] Playwright dependency** — e in requirements.txt dar nu am verificat daca e folosit activ in backend (posibil doar pentru web scraping).
5. **[PROBABIL] openapi_client.py import httpx** — un agent a raportat posibil `import httpx` lipsa, dar httpx e importat indirect via `get_client()` din `http_client.py`. Necesita verificare la runtime.
6. **Presupuneri:** Am presupus ca app-ul ruleaza doar local + Tailscale. Daca merge pe server public, scorurile de securitate scad semnificativ (agentul de securitate a evaluat 4/10 pentru internet exposure).
7. **[NEVERIFICAT] LangGraph parallelism** — nu am verificat la runtime daca agentii web/market ruleaza in paralel sau sequential prin conditional_edges.

---

## Snapshot JSON

```json
{
  "snapshot_date": "2026-03-21",
  "project": "Roland Intelligence System (RIS)",
  "stack": "Python 3.13 + FastAPI + React 19 + Vite + TypeScript + SQLite",
  "metrics": {
    "backend_import_time_s": 9.39,
    "frontend_bundle_kb_gzip": 92.48,
    "db_size_kb": 112,
    "total_endpoints": 33,
    "total_pages": 10,
    "total_loc_backend": 7662,
    "total_loc_frontend": 3085,
    "db_tables": 9,
    "test_files": 0
  },
  "scores": {
    "security": 6,
    "code_quality": 7,
    "architecture": 8,
    "testing": 1,
    "performance": 6,
    "documentation": 9,
    "dependencies": 6,
    "deploy_ready": 4,
    "total": 47
  },
  "issues": {
    "critical": 3,
    "high": 6,
    "medium": 12,
    "low": 3
  },
  "improvements_proposed": 24
}
```

---

## PROGRES FATA DE ULTIMUL SCAN (2026-03-21, raport anterior)

```
Scor: 48/80 → 47/80 (delta: -1)
  - Performance: 5 → 6 (+1) — import time redus de la 12.95s la 9.39s
  - Dependente: 8 → 6 (-2) — requirements.txt divergent descoperit

Probleme critice: 2 → 2 (=)
  - NOI: requirements.txt divergent, backups/ nu e in .gitignore
  - REZOLVATE: httpx singleton (acum corect), console.log (0 in frontend)

Metrici cu delta semnificativa:
  - Backend import: 12.95s → 9.39s (-27%) — lazy imports functional
  - Frontend bundle: 240KB → 308KB (+28% uncompressed, gzip identic 92KB)
  - console.log: 11 → 0 (-100%)
  - Endpoints: 30 → 33 (+10%)
```

---

**Surse web consultate:**
- [FastAPI Best Practices Production 2026](https://fastlaunchapi.dev/blog/fastapi-best-practices-production-2026)
- [React 19 Best Practices 2026](https://dev.to/jay_sarvaiya_reactjs/react-19-best-practices-write-clean-modern-and-efficient-react-code-1beb)
- [Vercel React Best Practices (40+ Rules)](https://vercel.com/blog/introducing-react-best-practices)
- [SQLite Production Setup 2026](https://oneuptime.com/blog/post/2026-02-02-sqlite-production-setup/view)
- [SQLite WAL Mode Documentation](https://sqlite.org/wal.html)
- [SQLite Performance Optimization 2026](https://forwardemail.net/en/blog/docs/sqlite-performance-optimization-pragma-chacha20-production-guide)
- [FastAPI Security Guide](https://davidmuraya.com/blog/fastapi-security-guide/)
- [LangGraph Build Stateful Multi-Agent Systems](https://www.mager.co/blog/2026-03-12-langgraph-deep-dive/)
- [fpdf2 Security Status (Snyk)](https://security.snyk.io/package/pip/fpdf2)
