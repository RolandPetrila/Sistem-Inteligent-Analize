# TODO R14 — Ce A Rămas De Făcut
**Generat:** 2026-04-06 | **Autor:** Claude Code | **Context:** Post-implementare Faza 0-6 parțial
**Referință:** `99_Plan_vs_Audit/RECOMANDARI_IMBUNATATIRI_R4.md`

---

## SECȚIUNEA 1 — TESTARE MANUALĂ (ce AI a implementat azi)

> Verifică FIECARE item de mai jos înainte de a continua implementarea.
> Durata estimată: **30-45 minute**.

---

### ✅ TEST 1 — F0.1: Gemini key NU apare în log-uri

**Fișier modificat:** `backend/agents/agent_synthesis.py`

**Pași de verificare:**
1. Pornește backend: dublu-click `START_RIS.vbs`
2. Fă o analiză CUI (orice firmă din interfață)
3. Deschide fișierul `logs/ris_runtime.log`
4. Caută textul `key=` — **NU trebuie să apară**
5. Caută textul `REDACTED` — **trebuie să apară** dacă Gemini e apelat

**Comandă rapidă (PowerShell):**
```powershell
Select-String -Path "logs\ris_runtime.log" -Pattern "key=AIza"
# Rezultat așteptat: NICIUN rezultat (fișier clean)
```

**Dacă găsești `key=AIza...`:** Bug nerezolvat — raportează în ISSUES.md.

---

### ✅ TEST 2 — F0.3: Traceback complet în log la erori

**Fișier modificat:** `backend/main.py` linia 266

**Pași de verificare:**
1. Cu backend pornit, accesează: `http://localhost:8001/api/jobs/CUI-INVALID-000`
2. Deschide `logs/ris_runtime.log`
3. Caută eroarea — **trebuie să apară full traceback**, nu doar o linie

**Alternativă:** Orice eroare 500 în viitor va afișa traceback complet în log.
Comportament corect: `ERROR | backend.main | Unhandled error [req=xyz]: ... Traceback (most recent call last): ...`

---

### ✅ TEST 3 — F1.3: Magic numbers configurabile

**Fișier modificat:** `backend/config.py`

**Verificare automată:**
```bash
cd C:\Proiecte\Sistem_Inteligent_Analize
python -c "from backend.config import settings; print('batch_max_parallel:', settings.batch_max_parallel); print('batch_max_cuis:', settings.batch_max_cuis); print('dedup_cleanup_s:', settings.dedup_cleanup_s)"
```
**Rezultat așteptat:**
```
batch_max_parallel: 2
batch_max_cuis: 50
dedup_cleanup_s: 600
```

**Test funcțional:** Încearcă să uploadezi un CSV cu 51 CUI-uri în pagina Batch Analysis.
Trebuie să primești eroarea: `"Maximum 50 CUI-uri per batch"`.

---

### ✅ TEST 4 — F1.5: safe_json_loads funcționează

**Fișier nou:** `backend/utils.py`

**Verificare automată:**
```bash
python -c "
from backend.utils import safe_json_loads
print(safe_json_loads(None))          # {}
print(safe_json_loads(''))            # {}
print(safe_json_loads('invalid'))     # {}
print(safe_json_loads('{\"a\": 1}')) # {'a': 1}
print('OK')
"
```
**Rezultat așteptat:**
```
{}
{}
{}
{'a': 1}
OK
```

---

### ✅ TEST 5 — F1.6: .gitignore corect

**Verificare:**
```bash
cd C:\Proiecte\Sistem_Inteligent_Analize
git status --short
```
**Rezultat așteptat:** Fișierele `node_modules/`, `info.md`, `CheckPoint/`, `frontend/*.txt` **NU apar** în `git status`.
Dacă apar, .gitignore nu funcționează corect.

---

### ✅ TEST 6 — F1.7 + F2.1: Pydantic versiune corectă

**Verificare:**
```bash
python -c "import pydantic; print(pydantic.__version__)"
# Rezultat așteptat: 2.12.5
```

