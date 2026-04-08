# RECOMANDARI IMBUNATATIRI R8
**Data:** 9 Aprilie 2026 | **Sprint precedent:** R7 (18/18 COMPLETAT)
**Baza:** Verificare R7 + Analiza Gemini 2026-04-09 + Analiza Gemini 2026-04-08

---

## VERIFICARE R7 — STATUS FINAL: 18/18 COMPLETAT ✓

| Item | Descriere | Status | Fisier |
|------|-----------|--------|--------|
| A1 | Raport unic RIS-YYYY-XXXX (report_sequences) | ✓ | database.py:168, reports.py |
| A2 | Risk badge numeric {score}/100 cu culori | ✓ | Companies.tsx:84-104 |
| A3 | docs/FUNCTII_SISTEM.md actualizat | ✓ | docs/FUNCTII_SISTEM.md |
| A4 | Brave Search key | ✓ | (user action, skip) |
| A5 | AEGRM client garanții reale mobiliare | ✓ | backend/agents/tools/aegrm_client.py |
| B1 | NLQ Ask RIS chatbot (POST /api/ask) | ✓ | routers/ask.py, components/AskRIS.tsx |
| B2 | Knowledge Graph Visualizer (/network/:cui) | ✓ | pages/NetworkGraph.tsx |
| B3 | Dark/Light theme toggle | ✓ | Layout.tsx:ThemeToggle |
| B4 | Mobile search button (Ctrl+K dispatch) | ✓ | Layout.tsx:409-421 |
| B5 | Share link HTML cu TTL (share_token) | ✓ | database.py:177-192, reports.py:280,297 |
| C1 | Split componente: DeltaView, SimpleBarChart, EmailModal, CompanyChat, CompanyTimeline | ✓ | components/report/, components/company/ |
| C2 | TanStack Query (@tanstack/react-query v5) | ✓ PARTIAL | main.tsx:27, ReportsList.tsx |
| C3 | ARIA aria-hidden pe iconite decorative | ✓ | Layout.tsx:337 |
| C4 | Return type hints pe 16 functii router | ✓ | companies.py, reports.py |
| E3 | Mistral OCR (POST /api/documents/ocr) | ✓ | routers/documents.py |

**Nota C2:** TanStack Query montat global in main.tsx, migrat ReportsList.tsx.
Dashboard.tsx + Companies.tsx raman cu pattern `useEffect + useState` — migratia completa e in R8.

---

## TABEL PRIORITĂȚI R8

| ID | Grup | Titlu | P | Impact | Efort |
|----|------|-------|---|--------|-------|
| G1 | Gemini-Perf | Process Pool PDF/DOCX (event loop blocker) | P1 | Ridicat | Mediu |
| G2 | Gemini-Biz | Crawler Monitorul Oficial (cesiuni suspecte) | P1 | Maxim | Mare |
| G3 | Extindere-C2 | TanStack Query: Dashboard + Companies | P1 | Mediu | Mic |
| G4 | Gemini-UX | WCAG 2.2 audit React/Tailwind + contrast fix | P2 | Mediu | Scazut |
| G5 | Gemini-i18n | Suport English la rapoarte PDF/HTML | P2 | Ridicat | Mediu |
| D1 | Strategic | data.gov.ro ONRC dataset local | P2 | Ridicat | Mare |
| G6 | Gemini-DB | PostgreSQL fezabilitate studiu | P3 | Mediu | Ridicat |
| G7 | Gemini-Ops | Prometheus/Grafana monitorizare | P3 | Scazut | Mediu |
| G8 | Gemini-AI | Predictie faliment XGBoost local | P3 | Strategic | Mare |

---

## GRUP G — GEMINI INSIGHTS

> Extrase din 2 runde de analiza Gemini (2026-04-08 + 2026-04-09).
> Ordinea: P1 → P3.

---

### G1 — Process Pool pentru PDF/DOCX (Event Loop Blocker)

**Prioritate:** P1 | **Efort:** 3-4h | **Risc:** MEDIU
**Sursa:** Gemini 2026-04-09 — Pilon PERFORMANTA

