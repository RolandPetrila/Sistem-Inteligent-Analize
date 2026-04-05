# RECOMANDARI IMBUNATATIRI R3 — RIS (Post-R12)
**Data:** 2026-04-04 | **Versiune:** 3.1 | **Mod:** complet + audit
**Context:** Runda 3, dupa implementarea tuturor 15 items R2 + 40 items R1 (confirmate prin audit)
**Focus:** Gap-uri noi descoperite prin deep code analysis + web research 2026 + API completeness audit
**Actualizat:** 2026-04-04 — Audit R4 complet (73/100) — 12 descoperiri noi adaugate (items 31–42)

---

## COMPARATIE CU R2 (SNAPSHOT ANTERIOR)

| Aspect | R2 (01.04) | R3 (04.04) | Status |
|--------|-----------|-----------|--------|
| Notifications create | 40% BROKEN | COMPLET — apelat din job_service + monitoring | IMPLEMENTAT |
| Circuit breaker | Neintegrat | COMPLET — wired in synthesis (4 provideri) | IMPLEMENTAT |
| AbortController retry | Broken | COMPLET — progress guard Math.max() | IMPLEMENTAT |
| L1 cache threading | Unsafe | COMPLET — threading.Lock() pe get/put | IMPLEMENTAT |
| Email validator | Lipsa | COMPLET — regex @field_validator | IMPLEMENTAT |
| Zombie exclude inactive | False positive | COMPLET — exclude INACTIV/DIZOLVATA/RADIATA | IMPLEMENTAT |
| CSV header detection | Lipsea | COMPLET — 7 keywords detect+skip | IMPLEMENTAT |
| ETA progress guard | Race condition | COMPLET — Math.max + guard >5% | IMPLEMENTAT |
| Monitoring loading | Lipsa | COMPLET — loading state + spinner | IMPLEMENTAT |
| Notification Bell UI | MISSING | COMPLET — poll 60s + dropdown + mark read | IMPLEMENTAT |
| Favorites UI | MISSING | COMPLET — star + toggle + backend | IMPLEMENTAT |
| Risk Movers Widget | MISSING | COMPLET — top 5 + delta arrows | IMPLEMENTAT |
| Timeline UI | MISSING | COMPLET — events + icons | IMPLEMENTAT |
| Email Send Modal | MISSING | COMPLET — form + send + toast | IMPLEMENTAT |
| Circuit breaker module | Circular import | COMPLET — standalone module | IMPLEMENTAT |

**Concluzie R2:** TOATE 15 items implementate si verificate prin audit cod. R2 = DONE.

---

## AUDIT R4 — STATUS R3 + DESCOPERIRI NOI (2026-04-04)

**Scor audit:** 73/100 | **Delta R10→R4:** 90 → 73 (audit mai riguros, 12 domenii vs fix-focused)
**Agenti rulati:** 5 paralel — Securitate, Calitate Cod, Corectitudine+Performanta, Dependente+Teste, Git+Docs

### R3 items CONFIRMATE de audit (validate, PENDING implementare):

| # | Item R3 | Confirmat | Observatie audit |
|---|---------|-----------|-----------------|
| 1 | Timeout individual per task | DA | `asyncio.gather` fara timeout individual confirmat in agent_official.py |
| 2 | Memory leak `_in_flight` dedup | DA | Race condition confirmata — `_in_flight` dict fara Lock |
| 5 | WebSocket broadcast fix | DA | 4x `except Exception: pass` in main.py confirmate |
| 6 | Cache L1/L2 TTL sync | DA | `_fetch_locks` TOCTOU race confirmat in cache_service.py:213 |
| 21 | Input validation bounds (limit/offset) | DA | Niciun `Query(ge=1, le=100)` pe endpoint-uri |
| 27 | Frontend test coverage | DA | 12 teste (1 fisier), 0 componente testate |
| 28 | Backend test gaps | DA | 43 din 58 endpoint-uri fara teste |
| 30 | Token budget double-build | DA | Prompt construit de 2 ori in agent_synthesis.py:79-82 confirmat |

### Descoperiri NOI din Audit R4 (items 31–42):

> Adaugate la sfarsitul documentului in PARTEA IV.

---

## PARTEA I — IMBUNATATIRI FUNCTII EXISTENTE

---

### 1. Agent 1: Timeout individual per task (nu doar group timeout)

**Fisier:** `backend/agents/agent_official.py` — linia ~99-101
**Problema actuala:** 5 task-uri paralele (ANAF, openapi, ANAF Bilant, BNR, BPI) ruleaza cu `asyncio.gather()` dar FARA timeout individual. Un ANAF lent (30s+) blocheaza TOATE cele 5 surse. Timeout-ul exista doar la nivel de grup (300s).

**Imbunatatire propusa:**
- Wrap fiecare task in `asyncio.wait_for()` cu timeout individual
- ANAF: 15s, openapi: 10s, ANAF Bilant: 15s, BNR: 5s, BPI: 10s
- Task-ul care depaseste timeout-ul returneaza eroare, celelalte continua

**Exemplu implementare:**
```python
# agent_official.py — in metoda de fetch paralel
async def _fetch_with_individual_timeout(self, coro, source_name: str, timeout_s: int):
    """Wrap coroutine with individual timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except asyncio.TimeoutError:
        logger.warning(f"[{source_name}] Individual timeout after {timeout_s}s")
        return {"error": f"Timeout {timeout_s}s", "source": source_name}

# In run():
SOURCE_TIMEOUTS = {
    "anaf": 15, "openapi": 10, "anaf_bilant": 15, "bnr": 5, "bpi": 10
}

tasks = [
    self._fetch_with_individual_timeout(self._fetch_anaf(cui), "anaf", 15),
    self._fetch_with_individual_timeout(self._fetch_openapi(cui), "openapi", 10),
    self._fetch_with_individual_timeout(self._fetch_bilant(cui, years), "anaf_bilant", 15),
    self._fetch_with_individual_timeout(self._fetch_bnr(), "bnr", 5),
    self._fetch_with_individual_timeout(self._fetch_bpi(cui, name), "bpi", 10),
]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Complexitate:** Mica | **Impact:** Mare — previne cascading timeout (1 sursa lenta NU mai blocheaza 4 surse rapide)

---

### 2. Orchestrator: Fix memory leak in `_in_flight` deduplication

**Fisier:** `backend/agents/orchestrator.py` — linia ~40-60
**Problema actuala:** `_in_flight[cui]` salveaza asyncio.Event pentru deduplicare. Cleanup-ul se face cu `loop.call_later(60)` dar:
- 60s e prea scurt (job-urile ruleaza 2-5 min)
- `call_later` + `event.set()` are race condition cu event loop-ul
- Daca job-ul crash-uieste, Event nu e niciodata set() — waiters asteapta infinit

**Imbunatatire propusa:**
- Creste cleanup la 600s (10 min)
- Adauga timeout pe `event.wait()` (maxim 300s)
- Cleanup explicit in finally block (nu doar call_later)

**Exemplu implementare:**
```python
# orchestrator.py — fix dedup cleanup
_in_flight: dict[str, asyncio.Event] = {}
_in_flight_results: dict[str, dict] = {}

async def run_analysis(self, cui: str, **kwargs) -> dict:
    if cui in _in_flight:
        event = _in_flight[cui]
        try:
            await asyncio.wait_for(event.wait(), timeout=300)
            return _in_flight_results.get(cui, {})
        except asyncio.TimeoutError:
            logger.warning(f"Dedup wait timeout for {cui}, proceeding with new analysis")
            # Fall through to run new analysis
    
    event = asyncio.Event()
    _in_flight[cui] = event
    try:
        result = await self._execute_pipeline(cui, **kwargs)
        _in_flight_results[cui] = result
        return result
    finally:
        event.set()
        # Cleanup after 10 min (jobs run 2-5 min, buffer for late joiners)
        async def _cleanup():
            await asyncio.sleep(600)
            _in_flight.pop(cui, None)
            _in_flight_results.pop(cui, None)
        asyncio.create_task(_cleanup())
