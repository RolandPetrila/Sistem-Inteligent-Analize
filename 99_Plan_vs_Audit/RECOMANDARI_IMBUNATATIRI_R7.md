# PLAN IMPLEMENTARE R7 — Roland Intelligence System

**Data creare:** 2026-04-09
**Versiune:** 7.0
**Baza:** Analiza Gemini CLI (2026-04-08) + audit documente Gemini_Documentatie/ + 99_Plan_vs_Audit/ + 99_Deep_Research/
**Status pytest la creare:** 365 PASSED, 0 failures (commit c401077)

---

## CONTEXT — CE S-A IMPLEMENTAT DEJA

Înainte de a citi planul, itemele de mai jos au fost marcate ca neimplementate în documentele anterioare dar
**SUNT DE FAPT DEJA IMPLEMENTATE** și nu apar în R7:

| Item                                                                                        | Faza implementat         |
| ------------------------------------------------------------------------------------------- | ------------------------ |
| ANAF Bilant API, Scoring 0-100 multi-dimensional, Cross-validare, CUI MOD11                 | Faza 4.5                 |
| SEAP, Openapi.ro, Excel 4 sheet-uri, Comparator, Detectare Anomalii                         | Faza 5                   |
| Lazy imports, CORS Tailscale, httpx singleton, health deep, stats cache                     | Faza 6A                  |
| Due Diligence, Actionariat, 1-Pager PDF, CAEN Context, Benchmark, Early Warnings, Batch CSV | Faza 6B                  |
| Error Boundaries, CSP headers, Toast, CUI validator JS, Prompt optimization                 | Faza 6C                  |
| Matricea Relatii, INS TEMPO live, Scheduler, AI Smart Routing, React 19                     | Faza 6D                  |
| Rate limiting, API Key auth (X-RIS-Key), api.ts complet, CSP hardened                       | Faza 7C                  |
| 28 pytest + 11 vitest, React.lazy 10 pagini, retry logic ANAF                               | Faza 7D                  |
| Predictive models (Altman Z, Piotroski F, Beneish M, Zmijewski X)                           | Faza R6 (2026-04-08)     |
| Cross-section coherence, anti-halucinare, token budget, prompt injection hardening          | Faza 10B/10F             |
| Watermark CONFIDENTIAL, TOC PDF/DOCX                                                        | Faza 9D                  |
| WS auth token, scoring constants extracted, 15 router tests                                 | Faza R10/R17             |
| NetworkX BFS depth-4, Toxic PageRank, shell company detection                               | network_client.py R6     |
| Agentic Reflexion, CA percentile scoring, scheduler log cleanup                             | Gemini Sprint 2026-04-08 |
| .gitignore pentru .claude-outputs/ și Gemini_Documentatie/                                  | Existent în .gitignore   |
| Monitorul Oficial via Tavily (osint_client.py)                                              | agent_official.py        |
| React Router v7 (7.4.0)                                                                     | frontend/package.json    |
| CSV Export StreamingResponse cu generator                                                   | routers/companies.py     |
| F8-3 rollup-plugin-visualizer + npm run analyze                                             | Faza R6 (vite.config.ts) |

---

## STRUCTURA PLAN R7

```
GRUP A — Quick Wins          (efort total: ~6-8h)
GRUP B — Features UX         (efort total: ~12-18h)
GRUP C — Calitate Cod        (efort total: ~8-12h)
GRUP D — Strategic           (efort total: 3-15 zile)
GRUP E — Surse Noi de Date   (efort total: ~10-15h)
```

---

## GRUP A — QUICK WINS

> Efort mic, impact vizibil imediat. Implementare în ordinea listată.

---

### A1 — Număr Raport Unic

**Prioritate:** P1 | **Efort:** 30-45 min | **Risc:** SCĂZUT

**Descriere:**
Fiecare raport generat primește un număr unic în format `RIS-2026-XXXX`. Auto-increment din DB.
Apare pe cover page PDF, header HTML, footer DOCX.

**Implementare:**

1. Migrare SQL — adaugă coloana în tabelul `reports`:

```sql
-- Se adaugă în database.py la connect (idempotent):
ALTER TABLE reports ADD COLUMN report_number TEXT DEFAULT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_number ON reports(report_number);

-- Sequencer:
CREATE TABLE IF NOT EXISTS report_sequences (
    year INTEGER PRIMARY KEY,
    last_seq INTEGER DEFAULT 0
);
```

2. Funcție DB (`database.py`):

```python
async def get_next_report_number(self) -> str:
    """Genereaza numarul urmator in format RIS-YYYY-XXXX."""
    from datetime import datetime, UTC
    year = datetime.now(UTC).year
    await self.execute(
        "INSERT INTO report_sequences (year, last_seq) VALUES (?, 1) "
        "ON CONFLICT(year) DO UPDATE SET last_seq = last_seq + 1",
        (year,)
    )
    row = await self.fetch_one(
        "SELECT last_seq FROM report_sequences WHERE year = ?", (year,)
    )
    seq = row["last_seq"] if row else 1
    return f"RIS-{year}-{seq:04d}"
```