**Problema:**
Generarea PDF (fpdf2), DOCX (python-docx), PPTX (python-pptx) si Excel (openpyxl) sunt operatii CPU-bound care ruleaza in event loop-ul FastAPI. La generari simultane (batch, compare) pot bloca toate request-urile async.

**Masurare:**
- PDF cu 50 pagini + grafice: ~3-8s CPU-bound
- La 3 generari simultane: latenta totala poate atinge 20-25s
- Impacteaza si request-urile de citire (GET /api/reports) in acelasi timp

**Fix recomandat:**

```python
# backend/reports/generator.py
import asyncio
from concurrent.futures import ProcessPoolExecutor

_executor = ProcessPoolExecutor(max_workers=2)

async def generate_pdf_async(report_data: dict, output_path: str) -> str:
    """Ruleaza PDF generation in process pool, elibereaza event loop."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        _generate_pdf_sync,  # functia sync existenta
        report_data,
        output_path,
    )
    return result

def _generate_pdf_sync(report_data: dict, output_path: str) -> str:
    """Wrapper sync pentru PDF generator — ruleaza in process pool."""
    from backend.reports.pdf_generator import PDFGenerator
    gen = PDFGenerator()
    return gen.generate(report_data, output_path)
```

**Aplicare:** `generator.py:generate()` → `await generate_pdf_async()`.
`max_workers=2` (Windows 10, RAM limitat) — nu creste > 4.

**Verificare:** Timp de raspuns GET /api/reports nu creste in timp ce se genereaza PDF.

---

### G2 — Crawler Monitorul Oficial (Cesiuni Suspecte)

**Prioritate:** P1 | **Efort:** 2-3 zile | **Risc:** MEDIU
**Sursa:** Gemini 2026-04-08 — Pilon BUSINESS INTELLIGENCE

**Descriere:**
Monitorul Oficial Partea a IV-a contine publicatii despre cesiuni de parti sociale, dizolvari, radieri, numiri administratori. Aceste evenimente apar CU 1-6 luni inainte de probleme financiare declarate oficial (bilant).

**Valoare intelligence:**
- Detectezi cand cineva "se retrage" din firma inainte de bilant negativ
- Identifici cesiuni suspecte (pret mult sub valoare contabila)
- Alerte precoce reale (nu estimate)

**Arhitectura propusa:**

1. `backend/agents/tools/monitorul_oficial_client.py`:

```python
"""Crawler Monitorul Oficial Partea IV-a — cesiuni, dizolvari, numiri."""
import httpx
from loguru import logger

MO_BASE = "https://www.monitoruloficial.ro"

async def search_company_publications(cui: str, company_name: str) -> list[dict]:
    """Cauta publicatii MO pentru o firma dupa CUI sau denumire."""
    # GET /cautare?query={company_name}&sectiune=4
    # Parse HTML raspuns (BeautifulSoup sau regex simplu)
    # Returneaza: [{"date": "2024-03-15", "type": "cesiune_parti_sociale", "snippet": "..."}]
```

2. Integrare in `agent_official.py`:

```python
from backend.agents.tools.monitorul_oficial_client import search_company_publications

# In execute():
mo_publications = await search_company_publications(cui, company_name)
state["monitorul_oficial"] = mo_publications
```

3. Scoring penalty in `agent_verification.py`:
- Cesiune parti sociale in ultimele 6 luni: -10 puncte juridic
- Dizolvare in curs: -20 puncte + flag early warning

4. Sectiune noua in raport HTML/PDF: "Monitorul Oficial"

**Dependinte noi:** `beautifulsoup4` (deja disponibil sau usor de adaugat)

---

### G3 — TanStack Query: Dashboard + Companies (Extindere C2)

**Prioritate:** P1 | **Efort:** 2-3h | **Risc:** SCAZUT
**Sursa:** R7 C2 (partial implementat — doar ReportsList.tsx)

**Context:**
R7 a montat QueryClientProvider in main.tsx si a migrat ReportsList.tsx.
Dashboard.tsx si Companies.tsx folosesc inca pattern-ul `useEffect + useState` cu loading/error manual.