```

**Complexitate:** Mica | **Impact:** Mare — previne memory leak si infinite waits

---

### 3. Error handling: Standardizare HTTPException → RISError

**Fisiere:** `backend/routers/batch.py`, `companies.py`, `compare.py`, `monitoring.py`, `reports.py`
**Problema actuala:** ErrorCode enum definit in `errors.py` cu 26 coduri, dar ~90% din routere folosesc HTTPException direct. Frontend-ul asteapta `error_code` dar primeste `detail` in cele mai multe cazuri.

**Imbunatatire propusa:**
- Inlocuieste HTTPException cu RISError in toate routerele
- Frontend primeste consistent: `{error_code: "RATE_LIMITED", message: "...", details: {...}}`

**Exemplu implementare:**
```python
# batch.py — INAINTE:
raise HTTPException(status_code=429, detail="Maximum 2 batch-uri simultane")

# batch.py — DUPA:
from backend.errors import RISError, ErrorCode
raise RISError(ErrorCode.RATE_LIMITED, "Maximum 2 batch-uri simultane")

# companies.py — INAINTE:
raise HTTPException(status_code=404, detail="Company not found")

# companies.py — DUPA:
raise RISError(ErrorCode.JOB_NOT_FOUND, "Firma nu a fost gasita")
```

**Complexitate:** Mica | **Impact:** Mediu — consistenta error handling frontend-backend

---

### 4. api.ts: Wrap missing report endpoints (download, one_pager, send-email)

**Fisier:** `frontend/src/lib/api.ts`
**Problema actuala:** 4 backend endpoints au frontend consumers care folosesc `fetch()` direct, bypassing centralized error handling, timeout, logging:
- `GET /api/reports/{id}/download/{format}` — download direct
- `GET /api/reports/{id}/download/one_pager` — download direct
- `POST /api/reports/{id}/send-email` — signature mismatch
- `POST /api/compare/report` — returns Blob, unwrapped

**Imbunatatire propusa:**
- Adauga metode wrapper in api.ts
- Aliniaza signature send-email (backend + frontend)

**Exemplu implementare:**
```typescript
// api.ts — adauga:
downloadReport: async (reportId: string, format: string): Promise<Blob> => {
  const res = await fetch(`${BASE}/reports/${reportId}/download/${format}`);
  if (!res.ok) throw new ApiError(res.status, `Download ${format} failed`);
  return res.blob();
},

downloadOnePager: async (reportId: string): Promise<Blob> => {
  const res = await fetch(`${BASE}/reports/${reportId}/download/one_pager`);
  if (!res.ok) throw new ApiError(res.status, "Download one-pager failed");
  return res.blob();
},

sendReportEmail: async (reportId: string, data: {
  to: string; subject: string; message?: string;
}): Promise<{success: boolean}> => {
  return request(`/reports/${reportId}/send-email`, {
    method: "POST",
    body: JSON.stringify(data),
  });
},

downloadCompareReport: async (cui1: string, cui2: string): Promise<Blob> => {
  const res = await fetch(`${BASE}/compare/report`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({cui_1: cui1, cui_2: cui2}),
  });
  if (!res.ok) throw new ApiError(res.status, "Compare report failed");
  return res.blob();
},
```

**Complexitate:** Mica | **Impact:** Mediu — centralized error handling + logging pe TOATE call-urile

---

### 5. WebSocket: Broadcast error handling + agent-level messages

**Fisier:** `backend/main.py` — linia ~456-474, `backend/services/job_service.py`
**Problema actuala:**
- `broadcast()` nu catcha ConnectionError cand clientul se deconecteaza mid-send
- Frontend defineste `agent_complete` si `agent_warning` message types in types.ts dar backend-ul NU le trimite niciodata
- Daca clientul se deconecteaza in timpul broadcast, poate genera crash

**Imbunatatire propusa:**
- Adauga try/except in broadcast per connection
- Trimite mesaje agent_complete din orchestrator la finalul fiecarui agent
- Remove dead types din frontend SAU implementeaza trimiterea

**Exemplu implementare:**
```python
# main.py — fix broadcast:
async def broadcast(self, job_id: str, message: dict):
    if job_id in self.active_connections:
        dead = []
        for ws in self.active_connections[job_id]:
            try:
                await ws.send_json(message)
            except (WebSocketDisconnect, RuntimeError, ConnectionResetError):
                dead.append(ws)
        for ws in dead:
            try:
                self.active_connections[job_id].remove(ws)
            except ValueError:
                pass

# orchestrator.py — agent progress messages:
async def _run_agent_with_progress(self, agent, state, agent_name, job_id):
    await manager.broadcast(job_id, {
        "type": "agent_start", "agent": agent_name
    })
    result = await agent.run(state)
    await manager.broadcast(job_id, {
        "type": "agent_complete", "agent": agent_name,
        "duration_ms": int(elapsed * 1000)
    })
    return result
```

**Complexitate:** Medie | **Impact:** Mediu — previne crash-uri + progress granular pe frontend

---

### 6. Cache L1/L2: TTL sync + LRU fix

**Fisier:** `backend/services/cache_service.py` — linia ~94-157
**Problema actuala:**
- L1 hit NU refresheaza TTL in L2 → date stale servite din L1 dupa ce L2 a expirat
- L1 put se face DUPA L2 set → fereastra scurta unde L2 e fresh dar L1 e stale
- LRU eviction doar la INSERT, nu la fiecare fetch (hot data nu e mutat la sfarsit)

**Imbunatatire propusa:**
- La L1 hit, touch L2 expiry (optional, lazy)
- La L1 put, faci put INAINTE de L2 (sau atomic)
- La L1 get, move entry la sfarsitul OrderedDict (true LRU)

**Exemplu implementare:**
```python
# cache_service.py — L1Cache.get() fix:
def get(self, key: str) -> Any | None:
    with self._lock:
        if key in self._store:
            value, expires_at = self._store[key]
            if time.time() < expires_at:
                # Move to end for true LRU
                self._store.move_to_end(key)
                return value
            else:
                del self._store[key]
        return None

# cache_service.py — get_or_fetch() fix order:
async def get_or_fetch(self, key, fetch_fn, ttl, source):
    # Check L1 first
    cached = self._l1.get(key)
    if cached is not None:
        self._stats[source]["hits"] += 1
        return cached
    
    # Check L2
    cached = await self._get_l2(key)
    if cached is not None:
        self._l1.put(key, cached)  # Populate L1 from L2
        self._stats[source]["hits"] += 1
        return cached
    
    # Fetch with lock
    self._stats[source]["misses"] += 1
    result = await self._locked_fetch(key, fetch_fn)
    
    # Write L1 THEN L2 (L1 always has freshest)
    self._l1.put(key, result)
    await self._set_l2(key, result, ttl, source)
    return result
```

**Complexitate:** Mica | **Impact:** Mediu — elimina serving stale data + adevarata LRU eviction

---

### 7. Scoring: "Why?" explanations per dimensiune

**Fisier:** `backend/agents/verification/scoring.py` — linia ~41-685
**Problema actuala:** Scoring-ul calculeaza un numar (0-100) per dimensiune, dar NU explica DE CE. Utilizatorul vede "Financiar: 72/100" dar nu stie ce a contribuit pozitiv sau negativ. Risk factors sunt colectate dar nu expuse granular.

**Imbunatatire propusa:**
- Fiecare dimensiune returneaza lista de `reasons[]` cu impact (+/- puncte)
- Frontend afiseaza tooltip cu breakdown
- Pattern: `{score: 72, reasons: [{text: "CA > 1M RON", impact: +10}, {text: "Volatilitate ridicata (CV=0.6)", impact: -10}]}`

**Exemplu implementare:**
```python
# scoring.py — adauga reasons tracking:
def _score_financial(self, data: dict) -> dict:
    score = 70
    reasons = []
    
    ca = self._extract_value(data, "cifra_afaceri")
    if ca is not None:
        if ca > 10_000_000:
            score += 15
            reasons.append({"text": f"CA excelenta: {ca:,.0f} RON", "impact": 15})
        elif ca > 1_000_000:
            score += 10
            reasons.append({"text": f"CA buna: {ca:,.0f} RON", "impact": 10})
        elif ca <= 0:
            score -= 20
            reasons.append({"text": "CA zero sau negativa", "impact": -20})
    
    # ... similar for profit, trend, volatility, solvency
    
    return {
        "score": max(0, min(100, score)),
        "reasons": reasons,
        "weight": 0.30
    }