**Verificare requirements.txt:**
```bash
grep pydantic requirements.txt
# Rezultat așteptat: pydantic==2.12.5
```

---

### ✅ TEST 7 — F2.1: date-fns eliminat din bundle

**Verificare:**
```bash
cd C:\Proiecte\Sistem_Inteligent_Analize\frontend
grep "date-fns" package.json
# Rezultat așteptat: NICIO linie cu date-fns
```

**Verificare bundle size** (frontend trebuie rebuilt mai mic):
```bash
npm run build 2>&1 | grep "index-"
# Era: ~122 kB gzip. Acum ar trebui mai mic (date-fns era ~35KB).
```

---

### ✅ TEST 8 — F3.4: pytest fără deprecation warnings

**Verificare:**
```bash
cd C:\Proiecte\Sistem_Inteligent_Analize
python -m pytest tests/ -q 2>&1 | grep -i "deprecat\|warning\|passed"
```
**Rezultat așteptat:**
```
171 passed in XX.XXs
```
**NU trebuie să apară:** `DeprecationWarning: asyncio_mode` sau `PytestUnraisableExceptionWarning`

---

### ✅ TEST 9 — F5.3: Cache TTL actualizat

**Verificare:**
```bash
python -c "
from backend.services.cache_service import TTL_HOURS
print('seap_active:', TTL_HOURS['seap_active'], '(expected 24)')
print('tavily:', TTL_HOURS['tavily'], '(expected 48)')
"
```
**Rezultat așteptat:**
```
seap_active: 24 (expected 24)
tavily: 48 (expected 48)
```

---

### ✅ TEST 10 — F5.5: DB indexes create la startup

**Pași:**
1. Pornește backend (dacă nu e pornit)
2. Verifică în log că migration 006 a rulat:
```powershell
Select-String -Path "logs\ris_runtime.log" -Pattern "006_performance"
```
**Rezultat așteptat:** `Running migration: 006_performance_indexes.sql`

**Alternativ — verificare directă DB:**
```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/ris.db')
idxs = conn.execute(\"SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'\").fetchall()
for i in idxs: print(i[0])
"
```
**Trebuie să apară:** `idx_score_company_date`, `idx_reports_company_created`, `idx_monitoring_company_created`

---

### ✅ TEST 11 — F5.1: Company detail mai rapid

**Vizual:**
1. Deschide pagina unei companii analizate: `http://localhost:5173/company/[id]`
2. Pagina trebuie să se încarce fără erori
3. Sunt vizibile: rapoartele anterioare + graficul score history

**Test de performanță (opțional):**
Compară timpul de încărcare înainte vs acum. Ar trebui ~2x mai rapid dacă ai zeci de rapoarte per firmă.

---

### ✅ TEST 12 — F6.3: Report generator funcționează

**Test complet:**
1. Fă o analiză completă dintr-o firmă
2. Verifică că se generează TOATE formatele: PDF, DOCX, HTML, Excel, PPTX, 1-Pager, ZIP
3. În `logs/ris_runtime.log` caută `[reports]`:
```powershell
Select-String -Path "logs\ris_runtime.log" -Pattern "\[reports\]"
```
**Trebuie să apară:** `[reports] PDF generated OK`, `[reports] DOCX generated OK`, etc.
**NU trebuie:** `[reports] PDF generation failed`

---

### ✅ TEST 13 — F6.5: CSP header actualizat

**Verificare header:**
```bash
curl -I http://localhost:8001/api/stats 2>/dev/null | grep -i "content-security"
```
sau în browser DevTools (F12 → Network → orice request → Response Headers):
**Rezultat așteptat:** `Content-Security-Policy: ... script-src 'self'; ...`
**NU trebuie să apară:** `'unsafe-inline'` în script-src

---

## SECȚIUNEA 2 — IMPLEMENTARE RĂMASĂ (ordered by priority)

---

## 🔴 PRIORITATE ÎNALTĂ — Implementeaza în următoarea sesiune

---

### F1.1 — Upgrade FastAPI 0.115.5 → latest
**Efort:** 30 minute | **Risc:** LOW