3. Integrare în `reports/generator.py`:

```python
# În generate_report(), înainte de salvare:
from backend.database import db
report_number = await db.get_next_report_number()
# Pasează report_number în pdf_generator, html_generator, docx_generator
# Salvează în DB: await db.execute("UPDATE reports SET report_number=? WHERE id=?", ...)
```

4. Afișare în fiecare generator:

- **PDF**: Cover page — rând sub titlu: `f"Raport #{report_number}"`
- **HTML**: Metadata header
- **DOCX**: Proprietate document + footer

**Fișiere modificate:** `backend/database.py`, `backend/reports/generator.py`, `backend/reports/pdf_generator.py`, `backend/reports/html_generator.py`, `backend/reports/docx_generator.py`

**Teste:** Verificare `report_number IS NOT NULL` și format regex `^RIS-\d{4}-\d{4}$`

---

### A2 — Risk Badge Vizibil pe Card Companie

**Prioritate:** P1 | **Efort:** 20-30 min | **Risc:** SCĂZUT

**Descriere:**
Cardurile din Companies.tsx afișează deja filterul după risc dar badge-ul de culoare lipsește vizual pe fiecare card.
Adaugă badge colorat cu scorul numeric și culoarea (Verde/Galben/Roșu) pe fiecare card.

**Fișier:** `frontend/src/pages/Companies.tsx`

**Implementare:**

```tsx
// Componentă helper adăugată în fișier:
function RiskBadge({ score, color }: { score?: number; color?: string }) {
  if (score === undefined || score === null) return null;
  const bg =
    color === "Verde"
      ? "bg-green-500/20 text-green-400 border-green-500/30"
      : color === "Galben"
        ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
        : "bg-red-500/20 text-red-400 border-red-500/30";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${bg}`}
    >
      {score}/100
    </span>
  );
}

// În render card:
<RiskBadge score={company.risk_score} color={company.risk_color} />;
```

**Verificare:** Badge apare pe toate cardurile care au `risk_score` !== null.

---

### A3 — Actualizare FUNCTII_SISTEM.md

**Prioritate:** P1 | **Efort:** 20 min | **Risc:** ZERO

**Descriere:**
Fișierul `docs/FUNCTII_SISTEM.md` are data 2026-03-22, versiunea V8 și ~37 endpoints.
Trebuie actualizat la starea curentă: 365 teste, 42+ endpoints, versiunea R7, toate fazele R1-R7.

**Fișier:** `docs/FUNCTII_SISTEM.md`

**Ce se actualizează:**

- Data: 2026-04-09
- Versiune: R7.0
- Teste: 365 pytest + 38 vitest = 403 total
- Endpoints: 42 REST + 1 WebSocket
- Faze: adaugă R5/R6/R7 cu itemele implementate
- Provideri AI: 9 (Claude + Groq + Gemini + Cerebras + Mistral + GitHub Models + Fireworks AI + SambaNova + OpenRouter)
- Surse date: ANAF TVA + Bilant + BNR + Tavily + openapi.ro + SEAP + CAEN + INS TEMPO + BPI + osint_client (Monitorul Oficial) + Portal Just SOAP
- Features noi adăugate (predictive models, reflexion, CA percentile, network analysis)

---

### A4 — Brave Search API Key (Acțiune User)

**Prioritate:** P1 | **Efort:** 5 min | **Risc:** ZERO

**Descriere:**
Codul pentru Brave Search este deja implementat în backend. Lipsește doar API key-ul.
Brave oferă 1 lună gratuită + 2000 req/lună permanent gratuit (Basic tier).

**Pași:**

1. Accesează: `https://api.search.brave.com/` → Sign Up
2. Dashboard → API Keys → Create New Key
3. Adaugă în `.env`: `BRAVE_SEARCH_API_KEY=BSA...`
4. Verificare: `python -c "from backend.config import settings; print(settings.brave_search_api_key)"`

**Valoare adăugată:** Alternativă la Tavily (1000 req/lună) pentru search web.

---

### A5 — AEGRM Client (Garanții Reale Mobiliare)

**Prioritate:** P1 | **Efort:** 2-3h | **Risc:** SCĂZUT

**Descriere:**
`aegrm.ro` — Arhiva Electronică de Garanții Reale Mobiliare. API public gratuit.
Verifică dacă o firmă are vehicule, stocuri, creanțe sau active gajate.
Date extrem de relevante în due diligence — un gaj nemenționat poate bloca tranzacții.

**Fișier nou:** `backend/agents/tools/aegrm_client.py`

**Implementare:**