```

```typescript
// CompanyDetail.tsx — tooltip cu reasons:
{dimensions.map(dim => (
  <div key={dim.name} className="group relative">
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-400">{dim.name}</span>
      <div className="flex-1 bg-dark-border rounded h-2">
        <div className={`h-2 rounded ${scoreColor(dim.score)}`}
             style={{width: `${dim.score}%`}} />
      </div>
      <span className="text-sm font-mono">{dim.score}</span>
    </div>
    {/* Tooltip cu reasons */}
    <div className="hidden group-hover:block absolute z-10 bg-dark-card
                    border border-dark-border rounded-lg p-3 shadow-lg w-72">
      <p className="text-xs text-gray-400 mb-2">De ce {dim.score}/100:</p>
      {dim.reasons?.map((r, i) => (
        <div key={i} className="flex justify-between text-xs">
          <span>{r.text}</span>
          <span className={r.impact > 0 ? "text-green-400" : "text-red-400"}>
            {r.impact > 0 ? "+" : ""}{r.impact}
          </span>
        </div>
      ))}
    </div>
  </div>
))}
```

**Complexitate:** Medie | **Impact:** Maxim — transparenta scoring, utilizatorul intelege DE CE o firma are un anumit scor

---

### 8. GlobalSearch: Extindere la rapoarte + actiuni rapide

**Fisier:** `frontend/src/components/GlobalSearch.tsx`
**Problema actuala:** Ctrl+K cauta DOAR firme (companies). Nu cauta rapoarte, nu ofera actiuni rapide ("Analizeaza CUI X", "Compara firme").

**Imbunatatire propusa:**
- Adauga search in rapoarte (titlu, tip analiza)
- Adauga actiuni rapide (navigate, start analysis, compare)
- Grupeaza rezultatele: Firme | Rapoarte | Actiuni

**Exemplu implementare:**
```typescript
// GlobalSearch.tsx — extindere:
const QUICK_ACTIONS = [
  { label: "Analiza noua", icon: Plus, action: () => navigate("/new-analysis") },
  { label: "Compara firme", icon: GitCompare, action: () => navigate("/compare") },
  { label: "Batch analiza", icon: Upload, action: () => navigate("/batch") },
  { label: "Setari", icon: Settings, action: () => navigate("/settings") },
];

// In search handler:
const searchAll = async (query: string) => {
  const [companies, reports] = await Promise.all([
    api.listCompanies({ search: query, limit: 5 }),
    api.listReports({ search: query, limit: 5 }),
  ]);
  
  const matchingActions = QUICK_ACTIONS.filter(a =>
    a.label.toLowerCase().includes(query.toLowerCase())
  );
  
  // Check if query looks like a CUI
  const cuiMatch = query.match(/^\d{6,10}$/);
  if (cuiMatch) {
    matchingActions.unshift({
      label: `Analizeaza CUI ${query}`,
      icon: Search,
      action: () => navigate(`/new-analysis?cui=${query}`),
    });
  }
  
  return { companies: companies.items, reports: reports.items, actions: matchingActions };
};
```

**Complexitate:** Medie | **Impact:** Mare — cautare unificata peste tot sistemul

---

### 9. Synthesis: Fallback concurrent (nu secvential)

**Fisier:** `backend/agents/agent_synthesis.py` — linia ~104-122
**Problema actuala:** Cand provider-ul principal esueaza, synthesis-ul incearca urmatorii 4 provideri SECVENTIAL. Fiecare esec adauga 2-10s latenta. Worst case: 5 provideri x 10s = 50s pierdute inainte de fallback Tier 2.

**Imbunatatire propusa:**
- La esecul provider-ului 1, lanseaza urmatorii 2 provideri IN PARALEL
- Primul raspuns valid castiga (asyncio.wait FIRST_COMPLETED)
- Cancelleaza task-urile ramase

**Exemplu implementare:**
```python
# agent_synthesis.py — concurrent fallback:
async def _generate_section_with_fallback(self, section, prompt, route):
    providers = self._get_provider_order(route)
    
    # Try first provider normally
    try:
        result = await self._call_provider(providers[0], prompt)
        reset_provider_circuit(providers[0])
        return result
    except Exception as e:
        record_provider_failure(providers[0])
        logger.warning(f"Primary provider {providers[0]} failed: {e}")
    
    # Concurrent fallback: race remaining providers
    remaining = [p for p in providers[1:] if not is_provider_circuit_open(p)]
    if not remaining:
        return self._tier2_fallback(section)
    
    tasks = [
        asyncio.create_task(self._call_provider(p, prompt))
        for p in remaining[:3]  # Max 3 concurrent
    ]
    
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    
    for task in done:
        if not task.exception():
            return task.result()
    
    return self._tier2_fallback(section)
```

**Complexitate:** Medie | **Impact:** Mare — reduce fallback latency de la 50s la ~10s

---

### 10. Scoring: Normalizare volatilitate per industrie

**Fisier:** `backend/agents/verification/scoring.py` — linia ~187-189
**Problema actuala:** Volatility scoring penalizeaza CV > 0.5 uniform, dar constructii au natural CV 0.5-0.8, pe cand consultanta are CV 0.1-0.2. O firma de constructii "normala" primeste penalizare nejustificata.

**Imbunatatire propusa:**
- Adauga volatility baselines per sector CAEN (sectiune majora A-U)
- Penalizeaza doar cand CV depaseste baseline-ul sectorului cu >50%

**Exemplu implementare:**
```python
# scoring.py — sector-aware volatility:
SECTOR_VOLATILITY_BASELINE = {
    "F": 0.60,  # Constructii — natural volatile
    "A": 0.50,  # Agricultura — sezonier
    "C": 0.35,  # Manufacturing
    "G": 0.30,  # Comert
    "J": 0.25,  # IT
    "M": 0.20,  # Consultanta
    "DEFAULT": 0.35,
}

def _penalize_volatility(self, cv: float, caen_section: str) -> tuple[int, str]:
    baseline = SECTOR_VOLATILITY_BASELINE.get(
        caen_section, SECTOR_VOLATILITY_BASELINE["DEFAULT"]
    )
    ratio = cv / baseline if baseline > 0 else cv / 0.35
    
    if ratio > 2.0:
        return -10, f"Volatilitate extrema (CV={cv:.2f}, sectorul are baseline {baseline:.2f})"
    elif ratio > 1.5:
        return -5, f"Volatilitate ridicata vs sector (CV={cv:.2f})"
    else:
        return 0, None  # Normal for sector
```

**Complexitate:** Mica | **Impact:** Mediu — scoring mai corect per context de industrie

---

### 11. Companies: Sortare + filtrare avansata

**Fisier:** `frontend/src/pages/Companies.tsx`
**Problema actuala:** Lista de firme permite doar search si paginare. NU exista sortare (dupa nume, scor, data, nr analize) sau filtre avansate (dupa judet, CAEN, scor minim).

**Imbunatatire propusa:**
- Adauga dropdown sort (A-Z, scor desc, ultima analiza, nr analize)
- Adauga filtre: judet, CAEN section, scor minim
- Persistent URL params (sa poti share un URL filtrat)

**Exemplu implementare:**
```typescript
// Companies.tsx — sort + filter:
const SORT_OPTIONS = [
  { value: "name_asc", label: "Nume A-Z" },
  { value: "name_desc", label: "Nume Z-A" },
  { value: "score_desc", label: "Scor (mare → mic)" },
  { value: "score_asc", label: "Scor (mic → mare)" },
  { value: "last_analyzed", label: "Ultima analiza" },
  { value: "analysis_count", label: "Nr. analize" },
];

// In URL params:
const [searchParams, setSearchParams] = useSearchParams();
const sort = searchParams.get("sort") || "last_analyzed";
const county = searchParams.get("county") || "";
const minScore = parseInt(searchParams.get("min_score") || "0");

// Pass to API:
const { data } = await api.listCompanies({
  search, page, sort, county, min_score: minScore
});
```

```python
# companies.py — backend sort support:
@router.get("/")
async def list_companies(
    search: str = "", page: int = 0, limit: int = 20,
    sort: str = "last_analyzed",
    county: str = None, min_score: int = None,
):
    ORDER_MAP = {
        "name_asc": "c.name ASC",
        "name_desc": "c.name DESC",
        "score_desc": "COALESCE(latest_score, 0) DESC",
        "last_analyzed": "c.last_analyzed_at DESC",
        "analysis_count": "c.analysis_count DESC",
    }
    order = ORDER_MAP.get(sort, "c.last_analyzed_at DESC")
    # ... build WHERE + ORDER BY
