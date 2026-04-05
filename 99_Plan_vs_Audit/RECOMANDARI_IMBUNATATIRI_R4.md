# RECOMANDARI IMBUNATATIRI R4 — RIS
**Data creare:** 2026-04-05 | **Ultima actualizare:** 2026-04-05 | **Versiune:** 4.1
**Context:** post-R13 (39 items implementate) + Audit /audit R14
**Metoda:** /improve complet + /audit standard (12 domenii, 4 agenti paraleli)

---

## LEGENDA STATUS

| Simbol | Semnificatie |
|--------|-------------|
| `[ ]` | De facut |
| `[x]` | Implementat |
| `[~]` | In progres |
| `[!]` | Blocat / necesita atentie |
| `[-]` | Ignorat / deprioritizat |

---

## PROFILING BASELINE (2026-04-05)

| Metric | Valoare |
|--------|---------|
| DB size | 748 KB |
| Bundle (gzip main) | 87 KB |
| Build time | 73s (backend) / 49s (frontend) |
| Backend LOC | 14,133 (63 fisiere .py) |
| Frontend LOC | 6,399 (27 fisiere .ts/.tsx) |
| Teste | 171 pytest + 11 vitest, 0 failures |
| SQLite | 3.50.4 |
| Test coverage | ~19% (12/90 fisiere) |
| Scor audit R10 | 90/100 |
| Scor audit R14 | 82/100 (delta -8) |

---

## SCOR AUDIT PE DOMENII (2026-04-05)

| Domeniu | Scor | Delta R10 |
|---------|------|-----------|
| Calitate cod | 7/10 | -1 |
| Securitate | 7/10 | -1 |
| Corectitudine | 8/10 | = |
| Arhitectura | 8/10 | = |
| Documentatie | 7/10 | -1 |
| Secrets scan | 9/10 | = |
| OWASP | 9/10 | = |
| Dependente | 7/10 | -1 |
| Git status | 4/10 | -3 |
| Build & Runtime | 9/10 | = |
| Testare | 6/10 | -1 |
| Performanta | 7/10 | = |
| **TOTAL** | **82/100** | **-8** |

---

## ORDINE GLOBALA RECOMANDATA DE EXECUTIE

```
FAZA 0 (30 min): AUDIT CRITICA — securitate + git  ← PRIORITATE MAXIMA
FAZA 1 (3-4h):   QUICK WINS — FastAPI, lucide, config, N+1, DRY
FAZA 2 (4-5h):   MODERNIZARE — Pydantic, Vite, Tailwind, split fisiere
FAZA 3 (2-4z):   CALITATE & TESTARE — teste frontend + backend + TanStack
FAZA 4 (3-5z):   FEATURES STRATEGICE — NLQ chatbot
FAZA 5 (1-2z):   AUDIT R14 HIGH — traceback, N+1 queries, docs, performance
FAZA 6 (2-4z):   AUDIT R14 MEDIUM — teste coverage, refactor god functions
```

**Regula:** Ruleaza `python -m pytest tests/ -q` dupa fiecare FAZA inainte de a trece la urmatoarea.

---

---

# FAZA 0 — CRITICA AUDIT R14 (30 min)
> Probleme de securitate si integritate date. Trebuie rezolvate INAINTE de orice altceva.

---

### F0.1 Fix API key Gemini in log-uri (plaintext leak)
**Status:** `[ ]`
**Fisier:** `backend/agents/agent_synthesis.py:532-534`
**Severitate:** CRITICA — SECURITY
**Descriere:** Cand Gemini returneaza eroare HTTP, exceptia httpx include URL-ul cu `?key=AIzaSy...` care se scrie in `logs/ris_runtime.log` vizibil.
**Implementare:**
```python
# Inlocuieste linia 533 cu:
except Exception as e:
    err_msg = str(e)
    if "key=" in err_msg:
        import re
        err_msg = re.sub(r'key=[A-Za-z0-9_-]+', 'key=***REDACTED***', err_msg)
    logger.warning(f"[synthesis] Gemini error: {err_msg}")
    record_provider_failure("gemini")
    return None
```
**Verificare:** Ruleaza o analiza si verifica `logs/ris_runtime.log` — key-ul nu trebuie sa apara.