```python
"""
AEGRM Client — Arhiva Electronica de Garantii Reale Mobiliare.
API public: aegrm.justportal.ro/aegrm/rest/
Verificare grarant: GET /debitoriPJ?cui={cui}
"""
import asyncio
from loguru import logger
from backend.http_client import get_http_client

AEGRM_BASE = "https://aegrm.justportal.ro/aegrm/rest"

async def check_aegrm_guarantees(cui: str) -> dict:
    """
    Verifica garantiile reale mobiliare ale unei firme dupa CUI.
    Returneaza: has_guarantees, count, details, source_url.
    """
    if not cui:
        return {"has_data": False, "has_guarantees": False, "count": 0, "details": []}
    cui_clean = str(cui).strip().lstrip("RO").lstrip("0")

    try:
        client = await get_http_client()
        resp = await client.get(
            f"{AEGRM_BASE}/debitoriPJ",
            params={"cui": cui_clean},
            timeout=15.0,
        )
        if resp.status_code != 200:
            return {"has_data": False, "error": f"HTTP {resp.status_code}"}

        data = resp.json()
        entries = data.get("debitoriPJ", []) or []

        details = []
        for entry in entries[:10]:  # max 10 garanții afișate
            details.append({
                "nr_inregistrare": entry.get("numarInregistrare", "N/A"),
                "data": entry.get("dataInregistrare", "N/A"),
                "creditor": entry.get("creditor", {}).get("denumire", "N/A"),
                "tip_bun": entry.get("descriereBun", "N/A"),
                "status": entry.get("status", "N/A"),
            })

        logger.info(f"[aegrm] CUI {cui_clean}: {len(entries)} garantii gasite")
        return {
            "has_data": True,
            "has_guarantees": len(entries) > 0,
            "count": len(entries),
            "details": details,
            "source": "AEGRM",
            "source_url": f"https://aegrm.justportal.ro",
        }

    except Exception as e:
        logger.warning(f"[aegrm] Error pentru {cui}: {e}")
        return {"has_data": False, "error": str(e)}
```

**Integrare în Agent 1:**

- Adaugă call în `agent_official.py` în secțiunea Due Diligence, paralel cu BPI
- Adaugă câmp `aegrm_guarantees` în `verified_data`
- Scoring: dacă `count > 0` → penalizare -5 în dimensiunea Juridic + flag în due diligence checklist

**Afișare în raport HTML/PDF:** Secțiunea "Due Diligence" — rând nou: "Garanții Reale Mobiliare: DA/NU (N înregistrări)"

---

## GRUP B — FEATURES UX

> Impact vizibil mare pentru utilizator. Implementare în ordinea preferată.

---

### B1 — NLQ Ask RIS Chatbot

**Prioritate:** P1 | **Efort:** 4-6h | **Risc:** MEDIU

**Descriere:**
Chat panel flotant în Dashboard care înțelege întrebări naturale despre datele din sistem.
Arhitectură rule-based (fără ML, fără vector DB) — mapare intenție → SQL → răspuns formatat.

**Intenții suportate (v1):**

1. `top_risc` — "care firme au risc ridicat?" → `SELECT ... WHERE risk_score < 40 ORDER BY risk_score LIMIT 5`
2. `statistici` — "câte analize am făcut?" → `SELECT COUNT(*) FROM jobs WHERE status='COMPLETED'`
3. `firma_info` — "spune-mi despre [firma]" → `SELECT ... FROM companies WHERE name LIKE ?`
4. `comparatie` — "compară [firma1] cu [firma2]" → redirect la /compare cu CUI-urile
5. `ultimele` — "ce am analizat ultima oară?" → `SELECT ... FROM jobs ORDER BY created_at DESC LIMIT 5`

**Backend — fișier nou:** `backend/routers/ask.py`