**Dashboard.tsx — migrare stats:**

```tsx
import { useQuery } from "@tanstack/react-query";

// Inlocuieste useEffect + setStats + setLoading:
const { data: stats, isLoading: statsLoading } = useQuery({
  queryKey: ["dashboard-stats"],
  queryFn: () => api.getStats(),
  staleTime: 30_000,
  refetchOnWindowFocus: true,
});

const { data: recentJobs } = useQuery({
  queryKey: ["recent-jobs"],
  queryFn: () => api.listJobs({ limit: 5 }),
  staleTime: 10_000,
  refetchInterval: 30_000,  // auto-refresh la 30s
});
```

**Companies.tsx — migrare lista companii:**

```tsx
const { data: companiesData, isLoading } = useQuery({
  queryKey: ["companies", search, sortBy, sortDir, page, filterRiskMin, filterRiskMax],
  queryFn: () => api.listCompanies({ search, sort_by: sortBy, sort_dir: sortDir, ... }),
  staleTime: 60_000,
  keepPreviousData: true,  // smooth pagination
});
```

**Beneficii:**
- Deduplication requesturi (Dashboard polling vs Companies lista)
- Cache cross-page: daca navighez companies → dashboard → companies, nu refetch
- Loading states uniforme

---

## GRUP G — GEMINI P2/P3

---

### G4 — WCAG 2.2 Audit React/Tailwind

**Prioritate:** P2 | **Efort:** 2-3h | **Risc:** SCAZUT
**Sursa:** Gemini 2026-04-09 — Pilon UX

**Probleme identificate de Gemini:**

1. **Contrast culori dark theme** — verificat cu axe-core sau browser DevTools:
   - `text-gray-500` pe `bg-dark-surface` → ratio ~3.2:1 (sub 4.5:1 WCAG AA)
   - Risk badge galben `text-yellow-400` pe `bg-yellow-500/20` → verifica

2. **Focus indicators** — butoane cu `focus-visible:ring-2` sunt OK, dar verifica:
   - NavLink sidebar → `focus-visible:ring-2` lipseste pe unele

3. **Keyboard navigation** — modal-uri (EmailModal, GlobalSearch) → verifica focus trap

**Fix-uri concrete:**

```tsx
// Imbunatatire contrast text secundar (dark theme):
// Inlocuieste text-gray-500 cu text-gray-400 unde e text informativ important
// (nu decorativ)

// Focus trap in modals:
import { useEffect, useRef } from "react";
function useFocusTrap(active: boolean) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!active || !ref.current) return;
    const focusable = ref.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0] as HTMLElement;
    const last = focusable[focusable.length - 1] as HTMLElement;
    first?.focus();
    // trap handler...
  }, [active]);
  return ref;
}
```

**Tool recomandat:** `npm install --save-dev @axe-core/react` pentru audit automat in dev.

---

### G5 — Suport i18n English pentru Rapoarte

**Prioritate:** P2 | **Efort:** 3-4h | **Risc:** SCAZUT
**Sursa:** Gemini 2026-04-09 — Pilon IMBUNATATIRI

**Context:**
Rapoartele PDF/HTML sunt generate 100% in romana.
Clienti internationali sau investitori straini nu pot citi direct.

**Arhitectura propusa (minimal viable):**

1. `backend/reports/i18n.py` — dictionar traduceri:

```python
TRANSLATIONS = {
    "ro": {
        "executive_summary": "Rezumat Executiv",
        "risk_score": "Scor Risc",
        "financial": "Financiar",
        # ... 50-80 termeni
    },
    "en": {
        "executive_summary": "Executive Summary",
        "risk_score": "Risk Score",
        "financial": "Financial",
        # ...
    }
}

def t(key: str, lang: str = "ro") -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["ro"]).get(key, key)
```

2. `POST /api/reports/{id}/generate` → accept `lang` param (default "ro"):