```

**Complexitate:** Medie | **Impact:** Mare — UX fundamental — utilizatorul gaseste firme mult mai rapid

---

### 12. Toast: Deduplicare mesaje identice

**Fisier:** `frontend/src/components/Toast.tsx`
**Problema actuala:** 100 erori identice = 100 toast-uri stacked. API error retry genereaza toast spam.

**Imbunatatire propusa:**
- Dedup pe mesaj: daca toast cu acelasi text exista deja, incrementeaza counter
- Afiseaza "(x3)" langa mesaj

**Exemplu implementare:**
```typescript
// Toast.tsx — dedup:
const addToast = useCallback((type: ToastType, message: string) => {
  setToasts(prev => {
    const existing = prev.find(t => t.message === message && t.type === type);
    if (existing) {
      return prev.map(t =>
        t.id === existing.id
          ? { ...t, count: (t.count || 1) + 1, timestamp: Date.now() }
          : t
      );
    }
    return [...prev, { id: Date.now(), type, message, count: 1, timestamp: Date.now() }];
  });
}, []);

// In render:
<span>{toast.message}{toast.count > 1 && ` (x${toast.count})`}</span>
```

**Complexitate:** Mica | **Impact:** Mic — previne toast spam, UX mai curat

---

### 13. Favorites: Foloseste endpoint backend dedicat

**Fisier:** `frontend/src/pages/Companies.tsx` — linia ~55-72
**Problema actuala:** Backend are `GET /api/companies/favorites` dar frontend-ul nu il foloseste niciodata. In schimb, apeleaza `listCompanies()` si filtreaza client-side. Ineficient la 100+ firme.

**Imbunatatire propusa:**
- Cand filtrul "Favorites" e activ, apeleaza `GET /api/companies/favorites` direct
- Reduce payload si procesare client-side

**Exemplu implementare:**
```typescript
// Companies.tsx — use dedicated endpoint:
useEffect(() => {
  const load = async () => {
    setLoading(true);
    try {
      const data = showFavoritesOnly
        ? await api.listFavorites()  // dedicated endpoint
        : await api.listCompanies({ search: debouncedSearch, page, limit: 20 });
      setCompanies(data.items || data);
      setTotal(data.total || data.length);
    } finally {
      setLoading(false);
    }
  };
  load();
}, [debouncedSearch, page, showFavoritesOnly]);
```

```typescript
// api.ts — adauga:
listFavorites: () => request<Company[]>("/companies/favorites"),
```

**Complexitate:** Mica | **Impact:** Mic — performance optimization la volum mare

---

### 14. Dashboard: Skeleton UI in loc de spinner

**Fisier:** `frontend/src/pages/Dashboard.tsx`
**Problema actuala:** La loading, Dashboard-ul afiseaza un spinner generic. Pattern-ul modern este skeleton UI — placeholder-uri gri animate care arata structura datelor inainte de incarcare. Perceptia de viteza creste semnificativ.

**Imbunatatire propusa:**
- Inlocuieste spinner cu skeleton cards
- Aplica si pe Companies, ReportsList

**Exemplu implementare:**
```typescript
// Dashboard.tsx — skeleton:
const SkeletonCard = () => (
  <div className="card animate-pulse">
    <div className="h-4 bg-dark-border rounded w-1/3 mb-3" />
    <div className="h-8 bg-dark-border rounded w-2/3 mb-2" />
    <div className="h-3 bg-dark-border rounded w-1/2" />
  </div>
);

const SkeletonDashboard = () => (
  <div className="space-y-6">
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="card animate-pulse h-64" />
      <div className="card animate-pulse h-64" />
    </div>
  </div>
);

// In render:
if (loading) return <SkeletonDashboard />;
```

**Complexitate:** Mica | **Impact:** Mediu — perceptie de viteza si profesionalism UI

---

## PARTEA II — FUNCTII NOI

---

### 15. FTS5 Full-Text Search pe companies + reports

**Descriere:** Implementeaza cautare full-text cu SQLite FTS5 (BM25 ranking, prefix search) pe firme si rapoarte. Inlocuieste `LIKE '%...%'` cu performanta de 10-100x mai buna si rezultate ranked by relevance.

**De ce e util:** Cautarea globala (Ctrl+K) si search-ul din Companies depind de LIKE care e lent la 1000+ firme si nu rankuieste rezultatele. FTS5 e built-in SQLite, zero dependinte noi.

**Complexitate:** Medie | **Impact:** Mare

**Exemplu implementare:**
```sql
-- migration 005_fts5.sql:
CREATE VIRTUAL TABLE IF NOT EXISTS companies_fts USING fts5(
    name, caen_description, county, city,
    content='companies',
    content_rowid='id',
    tokenize='unicode61'
);

-- Populate:
INSERT INTO companies_fts(rowid, name, caen_description, county, city)
SELECT id, name, caen_code, county, city FROM companies;

-- Triggers to keep in sync:
CREATE TRIGGER companies_ai AFTER INSERT ON companies BEGIN
    INSERT INTO companies_fts(rowid, name, caen_description, county, city)
    VALUES (new.id, new.name, new.caen_code, new.county, new.city);
END;

CREATE TRIGGER companies_ad AFTER DELETE ON companies BEGIN
    INSERT INTO companies_fts(companies_fts, rowid, name, caen_description, county, city)
    VALUES('delete', old.id, old.name, old.caen_code, old.county, old.city);
END;

CREATE TRIGGER companies_au AFTER UPDATE ON companies BEGIN
    INSERT INTO companies_fts(companies_fts, rowid, name, caen_description, county, city)
    VALUES('delete', old.id, old.name, old.caen_code, old.county, old.city);
    INSERT INTO companies_fts(rowid, name, caen_description, county, city)
    VALUES (new.id, new.name, new.caen_code, new.county, new.city);
END;
```

```python
# companies.py — FTS5 search:
@router.get("/search")
async def search_companies(q: str = Query(..., min_length=2)):
    async with get_db() as db:
        rows = await db.execute_fetchall("""
            SELECT c.*, rank
            FROM companies_fts fts
            JOIN companies c ON c.id = fts.rowid
            WHERE companies_fts MATCH ?
            ORDER BY rank
            LIMIT 20
        """, (f"{q}*",))  # Prefix search
        return [dict(r) for r in rows]
```

---

### 16. React 19.2: `useOptimistic` pentru toggle-uri instant

**Descriere:** Foloseste `useOptimistic` hook din React 19.2 pentru actiuni ca toggle favorite, add to monitoring, mark notification read — UI update instant, rollback la eroare.

**De ce e util:** Acum toggle favorite asteapta raspunsul API (200-500ms latenta vizibila). Cu `useOptimistic`, star-ul se coloreaza INSTANT, rollback doar daca API esueaza.

**Complexitate:** Mica | **Impact:** Mediu

**Exemplu implementare:**
```typescript
// Companies.tsx — optimistic favorite:
import { useOptimistic } from "react";

function CompanyCard({ company }: { company: Company }) {
  const [optimisticFav, setOptimisticFav] = useOptimistic(
    company.is_favorite,
    (_current, next: boolean) => next
  );

  const toggleFav = async () => {
    setOptimisticFav(!optimisticFav);  // Instant UI update
    try {
      await api.toggleFavorite(company.id);
    } catch {
      // Rollback happens automatically (optimistic state resets)
      toast.error("Eroare la toggle favorit");
    }
  };

  return (
    <button onClick={toggleFav}>
      <Star className={optimisticFav ? "fill-yellow-400 text-yellow-400" : "text-gray-600"} />
    </button>
  );
}
```

---

### 17. Report Deltas: Endpoint + UI pentru change tracking

**Descriere:** Tabela `report_deltas` exista in DB si e populata la fiecare analiza noua, dar NU exista endpoint de fetch si NU exista UI. Utilizatorul nu poate vedea "ce s-a schimbat de la ultima analiza".

**De ce e util:** Utilizatorii care monitorizeaza firme au nevoie sa vada rapid CE s-a schimbat, nu sa compare manual 2 rapoarte.

**Complexitate:** Medie | **Impact:** Mare

**Exemplu implementare:**
```python
# reports.py — endpoint nou:
@router.get("/{report_id}/delta")
async def get_report_delta(report_id: str):
    async with get_db() as db:
        delta = await db.execute_fetchone(
            "SELECT * FROM report_deltas WHERE report_id = ?", (report_id,)
        )
        if not delta:
            return {"has_delta": False, "message": "Prima analiza — fara date anterioare"}
        
        changes = json.loads(delta["changes_json"])
        return {
            "has_delta": True,
            "previous_report_id": delta["previous_report_id"],
            "changes": changes,
            "previous_score": delta["previous_score"],
            "current_score": delta["current_score"],
            "score_delta": delta["current_score"] - delta["previous_score"],
        }