**Comandă:**
```bash
cd C:\Proiecte\Sistem_Inteligent_Analize
pip install "fastapi[standard]" --upgrade
pip show fastapi | grep Version
# Actualizează requirements.txt cu versiunea nouă
python -m pytest tests/ -q
```

**Test după implementare:**
```bash
python -c "import fastapi; print(fastapi.__version__)"
python -m pytest tests/ -q
# Toate 171 teste trebuie să treacă
```

**Risc cunoscut:** Niciun breaking change așteptat — FastAPI are backward compat excelent.

---

### F1.2 — Upgrade lucide-react 0.474 → latest
**Efort:** 15 minute | **Risc:** LOW

**Comandă:**
```bash
cd C:\Proiecte\Sistem_Inteligent_Analize\frontend
npm install lucide-react@latest
npm run build
```

**Test după implementare:**
1. `npm run build` → zero erori
2. Deschide frontend în browser
3. Verifică că icoanele apar corect pe toate paginile (sidebar, butoane, alerte)

---

### F5.2 — Update FUNCTII_SISTEM.md
**Efort:** 1-2h | **Risc:** ZERO (doar documentație)

**Ce trebuie actualizat în `FUNCTII_SISTEM.md`:**
- Data: `2026-03-22` → `2026-04-06`
- Version: `8.0` → `14.0`
- Endpoints: `37 endpoints` → `43 REST endpoints + 1 WebSocket`
- Adaugă secțiunile: Faze 7A → 21 (R14)
- Funcții noi: notifications, favorites, circuit breaker, FTS5 search, GlobalSearch, AI tools F7

**Comandă rapidă de verificare:**
```bash
grep -c "POST\|GET\|PUT\|DELETE" backend/routers/*.py
# Numără endpoint-urile actuale
```

---

### F5.4 — CSV export streaming (memory fix)
**Efort:** 1h | **Risc:** LOW

**Fișier:** `backend/routers/companies.py:134-168`

**Implementare:**
```python
# Înlocuiește fetch_all() + BytesIO cu StreamingResponse generator:
from fastapi.responses import StreamingResponse
import csv, io

async def _csv_stream_generator():
    """Generează CSV în chunks de 1000 rânduri."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["CUI", "Denumire", "CAEN", "Scor", "Data"])
    yield output.getvalue(); output.truncate(0); output.seek(0)
    
    offset = 0
    while True:
        rows = await db.fetch_all(
            "SELECT * FROM companies ORDER BY last_analyzed_at DESC LIMIT 1000 OFFSET ?",
            (offset,)
        )
        if not rows: break
        for row in rows:
            writer.writerow([row["cui"], row["name"], row.get("caen",""), ...])
        yield output.getvalue(); output.truncate(0); output.seek(0)
        offset += 1000

return StreamingResponse(
    _csv_stream_generator(),
    media_type="text/csv",
    headers={"Content-Disposition": "attachment; filename=companii_ris.csv"}
)
```

**Test după implementare:**
1. Du-te la pagina Companies → Export CSV
2. Descarcă fișierul
3. Verifică că CSV-ul se descarcă corect și are toate companiile

---

### F7.4 — Brave Search (COD DEJA IMPLEMENTAT — doar key lipsește)
**Efort:** 5 minute | **Risc:** ZERO

**Obținere key:**
1. Accesează: `https://api.search.brave.com/register`
2. Sign Up cu email (fără card)
3. Alege planul "Free" (2000 req/lună)
4. Dashboard → "API Keys" → copiaza cheia
5. Adaugă în `.env`:
```
BRAVE_API_KEY=BSA...
```
6. Restart backend

**Test după key:**
1. Fă o analiză completă
2. În raportul HTML, secțiunea "Reputație" trebuie să conțină date din Brave Search
3. Log: `Select-String logs\ris_runtime.log -Pattern "brave"` → trebuie să apară calls Brave

---

### F7.2 — DeepSeek R1 (COD DEJA IMPLEMENTAT — doar key lipsește)
**Efort:** 10 minute | **Risc:** LOW