```python
"""
NLQ Ask RIS — Natural Language Query endpoint.
Intent classifier rule-based → SQL → formatare raspuns.
POST /api/ask { "question": "..." }
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.auth import require_api_key
from backend.database import db
from loguru import logger
import re

router = APIRouter(prefix="/api/ask", tags=["ask"])

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    intent: str
    data: list | None = None

def _classify_intent(q: str) -> str:
    q_lower = q.lower()
    if any(k in q_lower for k in ["risc ridicat", "risc mare", "roșu", "periculoas", "risc"]):
        return "top_risc"
    if any(k in q_lower for k in ["câte", "cate", "statistici", "total", "câți", "cati"]):
        return "statistici"
    if any(k in q_lower for k in ["ultima", "ultimele", "recent", "ieri", "astăzi"]):
        return "ultimele"
    if any(k in q_lower for k in ["compară", "compara", "vs", "versus", "diferenta"]):
        return "comparatie"
    if any(k in q_lower for k in ["despre", "info", "detalii", "spune"]):
        return "firma_info"
    return "necunoscut"

@router.post("", response_model=AskResponse)
async def ask_ris(req: AskRequest, _=Depends(require_api_key)):
    question = req.question.strip()
    if not question:
        return AskResponse(answer="Introduceți o întrebare.", intent="gol")

    intent = _classify_intent(question)
    logger.info(f"[ask] intent={intent} | question={question[:80]}")

    if intent == "top_risc":
        rows = await db.fetch_all(
            "SELECT name, cui, risk_score, risk_color FROM companies "
            "WHERE risk_score IS NOT NULL ORDER BY risk_score ASC LIMIT 5"
        )
        if not rows:
            return AskResponse(answer="Nu există date de scoring în sistem.", intent=intent)
        lines = [f"• {r['name']} (CUI {r['cui']}): {r['risk_score']}/100 — {r['risk_color']}" for r in rows]
        return AskResponse(
            answer="Top 5 firme cu risc ridicat:\n" + "\n".join(lines),
            intent=intent, data=[dict(r) for r in rows]
        )

    if intent == "statistici":
        total = await db.fetch_one("SELECT COUNT(*) as c FROM jobs WHERE status='COMPLETED'")
        companies = await db.fetch_one("SELECT COUNT(*) as c FROM companies")
        alerts = await db.fetch_one("SELECT COUNT(*) as c FROM monitoring_alerts WHERE is_active=1")
        return AskResponse(
            answer=(
                f"Statistici sistem:\n"
                f"• Analize completate: {total['c'] if total else 0}\n"
                f"• Companii în baza de date: {companies['c'] if companies else 0}\n"
                f"• Alerte active monitorizare: {alerts['c'] if alerts else 0}"
            ),
            intent=intent,
        )

    if intent == "ultimele":
        rows = await db.fetch_all(
            "SELECT j.id, c.name, c.cui, j.created_at, j.status "
            "FROM jobs j LEFT JOIN companies c ON c.cui = j.input_data "
            "ORDER BY j.created_at DESC LIMIT 5"
        )
        if not rows:
            return AskResponse(answer="Nu există analize recente.", intent=intent)
        lines = [f"• {r['name'] or r['cui'] or 'N/A'} — {r['created_at'][:10]} ({r['status']})" for r in rows]
        return AskResponse(
            answer="Ultimele 5 analize:\n" + "\n".join(lines),
            intent=intent,
        )

    if intent == "firma_info":
        # Extrage nume firma din intrebare
        name_match = re.search(r'despre\s+(.+?)(?:\?|$)', question, re.IGNORECASE)
        search_term = name_match.group(1).strip() if name_match else question
        rows = await db.fetch_all(
            "SELECT name, cui, risk_score, risk_color, caen_code FROM companies "
            "WHERE name LIKE ? LIMIT 3",
            (f"%{search_term}%",)
        )
        if not rows:
            return AskResponse(answer=f"Nu am găsit companii cu numele '{search_term}'.", intent=intent)
        lines = [f"• {r['name']} — CUI: {r['cui']}, Scor: {r['risk_score']}/100 ({r['risk_color']}), CAEN: {r['caen_code']}" for r in rows]
        return AskResponse(answer="\n".join(lines), intent=intent, data=[dict(r) for r in rows])

    return AskResponse(
        answer=(
            "Nu am înțeles întrebarea. Încearcă:\n"
            "• 'Care firme au risc ridicat?'\n"
            "• 'Câte analize am făcut?'\n"
            "• 'Ce am analizat ultima oară?'\n"
            "• 'Spune-mi despre [nume firmă]'"
        ),
        intent="necunoscut",
    )
```

**Înregistrare router în `main.py`:**

```python
from backend.routers.ask import router as ask_router
app.include_router(ask_router)
```

**Frontend — Chat Panel flotant:**

- Buton flotant `?` în colțul dreapta-jos al Dashboard-ului
- `useState` pentru `isOpen`, `messages[]`, `loading`
- `POST /api/ask` cu question → afișare răspuns în bule
- Fișier nou: `frontend/src/components/AskRIS.tsx`

**Integrare:** Import + render în `Dashboard.tsx`

---

### B2 — Knowledge Graph Visualizer

**Prioritate:** P1 | **Efort:** 4-5h | **Risc:** MEDIU

**Descriere:**
Pagina nouă `/network/:cui` care vizualizează interactiv rețeaua de firme din `network_client.py`.
Datele sunt deja disponibile în backend — lipsește doar UI.

**Dependință frontend:**

```bash
npm install @xyflow/react  # React Flow v12 — 47KB gzip, MIT license, gratuit
```

**Backend:** Endpoint existent sau nou:

```python
# Dacă nu există deja:
# GET /api/companies/{cui}/network → returnează date din network_client.get_company_network()
```

**Fișier nou:** `frontend/src/pages/NetworkGraph.tsx`

**Structura grafului:**

- Nod central: firma analizată (albastru)
- Noduri secundare: firme conectate (verde = active, roșu = inactive, gri = necunoscut)
- Edges: etichetă cu numele persoanei comune
- Noduri speciale: persoană toxică → border roșu pulsator
- Sidebar dreapta: detalii nod selectat

**Layout:** Force-directed (React Flow auto-layout) sau manual pe cercuri concentrice (depth 1, 2, 3...)

**Navigare:** Click pe nod firmă → link către `/company/:cui` (dacă firma e analizată în DB)

**Adăugare în `App.tsx`:**

```tsx
<Route path="/network/:cui" element={<Suspense fallback={...}><NetworkGraph /></Suspense>} />
```