---

### F0.2 Git commit — toate fisierele R13 + fisiere noi netracked
**Status:** `[ ]`
**Context:** 47 fisiere modificate + 6 fisiere noi critice neincluse in git
**Fisiere noi critice:**
- `backend/security.py` — importat din settings.py (NECESAR!)
- `backend/agents/circuit_breaker.py` — circuit breaker
- `backend/routers/notifications.py` — router notificari
- `backend/migrations/004_improvements.sql`
- `backend/migrations/005_fts5.sql`
- `frontend/src/components/GlobalSearch.tsx`
**Implementare:**
```bash
git add backend/security.py backend/agents/circuit_breaker.py \
  backend/routers/notifications.py \
  backend/migrations/004_improvements.sql \
  backend/migrations/005_fts5.sql \
  frontend/src/components/GlobalSearch.tsx
git add -u  # toate fisierele modificate
git commit -m "feat: R13 complete — 39 items (notifications, circuit breaker, FTS5, security, GlobalSearch)"
git push origin main
```
**Risc:** LOW — toate testele trec (171/171).

---

### F0.3 Fix global exception handler — adauga traceback logging
**Status:** `[ ]`
**Fisier:** `backend/main.py:266`
**Descriere:** `logger.error(...)` nu include traceback → erori ca `'int' object has no attribute 'value'` (3x aparute azi) imposibil de diagnosticat.
**Implementare:**
```python
# Linia 266 — inlocuieste logger.error cu logger.exception:
logger.exception(f"Unhandled error [req={request_id}]: {type(exc).__name__}: {exc}")
```
**Verificare:** Provoaca o eroare intentionata si verifica ca traceback-ul apare in log.

---

---

# FAZA 1 — QUICK WINS (ROI > 7)
> Estimat: 3-4h | Sursa: /improve R4

---

### F1.1 Upgrade FastAPI 0.115.5 → latest
**Status:** `[ ]`
**Fisier:** `requirements.txt`
**Implementare:**
```bash
pip install "fastapi[standard]" --upgrade
pip show fastapi | grep Version >> requirements.txt
python -m pytest tests/ -q
```
**Ce aduce:** SSE nativ, strict content-type, Starlette compat.
**Risc:** LOW — API backward compat.

---

### F1.2 Upgrade lucide-react 0.474 → latest
**Status:** `[ ]`
**Fisier:** `frontend/package.json`
**Implementare:**
```bash
cd frontend
npm install lucide-react@latest
npm run build
```
**Ce aduce:** API stabil v1, icons noi, tree-shaking identic.
**Risc:** LOW.

---

### F1.3 Extrage magic numbers in config.py
**Status:** `[ ]`
**Fisiere:** `backend/config.py`, `backend/routers/batch.py`, `backend/routers/compare.py`, `backend/agents/orchestrator.py`
**Implementare:** Adauga in `Settings` din `config.py`:
```python
batch_max_parallel: int = 2
batch_max_cuis: int = 50
batch_timeout_hours: int = 4
compare_rate_delay_s: int = 2
dedup_cleanup_s: int = 600
```
Inlocuieste valorile hardcoded cu `settings.batch_max_parallel` etc.
**Ce aduce:** Configurare fara modificare cod.
**Risc:** LOW.

---

### F1.4 Fix N+1 query in batch summary
**Status:** `[ ]`
**Fisier:** `backend/routers/batch.py` — linia ~278
**Implementare:**
```python
# Un singur query JOIN in loc de N query-uri
rows = await db.fetch_all("""
    SELECT br.*, c.name as company_name
    FROM batch_results br
    LEFT JOIN companies c ON c.cui = br.cui
    WHERE br.batch_id = ?
""", (batch_id,))
```
**Ce aduce:** Batch 50 CUI = 1 query in loc de 50.
**Risc:** LOW.