**Obținere key:**
1. Accesează: `https://platform.deepseek.com/`
2. Sign Up cu email → verifică email
3. Dashboard → "API Keys" → "Create new API key" → copiaza
4. Adaugă în `.env`:
```
DEEPSEEK_API_KEY=sk-...
```
5. Restart backend

**Bonus:** $2 credit gratuit la cont nou (suficient pentru ~3000 analize cu R1).

**Test după key:**
1. Fă o analiză — sectiunea `analiza_financiara` va folosi DeepSeek R1 când Claude/Groq eșuează
2. Log: `Select-String logs\ris_runtime.log -Pattern "deepseek"` → apeluri confirmate

---

## 🟡 PRIORITATE MEDIE — Planifică în 1-2 săptămâni

---

### F2.2 — Upgrade Vite 6.2 → 7.x
**Efort:** 1-2h | **Risc:** MEDIUM

**IMPORTANT:** Fă pe branch separat!
```bash
git checkout -b upgrade/vite7
cd frontend
npm install vite@latest @vitejs/plugin-react@latest
```

**Verificare `vite.config.ts` — caută API-uri deprecate:**
```bash
grep -n "createFilter\|transformIndexHtml\|resolveId" frontend/vite.config.ts
```

**Build + test:**
```bash
npm run build
npm run dev
# Testează manual fiecare pagină în browser
```

**Paginile de verificat:**
- [ ] Dashboard
- [ ] New Analysis (wizard 4 pași)
- [ ] Report View (cu raport existent)
- [ ] Companies
- [ ] Batch Analysis
- [ ] Compare
- [ ] Settings
- [ ] Monitoring
- [ ] Company Detail

**Merge doar dacă TOATE paginile funcționează.**

---

### F2.3 — Upgrade Tailwind CSS v3 → v4
**Efort:** 4-8h | **Risc:** MEDIUM

**IMPORTANT:** Fă pe branch separat DUPĂ F2.2!
```bash
git checkout -b upgrade/tailwind4
cd frontend
npx @tailwindcss/upgrade
```

**Clase custom de verificat manual (pot fi migrate greșit):**
```bash
grep -r "dark-card\|dark-border\|accent-primary\|bg-\[#\|text-\[#" frontend/src/ --include="*.tsx"
```

**Verificare build:**
```bash
npm run build
# Verifică că zero erori de clase necunoscute
```

**Verificare vizuală obligatorie per pagină:**
- [ ] Dashboard — carduri, grafice, sidebar
- [ ] New Analysis — wizard steps, CUI validator
- [ ] Report View — tabele, secțiuni, delta
- [ ] Companies — tabel sortabil, filtre
- [ ] Compare — side-by-side layout
- [ ] Settings — formulare, toggle-uri
- [ ] Monitoring — alertele colorate (RED/YELLOW/GREEN)
- [ ] Company Detail — score card, timeline

**Merge DOAR dacă totul arată identic cu înainte.**

---

### F2.4 — Split fișiere frontend >500 LOC
**Efort:** 4-6h | **Risc:** LOW

**Fișiere de split:**

| Fișier | LOC | Extrage în |
|--------|-----|-----------|
| `ReportView.tsx` | ~619 | `ReportSections.tsx` + `ReportDelta.tsx` |
| `CompanyDetail.tsx` | ~551 | `CompanyScoreCard.tsx` + `CompanyTimeline.tsx` |
| `Dashboard.tsx` | ~521 | `DashboardStats.tsx` + `DashboardJobs.tsx` + `DashboardHealth.tsx` |
| `NewAnalysis.tsx` | ~500 | `AnalysisWizardStep.tsx` |

**Test după fiecare split:**
```bash
cd frontend && npm run build
# Zero erori TypeScript
```
**Test vizual:** Fiecare pagină splitată trebuie să arate și să funcționeze IDENTIC.

---

### F6.1 — Refactor god functions (split fișiere >500 LOC backend)
**Efort:** 2-4 zile | **Risc:** MEDIUM — fă pe branch separat

**Target:**