**Adăugare în sidebar `Layout.tsx`:**

```tsx
{ icon: <Network size={20} />, label: "Rețea Firme", href: "/companies" }
// sau link dinamic din CompanyDetail.tsx: "Vezi rețea" → /network/{cui}
```

---

### B3 — Dark/Light Theme Toggle

**Prioritate:** P2 | **Efort:** 1-2h | **Risc:** SCĂZUT

**Descriere:**
Toggle în header — păstrează dark ca default, adaugă light theme complementar.
Persistență în `localStorage`. CSS variables deja definite → modificare minimă.

**Implementare:**

1. `frontend/src/lib/theme.ts` — utilitar:

```typescript
export type Theme = "dark" | "light";

export function getTheme(): Theme {
  return (localStorage.getItem("ris-theme") as Theme) ?? "dark";
}

export function setTheme(theme: Theme) {
  localStorage.setItem("ris-theme", theme);
  document.documentElement.classList.toggle("light", theme === "light");
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function initTheme() {
  setTheme(getTheme());
}
```

2. `frontend/src/index.css` — adaugă variabile light theme:

```css
.light {
  --bg-primary: #f8fafc;
  --bg-secondary: #ffffff;
  --text-primary: #1e293b;
  --text-secondary: #475569;
  --border-color: #e2e8f0;
  --accent: #3b82f6;
}
```

3. Toggle button în `Layout.tsx`:

```tsx
import { Sun, Moon } from "lucide-react";
// În header:
<button onClick={() => { setTheme(theme === "dark" ? "light" : "dark"); setLocalTheme(...) }}>
  {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
</button>
```

4. `main.tsx` — apel `initTheme()` la startup

---

### B4 — GlobalSearch Accesibil pe Mobile

**Prioritate:** P2 | **Efort:** 1h | **Risc:** SCĂZUT

**Descriere:**
`GlobalSearch` (Ctrl+K) nu e accesibil pe mobile deoarece shortcuts de tastatură nu funcționează.
Adaugă buton lupă vizibil în mobile header → deschide același modal.

**Fișier:** `frontend/src/components/Layout.tsx`

**Implementare:**

```tsx
// În header-ul mobile (vizibil doar la sm: breakpoint):
<button
  className="sm:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10"
  onClick={() => setGlobalSearchOpen(true)}
  aria-label="Caută"
>
  <Search size={20} />
</button>
```

**Notă:** `setGlobalSearchOpen` trebuie expus din `GlobalSearch.tsx` — fie prin context, fie prin prop drilling sau un store Zustand simplu.

---

### B5 — Link Partajabil Raport HTML

**Prioritate:** P2 | **Efort:** 2-3h | **Risc:** SCĂZUT

**Descriere:**
Generează un token unic per raport → URL public accesibil fără autentificare → util pentru trimitere clienți.

**Backend:**

1. Migrare SQL (idempotent în `database.py`):

```sql
ALTER TABLE reports ADD COLUMN share_token TEXT DEFAULT NULL;
ALTER TABLE reports ADD COLUMN share_expires_at TEXT DEFAULT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_share_token ON reports(share_token);
```

2. Endpoint generate token — `routers/reports.py`:

```python
@router.post("/{report_id}/share")
async def generate_share_link(report_id: str, ttl_days: int = 30, _=Depends(require_api_key)):
    """Genereaza un link partajabil pentru raportul HTML."""
    import secrets
    from datetime import datetime, UTC, timedelta
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(UTC) + timedelta(days=ttl_days)).isoformat()
    await db.execute(
        "UPDATE reports SET share_token=?, share_expires_at=? WHERE id=?",
        (token, expires, report_id)
    )
    return {"share_url": f"/report/public/{token}", "expires_at": expires}
```

3. Endpoint public (fără auth):

```python
@router.get("/public/{token}", include_in_schema=False)
async def get_public_report(token: str):
    """Serveste raportul HTML prin token public (fara autentificare)."""
    from datetime import datetime, UTC
    from fastapi.responses import HTMLResponse
    row = await db.fetch_one(
        "SELECT * FROM reports WHERE share_token=? AND share_expires_at > ?",
        (token, datetime.now(UTC).isoformat())
    )
    if not row:
        raise HTTPException(404, "Link expirat sau invalid")
    # Citeste fisierul HTML din outputs/{job_id}/
    html_path = Path(f"outputs/{row['job_id']}/report.html")
    if not html_path.exists():
        raise HTTPException(404, "Raport HTML indisponibil")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))
```

**Frontend:**

- Buton "Partajează" în `ReportView.tsx` toolbar
- Click → `POST /api/reports/{id}/share` → afișează URL cu buton copy-to-clipboard
- Toast confirmare "Link copiat!"

---

## GRUP C — CALITATE COD

> Îmbunătățiri tehnice care reduc datoria tehnica fără a schimba funcționalitatea.

---

### C1 — Split Frontend Files > 500 LOC

**Prioritate:** P2 | **Efort:** 3-4h | **Risc:** MEDIU