```

```typescript
// ReportView.tsx — delta tab:
const DeltaView = ({ reportId }: { reportId: string }) => {
  const [delta, setDelta] = useState<ReportDelta | null>(null);
  
  useEffect(() => {
    api.getReportDelta(reportId).then(setDelta);
  }, [reportId]);
  
  if (!delta?.has_delta) return <p className="text-gray-500">Prima analiza</p>;
  
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold">
          Scor: {delta.previous_score} → {delta.current_score}
        </span>
        <span className={delta.score_delta > 0 ? "text-green-400" : "text-red-400"}>
          ({delta.score_delta > 0 ? "+" : ""}{delta.score_delta})
        </span>
      </div>
      {delta.changes.map((c, i) => (
        <div key={i} className="flex justify-between border-b border-dark-border pb-2">
          <span className="text-gray-400">{c.field}</span>
          <span><s className="text-red-400">{c.old}</s> → <b className="text-green-400">{c.new}</b></span>
        </div>
      ))}
    </div>
  );
};
```

---

### 18. fpdf2 Markdown Pipeline: Sinteza AI direct in Markdown → PDF

**Descriere:** fpdf2 v2.8+ suporta `cell(markdown=True)` si `write_html()` cu `markdown-it-py`. Sinteza AI poate genera direct Markdown, renderizat nativ in PDF fara conversie intermediara.

**De ce e util:** Acum sinteza genereaza text plain care e procesat manual pentru formatare PDF. Cu Markdown pipeline, bold/italic/liste/tabele apar automat in PDF.

**Complexitate:** Medie | **Impact:** Mare

**Exemplu implementare:**
```python
# pdf_generator.py — markdown rendering:
from fpdf import FPDF