---

### F1.5 DRY safe_json_loads utility
**Status:** `[ ]`
**Fisiere:** `backend/utils.py` (nou), `backend/routers/jobs.py`
**Implementare:** Creeaza `backend/utils.py`:
```python
import json
from typing import Any

def safe_json_loads(data: str | None, default: Any = None) -> Any:
    """Parse JSON string safely, return default on error."""
    if not data:
        return default if default is not None else {}
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}
```
Inlocuieste cele 4 locatii duplicate din `jobs.py`.
**Ce aduce:** DRY, 4 locatii → 1 functie.
**Risc:** LOW.

---

### F1.6 Fix .gitignore + .gitattributes (AUDIT R14)
**Status:** `[ ]`
**Fisiere:** `.gitignore`, `.gitattributes` (nou)
**Descriere:** node_modules/ la root neignorat, stray files, CRLF/LF warnings pe 16+ fisiere.
**Implementare:**
```
# Adauga in .gitignore:
node_modules/
99_*/
info.md
frontend/*.txt
```
```
# Creeaza .gitattributes:
* text=auto
*.py text eol=lf
*.ts text eol=lf
*.tsx text eol=lf
*.md text eol=lf
*.bat text eol=crlf
```
**Implementare cleanup:**
```bash
git rm --cached frontend/tsconfig.tsbuildinfo
```
**Risc:** LOW.

---

### F1.7 Fix Pydantic version pin + remove date-fns
**Status:** `[ ]`
**Fisiere:** `requirements.txt`, `frontend/package.json`
**Descriere:** Pydantic pinned 2.9.2 dar instalat 2.12.5. date-fns listat dar nefolosit (+35KB bundle).
**Implementare:**
```bash
# requirements.txt — update linia 4:
# pydantic==2.12.5

# frontend:
cd frontend && npm remove date-fns
npm run build  # verifica ca bundle-ul scade
```
**Risc:** LOW.

---

---

# FAZA 2 — MODERNIZARE
> Estimat: 4-5h | Sursa: /improve R4

---

### F2.1 Upgrade Pydantic 2.9.2 → 2.12.5
**Status:** `[ ]`
**Fisier:** `requirements.txt`
**Implementare:**
```bash
pip install "pydantic==2.12.5" "pydantic-settings==2.13.1"
python -m pytest tests/ -q
```
**Ce aduce:** Partial validation pentru LLM streaming, protected_namespaces relaxat.
**Nota:** Combinat cu F1.7 daca nu e facut deja.
**Risc:** LOW.

---

### F2.2 Upgrade Vite 6.2 → 7.x
**Status:** `[ ]`
**Fisier:** `frontend/package.json`
**Implementare:**
```bash
cd frontend
npm install vite@latest @vitejs/plugin-react@latest
npm run build
npm run dev  # verifica ca porneste
```
**Ce aduce:** Browser target modern, bundle mai mic.
**Risc:** LOW — verifica `vite.config.ts` nu foloseste API-uri deprecate.

---

### F2.3 Upgrade Tailwind CSS v3 → v4
**Status:** `[ ]`
**Fisier:** `frontend/package.json`, `frontend/tailwind.config.js`, `frontend/src/index.css`
**Implementare:**
```bash
cd frontend
npx @tailwindcss/upgrade  # migreaza automat 90% clase
npm run build
# verifica vizual fiecare pagina in browser
```
**Ce aduce:** Build 5-10x mai rapid (Oxide/Rust), CSS-first config.
**Risc:** MEDIUM — verifica clase custom: `dark-card`, `dark-border`, `accent-primary`.
**Nota:** Ruleaza in branch separat. Verifica fiecare pagina dupa migrare.

---