**Descriere:**
4 pagini au depășit pragul de 500 LOC și devin greu de menținut.
Strategia: extrage componente reutilizabile în `components/`.

**Fișiere afectate:**

| Fișier              | LOC actuale | Target                                        |
| ------------------- | ----------- | --------------------------------------------- |
| `ReportView.tsx`    | ~619        | < 300 (extrage ReportToolbar, ReportMetadata) |
| `CompanyDetail.tsx` | ~551        | < 300 (extrage CompanyHeader, ScoreHistory)   |
| `Dashboard.tsx`     | ~521        | < 300 (extrage StatCards, QuickActions)       |
| `NewAnalysis.tsx`   | ~500        | < 280 (extrage WizardStep, CUIInput)          |

**Procedura pentru fiecare:**

1. Identifică blocuri vizuale coerente (≥50 LOC, props clare)
2. Extrage în `frontend/src/components/[PageName]/ComponentName.tsx`
3. `npm run build` — verifică 0 erori TypeScript
4. `npm test` — verifică că testele vitest trec

**NOTĂ:** Nu modifica logica sau stilurile — doar mutare cod.

---

### C2 — TanStack Query pentru Data Fetching

**Prioritate:** P2 | **Efort:** 3-4h | **Risc:** MEDIU

**Descriere:**
Înlocuiește pattern-ul `useEffect + useState + loading + error` cu `useQuery` din TanStack Query.
Beneficii: cache automat, revalidare, loading states, deduplication requests.

**Instalare:**

```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
```

**Setup `main.tsx`:**

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 2 } },
});
// Wrap <App /> cu <QueryClientProvider client={queryClient}>
```

**Migrare prioritizată (în ordine):**

1. `Dashboard.tsx` — stats și recent jobs:

```tsx
const { data: stats } = useQuery({
  queryKey: ["stats"],
  queryFn: () => api.getStats(),
  staleTime: 30_000,
});
```

2. `Companies.tsx` — lista companii:

```tsx
const { data: companies, isLoading } = useQuery({
  queryKey: ["companies", search, sortBy, filters],
  queryFn: () => api.getCompanies({ search, sortBy, ...filters }),
});
```

3. `ReportsList.tsx` — lista rapoarte:

```tsx
const { data } = useQuery({
  queryKey: ["reports", page],
  queryFn: () => api.getReports(page),
});
```

**Eliminare boilerplate:** Șterge `useEffect`, `useState(loading)`, `useState(error)` înlocuite.

---

### C3 — Accessibility ARIA

**Prioritate:** P3 | **Efort:** 1-2h | **Risc:** SCĂZUT

**Descriere:**
Adaugă atribute ARIA pentru screen readers și utilizatori cu daltonism.

**Fix-uri concrete:**

```tsx
// 1. Icoane fără text — adaugă aria-label:
<Bell size={20} aria-label="Notificări" />
<Trash2 size={16} aria-label="Șterge" />

// 2. Risk badges — text alternativ pentru culoare:
// NU: <span className="bg-red-500">●</span>
// DA: <span className="bg-red-500" aria-label="Risc ridicat">●</span>

// 3. Butoane acțiune — role și aria-label:
<button aria-label="Pornește analiza" aria-busy={loading}>
  {loading ? <Loader2 className="animate-spin" /> : <Play />}
</button>

// 4. Toast — role="alert" pentru screen readers:
<div role="alert" aria-live="polite">
  {message}
</div>

// 5. Verde/Galben/Roșu — nu doar culoare, și text:
"Verde (risc scăzut)" | "Galben (risc mediu)" | "Roșu (risc ridicat)"
```

---

### C4 — Type Hints Funcții Publice Backend

**Prioritate:** P3 | **Efort:** 1-2h | **Risc:** SCĂZUT

**Descriere:**
~20 funcții publice din 3 module lipsă type annotations.
Ajută IDE-ul, mypy și colegii să înțeleagă contractul funcțiilor.

**Fișiere prioritare:**

```python
# agent_official.py — adaugă return types:
async def execute(self, state: AnalysisState) -> dict: ...
async def _fetch_anaf_data(self, cui: str) -> dict: ...

# cache_service.py:
async def get(self, key: str) -> dict | None: ...
async def set(self, key: str, value: dict, ttl: int = 3600) -> None: ...
async def cleanup_expired(self) -> int: ...