| Fișier | LOC | Extrage clasele |
|--------|-----|----------------|
| `backend/agents/agent_synthesis.py` | ~1004 | `ProviderRouter`, `TokenBudgetChecker`, `SectionPromptBuilder` |
| `backend/agents/verification/scoring.py` | ~832 | `RiskScoreCalculator` cu methods per dimensiune |
| `backend/agents/agent_official.py` | ~587 | `OfficialDataFetcher`, `OfficialDataTransformer` |

**Regula:** Rulează `python -m pytest tests/ -q` după FIECARE fișier split.
**171/171 trebuie să treacă mereu.**

---

### F6.2 — Service layer din routers
**Efort:** 4-6h | **Risc:** MEDIUM

**Fișier nou de creat:** `backend/services/report_file_service.py`
```python
async def get_available_formats(job_id: str, row: dict) -> list[str]: ...
async def get_report_file_path(report_id: str, format: str) -> Path: ...
```

**Extrage din:** `backend/routers/reports.py` — file I/O direct în HTTP layer

**Test:** `python -m pytest tests/ -q` → 171/171

---

### F6.4 — Type hints pe funcții publice
**Efort:** 2-3h | **Risc:** ZERO

**Fișiere de actualizat:**
- `backend/agents/agent_official.py` — ~8 funcții fără return type
- `backend/agents/agent_synthesis.py` — ~6 funcții fără return type
- `backend/services/cache_service.py` — ~6 funcții fără return type

**Verificare cu mypy (opțional):**
```bash
pip install mypy
mypy backend/agents/agent_official.py --ignore-missing-imports
```

---

## 🟢 PRIORITATE STRATEGICĂ — Planifică în 2-4 săptămâni

---

### F3.1 — Teste frontend (Vitest + Testing Library)
**Efort:** 2-4 zile | **Risc:** LOW

**Fișiere de creat:**

**1. `frontend/src/lib/api.test.ts`**
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('api.ts', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  
  it('listJobs returns array', async () => {
    // mock fetch → { jobs: [] }
  })
  
  it('createJob sends correct payload', async () => {
    // verify fetch called with POST + body
  })
  
  it('handles 429 Too Many Requests', async () => {
    // mock fetch → 429 → expect ApiError thrown
  })
})
```

**2. `frontend/src/hooks/useWebSocket.test.ts`**
```typescript
describe('useWebSocket', () => {
  it('connects on mount', () => { ... })
  it('reconnects on close', () => { ... })
  it('handles ping/pong', () => { ... })
})
```

**3. `frontend/src/pages/Dashboard.test.tsx`**
```typescript
describe('Dashboard', () => {
  it('renders skeleton while loading', () => { ... })
  it('shows stats after load', () => { ... })
})
```

**4. `frontend/src/pages/NewAnalysis.test.tsx`**
```typescript
describe('NewAnalysis', () => {
  it('validates CUI format', () => { ... })
  it('shows error on invalid CUI', () => { ... })
  it('wizard step 1 → 2 on valid CUI', () => { ... })
})
```

**Rulare:**
```bash
cd frontend && npm run test
# Target: 40+ teste vitest (de la 11 acum)
```

---

### F3.2 — Teste backend servicii critice
**Efort:** 3-5 zile | **Risc:** LOW

**Fișiere de creat (în ordine prioritate):**

**1. `tests/test_job_execution.py`**
```python
# Pipeline complet: create → run → save → notify
async def test_job_create_and_run():
    # Mock ANAF, mock synthesis
    # Verifică că job trece din PENDING → RUNNING → DONE
    
async def test_job_invalid_cui():
    # CUI invalid → FAILED imediat
    
async def test_job_websocket_progress():
    # WebSocket primește mesaje: agent_start, agent_complete, done
```

**2. `tests/test_cache_service.py`**
```python
async def test_cache_set_get():
    await cache_service.set("test_key", {"data": 1}, "anaf")
    result = await cache_service.get("test_key", "anaf")
    assert result == {"data": 1}
    
async def test_cache_ttl_expired():
    # Setează cu TTL 0 → verifică că get returnează None
    