def _render_section_markdown(self, pdf: FPDF, title: str, markdown_text: str):
    """Render markdown text directly in PDF."""
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    pdf.set_font("DejaVu", "", 10)
    # fpdf2 markdown support: **bold**, __italic__, ~~strike~~
    for line in markdown_text.split("\n"):
        if line.startswith("# "):
            pdf.set_font("DejaVu", "B", 13)
            pdf.cell(0, 8, line[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("DejaVu", "", 10)
        elif line.startswith("- ") or line.startswith("* "):
            pdf.cell(5)
            pdf.cell(0, 6, f"  \u2022 {line[2:]}", markdown=True, new_x="LMARGIN", new_y="NEXT")
        elif line.strip():
            pdf.multi_cell(0, 6, line, markdown=True)
        else:
            pdf.ln(3)
```

---

### 19. Window Functions SQL: Trend calculus nativ in DB

**Descriere:** Inlocuieste calculul de trend/delta din Python cu window functions SQL (LAG, LEAD, running SUM) — mai rapid, mai corect, mai simplu.

**De ce e util:** Scoring-ul face acum trend calculation in Python cu loop-uri. LAG/LEAD in SQL sunt 10x mai rapide si corecte by design.

**Complexitate:** Mica | **Impact:** Mediu

**Exemplu implementare:**
```sql
-- Score trend cu LAG:
SELECT
    company_id,
    created_at,
    numeric_score,
    LAG(numeric_score) OVER (PARTITION BY company_id ORDER BY created_at) AS prev_score,
    numeric_score - LAG(numeric_score) OVER (PARTITION BY company_id ORDER BY created_at) AS score_delta,
    NTILE(10) OVER (ORDER BY numeric_score DESC) AS decile
FROM score_history
WHERE company_id = ?
ORDER BY created_at DESC;
```

```python
# companies.py — score trend query:
@router.get("/{company_id}/score-trend")
async def get_score_trend(company_id: int):
    async with get_db() as db:
        rows = await db.execute_fetchall("""
            SELECT
                created_at,
                numeric_score as score,
                numeric_score - LAG(numeric_score) OVER (ORDER BY created_at) as delta
            FROM score_history
            WHERE company_id = ?
            ORDER BY created_at
        """, (company_id,))
        return [dict(r) for r in rows]
```

---

### 20. NLQ Chatbot "Ask RIS" — Intrebari in limba romana

**Descriere:** Chatbot integrat in Dashboard care permite intrebari in limba romana: "Care firma are cel mai mare risc?", "Cat a facturat firma X in 2024?", "Cate analize am facut luna asta?". Traduce intrebari in query-uri SQL/API.

**De ce e util:** Trend 2026 #1 in BI tools. Utilizatorul non-tehnic obtine raspunsuri fara sa navigheze prin pagini.

**Complexitate:** Mare | **Impact:** Maxim

**Exemplu implementare:**
```python
# routers/ask.py — NLQ endpoint:
@router.post("/ask")
async def ask_ris(request: AskRequest):
    """Natural Language Query over RIS data."""
    # Classify intent
    intent = await _classify_intent(request.question)
    
    QUERY_MAP = {
        "highest_risk": "SELECT name, cui FROM companies ORDER BY last_risk_score ASC LIMIT 5",
        "company_revenue": "SELECT json_extract(data, '$.cifra_afaceri') FROM reports WHERE company_cui = ?",
        "monthly_stats": "SELECT COUNT(*) FROM jobs WHERE created_at > date('now', '-30 days')",
    }
    
    if intent.type in QUERY_MAP:
        result = await db.execute_fetchall(QUERY_MAP[intent.type], intent.params)
        answer = _format_answer(intent, result)
        return {"answer": answer, "confidence": intent.confidence, "source": "database"}
    
    # Fallback: AI-powered answer from context
    return {"answer": "Nu am gasit date relevante. Incearca sa reformulezi.", "confidence": 0.3}
```

---

## PARTEA III — IMBUNATATIRI TEHNICE

---

### 21. Input validation: Bounds pe limit/offset/report_level

**Problema:** `limit` si `offset` din query params nu au bounds. Un request cu `limit=999999` returneaza tot DB-ul. `report_level` accepta orice int (ar trebui 1-3). `analysis_type` nu e validat contra enum.
**Solutie:** Adauga Pydantic constraints sau Query bounds pe toate endpoint-urile.
**Complexitate:** Mica | **Impact:** Securitate — previne data exfiltration

```python
# Exemplu fix in routers:
from fastapi import Query

@router.get("/")
async def list_companies(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str = Query("last_analyzed", regex="^(name_asc|name_desc|score_desc|last_analyzed|analysis_count)$"),
):
    ...

# models.py — report_level validation:
class JobCreateRequest(BaseModel):
    report_level: int = Field(default=2, ge=1, le=3)
    analysis_type: str  # validated in router against ANALYSIS_TYPES_META keys
```

---

### 22. SSRF prevention pe httpx requests

**Problema:** `http_client.py` face fetch-uri catre URL-uri externe (ANAF, BNR, Tavily). Daca URL-ul e configurat gresit sau manipulat, ar putea accesa IP-uri private (127.0.0.1, 10.x.x.x). OWASP 2025 claseaza SSRF ca risc TOP.
**Solutie:** Validare URL inainte de request — blocheaza IP ranges private.
**Complexitate:** Mica | **Impact:** Securitate HIGH

```python
# http_client.py — SSRF protection:
import ipaddress
from urllib.parse import urlparse

BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
]

def validate_url(url: str) -> bool:
    """Block requests to private/internal IPs."""
    parsed = urlparse(url)
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        return not any(ip in net for net in BLOCKED_RANGES)
    except ValueError:
        return True  # Hostname, not IP — OK (DNS resolves externally)
```

---

### 23. Dead code cleanup: markets table + WS types

**Problema:** Tabela `markets` (001_initial.sql) nu e populata si nu e referita din niciun router sau service. WebSocket message types `agent_complete` si `agent_warning` definite in frontend types.ts dar niciodata trimise de backend.
**Solutie:** Elimina markets table (sau implementeaza). Elimina WS types nefolosite SAU implementeaza trimiterea.
**Complexitate:** Mica | **Impact:** Mentenanta — reduce confuzia

---

### 24. Path traversal hardening in jobs router

**Problema:** `routers/jobs.py:185` construieste `log_path = os.path.join("logs", f"job_{job_id}.log")` fara validare explicita. Daca `job_id` contine `../`, ar putea accesa fisiere in afara directorului `logs/`.
**Solutie:** Validare UUID + resolve path check.
**Complexitate:** Mica | **Impact:** Securitate MEDIUM

```python
# jobs.py — path validation:
import re
from pathlib import Path

def _safe_log_path(job_id: str) -> Path:
    if not re.match(r'^[a-f0-9\-]{36}$', job_id):
        raise HTTPException(400, "Invalid job ID format")
    log_path = (Path("logs") / f"job_{job_id}.log").resolve()
    if not log_path.is_relative_to(Path("logs").resolve()):
        raise HTTPException(403, "Access denied")
    return log_path
```

---

### 25. pip-audit + npm audit periodic

**Problema:** Nicio scanare periodica de vulnerabilitati in dependinte. requirements.txt si package.json pot contine pachete cu CVE-uri cunoscute.
**Solutie:** Adauga comanda in RIS_TEST.bat sau script separat.
**Complexitate:** Mica | **Impact:** Securitate

```bat
REM In RIS_TEST.bat — adauga:
echo === SECURITY AUDIT ===
pip-audit --requirement requirements.txt --desc 2>>TEST_RESULTS.log
cd frontend && npm audit --production 2>>../TEST_RESULTS.log
```

---

### 26. Pydantic `extra = "forbid"` pe API models

**Problema:** Modelele Pydantic din `models.py` accepta campuri extra (mass assignment risk). Un request cu `{"cui": "123", "is_admin": true}` nu ar fi respins.
**Solutie:** Adauga `model_config = ConfigDict(extra="forbid")` pe toate modelele de request.
**Complexitate:** Mica | **Impact:** Securitate

```python
# models.py:
from pydantic import ConfigDict

class JobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cui: str
    analysis_type: str
    report_level: int = 2
    # ...
```

---

### 27. Frontend test coverage (26 module la 0%)

**Problema:** Doar `cui-validator.test.ts` exista (11 teste). 26 module frontend — inclusiv toate paginile, componente, hooks, api.ts — au ZERO teste.
**Solutie:** Prioritizeaza teste pentru: api.ts (cel mai critic), useWebSocket, Dashboard, NewAnalysis.
**Complexitate:** Mare | **Impact:** Calitate

---

### 28. Backend test gaps: API clients + services

**Problema:** 6 API clients (anaf, bnr, openapi, seap, tavily, retry) si 6 services (cache, job_logger, job_service, monitoring, notification, scheduler) au ZERO teste.
**Solutie:** Adauga unit tests cu mock-uri pentru fiecare client extern.
**Complexitate:** Mare | **Impact:** Calitate

---

### 29. Accessibility audit: ARIA + focus-visible

**Problema:** Icon-only buttons fara `aria-label`. Dropdowns fara keyboard navigation. Risk indicators bazate DOAR pe culoare (daltonism). Lipsa `focus-visible` styles.
**Solutie:** Audit si fix ARIA labels, keyboard nav, color + text indicators.
**Complexitate:** Medie | **Impact:** Accesibilitate

```tsx
// Fix exemplu — icon button:
<button
  onClick={toggleFav}
  aria-label={isFavorite ? "Elimina din favorite" : "Adauga la favorite"}
  className="focus-visible:ring-2 focus-visible:ring-accent-primary"
>
  <Star className={...} />
</button>

// Fix risk — culoare + text:
<span className={`${riskColor(score)} flex items-center gap-1`}>
  {score >= 70 ? "Verde" : score >= 40 ? "Galben" : "Rosu"}
  <span className="text-xs">({score})</span>
</span>
```

---

### 30. Token budget: Elimina prompt double-build

**Problema:** `agent_synthesis.py:79-82` construieste prompt-ul DE 2 ORI — o data pentru token check, o data pentru generare. La prompt-uri mari (50K+ chars), asta adauga 100-200ms per sectiune.
**Solutie:** Construieste prompt-ul O SINGURA DATA, apoi verifica tokens pe rezultat.
**Complexitate:** Mica | **Impact:** Performanta

```python
# agent_synthesis.py — fix:
async def _generate_section(self, section, data, route):
    # Build prompt ONCE
    prompt = self._build_prompt(section, data)
    
    # Check token budget on already-built prompt
    estimated_tokens = len(prompt) // 4
    provider = self._select_provider(route, estimated_tokens)
    
    # Generate with selected provider
    return await self._call_provider(provider, prompt)
```

---

## PARTEA IV — DESCOPERIRI AUDIT R4 (2026-04-04)

Items noi descoperite prin audit complet pe 12 domenii. Nu existau in R3.

---

### 31. `.env.bak*` nu sunt in `.gitignore` — BLOCKER SECURITATE

**Fisier:** `.gitignore`
**Problema:** 4 fisiere `.env.bak.XXXXXXXXXX` sunt vizibile in `git status` ca untracked. Contin chei API reale. Un `git add .` accidental le commite in repo public.
**Severitate:** CRITICA | **Complexitate:** Minima

**Fix — 2 pasi:**
```bash
# 1. Adauga in .gitignore:
echo ".env.bak*" >> .gitignore
echo "*.env.bak*" >> .gitignore

# 2. Sterge fisierele local:
del .env.bak.1774988819 .env.bak.1774988878 .env.bak.1775057740 .env.bak.1775057788
```

---

### 32. `datetime.now()` fara UTC — 4 locatii ramase

**Fisiere:**
- `backend/agents/agent_verification.py:686` — calcul varsta firma (naive vs aware → eroare)
- `backend/services/monitoring_service.py:188` — timestamp mesaj verificare
- `backend/services/monitoring_service.py:274` — timestamp mesaj alert
- `backend/services/scheduler.py:155` — data backup (doar format string, risc mic)

**Problema:** Calcul `age_years = (datetime.now() - inreg_date).days / 365.25` combina datetime naive (now) cu aware (inreg_date din ANAF) → `TypeError` sau rezultat gresit daca server e in alt timezone.
**Severitate:** HIGH | **Complexitate:** Minima

**Fix:**
```python
# agent_verification.py:686:
from datetime import UTC
age_years = (datetime.now(UTC) - inreg_date).days / 365.25

# monitoring_service.py:188 si 274:
f"Verificat: {datetime.now(UTC).strftime('%d.%m.%Y %H:%M')}"

# scheduler.py:155:
date_str = datetime.now(UTC).strftime("%Y-%m-%d")
```

---

### 33. Database: auto-commit fara tranzactii pentru operatii multi-step

**Fisier:** `backend/database.py:40-43`
**Problema:** Fiecare `execute()` face commit imediat. Daca un job creeaza company + report + score_history (3 operatii), si operatia 2 esueaza, company ramane fara report — date inconsistente in DB.
**Severitate:** HIGH | **Complexitate:** Mica

**Fix — context manager tranzactie:**
```python
# database.py — adauga metoda:
from contextlib import asynccontextmanager

@asynccontextmanager
async def transaction(self):
    """Context manager for atomic multi-step operations."""
    try:
        yield self
        await self.db.commit()
    except Exception:
        await self.db.rollback()
        raise

# Utilizare in job_service.py:
async with db.transaction():
    await db.execute("INSERT INTO companies ...", ...)
    await db.execute("INSERT INTO reports ...", ...)
    await db.execute("INSERT INTO score_history ...", ...)
```

---

### 34. Full JSON report fara paginare (>500KB payload)

**Fisier:** `backend/routers/reports.py:70-107`
**Problema:** `GET /api/reports/{id}` returneaza `full_data` JSON complet (>500KB cu toate datele de verificare). Frontend incarca tot, inclusiv pe mobile. Fara streaming, fara lazy-load.
**Severitate:** HIGH | **Complexitate:** Mica

**Fix — returneaza summary + lazy-load sectiuni:**
```python
# reports.py — split in 2 endpoint-uri:
@router.get("/{report_id}")
async def get_report_summary(report_id: str):
    """Returneaza metadata + scor. Fara full_data."""
    row = await db.fetch_one("SELECT id, job_id, company_name, numeric_score, ... FROM reports WHERE id = ?", (report_id,))
    return dict(row)

@router.get("/{report_id}/data")
async def get_report_data(report_id: str, section: str | None = None):
    """Returneaza full_data, optional filtrat per sectiune."""
    row = await db.fetch_one("SELECT full_data FROM reports WHERE id = ?", (report_id,))
    data = json.loads(row["full_data"])
    if section:
        return {section: data.get(section)}
    return data
```

---

### 35. 22x `except Exception: pass` — lista completa + fix

**Fisiere si locatii:**

| Fisier | Linia | Context | Fix recomandat |
|--------|-------|---------|----------------|
| `main.py` | 59, 331, 376, 385, 484 | WS dead conn, health check, Tavily, disk, WS recv | `logger.debug(...)` |
| `agents/agent_official.py` | 229 | Tavily quota check | `logger.debug(...)` |
| `routers/companies.py` | 21, 183, 187, 249 | is_favorite col, toggle, migration, monitoring | `logger.debug(...)` |
| `routers/compare.py` | 83, 119, 172 | bilant, compare history, fallback scoring | `logger.warning(...)` |
| `routers/batch.py` | 306 | CSV row build | `logger.warning(...)` |
| `services/scheduler.py` | 34 | sleep prevention | `logger.debug(...)` |
| `services/job_logger.py` | 269 | Summary log | `logger.warning(...)` |
| `services/monitoring_service.py` | 114 | Check company | `logger.warning(...)` |
| `services/job_service.py` | 34, 41, 373 | sleep prevention (2x), notification | `logger.debug(...)` |
| `reports/pdf_generator.py` | 275 | Font fallback | `logger.debug(...)` |
| `agents/tools/caen_context.py` | 309 | INS TEMPO fetch | `logger.warning(...)` |

**Problema:** Exceptii swallowed fara logging → imposibil de diagnosticat erori in productie.
**Severitate:** HIGH | **Complexitate:** Mica

**Fix pattern:**
```python
# INAINTE:
except Exception:
    pass

# DUPA — pentru exceptii non-critice:
except Exception as e:
    logger.debug(f"[context] Non-critical error: {e}")

# DUPA — pentru exceptii care ar trebui monitorizate:
except Exception as e:
    logger.warning(f"[context] Unexpected error: {type(e).__name__}: {e}")
```

---

### 36. Settings endpoint fara autentificare

**Fisier:** `backend/routers/settings.py`
**Problema:** `GET /api/settings` si `PUT /api/settings` nu cer API key. Oricine din retea poate citi si modifica configuratia sistemului (Telegram token, email, API keys).
**Severitate:** MEDIUM | **Complexitate:** Minima

**Fix:**
```python
# settings.py — adauga dependency:
from backend.security import require_api_key
from fastapi import Depends

@router.get("", dependencies=[Depends(require_api_key)])
async def get_settings():
    ...

@router.put("", dependencies=[Depends(require_api_key)])
async def update_settings(...):
    ...
```

---

### 37. TypeScript: `noUnusedLocals` si `noUnusedParameters` dezactivate

**Fisier:** `frontend/tsconfig.json`
**Problema:** Variabile si parametri neutilizati nu sunt detectati la build. Acumuleaza dead code in componente.
**Severitate:** MEDIUM | **Complexitate:** Minima

**Fix:**
```json
// tsconfig.json — schimba:
{
  "compilerOptions": {
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```
Dupa activare: ruleaza `npx tsc --noEmit` si rezolva erorile gasite.

---

### 38. Race condition in stats cache (`_stats_cache`)

**Fisier:** `backend/main.py:411-440`
**Problema:** `_stats_cache` si `_stats_cache_time` sunt globale modificate fara Lock. Doua request-uri simultane la `/api/stats` pot ambele calcula stats si una suprascrie cealalta.
**Severitate:** MEDIUM | **Complexitate:** Minima

**Fix:**
```python
# main.py — adauga:
_stats_lock = asyncio.Lock()

@app.get("/api/stats")
async def get_stats():
    async with _stats_lock:
        now = time.time()
        if _stats_cache and (now - _stats_cache_time) < 30:
            return _stats_cache
        # compute stats...
        _stats_cache = result
        _stats_cache_time = now
        return result
```

---

### 39. is_favorite — mismatch contract API frontend-backend

**Fisier:** `backend/routers/companies.py:21` vs `frontend/src/pages/CompanyDetail.tsx:86`
**Problema:** Backend prinde exceptia si returneaza `{}` daca coloana `is_favorite` nu exista inca (migratie incompleta). Frontend citeste `company.is_favorite` si primeste `undefined` → star button broken silent.
**Severitate:** MEDIUM | **Complexitate:** Mica

**Fix:**
```python
# companies.py — asigura-te ca is_favorite e mereu prezent:
try:
    row = await db.fetch_one("SELECT *, COALESCE(is_favorite, 0) as is_favorite FROM companies WHERE id = ?", (company_id,))
except Exception:
    # Coloana nu exista — returneaza cu default
    row = await db.fetch_one("SELECT *, 0 as is_favorite FROM companies WHERE id = ?", (company_id,))
```

---

### 40. Index lipsa pe `score_history(company_id)` si `jobs(type, status)`

**Fisier:** `backend/migrations/004_improvements.sql` (sau creeaza 005)
**Problema:**
- `SELECT * FROM score_history WHERE company_id = ?` — full scan fara index
- `SELECT COUNT(*) FROM jobs WHERE type LIKE 'BATCH_%' AND status = 'RUNNING'` — scan fara index compozit

**Severitate:** MEDIUM | **Complexitate:** Minima

**Fix:**
```sql
-- adauga in migration:
CREATE INDEX IF NOT EXISTS idx_score_history_company
    ON score_history(company_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_type_status
    ON jobs(type, status);

CREATE INDEX IF NOT EXISTS idx_jobs_created_at
    ON jobs(created_at DESC);
```

---

### 41. `asyncio.sleep(2)` neconditionat pe cache hit in compare.py

**Fisier:** `backend/routers/compare.py:63, 86`
**Problema:** Rate limiting sleep de 2s se executa CHIAR SI cand datele vin din cache. O comparatie cu 2 firme deja in cache dureaza inutile 4+ secunde.
**Severitate:** MEDIUM | **Complexitate:** Minima

**Fix:**
```python
# compare.py — sleep doar la fetch real:
anaf_cached = await cache_service.get(cache_key)
if anaf_cached:
    anaf = anaf_cached
else:
    anaf = await get_anaf_data(cui)
    if anaf:
        await cache_service.set(cache_key, anaf, "anaf")
    await asyncio.sleep(2)  # Rate limit doar la fetch real
```

---

### 42. Config.py — validare lipseste pentru API keys obligatorii

**Fisier:** `backend/config.py`
**Problema:** Daca `TAVILY_API_KEY`, `GROQ_API_KEY` sau `ANTHROPIC_API_KEY` lipsesc din `.env`, aplicatia porneste normal dar esueaza la primul request cu erori criptice.
**Severitate:** MEDIUM | **Complexitate:** Minima

**Fix:**
```python
# config.py — adauga validator post-init:
from pydantic import model_validator

class Settings(BaseSettings):
    # ... campurile existente ...

    @model_validator(mode="after")
    def validate_critical_keys(self) -> "Settings":
        if not self.tavily_api_key:
            import warnings
            warnings.warn("TAVILY_API_KEY lipseste — cautarea web va fi dezactivata", stacklevel=2)
        if not self.groq_api_key and not self.anthropic_api_key:
            raise ValueError("Cel putin GROQ_API_KEY sau ANTHROPIC_API_KEY trebuie configurat in .env")
        return self
```

---

## SUMAR PRIORITATI

| Prioritate | # | Nume | Complexitate | Impact | Categorie | Sursa |
|---|---|---|---|---|---|---|
| **P0 — BLOCKER** | 31 | `.env.bak*` nu e in .gitignore — chei expuse | Minima | CRITICA | Audit R4 | Securitate |
| **P0 — URGENT** | 32 | `datetime.now()` fara UTC — 4 locatii | Minima | Mare | Audit R4 | Corectitudine |
| **P0 — URGENT** | 2 | Fix memory leak `_in_flight` dedup | Mica | Mare | R3 + Audit | Existenta |
| **P0 — URGENT** | 1 | Agent 1 timeout individual per task | Mica | Mare | R3 + Audit | Existenta |
| **P0 — URGENT** | 21 | Input validation bounds (limit, report_level) | Mica | Securitate | R3 + Audit | Tehnic |
| **P1 — IMPORTANT** | 33 | DB auto-commit fara tranzactii | Mica | HIGH | Audit R4 | Corectitudine |
| **P1 — IMPORTANT** | 34 | Full JSON report fara paginare (>500KB) | Mica | HIGH | Audit R4 | Performanta |
| **P1 — IMPORTANT** | 35 | 22x `except Exception: pass` — fix complet | Mica | HIGH | Audit R4 | Calitate |
| **P1 — IMPORTANT** | 7 | Scoring "Why?" explanations per dimensiune | Medie | Maxim | R3 | Existenta |
| **P1 — IMPORTANT** | 3 | Error handling standardizare HTTPException → RISError | Mica | Mediu | R3 | Existenta |
| **P1 — IMPORTANT** | 4 | api.ts wrap missing endpoints (download, email) | Mica | Mediu | R3 | Existenta |
| **P1 — IMPORTANT** | 5 | WebSocket broadcast fix + agent messages | Medie | Mediu | R3 + Audit | Existenta |
| **P1 — IMPORTANT** | 15 | FTS5 full-text search companies + reports | Medie | Mare | R3 | Noua |
| **P1 — IMPORTANT** | 22 | SSRF prevention pe httpx | Mica | Securitate | R3 | Tehnic |
| **P1 — IMPORTANT** | 24 | Path traversal hardening jobs router | Mica | Securitate | R3 | Tehnic |
| **P1 — IMPORTANT** | 23 | Dead code cleanup (markets, WS types) | Mica | Mentenanta | R3 | Tehnic |
| **P1 — IMPORTANT** | 25 | pip-audit + npm audit periodic | Mica | Securitate | R3 | Tehnic |
| **P2 — VALOROS** | 36 | Settings endpoint fara autentificare | Minima | MEDIUM | Audit R4 | Securitate |
| **P2 — VALOROS** | 37 | TypeScript `noUnusedLocals: false` | Minima | MEDIUM | Audit R4 | Calitate |
| **P2 — VALOROS** | 38 | Race condition stats cache `_stats_lock` | Minima | MEDIUM | Audit R4 | Corectitudine |
| **P2 — VALOROS** | 39 | `is_favorite` API contract mismatch | Mica | MEDIUM | Audit R4 | Corectitudine |
| **P2 — VALOROS** | 40 | Indexes lipsa (score_history + jobs) | Minima | MEDIUM | Audit R4 | Performanta |
| **P2 — VALOROS** | 41 | `asyncio.sleep(2)` neconditionat pe cache hit | Minima | MEDIUM | Audit R4 | Performanta |
| **P2 — VALOROS** | 42 | Config.py validare API keys obligatorii | Minima | MEDIUM | Audit R4 | Corectitudine |
| **P2 — VALOROS** | 9 | Synthesis concurrent fallback | Medie | Mare | R3 | Existenta |
| **P2 — VALOROS** | 6 | Cache L1/L2 TTL sync + LRU fix | Mica | Mediu | R3 | Existenta |
| **P2 — VALOROS** | 8 | GlobalSearch: rapoarte + actiuni | Medie | Mare | R3 | Existenta |
| **P2 — VALOROS** | 10 | Scoring volatilitate per industrie | Mica | Mediu | R3 | Existenta |
| **P2 — VALOROS** | 11 | Companies sortare + filtrare avansata | Medie | Mare | R3 | Existenta |
| **P2 — VALOROS** | 14 | Dashboard skeleton UI | Mica | Mediu | R3 | Existenta |
| **P2 — VALOROS** | 16 | React 19.2 useOptimistic toggles | Mica | Mediu | R3 | Noua |
| **P2 — VALOROS** | 17 | Report deltas endpoint + UI | Medie | Mare | R3 | Noua |
| **P2 — VALOROS** | 18 | fpdf2 Markdown pipeline | Medie | Mare | R3 | Noua |
| **P2 — VALOROS** | 19 | Window functions SQL trends | Mica | Mediu | R3 | Noua |
| **P2 — VALOROS** | 26 | Pydantic extra="forbid" | Mica | Securitate | R3 | Tehnic |
| **P2 — VALOROS** | 29 | Accessibility ARIA + focus | Medie | Accesibilitate | R3 | Tehnic |
| **P2 — VALOROS** | 30 | Token budget double-build fix | Mica | Performanta | R3 + Audit | Tehnic |
| **P3 — STRATEGIC** | 12 | Toast deduplicare mesaje | Mica | Mic | R3 | Existenta |
| **P3 — STRATEGIC** | 13 | Favorites endpoint dedicat | Mica | Mic | R3 | Existenta |
| **P3 — STRATEGIC** | 20 | NLQ "Ask RIS" chatbot | Mare | Maxim | R3 | Noua |
| **P3 — STRATEGIC** | 27 | Frontend test coverage (26 module la 0%) | Mare | Calitate | R3 + Audit | Tehnic |
| **P3 — STRATEGIC** | 28 | Backend test gaps (43 endpoints) | Mare | Calitate | R3 + Audit | Tehnic |

---

## NOTE IMPLEMENTARE

1. **Constrangere globala:** fpdf2 (NU WeasyPrint), SQLite (nu PostgreSQL), Windows 10. Toate solutiile trebuie sa functioneze local fara Docker/cloud.

2. **Dependinte intre recomandari:**
   - #15 (FTS5) ar trebui inainte de #8 (GlobalSearch upgrade) — search-ul devine mult mai rapid
   - #7 (Scoring Why) necesita modificari in scoring.py + frontend CompanyDetail + ReportView
   - #3 (Error standardization) ar trebui inainte de #4 (api.ts endpoints) — sa aiba aceeasi structura de erori
   - #21-26 (securitate) pot fi facute independent, in orice ordine

3. **Ce NU se schimba:** Stack-ul (FastAPI, React 19, SQLite, fpdf2), structura de directoare, API key management, LangGraph orchestration flow.

4. **Ordinea recomandata de implementare:**
   - **Sprint 0 (IMEDIAT, <1h):** #31 (.env.bak gitignore + delete), #32 (datetime UTC 4 locatii)
   - **Sprint 1 (P0/P1 critice):** #1, #2, #33, #35, #21 — timeout, memory leak, DB tranzactii, bare except, validation
   - **Sprint 2 (Securitate):** #36, #22, #24, #25, #26, #34 — settings auth, SSRF, path traversal, audit, paginare report
   - **Sprint 3 (Corectitudine):** #38, #39, #41, #42, #37, #40 — race conditions, mismatch, sleep, config, TS config, indexes
   - **Sprint 4 (P1 features):** #3, #4, #5, #7, #15 — error handling, FTS5, scoring Why
   - **Sprint 5 (P2 UX):** #8, #11, #14, #16, #17 — search, sort, skeleton, optimistic, deltas
   - **Sprint 6 (P2 backend):** #6, #9, #10, #18, #19, #30 — cache, synthesis, scoring, PDF, SQL
   - **Sprint 7 (P3):** #12, #13, #20, #23, #27-29 — polish, chatbot, tests, a11y

5. **Web research 2026 — trends relevante aplicate:**
   - FTS5 (#15) — recomandat de multiple surse pentru SQLite analytics
   - React 19.2 hooks (#16) — useOptimistic confirmat production-ready [CERT]
   - fpdf2 Markdown (#18) — suport nativ din v2.8+ [CERT]
   - SSRF (#22) — OWASP 2025 top risk [CERT]
   - NLQ (#20) — trend #1 in BI tools 2026 [CERT]
   - Skeleton UI (#14) — pattern UX standard 2026 [CERT]

---

**Document generat:** 2026-04-04 | **Versiune:** 3.1 | **Recomandari:** 42 total
- R3 originale: 30 (14 existente + 6 noi + 10 tehnice) — din deep analysis + web research
- Audit R4 adaugate: 12 (items 31–42) — din audit complet 12 domenii, scor 73/100
- R3 items confirmate de audit: 8 (#1, #2, #5, #6, #21, #27, #28, #30)

**Comparatie:** R2 done (15/15) → R3 = 42 items pending → Sprint 0 = #31 + #32 (imediat, <1h)