# notification.py:
async def send_telegram(self, message: str, severity: str = "INFO") -> bool: ...
```

---

## GRUP D — STRATEGIC

> Sesiuni dedicate, cu branch separat și testare manuală completă.

---

### D1 — data.gov.ro ONRC Dataset Local

**Prioritate:** P1 | **Efort:** 2-3 zile | **Risc:** MEDIU

**Descriere:**
Dataset oficial ONRC disponibil gratuit pe data.gov.ro (CC BY 4.0).
Înlocuiește limita de 100 req/lună de la openapi.ro cu date locale pentru câmpurile de bază.

**Dimensiuni dataset:**

- Firme active: ~660 MB CSV
- Firme radiate: ~392 MB CSV
- Persoane juridice: ~89 MB CSV

**Arhitectură propusă:**

1. Script `tools/import_onrc.py` — download + parse CSV + import SQLite
2. Tabel nou `onrc_companies` (CUI, denumire, CAEN, județ, data_înregistrare, status)
3. Index pe `cui` (lookup O(log n))
4. Agent Official: interoghează local ÎNAINTE de openapi.ro API call
5. Fallback automat pe openapi.ro dacă CUI nu e în dataset local

**Notă:**
Dataset-ul se actualizează lunar pe data.gov.ro. Scriptul de import are și modul `--update` care descarcă diff-ul.
Dacă dimensiunea SQLite devine problemă (~500MB), se poate folosi FTS5 pentru căutare text rapid.

---

### D2 — Vite 6 → 7 Upgrade

**Prioritate:** P2 | **Efort:** 2-4h | **Risc:** MEDIU

**Descriere:**
Vite 7 aduce îmbunătățiri de performanță la build și HMR. Upgrade recomandat pe branch separat.

**Pași:**

```bash
git checkout -b upgrade/vite7
cd frontend
npm install vite@latest @vitejs/plugin-react@latest
npm run build    # verifică erori
npm run dev      # verifică HMR
# Testare manuală: toate cele 12 pagini
npm test         # vitest trebuie să treacă
git merge main   # dacă OK
```

**Risc:** API din `vite.config.ts` poate fi deprecat. Verifică `plugins`, `build.rollupOptions`.

---

### D3 — Tailwind v3 → v4

**Prioritate:** P3 | **Efort:** 4-8h | **Risc:** MARE

**PREREQUISITE:** D2 (Vite 7) trebuie să fie COMPLET și pe main.

**Descriere:**
Tailwind v4 aduce engine Rust (Oxide) — build de 5-10x mai rapid. Breaking changes semnificative.

**Breaking changes de cunoscut:**

- `tailwind.config.js` **dispare** — configurare prin `@theme` în CSS
- `@apply` sintaxa schimbată
- Unele clase sunt redenumite (ex: `shadow` → `shadow-sm`)
- `JIT` devine default și unic mod

**Pași:**

```bash
git checkout -b upgrade/tailwind4
cd frontend
npx @tailwindcss/upgrade  # migration tool oficial
# Revizuire manuală diff-ului generat
npm run build
# Testare vizuală OBLIGATORIE: dark theme, toate 12 pagini, mobile view
npm test
```

**Fallback:** Dacă dark theme se strică → `git revert` și amână pentru sprint dedicat.

---

### D4 — XGBoost Predicție Faliment

**Prioritate:** P3 | **Efort:** 5-10 zile | **Risc:** SCĂZUT (funcționalitate izolată)

**Descriere:**
Model Gradient Boosting antrenat pe date ANAF acumulate în sistem.
Output: `AI_Bankruptcy_Probability_Score` (0-100%) adăugat în scoring.

**Prerequisites:**

- Minim 200 firme analizate în DB cu date ANAF Bilant complete
- Cel puțin 2 ani de date per firmă

**Arhitectură:**

```python
# backend/agents/tools/ml_predictor.py
# Features: CA trend, profit_margin, equity_ratio, angajati_trend,
#           altman_z, piotroski_f, beneish_m, zmijewski_x
# Target: insolventa_flag (1 dacă firma a intrat în insolvență în 2 ani)
# Model: XGBClassifier (xgboost>=2.0)
# Format persistare: model.json (ONNX sau XGBoost native)
```

**Notă:** Fără date suficiente, modelul nu e util. Monitorizează dimensiunea DB și porni implementarea când `SELECT COUNT(*) FROM companies WHERE latest_ca IS NOT NULL` > 200.

---

## GRUP E — SURSE NOI DE DATE

---

### E1 — AEGRM Client _(mutat la A5 — Quick Win)_

---

### E2 — Cohere Embed + Semantic Search Firme Similare

**Prioritate:** P2 | **Efort:** 4-6h | **Risc:** SCĂZUT

**Descriere:**
Utilizează Cohere Embed (gratuit, 1000 req/lună Trial) pentru embeddings vectoriale ale firmelor.
Endpoint `GET /api/companies/{cui}/similar?semantic=true` → returnează firme similare semantic.

**Arhitectură:**

```python
# backend/services/semantic_service.py
# 1. La fiecare analiză completă: generează embedding din rezumatul firmei
# 2. Stochează în tabel embeddings (SQLite JSON sau tabel separat)
# 3. La query: calculează cosine similarity → top 5 firme similare

# Migrare SQL (idempotent):
# ALTER TABLE companies ADD COLUMN embedding_json TEXT DEFAULT NULL;
# ALTER TABLE companies ADD COLUMN embedding_model TEXT DEFAULT NULL;
```

**Instalare:**

```bash
pip install cohere>=5.0  # adaugă în requirements.txt
```

**Cheie API:**

- Signup gratuit: `https://dashboard.cohere.com/`
- Adaugă în `.env`: `COHERE_API_KEY=co-...`