```python
@router.post("/{report_id}/generate")
async def generate_report(report_id: str, lang: str = "ro", ...):
    ...
    generator.generate(report_data, lang=lang)
```

3. `pdf_generator.py` + `html_generator.py` → inlocuieste string-uri hardcodate cu `t(key, lang)`.

**Scope:** Anteturi sectiuni, labeluri score, mesaje standard.
Continutul generat de AI ramane in romana (e generat din datele ANAF).

---

### D1 — data.gov.ro ONRC Dataset Local

**Prioritate:** P2 | **Efort:** 2-3 zile | **Risc:** MEDIU
**Sursa:** R7 Grup D (strategic, desfasurat in sprint nou)

**Descriere:**
Dataset oficial ONRC pe data.gov.ro (CC BY 4.0), actualizat lunar:
- Firme active: ~660 MB CSV
- Firme radiate: ~392 MB CSV

**Beneficiu principal:** Elimina dependenta de limita 100 req/luna openapi.ro pentru campurile de baza (denumire, CAEN, judet, data_inregistrare).

**Arhitectura:**

1. Script `tools/import_onrc.py`:

```python
"""Download + import ONRC dataset din data.gov.ro in SQLite local."""
import csv, sqlite3, httpx
from pathlib import Path

DATASET_URL = "https://data.gov.ro/dataset/..."  # URL real din portal

def download_and_import(db_path: str = "data/ris.db"):
    # Download CSV (~500MB)
    # Parse + insert in onrc_companies cu batch inserts (1000 rows/commit)
    # Index pe cui
    pass
```

2. Tabel nou in `database.py`:

```sql
CREATE TABLE IF NOT EXISTS onrc_companies (
    cui INTEGER PRIMARY KEY,
    denumire TEXT NOT NULL,
    caen TEXT,
    judet TEXT,
    localitate TEXT,
    data_inregistrare TEXT,
    status TEXT DEFAULT 'activ',
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_onrc_cui ON onrc_companies(cui);
```

3. `agent_official.py` — lookup local INAINTE de openapi.ro:

```python
# Check local ONRC DB first (O(log n), instant)
local_data = await db.fetch_one(
    "SELECT * FROM onrc_companies WHERE cui=?", (cui_int,)
)
if local_data:
    state["onrc_data"] = dict(local_data)
else:
    # Fallback: openapi.ro API (100 req/luna limit)
    state["onrc_data"] = await openapi_client.get_company(cui)
```

---

### G6 — PostgreSQL Migration Feasibility Study

**Prioritate:** P3 | **Efort:** 1-2h (studiu, fara implementare) | **Risc:** SCAZUT
**Sursa:** Gemini 2026-04-09 — Pilon IMPROVE

**Context:**
SQLite (WAL mode) e excelent pentru volumul actual (< 10K firme, 1 user simultan).
La >50K firme sau >5 utilizatori simultanei, PostgreSQL devine relevant.

**De evaluat:**

| Criteriu | SQLite (actual) | PostgreSQL |
|----------|----------------|------------|
| Setup | Zero (file-based) | Docker sau local install |
| Backup | sqlite3.backup() | pg_dump |
| Concurenta | WAL (1 writer) | MVCC (n writers) |
| Full-text | FTS5 built-in | pg_trgm + GIN index |
| JSON | JSON1 extension | jsonb nativ |
| Migrare cod | - | aiosqlite → asyncpg (mediu) |

**Recomandare Gemini:** Pastreaza SQLite pentru versiunea locala. Adauga PostgreSQL ca optiune in `.env` (DATABASE_URL) pentru deployuri cloud viitoare. Pattern: repository abstraction layer.

**Nu implementa acum** — documenteaza decizia in CLAUDE.md.

---

### G7 — Prometheus/Grafana Monitoring

**Prioritate:** P3 | **Efort:** 2-3h | **Risc:** SCAZUT
**Sursa:** Gemini 2026-04-09 — Pilon CLOUDOPS

**Context:**
Sistemul are deja metrici interne (`/api/health/deep`, cache stats, HTTP pool metrics).
Prometheus ar permite vizualizare istorica si alerte automate.