### F2.4 Split fisiere frontend >500 LOC
**Status:** `[ ]`
**Fisiere mari:**
- `ReportView.tsx` (619 LOC) → extrage `ReportSections.tsx`, `ReportDelta.tsx`
- `CompanyDetail.tsx` (551 LOC) → extrage `CompanyScoreCard.tsx`, `CompanyTimeline.tsx`
- `Dashboard.tsx` (521 LOC) → extrage `DashboardStats.tsx`, `DashboardJobs.tsx`, `DashboardHealth.tsx`
- `NewAnalysis.tsx` (500 LOC) → extrage `AnalysisWizardStep.tsx`

**Ce aduce:** Fisiere <200 LOC, testare mai usoara.
**Risc:** LOW — doar refactor structural.

---

---

# FAZA 3 — CALITATE & TESTARE
> Estimat: 2-4 zile | Sursa: /improve R4 + Audit R14

---

### F3.1 Teste frontend — api.ts + useWebSocket + Dashboard
**Status:** `[ ]`
**Fisiere noi:**
1. `frontend/src/lib/api.test.ts` — mock fetch, test fiecare metoda din api.ts
2. `frontend/src/hooks/useWebSocket.test.ts` — mock WebSocket, test reconnect
3. `frontend/src/pages/Dashboard.test.tsx` — render test, skeleton UI
4. `frontend/src/pages/NewAnalysis.test.tsx` — form validation CUI

**Framework:** Vitest + Testing Library (deja in devDependencies)
**Ce aduce:** Regresii detectate automat.
**Risc:** LOW.

---

### F3.2 Teste backend — servicii critice
**Status:** `[ ]`
**Fisiere noi (in ordine prioritate):**
1. `tests/test_job_execution.py` — pipeline complet job: create → run → save → notify
2. `tests/test_cache_service.py` — L1/L2 TTL, LRU eviction, schema version
3. `tests/test_monitoring_service.py` — alert dedup 24h, severity throttling
4. `tests/test_anaf_client.py` — mock ANAF responses, test parsing
5. `tests/test_notification.py` — Telegram + email mock send

**Ce aduce:** Coverage de la 19% → ~45%.
**Risc:** LOW.

---

### F3.3 TanStack Query pentru data fetching frontend
**Status:** `[ ]`
**Fisier:** `frontend/package.json`, `frontend/src/main.tsx`, pagini principale
**Implementare:**
```bash
cd frontend
npm install @tanstack/react-query
```
Converteste fetch-urile din: `Dashboard`, `Companies`, `ReportsList` la `useQuery`.
**Ce aduce:** Cache automat, dedup requests, stale-while-revalidate. Elimina ~100 linii de useEffect boilerplate.
**Risc:** MEDIUM — refactor semnificativ, fa dupa F2.4.
**Dependenta:** F2.4 trebuie facut inainte.

---