---

### E3 — Mistral OCR (Upload Documente Scanate)

**Prioritate:** P3 | **Efort:** 3-4h | **Risc:** SCĂZUT

**Descriere:**
Endpoint `POST /api/documents/ocr` — upload PDF scanat → text structurat JSON.
Model: `pixtral-12b` (Mistral multimodal). Util pentru bilanțuri scanate, contracte, acte ONRC.

**Backend — fișier nou:** `backend/routers/documents.py`

```python
@router.post("/ocr")
async def ocr_document(file: UploadFile, _=Depends(require_api_key)):
    """Upload PDF/imagine scanata → text structurat via Mistral Pixtral."""
    # Validare: max 10MB, tipuri acceptate: pdf/png/jpg
    # Conversie PDF → imagini (pypdfium2 sau pdf2image)
    # Trimitere la Mistral API cu model pixtral-12b
    # Răspuns: { text: "...", pages: N, model: "pixtral-12b" }
```

**Instalare:**

```bash
pip install pypdfium2  # conversie PDF → imagini (pur Python, fără dependințe native)
```

---

## ORDINE RECOMANDATĂ DE IMPLEMENTARE

```
┌─────────────────────────────────────────────────────────────────┐
│  SESIUNEA 1 — Quick Wins (2-4h)                                 │
│  A1 → A2 → A3 (în paralel posibil) → A5 (AEGRM)                │
│  A4 = acțiune user (Brave Search key)                           │
├─────────────────────────────────────────────────────────────────┤
│  SESIUNEA 2 — UX Features (3-4h)                                │
│  B3 (Dark/Light theme) → B4 (Mobile search) → B2 (Network Viz) │
├─────────────────────────────────────────────────────────────────┤
│  SESIUNEA 3 — Chatbot + Share (4-6h)                            │
│  B1 (NLQ Ask RIS) → B5 (Link partajabil)                        │
├─────────────────────────────────────────────────────────────────┤
│  SESIUNEA 4 — Technical Quality (4-6h)                          │
│  C1 (Split files) → C2 (TanStack Query) → C3/C4                 │
├─────────────────────────────────────────────────────────────────┤
│  SESIUNEA 5 — Semantic Search (4-6h)                            │
│  E2 (Cohere Embed) + E3 (Mistral OCR) în paralel               │
├─────────────────────────────────────────────────────────────────┤
│  SESIUNEA 6+ — Strategic (sesiuni dedicate)                     │
│  D1 (data.gov.ro) → D2 (Vite 7) → D3 (Tailwind 4) → D4 (ML)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ESTIMĂRI EFORT

| Grup                | Items  | Efort estimat | Complexitate |
| ------------------- | ------ | ------------- | ------------ |
| A — Quick Wins      | 5      | 6-8h          | SCĂZUTĂ      |
| B — Features UX     | 5      | 12-18h        | MEDIE        |
| C — Calitate Cod    | 4      | 8-12h         | MEDIE        |
| D — Strategic       | 4      | 3-15 zile     | MARE         |
| E — Surse Noi       | 3      | 10-15h        | MEDIE        |
| **TOTAL (excl. D)** | **17** | **~36-53h**   | —            |

---

## DEPENDINȚE ÎNTRE ITEMS

```
A5 (AEGRM) — independent
B2 (Network Viz) — necesită: npm install @xyflow/react
B1 (NLQ Chatbot) — independent (rule-based, fără ML)
B5 (Share Link) — necesită: A1 (raport number opțional)
C2 (TanStack) — necesită: npm install @tanstack/react-query
D3 (Tailwind v4) — REQUIRES: D2 (Vite 7) COMPLET
D4 (XGBoost) — REQUIRES: min. 200 firme în DB cu latest_ca
E2 (Cohere) — necesită: COHERE_API_KEY în .env
E3 (Mistral OCR) — necesită: MISTRAL_API_KEY în .env (deja existent)
```

---

## REGULI DE CALITATE — OBLIGATORII DUPĂ FIECARE ITEM

```bash
# Backend:
python -m pytest tests/ -q --tb=short    # 365+ PASSED, 0 failures
python -c "from backend.main import app; print('import OK')"

# Frontend:
npm run build                             # 0 erori TypeScript
npm test                                  # 38+ vitest PASSED

# Commit format:
git commit -m "feat(grup-id): descriere scurta — item AX/BX/CX"
```

---

## ITEMS CARE NECESITĂ ACȚIUNE USER (NU COD)

| Item              | Acțiune                                              | Timp  | URL                  |
| ----------------- | ---------------------------------------------------- | ----- | -------------------- |
| A4 — Brave Search | Signup + API key                                     | 5 min | api.search.brave.com |
| E2 — Cohere Embed | Signup + API key                                     | 5 min | dashboard.cohere.com |
| DeepSeek R1       | ATENȚIE: servere China — NU pentru date reale client | —     | —                    |

---

_Plan generat: 2026-04-09 | Baza: commit c401077 | 365 pytest PASSED_