async def test_cache_lru_eviction():
    # Umple cache-ul > 100MB → verifică că vechile intrări sunt evictate
    
async def test_cache_schema_version():
    # Schimbă schema version → cache vechi invalid
```

**3. `tests/test_monitoring_service.py`**
```python
async def test_alert_dedup_24h():
    # Trimite aceeași alertă de 2 ori în 24h → a doua e ignorată
    
async def test_severity_throttle():
    # RED alert → trimis. Duplicate RED în 1h → nu retrimis.
    
async def test_zombie_detection():
    # Firmă cu CA 0, 0 angajați, inactivă ANAF → marcată zombie
```

**4. `tests/test_anaf_client.py`**
```python
async def test_anaf_found():
    # Mock response ANAF cu firmă validă → parsare corectă
    
async def test_anaf_not_found():
    # 404 HTTP cu JSON notFound → handled corect (nu raise)
    
async def test_anaf_rate_limit():
    # 429 → retry cu delay → succes la retry 2
```

**5. `tests/test_notification.py`**
```python
async def test_telegram_send_mock():
    # Mock httpx → verifică payload corect
    
async def test_email_send_mock():
    # Mock aiosmtplib → verifică headers email
    
async def test_notification_severity_filter():
    # Alertă GREEN nu trimite notificare
```

**Target coverage:** 19% → 45% (de la 12/90 fișiere la ~40/90)

**Rulare:**
```bash
python -m pytest tests/ -q --cov=backend --cov-report=term-missing
```

---

### F3.3 — TanStack Query pentru data fetching
**Efort:** 3-5 zile | **Risc:** MEDIUM
**DEPENDENȚĂ:** F2.4 (split fișiere) trebuie făcut ÎNAINTE.

**Instalare:**
```bash
cd frontend && npm install @tanstack/react-query @tanstack/react-query-devtools
```

**Configurare în `frontend/src/main.tsx`:**
```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
const queryClient = new QueryClient()
// Wrap App cu <QueryClientProvider client={queryClient}>
```

**Pagini de convertit (în ordine):**
1. `Dashboard.tsx` — `useQuery(['stats'], api.getStats)`
2. `Companies.tsx` — `useQuery(['companies'], api.listCompanies)`
3. `ReportsList.tsx` — `useQuery(['reports'], api.listReports)`

**Ce se elimină:** ~100 linii de `useEffect + useState + fetch` boilerplate

**Test după fiecare conversie:**
```bash
npm run build && npm run dev
# Verifică că datele se încarcă corect pe fiecare pagină
```

---

### F4.1 — NLQ "Ask RIS" Chatbot
**Efort:** 3-5 zile | **Risc:** MEDIUM

**Backend — `backend/routers/ask.py` (fișier nou):**
```python
from fastapi import APIRouter
from pydantic import BaseModel
from backend.database import db

router = APIRouter()

class AskRequest(BaseModel):
    question: str  # "Care firmă are cel mai mare risc?"
    
@router.post("/ask")
async def ask_ris(req: AskRequest):
    # 1. Intent classifier (Groq fast) → SQL intent
    # 2. SQL mapper → query DB
    # 3. Response formatter → text natural
    # 4. Return { answer: str, data: list, sql_used: str }
    ...
```

**Intenții de suportat:**
- "Care firmă are cel mai mare/mic risc?" → ORDER BY numeric_score
- "Câte firme am analizat?" → COUNT companies
- "Firme din domeniul [X]?" → WHERE caen LIKE
- "Ultimele analize" → ORDER BY last_analyzed_at DESC
- "Firme cu scor roșu" → WHERE risk_score = 'Rosu'

**Frontend — panel flotant în `Dashboard.tsx`:**
```typescript
// Buton "Ask RIS" în colțul dreapta-jos
// Click → panel cu input text + messages
// Enter → POST /api/ask → afișează răspunsul
```

**Test:**
1. Scrie: "Care firmă are cel mai mare risc?"
2. Trebuie să primești un răspuns coerent în română
3. Scrie: "Câte analize am făcut?"
4. Trebuie să primești numărul corect

---

### F7.3 — Cohere Embed + Semantic Search
**Efort:** 2-3 zile | **Risc:** MEDIUM (necesită migrare DB)

**Obținere key:**
1. Accesează: `https://dashboard.cohere.com/`
2. Sign Up cu email sau Google
3. Dashboard → stânga jos → "API Keys" → "New Trial key"
4. Adaugă în `.env`: `COHERE_API_KEY=...`