### F3.4 Fix pytest asyncio deprecation warning
**Status:** `[ ]`
**Fisier:** `pyproject.toml` (nou sau existent)
**Implementare:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```
**Ce aduce:** Zero deprecation warnings la teste.
**Risc:** LOW.

---

---

# FAZA 4 — FEATURES STRATEGICE
> Estimat: 3-5 zile | Sursa: /improve R4

---

### F4.1 NLQ "Ask RIS" chatbot
**Status:** `[ ]`
**Fisiere:** `backend/routers/ask.py` (nou), `frontend/src/pages/Dashboard.tsx`
**Implementare:**
- Backend: `POST /api/ask` — intent classifier (Groq/fast) + SQL mapper + response formatter
- Frontend: chat panel flotant in Dashboard, input + mesaje
**Ce aduce:** Utilizatorul poate intreba: "Care firma are cel mai mare risc?"
**Risc:** MEDIUM — calitatea raspunsurilor depinde de prompt engineering.

---

---

# FAZA 5 — AUDIT R14 HIGH (din /audit 2026-04-05)
> Estimat: 1-2 zile | Sursa: /audit standard 12 domenii

---

### F5.1 Fix N+1 queries — company detail + report listing
**Status:** `[ ]`
**Fisiere:** `backend/routers/companies.py:171-195`, `backend/routers/reports.py:45-65`

**A) Company detail — 3 queries sequentiale → parallel:**
```python
# companies.py get_company — inlocuieste cu:
reports, scores = await asyncio.gather(
    db.fetch_all("SELECT ... FROM reports WHERE company_id = ? ORDER BY created_at DESC", (company_id,)),
    db.fetch_all("SELECT ... FROM score_history WHERE company_id = ? ORDER BY recorded_at DESC LIMIT 10", (company_id,)),
)
```

**B) Report listing — Path.exists() sincron → async:**
```python
# Inlocuieste Path.exists() cu gather pe aiofiles:
import aiofiles.os
formats_list = await asyncio.gather(*[_get_formats_async(r) for r in rows])
```

**C) Report sources — serial INSERT → batch INSERT:**
```python
# job_service.py:240-253 — inlocuieste loop cu:
placeholders = ",".join(["(?, ?, ?, ?, ?, ?)"] * len(sources))
await db.execute(f"INSERT INTO report_sources ... VALUES {placeholders}", flat_values)
```
**Risc:** LOW-MEDIUM.

---

### F5.2 Fix FUNCTII_SISTEM.md outdated
**Status:** `[ ]`
**Fisier:** `FUNCTII_SISTEM.md`
**Descriere:** Data: "2026-03-22", zice "37 endpoints" (actual: 43), documenteaza doar Faza 6D.
**Implementare:** Regenerare completa cu:
- Data: 2026-04-05
- Version: 13.0 | Faze 1-20 complete
- 43 REST endpoints + 1 WebSocket
- Toate functiile din Faze 7A-20

---

### F5.3 Cache TTL optimizare
**Status:** `[ ]`
**Fisier:** `backend/services/cache_service.py:74-84`
**Implementare:**
```python
TTL_HOURS = {
    "anaf": 12,
    "onrc": 168,
    "seap_active": 24,      # era 2h → 24h
    "seap_history": 720,
    "tavily": 48,            # era 6h → 48h
    "bnr": 24,
    "ins": 720,
    "funds": 24,
}
```
**Ce aduce:** 10-20% reducere API calls pentru analize repetate.
**Risc:** LOW.

---

### F5.4 CSV export streaming (memory fix)
**Status:** `[ ]`
**Fisier:** `backend/routers/companies.py:134-168`
**Descriere:** `fetch_all()` incarca toti in memorie. La 100K companii → OOM.
**Implementare:** StreamingResponse cu generator pe chunks de 1000 randuri.
**Risc:** LOW.

---

### F5.5 Adauga index-uri composite DB
**Status:** `[ ]`
**Fisier:** `backend/migrations/` — fisier nou migration
**Implementare:**
```sql
CREATE INDEX IF NOT EXISTS idx_score_company_date
ON score_history(company_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_reports_company_created
ON reports(company_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_monitoring_company_created
ON monitoring_audit(company_id, created_at DESC);
```
**Ce aduce:** Queries timeline + score history 2-5x mai rapide.
**Risc:** LOW.

---

---

# FAZA 6 — AUDIT R14 MEDIUM (din /audit 2026-04-05)
> Estimat: 2-4 zile | Sursa: /audit standard 12 domenii

---

### F6.1 Refactor god functions — split in clase specializate
**Status:** `[ ]`
**Fisiere cu >500 LOC:**

| Fisier | LOC | Target |
|--------|-----|--------|
| `backend/agents/agent_synthesis.py` | ~1004 | Extract: `ProviderRouter`, `TokenBudgetChecker`, `SectionPromptBuilder` |
| `backend/agents/verification/scoring.py` | ~832 | Extract: `RiskScoreCalculator` cu methods per dimensiune |
| `backend/agents/agent_official.py` | ~587 | Extract: `OfficialDataFetcher`, `OfficialDataTransformer` |

**Risc:** MEDIUM — refactor major, fa pe branch separat.

---

### F6.2 Extract service layer din routers
**Status:** `[ ]`
**Descriere:** Routerele acceseaza DB direct in loc sa delege la services.
**Target principal:** `backend/routers/reports.py` — file I/O in HTTP layer.
**Implementare:** Creeaza `backend/services/report_file_service.py`:
```python
async def get_available_formats(job_id: str, row: dict) -> list[str]: ...
async def get_report_file_path(report_id: str, format: str) -> Path: ...
```
**Risc:** MEDIUM.

---

### F6.3 DRY report generator — extract _generate_format helper
**Status:** `[ ]`
**Fisier:** `backend/reports/generator.py:60-130`
**Descriere:** Acelasi pattern try-except repetat de 7 ori (PDF, DOCX, HTML, Excel, PPTX, 1-Pager, ZIP).
**Implementare:**
```python
async def _generate_format(name: str, generator_fn, *args) -> str | None:
    try:
        result = await generator_fn(*args)
        logger.info(f"[reports] {name} generated OK")
        return result
    except Exception as e:
        logger.error(f"[reports] {name} failed: {e}")
        return None
```
**Risc:** LOW.

---

### F6.4 Type hints pe functii publice
**Status:** `[ ]`
**Fisiere:** `backend/agents/agent_official.py`, `backend/agents/agent_synthesis.py`, `backend/services/cache_service.py`
**Implementare:** Adauga return type pe ~20 functii publice fara hints.
**Risc:** LOW.

---

### F6.5 CSP fara unsafe-inline pe script-src
**Status:** `[ ]`
**Fisier:** `backend/main.py:189`
**Implementare:**
```python
"script-src 'self'; "  # Remove 'unsafe-inline'
```
**Nota:** Necesita verificare ca Vite nu injecteaza inline scripts in prod build.
**Risc:** MEDIUM.

---

---

# STATUS R3 PENDING (din sesiunea anterioara)

| Item | Status | Unde e acum |
|------|--------|-------------|
| #20 NLQ chatbot | `[ ]` | F4.1 in acest document |
| #27 Frontend teste | `[ ]` | F3.1 in acest document |
| #28 Backend API client teste | `[ ]` | F3.2 in acest document |

---

---

# CHECKLIST FINAL PRE-EXECUTIE

> Bifeaza inainte de a incepe o faza:

- [ ] `python -m pytest tests/ -q` → 171/171 passed
- [ ] `cd frontend && npm run build` → zero erori
- [ ] `git status` → working directory cunoscut
- [ ] Backup DB: `cp data/ris.db data/ris_backup_$(date +%Y%m%d).db`

---

# CHECKLIST FINAL POST-EXECUTIE (per faza)

> Bifeaza dupa finalizarea fiecarei faze:

- [ ] Teste trec: `python -m pytest tests/ -q`
- [ ] Frontend build OK: `cd frontend && npm run build`
- [ ] Backend porneste: `python -m backend.main`
- [ ] Git commit cu mesaj clar: `git commit -m "feat: FX.Y descriere"`
- [ ] Git push: `git push origin main`

---

# SUMAR FISIERE DE TINUT SINCRONIZATE

| Fisier | Rol | Ultima actualizare |
|--------|-----|--------------------|
| `99_Plan_vs_Audit/RECOMANDARI_IMBUNATATIRI_R4.md` | **Acest fisier** — plan executie R4 + Audit R14 | 2026-04-05 |
| `99_Plan_vs_Audit/RECOMANDARI_IMBUNATATIRI_R3.md` | R3 — 42 items (39 implementate, 3 P3 pending) | 2026-04-04 |
| `CLAUDE.md` | Status faze, decizii tehnice confirmate | 2026-04-05 |
| `FUNCTII_SISTEM.md` | Inventar complet functionalitati | OUTDATED — de regenerat (F5.2) |
| `TODO_ROLAND.md` | Items de facut | de verificat |
| `AUDIT_REPORT.md` | Raport audit complet | 2026-03-20 (vechi) |

---

*Generat automat dupa /audit standard 12 domenii — 2026-04-05*
*Scor curent: 82/100 | Target: 90/100 dupa Faza 0-5*