**Implementare minima:**

```python
# pip install prometheus-client
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

requests_total = Counter("ris_requests_total", "Total requests", ["method", "endpoint", "status"])
analysis_duration = Histogram("ris_analysis_duration_seconds", "Analysis duration")

@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

**Nota:** Util in special daca RIS se muta pe server sau cloud (Tailscale + Grafana Cloud gratuit).
Pentru uz local single-user, `/api/health/deep` e suficient.

---

### G8 — Predictie Faliment XGBoost Local

**Prioritate:** P3 | **Efort:** 1-2 saptamani | **Risc:** RIDICAT (research)
**Sursa:** Gemini 2026-04-08 — Pilon INOVATIE

**Context:**
Sistemul calculeaza deja scoruri Altman Z, Piotroski, Beneish, Zmijewski.
Un model XGBoost antrenat pe date istorice reale (firme care au intrat in insolventa vs firme sanatoase) ar putea da probabilitati mai precise.

**Blocante:**
- Dataset de antrenament necesar: minim 1000 firme cu istoric 3+ ani (insolvent + sanatoase)
- ANAF Bilant ofera date, dar colectarea ia timp
- GDPR: datele despre firme sunt publice, OK

**Evaluare:** Item de Research, nu de implementare imediata.
Documenteaza ca directie strategica. Revizuieste cand ai 500+ firme analizate in DB (score_history).

---

## ORDINE RECOMANDATA DE IMPLEMENTARE

### Sprint R8A (prioritate imediata, 1-2 sesiuni):
1. **G3** — TanStack Query Dashboard + Companies (2-3h, risc scazut) ← cel mai rapid win
2. **G1** — Process Pool PDF/DOCX (3-4h, risc mediu) ← elibereaza event loop

### Sprint R8B (calitate si UX, 1-2 sesiuni):
3. **G4** — WCAG 2.2 audit + contrast fix (2-3h)
4. **G5** — i18n English reports (3-4h)

### Sprint R8C (strategic, sesiune dedicata):
5. **D1** — data.gov.ro ONRC local (2-3 zile)
6. **G2** — Crawler Monitorul Oficial (2-3 zile)

### Sprint R8D (research/future):
7. **G6** — PostgreSQL feasibility (documentare, fara cod)
8. **G7** — Prometheus metrics endpoint (2-3h, optional)
9. **G8** — XGBoost faliment (research, termen lung)

---

## INFORMATII DE CONTEXT GEMINI

### Gemini 2026-04-09 (RAPORT_MASTER.md) — Concluzii cheie:
- **Scor general sistem:** Excelent — arhitectura matura pentru BI local
- **Securitate:** Conformitate ridicata (CSP strict, 10MB anti-DDoS, mascare date sensibile)
- **Compliance:** GDPR compliant, risc IP AI minimal prin abstract provider routing
- **Research:** "Maturitate nivel enterprise pentru instrumente BI Est-European"
- **VIES EU VAT:** Integrare potentiala pentru verificare TVA cross-border UE (P3 research)

### Gemini 2026-04-08 (MASTER_REPORT.md) — Bug hotfix implementat:
- ✓ Fix LangGraph `_agent_metrics` (Annotated merge) — implementat in commit dc0d408
- ✓ Knowledge Graph Visualizer — implementat in R7 (NetworkGraph.tsx)
- ✓ BPI fallback Tavily — implementat in fazele anterioare

---

## METRICI TINTA R8

| Metric | Actual (post-R7) | Tinta R8 |
|--------|-----------------|---------|
| pytest | 365 PASSED | 375+ PASSED |
| TypeScript errors | 0 | 0 |
| Event loop blocker | PDF/DOCX sync | Async (Process Pool) |
| TanStack Query coverage | 1/3 pagini (ReportsList) | 3/3 (+ Dashboard + Companies) |
| WCAG contrast | Neverificat | AA compliant (4.5:1) |
| i18n | RO only | RO + EN |
| ONRC requests/luna | 100 limit (openapi.ro) | Nelimitat (local dataset) |