**Instalare:**
```bash
pip install cohere numpy
# Adaugă în requirements.txt
```

**Migration DB (fișier nou `backend/migrations/007_embeddings.sql`):**
```sql
ALTER TABLE companies ADD COLUMN embedding BLOB;
```

**Implementare în `backend/services/semantic_service.py`** — conform planului din R4.

**Test:**
1. Fă o analiză → embedding calculat automat
2. Pagina CompanyDetail → "Firme similare" → rezultate semantice (nu doar CAEN identic)
3. Caută "constructii drumuri" → găsește firme CAEN 4211/4212

---

### F7.5 — Mistral OCR (upload documente scanate)
**Efort:** 2-3h | **Risc:** LOW

**IMPORTANT:** Dacă ai deja `MISTRAL_API_KEY` în `.env` — funcționează direct, nu trebuie key nou!

**Implementare:** `backend/routers/documents.py` (cod complet în R4.md F7.5)

**Adaugă router în `backend/main.py`:**
```python
from backend.routers.documents import router as documents_router
app.include_router(documents_router, tags=["documents"])
```

**Test:**
1. Upload un PDF scanat (bilant, act constitutiv)
2. `POST /api/documents/ocr` → JSON cu textul extras
3. Textul trebuie să fie lizibil în română

---

### F7.6 — OpenRouter Gateway (COD DEJA IMPLEMENTAT)
**Efort:** 5 minute | **Risc:** LOW

**Obținere key:**
1. Accesează: `https://openrouter.ai/`
2. Sign In → "Keys" → "Create Key" → copiaza
3. Adaugă în `.env`: `OPENROUTER_API_KEY=sk-or-v1-...`
4. Restart backend

**Bonus:** $1 credit gratuit la cont nou. Modele gratuite disponibile: DeepSeek R1, Llama 4, Qwen 3.

---

### F7.7 — xAI Grok (COD DEJA IMPLEMENTAT)
**Efort:** 5 minute (dacă ai key) | **Risc:** LOW — verifică TOS data sharing

**Obținere key:**
1. Accesează: `https://console.x.ai/`
2. Necesită cont X (Twitter)
3. Dashboard → "API Keys" → "Create key"
4. Adaugă în `.env`: `XAI_API_KEY=xai-...`

**NOTA:** Verifică că ești de acord cu termenii privind datele înainte de utilizare.

---

## SECȚIUNEA 3 — CHECKLIST PRE-FIECARE SESIUNE

> Rulează acestea ÎNAINTE de a implementa orice item nou.

```bash
# 1. Teste backend
python -m pytest tests/ -q
# Așteptat: 171 passed

# 2. Build frontend
cd frontend && npm run build
# Așteptat: ✓ built in XX.XXs, zero erori

# 3. Git status curat
git status --short
# Așteptat: niciun fișier modificat necomis

# 4. Backup DB (înainte de orice migrare)
copy data\ris.db data\ris_backup_$(date +%Y%m%d).db
```

---

## SECȚIUNEA 4 — ORDINE DE IMPLEMENTARE RECOMANDATĂ

```
SĂPTĂMÂNA 1:
  Ziua 1 (2h):  F1.1 + F1.2 + F7.4 (Brave key) + F7.2 (DeepSeek key)
  Ziua 2 (3h):  F5.2 (FUNCTII_SISTEM.md) + F5.4 (CSV streaming)
  Ziua 3 (4h):  F6.4 (type hints) + F2.2 (Vite 7 — pe branch)
  
SĂPTĂMÂNA 2:
  Ziua 1 (8h):  F2.3 (Tailwind v4 — pe branch, verificat vizual)
  Ziua 2-3:     F2.4 (split fișiere frontend)
  Ziua 4-5:     F3.1 (teste frontend — 40+ vitest)

SĂPTĂMÂNA 3:
  Ziua 1-3:     F3.2 (teste backend — +26 teste noi)
  Ziua 4-5:     F3.3 (TanStack Query)

SĂPTĂMÂNA 4:
  Ziua 1-2:     F4.1 (NLQ chatbot)
  Ziua 3-5:     F6.1 (god function refactoring — branch separat)

VIITOR (when ready):
  F7.3 Cohere semantic search
  F7.5 Mistral OCR
  F6.2 Service layer extraction
```

---

## SECȚIUNEA 5 — TRACKER STATUS

| Item | Prioritate | Efort | Status | Responsabil |
|------|-----------|-------|--------|-------------|
| F1.1 FastAPI upgrade | ÎNALT | 30min | ⬜ TODO | Claude/Tu |
| F1.2 lucide-react upgrade | ÎNALT | 15min | ⬜ TODO | Claude/Tu |
| F5.2 FUNCTII_SISTEM.md | ÎNALT | 2h | ⬜ TODO | Claude |
| F5.4 CSV streaming | ÎNALT | 1h | ⬜ TODO | Claude |
| F7.4 Brave Search key | ÎNALT | 5min | ⬜ TODO (Tu obții key) | Tu |
| F7.2 DeepSeek key | ÎNALT | 10min | ⬜ TODO (Tu obții key) | Tu |
| F2.2 Vite 7 upgrade | MEDIU | 2h | ⬜ TODO | Claude |
| F2.3 Tailwind v4 | MEDIU | 8h | ⬜ TODO | Claude |
| F2.4 Split frontend files | MEDIU | 6h | ⬜ TODO | Claude |
| F6.4 Type hints | MEDIU | 3h | ⬜ TODO | Claude |
| F3.1 Teste frontend | MEDIU | 4z | ⬜ TODO | Claude |
| F3.2 Teste backend | MEDIU | 5z | ⬜ TODO | Claude |
| F3.3 TanStack Query | MEDIU | 5z | ⬜ TODO | Claude |
| F4.1 NLQ chatbot | STRATEGIC | 5z | ⬜ TODO | Claude |
| F6.1 God function refactor | STRATEGIC | 4z | ⬜ TODO | Claude |
| F6.2 Service layer | STRATEGIC | 6h | ⬜ TODO | Claude |
| F7.3 Cohere semantic | VIITOR | 3z | ⬜ TODO | Claude |
| F7.5 Mistral OCR | VIITOR | 3h | ⬜ TODO | Claude |
| F7.6 OpenRouter key | OPȚIONAL | 5min | ⬜ TODO (Tu obții key) | Tu |
| F7.7 Grok key | OPȚIONAL | 5min | ⬜ TODO (Tu obții key, dacă vrei) | Tu |

---

## SECȚIUNEA 6 — SCORE AUDIT ESTIMAT POST-IMPLEMENTARE

| Domeniu | Acum (R14) | Estimat după toate TODO-urile |
|---------|-----------|-------------------------------|
| Calitate cod | 7/10 | 9/10 (F6.1, F6.3✅, F6.4, F2.4) |
| Securitate | 7/10 | 9/10 (F0.1✅, F6.5✅, F7.x) |
| Corectitudine | 8/10 | 9/10 |
| Arhitectura | 8/10 | 9/10 (F6.2, service layer) |
| Documentatie | 7/10 | 9/10 (F5.2) |
| Git status | 4/10 | 9/10 (F0.2✅, F1.6✅) |
| Testare | 6/10 | 8/10 (F3.1, F3.2, F3.4✅) |
| Dependente | 7/10 | 9/10 (F1.1, F1.2, F2.1✅, F2.2, F2.3) |
| **TOTAL estimat** | **82/100** | **~93/100** |

---

*Fișier generat automat de Claude Code. Actualizează coloana "Status" pe măsură ce implementezi.*
*La sesiunea următoare: `/status` pentru quick overview, `/audit` după toate implementările.*
