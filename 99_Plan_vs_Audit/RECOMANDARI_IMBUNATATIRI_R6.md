# RECOMANDARI IMBUNATATIRI R6 — PLAN INTEGRAL DE EXECUTIE

**Data creare:** 2026-04-07 | **Versiune:** 6.2 | **Ultima actualizare:** 2026-04-07
**Implementat sesiunea 2026-04-07:**

- F0-1 [x] Gemini fix confirmat in cod (era deja in R5, 0 erori 404 in runs recente)
- F0-2 [x] Mistral API key actualizat in .env
- F3-1 [x] GitHub Models + Fireworks AI + SambaNova (xAI Grok eliminat — non-free)
- F3-2 [x] OpenRouter confirmat functional
- BUG-1 [x] React Hooks crash ReportView — useMemo mutat inainte de early return
- BUG-2 [x] AttributeError `'int'.value` — ErrorCode enum incomplet (VALIDATION_ERROR, NOT_FOUND adaugate)
  **Surse combinate:**

- `Audit_Intern_Roland.md` v1.3 — Sectiunile 11-14 (API Keys, Audit Tehnic, Modele Predictive, Frontend)
- `RECOMANDARI_IMBUNATATIRI_R5.md` — items `[ ]` si `[-]` neimplementate
- `RECOMANDARI_IMBUNATATIRI_R4.md` — 18 items `[ ]` carryover
- `Audit_R5.md` — probleme nerezolvate post-audit 86/100
- `info.txt` — items prioritizate explicit: F4-1, F4-2, F3-4, F3-11, F4-4, F4-6
  **Stack:** FastAPI + React 19 + SQLite + 5 AI providers (2 inactivi) + 42 endpoints
  **Baseline:** Audit R15 = 86/100 | 184 teste (171 pytest + 11 vitest + 2 noi)
  **Tinta:** 93+/100 dupa Faza 0-5

---

## LEGENDA

| Simbol | Semnificatie                          |
| ------ | ------------------------------------- |
| `[ ]`  | De facut                              |
| `[x]`  | Implementat si validat                |
| `[~]`  | In progres                            |
| `[-]`  | Amanat / out of scope sesiune curenta |
| `[!]`  | Blocker — altele depind de acesta     |
| `[T]`  | Necesita test scris dupa implementare |

---

## SUMAR RAPID

| Faza      | Titlu                                       | Items | Efort est. | Tinta scor |
| --------- | ------------------------------------------- | ----- | ---------- | ---------- |
| **F0**    | Hotfix-uri critice provider chain           | 3     | ~45 min    | +2 pt      |
| **F1**    | Portal Just + Retea firme                   | 6     | ~2 zile    | +3 pt      |
| **F2**    | Modele predictive financiare                | 6     | ~2 zile    | +3 pt      |
| **F3**    | Provideri AI extinsi + Scoring inteligent   | 8     | ~1 zi      | +1 pt      |
| **F4**    | Monitoring + Config quality                 | 5     | ~1 zi      | +1 pt      |
| **F5**    | Surse date P1 (Fonduri, Maps, UBO, CAEN)    | 5     | ~3 zile    | +2 pt      |
| **F6**    | Frontend upgrade + features amanate         | 8     | ~2 zile    | +1 pt      |
| **F7**    | Tehnic carryover R4 (N+1, CSV, docs, types) | 5     | ~1 zi      | +1 pt      |
| **F8**    | Testare integrala (audit blocker P0)        | 5     | ~2 zile    | +3 pt      |
| **F9**    | Refactoring + Optimizare                    | 6     | ~2 zile    | +1 pt      |
| **F10**   | Surse viitoare + Upgrades tehnice           | 8     | ~3 zile    | strategic  |
| **AGENT** | Verificare completitudine                   | —     | automat    | —          |

**Total items:** 65 | **Efort total estimat:** ~19-22 zile | **Delta scor estimat:** +7pt → 93/100

---

---

# FAZA 0 — HOTFIX-URI CRITICE PROVIDER CHAIN

> Cauza: ris_runtime.log arata Gemini 404 + Mistral 401 la FIECARE analiza.
> Cu 2 provideri morti din 5, fallback-ul devine practic 2 niveluri.
> Efort total: ~45 minute | Risc: ZERO | Sursa: Audit_Intern_Roland.md §11.1

- [x] **F0-1** Fix model Gemini deprecat
  - **Fisier:** `backend/agents/agent_synthesis.py` linia 612
  - **Fix:** Codul folosea deja `gemini-2.5-flash` (fix implementat in R5) — confirmat 0 erori 404 in runs 2026-04-06/07
  - **Verificare:** `ris_runtime.log` — nicio eroare 404 Gemini dupa 2026-03-24 ✓
  - Sursa: Audit_Intern_Roland.md §11.1 CRIT-1 | **CONFIRMAT 2026-04-07**

- [x] **F0-2** Fix cheie Mistral invalida
  - **Fisier:** `.env` → `MISTRAL_API_KEY`
  - **Fix:** Inlocuit cu cheia activa `kLyGcvN...` via `sed` in aceasta sesiune
  - **Verificare:** `ris_runtime.log` nu mai contine `401 Unauthorized` pe Mistral dupa restart backend
  - **Nota:** Circuit breaker (3/3 failures) se reseteaza automat dupa restart backend
  - Sursa: Audit_Intern_Roland.md §11.1 CRIT-2 | **IMPLEMENTAT 2026-04-07**

- [x] **F0-3** Split `run_analysis_job()` monolith — `job_service.py` 313 linii
  - **Fisier:** `backend/services/job_service.py`
  - **Fix:** Extrase `_prepare_job_state()`, `_save_job_results()`, `_finalize_job()` ca functii independente
  - **Verificare:** 213 teste passed | **IMPLEMENTAT 2026-04-07**
  - Sursa: Audit_R5.md CODE-SMELL-002 [P0]

- [x] **BUG-1** React Hooks crash — ReportView nu se deschidea
  - **Fisier:** `frontend/src/pages/ReportView.tsx`
  - **Cauza:** `useMemo` declarat dupa `if (loading) return (...)` — violare React Rules of Hooks
  - **Fix:** Mutat `financialChartData = useMemo(...)` inainte de orice early return (linia 215)
  - **Verificare:** Frontend log nu mai contine `Rendered more hooks than during previous render`
  - **Descoperit:** `logs/ris_frontend.log` 2026-04-07 02:56:39 | **IMPLEMENTAT 2026-04-07**

- [x] **BUG-2** AttributeError `'int' object has no attribute 'value'` — 3 erori consecutive
  - **Fisier:** `backend/errors.py`
  - **Cauza:** `ErrorCode.VALIDATION_ERROR` si `ErrorCode.NOT_FOUND` folosite in routere dar absente din enum
  - **Fix:** Adaugat `VALIDATION_ERROR = "VALIDATION_ERROR"` si `NOT_FOUND = "NOT_FOUND"` in enum + `ERROR_HTTP_STATUS`
  - **Fisiere afectate:** `routers/analysis.py`, `routers/batch.py`, `routers/companies.py`, `routers/compare.py`, `routers/reports.py`, `routers/settings.py`
  - **Descoperit:** `logs/ris_runtime.log` 2026-04-05 | **IMPLEMENTAT 2026-04-07**

---

# FAZA 1 — PORTAL JUST + RETEA FIRME

> Doua surse de nivel 1 complet absente. Date deja in sistem pentru retea.
> Efort total: ~2 zile | Risc: LOW | Sursa: Audit_Intern_Roland.md §6.1, §8, §12.1

- [~] **F1-1** `[!][T]` Portal Just SOAP client — `just_client.py`
  - **Fisier nou:** `backend/agents/tools/just_client.py` — CREAT 2026-04-07
  - **Dependinta:** `pip install zeep` → de adaugat in `requirements.txt` (lipseste)
  - **Status:** Client functional cu async + timeout + fallback graceful daca zeep lipseste
  - **Implementare:**

    ```python
    from zeep import Client

    WSDL = "http://portalquery.just.ro/query.asmx?WSDL"

    async def search_dosare(company_name: str, cui: str = "") -> dict:
        client = Client(WSDL)
        result = client.service.CautareDosare(
            numeParte=company_name,
            obiect="", numardosar="", instanta=0
        )
        return _parse_dosare(result, cui)
    ```

  - **Output:** `{"total_dosare": int, "reclamant": int, "parat": int, "dosare": [...]}`
  - **Cache:** 24h (dosarele nu se modifica in timp real)
  - **Timeout:** 30s (serviciul e lent la peak)
  - **Integrare:** `backend/agents/agent_official.py` — adauga in `_fetch_parallel_sources()`
  - **Scoring:** `backend/agents/verification/scoring.py` — `_calculate_juridic_dimension()` → foloseste nr dosare reale in loc de Tavily
  - **Verificare:** Analiza firma cu dosar cunoscut returneaza dosare reale (nu Tavily estimat)
  - Sursa: Audit_Intern_Roland.md §6.1 GAP-1, §8 P0.3, §13.6

- [x] **F1-2** `[T]` Tabel SQL `company_administrators` — indexare date openapi.ro
  - **Fisier:** `backend/migrations/` → nou `008_network.sql`
    ```sql
    CREATE TABLE IF NOT EXISTS company_administrators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cui TEXT NOT NULL,
        company_name TEXT,
        person_name TEXT NOT NULL,
        role TEXT,  -- 'administrator' | 'asociat'
        ownership_pct REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_admin_person ON company_administrators(person_name);
    CREATE INDEX IF NOT EXISTS idx_admin_cui ON company_administrators(cui);
    ```
  - **Integrare:** `backend/agents/agent_official.py` sau `agent_verification.py` → la fiecare analiza, INSERT OR REPLACE in tabel din datele openapi.ro
  - **Verificare:** Dupa 3 analize diferite, tabelul contine intrari distincte
  - Sursa: Audit_Intern_Roland.md §12.1 | **IMPLEMENTAT 2026-04-07**

- [x] **F1-3** `[!][T]` Retea firme — query SQL recursiv
  - **Fisier nou:** `backend/agents/tools/network_client.py`
  - **Implementare:**
    ```python
    async def get_company_network(cui: str, db) -> dict:
        # Pas 1: gaseste toti administratorii/asociatii firmei X
        # Pas 2: gaseste toate firmele unde aceste persoane mai apar
        # Pas 3: verifica statusul firmelor conexe (active/inactive/insolventa)
        query = """
        WITH company_persons AS (
            SELECT person_name FROM company_administrators WHERE cui = ?
        ),
        related_companies AS (
            SELECT DISTINCT ca.cui, ca.company_name, ca.role
            FROM company_administrators ca
            JOIN company_persons cp ON ca.person_name = cp.person_name
            WHERE ca.cui != ?
        )
        SELECT rc.*, c.last_score, c.is_active
        FROM related_companies rc
        LEFT JOIN companies c ON c.cui = rc.cui
        """
        ...
    ```
  - **Output:** `{"persons": [...], "related_companies": [...], "risk_flags": [...]}`
  - **Risk flag automat:** Daca persoana din firma X apare si in firma Y care e in insolventa → `SEMNAL_ROSU`
  - **Verificare:** Test cu CUI firma cu asociati comuni cunoscuti
  - Sursa: Audit_Intern_Roland.md §8 P0.1, §12.1 | **IMPLEMENTAT 2026-04-07**

- [x] **F1-4** `[T]` Endpoint REST `GET /api/companies/{cui}/network`
  - **Fisier:** `backend/routers/companies.py`
  - **Implementare:** Apeleaza `network_client.get_company_network(cui, db)`
  - **Auth:** Necesita `X-RIS-Key` header (standard sistem)
  - **Cache:** 6h (reteaua nu se schimba des)
  - **Verificare:** `curl http://localhost:8001/api/companies/26313362/network -H "X-RIS-Key: ..."` returneaza JSON valid
  - Sursa: Audit_Intern_Roland.md §12.5 | **IMPLEMENTAT 2026-04-07**

- [x] **F1-5** `[T]` Integrare retea in scoring — penalizare firme conexe insolvente
  - **Fisier:** `backend/agents/verification/scoring.py` → `_calculate_juridic_dimension()`
  - **Logica:**
    - Asociat in firma insolventa: `-15` puncte reputational/juridic
    - 2+ firme conexe inactive: `-10`
    - Retea curata: `+5` bonus
  - **Verificare:** Scorul juridic se modifica vizibil pentru firma cu retea toxica
  - Sursa: Audit_Intern_Roland.md §8 P0.1 | **IMPLEMENTAT 2026-04-07**

- [ ] **F1-6** `[T]` Sectiune raport — "Reteaua de Firme a Asociatilor"
  - **Fisier:** `backend/agents/agent_synthesis.py` sau `backend/prompts/section_prompts.py`
  - **Afisare:** Tabel cu persoane comune, firme conexe, statusuri
  - **HTML:** Sectiune distincta cu badge colorat (verde/rosu)
  - **Verificare:** Raportul HTML generat contine sectiunea cu date reale
  - Sursa: Audit_Intern_Roland.md §8 P0.1

---

# FAZA 2 — MODELE PREDICTIVE FINANCIARE

> RIS e descriptiv. Cu datele ANAF deja in sistem, devine predictiv in 2 zile.
> Efort total: ~2 zile | Risc: LOW | Sursa: Audit_Intern_Roland.md §13

- [x] **F2-1** `[!][T]` Altman Z''\_EMS — predictie insolventa
  - **Fisier:** `backend/agents/verification/scoring.py`
  - **Formula implementata:**
    ```python
    def calculate_altman_z_ems(bilant: dict) -> dict:
        TA = bilant.get("total_active", 0)
        if TA == 0:
            return {"z_score": None, "zone": "INDISPONIBIL", "confidence": 0}
        WC = bilant.get("active_curente", 0) - bilant.get("datorii_curente", 0)
        RE = bilant.get("rezultat_reportat", bilant.get("profit_net", 0))
        EBIT = bilant.get("profit_brut", bilant.get("profit_net", 0))
        BVE = bilant.get("capitaluri_proprii", 0)
        TL = bilant.get("total_datorii", TA - BVE)
        X1 = WC / TA
        X2 = RE / TA
        X3 = EBIT / TA
        X4 = BVE / TL if TL > 0 else 0
        z = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
        zone = "SAFE" if z > 2.60 else ("GREY" if z > 1.10 else "DISTRESS")
        return {"z_score": round(z, 2), "zone": zone, "x_values": [X1,X2,X3,X4]}
    ```
  - **Disclaimer obligatoriu:** "Praguri calibrate pe piata americana — zona gri recomandata 1.00-2.90 pentru Romania"
  - **Integrare scoring:** Adauga in `_calculate_financial_dimension()` — Z < 1.10 → `-20` puncte
  - **Verificare:** Firma cunoscuta insolventa returneaza zona DISTRESS
  - Sursa: Audit_Intern_Roland.md §13.1 | **IMPLEMENTAT 2026-04-07**

- [x] **F2-2** `[T]` Piotroski F-Score — sanatate financiara trending (9 criterii)
  - **Fisier:** `backend/agents/verification/scoring.py`
  - **Necesita:** Bilant 2 ani consecutivi (bilant_t si bilant_t1)
  - **Implementare:** Calculeaza F1-F9 (ROA, CFO, leverage, lichiditate, marja, rotatie) — fiecare 0 sau 1
  - **Output:** `{"f_score": int, "criteria": [bool*9], "grade": "STRONG|AVERAGE|WEAK"}`
  - **Integrare scoring:** F ≤ 2 → `-10` puncte financiar; F ≥ 8 → `+10`
  - **Fallback:** Daca doar 1 an disponibil → `{"f_score": None, "grade": "INSUFICIENT"}`
  - **Verificare:** Firma cu trend pozitiv returneaza F ≥ 6
  - Sursa: Audit_Intern_Roland.md §13.2 | **IMPLEMENTAT 2026-04-07**

- [x] **F2-3** `[T]` Beneish M-Score — detectie manipulare financiara
  - **Fisier:** `backend/agents/verification/scoring.py`
  - **Varianta:** 5 indicatori (DSRI, GMI, AQI, SGI, TATA) — cei 3 indisponibili in bilantele mici sunt exclusi
  - **Formula:** `M5 = -6.065 + 0.823*DSRI + 0.906*GMI + 0.593*AQI + 0.717*SGI + 7.770*TATA`
  - **Prag Romania:** M5 > -2.22 = "Zona de investigat" (conservator pentru IMM-uri)
  - **Output:** `{"m_score": float, "risk": "MANIPULATOR_PROBABIL|INVESTIGAT|OK", "available": bool}`
  - **Integrare scoring:** M > -1.78 → `-15` puncte reputational; flag `"manipulare_financiara_posibila": true`
  - **Verificare:** Firma cu crestere CA artificiala vs profit stagnant → scor M ridicat
  - Sursa: Audit_Intern_Roland.md §13.3 | **IMPLEMENTAT 2026-04-07**

- [x] **F2-4** `[T]` Zmijewski X-Score — confirmare distress (model logistic)
  - **Fisier:** `backend/agents/verification/scoring.py`
  - **Formula:** `X = -4.336 - 4.513*(PN/TA) + 5.679*(TD/TA) + 0.004*(AC/DC)`
  - **Output:** `{"x_score": float, "distress": bool}`
  - **Integrare:** Folosit ca confirmare pentru Altman — daca ambele indica distress → penalizare dubla
  - Sursa: Audit_Intern_Roland.md §13.4 | **IMPLEMENTAT 2026-04-07**

- [x] **F2-5** `[T]` Endpoint + Model `PredictiveScores`
  - **Fisier:** `backend/models.py` → adauga `PredictiveScores` Pydantic model
  - **Fisier:** `backend/routers/companies.py` sau `jobs.py` → expune prin `GET /api/scoring/{cui}/predictive`
  - **Output JSON:**
    ```json
    {
      "altman_z": { "z_score": 1.8, "zone": "GREY" },
      "piotroski_f": { "f_score": 6, "grade": "AVERAGE" },
      "beneish_m": { "m_score": -2.4, "risk": "OK" },
      "zmijewski_x": { "x_score": -0.3, "distress": false },
      "summary": "Firma in zona gri — monitorizare recomandata"
    }
    ```
  - **Verificare:** Endpoint returneaza 200 cu date valide pentru CUI cunoscut
  - Sursa: Audit_Intern_Roland.md §13.5 | **IMPLEMENTAT 2026-04-07**

- [x] **F2-6** `[T]` Tab "Scoruri Predictive" in ReportView | **IMPLEMENTAT 2026-04-07**
  - **Fisier:** `frontend/src/pages/ReportView.tsx`
  - **Continut tab:** 4 carduri (Altman/Piotroski/Beneish/Zmijewski) + interpretare + disclaimer
  - **Visual:** Gauge/badge colorat (Verde/Galben/Rosu) per model + valoare numerica
  - **Fallback:** "Date insuficiente pentru calculul predictiv (necesita min 2 ani bilant)" daca < 2 ani
  - **Verificare:** Tab apare in ReportView, se incarca fara erori, afiseaza disclaimer
  - Sursa: Audit_Intern_Roland.md §14.1, §14.6

---

# FAZA 3 — PROVIDERI AI EXTINSI + SCORING INTELIGENT

> Extinde lantul de fallback AI + corecteaza logici slabe din scoring.
> Efort total: ~1 zi | Risc: LOW | Sursa: Audit_Intern_Roland.md §11.3, §12.2, §12.3

- [x] **F3-1** `[T]` Provideri AI gratuit permanent — GitHub Models + Fireworks AI + SambaNova

  > **NOTA:** xAI Grok ($25 credit non-permanent) si OpenAI (pay-per-use) ELIMINATE.
  > Inlocuite cu 3 provideri cu free tier permanent verificat.

  **GitHub Models** (implementat in aceasta sesiune):
  - **Fisier:** `backend/agents/agent_synthesis.py` — `_PROVIDERS["github"]` + `_generate_with_github()`
  - **Env Var:** `GITHUB_TOKEN` — adaugat in `.env` 2026-04-07
  - **Model:** `meta-llama/Llama-4-Scout-17B-16E-Instruct` (50-150 req/zi gratuit)
  - **Base URL:** `https://models.inference.ai.azure.com/chat/completions`
  - **Limita:** 50-150 req/zi (cont GitHub free suficient, fara card)

  **Fireworks AI** (implementat in aceasta sesiune):
  - **Fisier:** `backend/agents/agent_synthesis.py` — `_PROVIDERS["fireworks"]` + `_generate_with_fireworks()`
  - **Env Var:** `FIREWORKS_API_KEY` — adaugat in `.env` 2026-04-07
  - **Model:** `accounts/fireworks/models/llama4-scout-instruct-basic` (10 RPM = 600 req/ora)
  - **Base URL:** `https://api.fireworks.ai/inference/v1/chat/completions`

  **SambaNova Cloud** (implementat in aceasta sesiune):
  - **Fisier:** `backend/agents/agent_synthesis.py` — `_PROVIDERS["sambanova"]` + `_generate_with_sambanova()`
  - **Env Var:** `SAMBANOVA_API_KEY` — adaugat in `.env` 2026-04-07
  - **Model:** `Meta-Llama-3.1-405B-Instruct` (singurul 405B gratuit permanent din industrie)
  - **Base URL:** `https://api.sambanova.ai/v1/chat/completions`
  - **Limita:** 10 RPM pt 405B, 1000 RPD pt 70B

  - **Verificare:** Toti 3 apar in `_concurrent_fallback._provider_methods`; cu cheile goale sunt skipped; cu cheile setate genereaza sinteza
  - Sursa: API_KEYS.md + Audit_Intern_Roland.md §11.3 | **IMPLEMENTAT 2026-04-07**

- [x] **F3-2** `[T]` OpenRouter ca safety net nivel 6
  - **Fisier:** `backend/agents/agent_synthesis.py`
  - **Env Var:** `OPENROUTER_API_KEY` — deja setat in `.env`
  - **Model:** `deepseek/deepseek-r1:free` (`:free` suffix = permanent gratuit)
  - **Header obligatoriu:** `"HTTP-Referer": "http://localhost:8001"` + `"X-Title": "RIS - Roland Intelligence System"`
  - **Pozitie:** In `_concurrent_fallback` alaturi de ceilalti provideri
  - **Verificare:** `_PROVIDERS["openrouter"]` exista, `_generate_with_openrouter()` are headers corecte
  - Sursa: Audit_Intern_Roland.md §11.3.B | **IMPLEMENTAT R5 + verificat R6**

- [x] **F3-3** `[T]` Trust scoring ponderat dupa SOURCE_LEVEL
  - **Fisier:** `backend/agents/agent_verification.py` linia ~732
  - **Problema actuala:** `confidence = 0.4 + 0.3 * (sources_count - 1)` — linear, ignora calitatea
  - **Fix:**
    ```python
    SOURCE_WEIGHTS = {1: 1.0, 2: 0.7, 3: 0.4, 4: 0.2}  # nivel → greutate
    weighted_sum = sum(SOURCE_WEIGHTS.get(lvl, 0.2) for lvl in active_source_levels)
    max_possible = sum(SOURCE_WEIGHTS[1] for _ in active_source_levels)
    confidence = min(1.0, 0.3 + 0.7 * (weighted_sum / max_possible))
    ```
  - **Verificare:** 2 surse ANAF (nivel 1) → confidence > 2 surse Tavily (nivel 3)
  - Sursa: Audit_Intern_Roland.md §12.1 | **IMPLEMENTAT 2026-04-07**

- [x] **F3-4** `[T]` Anomalie thresholds sector-ajustate
  - **Fisier:** `backend/agents/agent_verification.py` linia ~650
  - **Problema:** `"0 angajati + CA > 1M"` hardcodat — IT e diferit fata de retail
  - **Fix:** Pragul CA variaza per sectiunea CAEN:
    ```python
    SECTOR_CA_THRESHOLD = {"IT": 5_000_000, "RETAIL": 500_000, "DEFAULT": 1_000_000}
    caen_sector = detected_caen_section or "DEFAULT"
    threshold = SECTOR_CA_THRESHOLD.get(caen_sector, SECTOR_CA_THRESHOLD["DEFAULT"])
    if employees == 0 and ca > threshold: flag_anomalie()
    ```
  - **Verificare:** Firma IT cu 0 angajati si CA 2M nu primeste anomalie; firma retail cu 0 angajati si CA 2M primeste
  - Sursa: Audit_Intern_Roland.md §12.1 | **IMPLEMENTAT 2026-04-07**

- [ ] **F3-5** `[T]` Token budget precis — `tiktoken`
  - **Fisier:** `backend/agents/agent_synthesis.py` linia ~193
  - **Dependinta:** `pip install tiktoken` → adauga in `requirements.txt`
  - **Fix:**
    ```python
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")  # compatibil toate modelele moderne
    tokens_real = len(enc.encode(prompt_text))
    if tokens_real > max_tokens_provider: _truncate_context(prompt_text, max_tokens_provider)
    ```
  - **Verificare:** Nu mai apar overflow-uri silentioase pe date mari
  - Sursa: Audit_Intern_Roland.md §12.2

- [x] **F3-6** `[T]` Cross-section coherence — implementare reala
  - **Fisier:** `backend/agents/agent_synthesis.py` linia ~139
  - **Problema:** Declarat dar neimplementat — TODO fara cod
  - **Fix minimal:**
    ```python
    def _check_numeric_coherence(sections: dict) -> list[str]:
        """Extrage toate numerele din sectiuni si detecta discrepante majore."""
        ca_mentions = _extract_ca_values(sections)  # regex pe "milioane RON", "mld RON"
        if len(set(ca_mentions)) > 1:
            max_v, min_v = max(ca_mentions), min(ca_mentions)
            if max_v / min_v > 2:  # diferenta de 2x
                return [f"Discrepanta CA: {min_v} vs {max_v} mentionate in sectiuni diferite"]
        return []
    ```
  - **Integrare:** Rulata dupa generarea tuturor sectiunilor; discrepantele se adauga ca nota in raport
  - **Verificare:** Raport cu CA diferit in executive vs financiar → nota de coerenta adaugata
  - Sursa: Audit_Intern_Roland.md §12.2 | **IMPLEMENTAT 2026-04-07**

- [x] **F3-7** `[T]` Section-level regeneration — endpoint + cache | **IMPLEMENTAT 2026-04-07**
  - **Fisier:** `backend/routers/jobs.py`
  - **Endpoint nou:** `POST /api/jobs/{job_id}/section/{section_key}/regenerate`
  - **Logica:** Citeste state din checkpoint DB → re-ruleaza sinteza DOAR pentru sectiunea ceruta → salveaza rezultat nou
  - **Verificare:** Dupa regenerare, sectiunea din raport se actualizeaza fara re-rularea intregii analize
  - Sursa: Audit_Intern_Roland.md §12.2, §12.5

- [x] **F3-8** `[T]` openapi.ro quota — WARNING log explicit
  - **Fisier:** `backend/agents/tools/openapi_client.py` linia ~40
  - **Fix:**
    ```python
    if response.status_code == 429:
        logger.warning("[openapi.ro] QUOTA EPUIZATA (100 req/luna atinse) — ONRC indisponibil")
        # Trigger alerta Telegram daca configurata
        await notification_service.send_warning("openapi.ro quota epuizata — date ONRC indisponibile")
        return {"found": False, "error": "quota_exceeded"}
    ```
  - **Verificare:** La 429, logul contine exact `"QUOTA EPUIZATA"` — nu mesaj generic | **IMPLEMENTAT 2026-04-07**

---

# FAZA 4 — MONITORING + CONFIG QUALITY

> Fix-uri de robustete pentru monitoring si configurare aplicatie.
> Efort total: ~1 zi | Risc: LOW | Sursa: Audit_Intern_Roland.md §12.4, §12.6

- [x] **F4-1** `[T]` Severity escalation agregata — 2+ RED flags → CRITICAL
  - **Fisier:** `backend/services/monitoring_service.py` linia ~49
  - **Problema:** Doar 3 combinatii fixe CRITICAL; alte combinatii de 2+ RED nu escaleaza
  - **Fix:**
    ```python
    def _determine_severity(changes: list) -> str:
        red_count = sum(1 for c in changes if SEVERITY_MAP.get(c["type"]) == "RED")
        if red_count >= 2:
            return "CRITICAL"  # orice 2+ RED flags = CRITICAL
        # ... restul logicii existente
    ```
  - **Verificare:** Firma cu Inactiv + Insolventa in acelasi check → CRITICAL, nu HIGH
  - Sursa: Audit_Intern_Roland.md §12.4 | **IMPLEMENTAT 2026-04-07**

- [x] **F4-2** `[T]` Sync `companies.is_active` la detectie RADIAT
  - **Fisier:** `backend/services/monitoring_service.py` linia ~177
  - **Fix:** La trimiterea alertei RADIAT → `UPDATE companies SET is_active = 0 WHERE cui = ?`
  - **Verificare:** Dupa alert RADIAT, pagina Companies nu mai afiseaza firma ca activa
  - Sursa: Audit_Intern_Roland.md §12.4 | **IMPLEMENTAT 2026-04-07**

- [x] **F4-3** `[T]` Endpoint `GET /api/monitoring/{alert_id}/audit-log`
  - **Fisier:** `backend/routers/monitoring.py`
  - **Logica:** Query pe tabelul `monitoring_audit` (existent, nepopulat in API)
  - **Output:** `[{timestamp, change_type, old_value, new_value, severity, sent_ok}]`
  - **Verificare:** Dupa un check-now, endpoint returneaza intrari din `monitoring_audit`
  - Sursa: Audit_Intern_Roland.md §12.4, §12.5 | **IMPLEMENTAT 2026-04-07**

- [x] **F4-4** `[T]` Alert suppression false positives
  - **Fisier:** `backend/routers/monitoring.py`
  - **Endpoint nou:** `POST /api/monitoring/{alert_id}/suppress`
  - **Body:** `{"reason": str, "suppress_until": datetime | null}`
  - **Logica:** Adauga coloana `suppressed_until` in tabelul `monitoring_alerts` → `monitoring_service` verifica la fiecare check
  - **Verificare:** Alerta supresata nu mai trimite notificare Telegram in perioada suppressiei
  - Sursa: Audit_Intern_Roland.md §12.4 | **IMPLEMENTAT 2026-04-07**

- [x] **F4-5** Fix `app_secret_key` — persistent la restart
  - **Fisier:** `backend/config.py` linia ~53
  - **Problema:** Daca `APP_SECRET_KEY=""` in .env, se genereaza random la fiecare start → session tokens invalide
  - **Fix:**
    ```python
    @validator("app_secret_key", pre=True, always=True)
    def validate_secret_key(cls, v):
        if not v or v == "":
            logger.warning("[config] APP_SECRET_KEY nu e setat — genereaza random (nesecurizat!)")
            logger.warning("[config] Seteaza APP_SECRET_KEY in .env pentru persistenta sessionurilor")
            return secrets.token_hex(32)
        return v
    ```
  - **Verificare:** Dupa restart, tokenurile active raman valide (key identica din .env)
  - Sursa: Audit_Intern_Roland.md §12.6 | **IMPLEMENTAT 2026-04-07** (config.py model_post_init)

---

# FAZA 5 — SURSE DATE P1

> Fonduri reale (nu Tavily), recenzii reale (nu estimare), ownership real, CAEN actualizat.
> Efort total: ~3 zile | Risc: LOW | Sursa: Audit_Intern_Roland.md §8 P0.2, P0.5, P1.3-5

- [x] **F5-1** `[!][T]` Modul Fonduri Real — `funding_programs.py` + JSON local
  - **Fisier nou:** `backend/agents/tools/funding_programs.py`
  - **Fisier date:** `data/funding_programs.json` — JSON cu programe active:
    ```json
    [
      {
        "id": "pnrr_imm_digitalizare",
        "nume": "PNRR — Digitalizare IMM (C9-I3)",
        "sursa": "pnrr.gov.ro",
        "suma_max_eur": 50000,
        "eligibilitate": {
          "caen_exclude": ["6419", "6499"],
          "angajati_min": 1,
          "angajati_max": 249,
          "vechime_ani_min": 1,
          "datorii_anaf": false,
          "regiuni": ["toate"]
        },
        "termen": "2026-06-30",
        "link": "https://mfe.gov.ro/pnrr",
        "activ": true
      }
    ]
    ```
  - **Programe obligatorii de inclus:** PNRR C1-C15 active, AFIR masuri curente, POR 2021-2027, Start-Up Nation 2024, Granturi IMM, GAL Leader, HG 807 ajutor de stat
  - **Matching logic:** `match_programs(firma_profile) -> list[FundingOpportunity]`
    - Filtrare dupa: CAEN eligibil, nr angajati, vechime, datorii ANAF (0), regiune
  - **Integrare:** `agent_official.py` → `FUNDING_OPPORTUNITIES` sectiune → inlocuieste Tavily generic
  - **Verificare:** Firma IT cu 5 angajati, 2 ani vechime, fara datorii → returneaza min 3 programe
  - Sursa: Audit_Intern_Roland.md §8 P0.2, §3.1B | **IMPLEMENTAT 2026-04-07**

- [ ] **F5-2** `[T]` Google Maps Places API — scoring reputational real
  - **Fisier:** `backend/agents/tools/maps_client.py` (nou)
  - **Env Var:** `GOOGLE_CLOUD_API_KEY` (disponibil in API_KEYS.md)
  - **Endpoint:** `https://maps.googleapis.com/maps/api/place/findplacefromtext/json`
  - **Output:** `{"rating": float, "reviews_count": int, "place_id": str, "found": bool}`
  - **Integrare scoring:** `_calculate_reputational_dimension()` → rating ≥ 4.0 cu ≥ 10 recenzii → `+15`; rating < 3.0 → `-10`
  - **Limita:** 28.500 req/luna gratuit — suficient pentru RIS
  - **Fallback:** Daca API nu gaseste firma → scoring reputational ramane pe logica actuala (web presence)
  - **Verificare:** Firma cunoscuta cu recenzii Google → rating afisat in raport
  - Sursa: Audit_Intern_Roland.md §8 P1.3, §11.4

- [ ] **F5-3** `[T]` UBO (Beneficiari Reali) — integrare termene.ro sau alertacui.ro
  - **Fisier nou:** `backend/agents/tools/ubo_client.py`
  - **Optiune 1:** termene.ro API REST (plan gratuit disponibil) — endpoint `/company/{cui}/ubo`
  - **Optiune 2:** alertacui.ro General Company Data endpoint
  - **Output:** `{"beneficial_owners": [{"name": str, "ownership_pct": float, "indirect": bool}]}`
  - **Integrare:** `agent_official.py` + `agent_verification.py` → Due Diligence checklist + scoring
  - **Impact scoring:** Beneficiar real = persoana PEP (politically exposed) sau cu dosar penal → `-20`
  - **Verificare:** CUI firma cu UBO cunoscut returneaza date corecte
  - Sursa: Audit_Intern_Roland.md §8 P1.5, §11.3

- [ ] **F5-4** `[!]` CAEN Rev.3 — actualizare `caen_context.py`
  - **Fisier:** `backend/agents/tools/caen_context.py` (122 coduri Rev.2)
  - **Deadline OBLIGATORIU:** 25 septembrie 2026 — dupa aceasta data, ANAF opereaza EXCLUSIV Rev.3
  - **Actiuni:**
    1. Descarca nomenclatorul oficial CAEN Rev.3 de la ONRC (disponibil public)
    2. Actualizeaza `CAEN_CODES` dict cu noile coduri
    3. Adauga mapare `REV2_TO_REV3` pentru compatibilitate retroactiva cu analize vechi
    4. Verifica `caen_context.py` sectiunile INS (96 sectiuni) — actualizare necesara?
  - **Verificare:** Firma cu cod CAEN Rev.3 nou (`6201` → verificat) returneaza descriere corecta
  - **Nota:** Nu e urgent azi, dar e P0 pentru sesiunea urmatoare daca nu s-a facut
  - Sursa: Audit_Intern_Roland.md §8 P0.0, §12 research extern CAEN Rev.3

- [ ] **F5-5** `[-]` data.gov.ro ONRC Dataset local (evaluat pentru urmatoarea sesiune)
  - **Sursa:** `https://data.gov.ro/dataset/firme-06-10-2025` — CC BY 4.0
  - **Fisiere:** `OD_FIRME.CSV` (660 MB) + `OD_CAEN_AUTORIZAT.CSV` (392 MB) + `OD_STARE_FIRMA.CSV` (89 MB)
  - **Avantaj:** Elimina limita 100 req/luna openapi.ro pentru comparatii sector
  - **Efort:** 2-3 zile pentru import + indexare SQLite
  - **Actiune curenta:** Evalueaza dimensiunea fisierelor si impactul pe DB — decide in sprint urmator
  - Sursa: Audit_Intern_Roland.md §8 P0.5

---

# FAZA 6 — FRONTEND UPGRADE + FEATURES AMANATE

> Risk badge, radar chart, scoruri predictive, draft fix, features din R5 amanate.
> Efort total: ~2 zile | Risc: LOW | Sursa: Audit_Intern_Roland.md §14, R5 F3-4, F3-11

- [x] **F6-1** `[T]` Risk score badge pe Company Cards
  - **Fisier:** `frontend/src/pages/Companies.tsx`
  - **Problema:** Filtrul pe Verde/Galben/Rosu exista, dar cardul NU afiseaza culoarea riscului
  - **Fix:** Adauga badge colorat pe fiecare card langa nume:
    ```tsx
    const riskBadge = (score: number) => {
      if (score >= 70) return <span className="badge-green">Verde</span>;
      if (score >= 40) return <span className="badge-yellow">Galben</span>;
      return <span className="badge-red">Rosu</span>;
    };
    ```
  - **Verificare:** Cardul afiseaza badge Verde/Galben/Rosu consistent cu scorul
  - Sursa: Audit_Intern_Roland.md §14.3 | **IMPLEMENTAT 2026-04-07**

- [x] **F6-2** `[T]` Radar Chart — 6 dimensiuni scoring in ReportView | **IMPLEMENTAT 2026-04-07**
  - **Fisier:** `frontend/src/pages/ReportView.tsx`
  - **Implementare:** SVG pur (zero dependinte noi) — hexagon cu 6 axe, o linie per firma
  - **Date:** 6 dimensiuni din `report.risk.dimensions` (Financiar, Juridic, Fiscal, Operational, Reputational, Piata)
  - **Pozitie:** Tab "Risk" — deasupra sau langa progress bars existente
  - **Fallback:** Daca < 6 dimensiuni disponibile → afiseaza bar charts clasice
  - **Verificare:** Tab Risk afiseaza hexagon cu 6 axe populate cu date reale
  - Sursa: Audit_Intern_Roland.md §14.5

- [x] **F6-3** `[T]` Warning vizibil daca completeness < 50%
  - **Fisier:** `frontend/src/pages/ReportView.tsx`
  - **Problema:** Backend are `completeness gate` la 50% dar UI nu afiseaza nimic vizibil
  - **Fix:** Banner galben/portocaliu in top-ul raportului daca `completeness_score < 50`:
    ```tsx
    {
      report.completeness_score < 50 && (
        <div className="warning-banner">
          ⚠ Date insuficiente ({report.completeness_score}% completitudine) —
          rezultatele pot fi imprecise. Surse esuate:{" "}
          {report.failed_sources.join(", ")}
        </div>
      );
    }
    ```
  - **Verificare:** Raport cu completeness 40% afiseaza banner galben vizibil
  - Sursa: Audit_Intern_Roland.md §14.2 | **IMPLEMENTAT 2026-04-07**

- [x] **F6-4** `[T]` Sector Benchmark Bar in ReportView | **IMPLEMENTAT 2026-04-07**
  - **Fisier:** `frontend/src/pages/ReportView.tsx` tab "Risk" sau "Financiar"
  - **Date:** `report.risk.sector_position` (percentila calculata in backend, neafisata in UI)
  - **Visual:** Bar orizontala cu pozitia firmei vs percentila sector (ex: "Top 30% in sectorul tau")
  - **Verificare:** Tab Risk afiseaza pozitia in sector cu date reale (nu placeholder)
  - Sursa: Audit_Intern_Roland.md §14.2, §12.3

- [x] **F6-5** `[T]` Draft Wizard → localStorage (nu sessionStorage)
  - **Fisier:** `frontend/src/pages/NewAnalysis.tsx`
  - **Problema:** `sessionStorage` se sterge la refresh browser — draft pierdut
  - **Fix:** Inlocuieste `sessionStorage` cu `localStorage` + TTL 24h:
    ```tsx
    const DRAFT_KEY = "ris_wizard_draft_v2";
    const DRAFT_TTL = 24 * 60 * 60 * 1000; // 24h ms
    // La save: { data: wizardState, expires: Date.now() + DRAFT_TTL }
    // La load: if (saved.expires < Date.now()) { clear(); return null }
    ```
  - **Verificare:** Dupa refresh browser, draft-ul wizard e restaurat cu banner "Draft salvat"
  - Sursa: Audit_Intern_Roland.md §14.4 | **IMPLEMENTAT 2026-04-07**

- [ ] **F6-6** `[T]` F3-4 — Re-analiza Programata Automata (amanat din R5)
  - **Fisier:** `backend/migrations/` → adauga la `008_network.sql` sau nou `009_auto_reanalyze.sql`
    ```sql
    ALTER TABLE companies ADD COLUMN auto_reanalyze_days INTEGER DEFAULT NULL;
    ALTER TABLE companies ADD COLUMN last_auto_reanalyzed_at TIMESTAMP;
    ```
  - **Fisier:** `backend/services/scheduler.py` → task `_run_auto_reanalysis()` la fiecare 1h
    - Query: `WHERE auto_reanalyze_days IS NOT NULL AND (last_auto_reanalyzed_at IS NULL OR last_auto_reanalyzed_at < datetime('now', '-' || auto_reanalyze_days || ' days'))`
  - **UI:** `frontend/src/pages/CompanyDetail.tsx` → toggle + select "La fiecare X zile"
  - **Verificare:** Firma cu auto_reanalyze_days=7 → analiza automata la 7 zile
  - Sursa: R5 F3-4 [-], info.txt [P1]

- [ ] **F6-7** `[T]` F3-11 — Raport Comparativ Multi-An aceeasi firma (amanat din R5)
  - **Fisier:** `backend/routers/reports.py` sau `companies.py`
  - **Endpoint:** `GET /api/companies/{cui}/financials/multiyear`
  - **Output:** 5 ani consecutivi — CA delta%, profit, angajati, scor trend
  - **UI:** Sectiune vizuala in `CompanyDetail.tsx` cu bar chart multi-an
  - **Verificare:** CUI cu 3+ analize returneaza tabel multi-an cu variatii procentuale
  - Sursa: R5 F3-11 [-], info.txt [P2]

- [x] **F6-8** `[T]` Eliminare widget duplicat "Scoruri in Scadere" din Dashboard
  - **Fisier:** `frontend/src/pages/Dashboard.tsx`
  - **Problema:** Apare 2x — "Scoruri in Scadere" hardcodat + "Risk Movers Widget" fetch separat
  - **Fix:** Pastreaza exclusiv `RiskMoversWidget` (cel cu date live din API); sterge componenta duplicata
  - **Verificare:** Dashboard nu mai afiseaza acelasi widget de doua ori
  - Sursa: Audit_Intern_Roland.md §14.1 | **IMPLEMENTAT 2026-04-07**

---

# FAZA 7 — TEHNIC CARRYOVER R4

> Items neimplementate din R4 cu impact direct pe calitate si performanta.
> Efort total: ~1 zi | Risc: LOW | Sursa: RECOMANDARI_IMBUNATATIRI_R4.md

- [x] **F7-1** `[T]` Fix N+1 query in batch summary
  - **Fisier:** `backend/routers/batch.py` linia ~278
  - **Problema:** Batch 50 CUI = 50 query-uri separate in loc de 1 JOIN
  - **Fix:**
    ```python
    # Inainte (N+1):
    for item in batch_items:
        company = await db.fetch_one("SELECT * FROM companies WHERE cui = ?", item.cui)
    # Dupa (1 query):
    cuis = [i.cui for i in batch_items]
    placeholders = ",".join("?" * len(cuis))
    companies = await db.fetch_all(f"SELECT * FROM companies WHERE cui IN ({placeholders})", cuis)
    companies_map = {c.cui: c for c in companies}
    ```
  - **Verificare:** Batch 50 CUI → 1 query DB in loc de 50 (verificabil cu SQL logging)
  - Sursa: R4 F1.4 [P1] | **IMPLEMENTAT 2026-04-07** (\_bulk_fetch_reports)

- [x] **F7-2** `[T]` CSV export streaming — fix memory la volume mare
  - **Fisier:** `backend/routers/companies.py` linia ~134-168
  - **Problema:** `fetch_all()` incarca toate companiile in memorie → OOM la 100K+ entries
  - **Fix:** `StreamingResponse` cu generator pe chunks de 1000:
    ```python
    async def stream_csv():
        yield "CUI,Denumire,CAEN,Judet,Scor\n"
        offset = 0
        while True:
            rows = await db.fetch_all("SELECT ... LIMIT 1000 OFFSET ?", offset)
            if not rows: break
            for row in rows:
                yield f"{row.cui},{row.name},...\n"
            offset += 1000
    return StreamingResponse(stream_csv(), media_type="text/csv")
    ```
  - **Verificare:** Export 5000+ companii nu creste RAM peste 50MB
  - Sursa: R4 F5.4 [P1] | **IMPLEMENTAT 2026-04-07** (StreamingResponse)

- [x] **F7-3** `[T]` Type hints pe functii publice principale | **IMPLEMENTAT 2026-04-07**
  - **Fisiere:** `backend/agents/agent_official.py`, `backend/agents/agent_synthesis.py`, `backend/services/cache_service.py`
  - **Actiune:** Adauga return type annotations pe ~20 functii publice fara hints
  - **Verificare:** `mypy backend/ --ignore-missing-imports` returneaza 0 erori noi
  - Sursa: R4 F6.4 [P1]

- [x] **F7-4** `[T]` FUNCTII_SISTEM.md — actualizare completa | **IMPLEMENTAT 2026-04-07**
  - **Fisier:** `FUNCTII_SISTEM.md`
  - **Problema:** Data "2026-03-22", "37 endpoints" (actual: 42+)
  - **Fix:** Regenereaza complet — data 2026-04-07, Version R6, toate endpoint-urile noi (inclusiv cele din F1-F6), 12 pagini frontend, AI providers activi
  - **Verificare:** Nr endpoints in document = nr real din `main.py` + routere
  - Sursa: R4 F5.2 [P1]

- [x] **F7-5** `[T]` lucide-react upgrade la latest stable | **IMPLEMENTAT 2026-04-07**
  - **Fisier:** `frontend/package.json`
  - **Comanda:** `npm install lucide-react@latest`
  - **Verificare:** `npm run build` fara erori; UI-ul afiseaza iconitele corect
  - Sursa: R4 F1.2 [P1]

---

# FAZA 8 — TESTARE INTEGRALA (AUDIT BLOCKER)

> Test coverage < 5% backend, < 1% frontend = cel mai mare gap in audit.
> Efort total: ~2 zile | Risc: LOW | Prioritate: P0 conform info.txt

- [ ] **F8-1** `[!][T]` Backend test coverage: 5% → 30%
  - **Fisiere noi de creat:**
    ```
    tests/test_job_service.py         — mock LangGraph, state transitions, timeout
    tests/test_cache_service.py       — TTL, eviction LRU, cache hit/miss
    tests/test_routers_extended.py    — toate endpoint-urile cu TestClient (42 endpoints)
    tests/test_database.py            — migrations, CRUD, WAL mode, backup
    tests/test_scoring.py             — scoring 6 dimensiuni + modele predictive F2
    tests/test_just_client.py         — Portal Just SOAP mock
    tests/test_network_client.py      — retea firme SQL recursive
    tests/test_funding_programs.py    — matching programe fonduri
    ```
  - **Setup:** `pip install pytest pytest-asyncio pytest-cov` (daca nu exista)
  - **Target minimum:** 30% coverage overall, 80% coverage pe fisierele noi din R6
  - **Comanda validare:** `pytest tests/ --cov=backend --cov-report=term-missing`
  - **Verificare:** `Coverage: XX%` ≥ 30% in output
  - Sursa: R5 F4-1 [ ], R4 F3.2 [ ], Audit_R5.md TEST-COVERAGE-001, info.txt [P0]

- [ ] **F8-2** `[!][T]` Frontend component tests: <1% → 20%
  - **Instalare:** `npm install --save-dev @testing-library/react @testing-library/user-event vitest jsdom`
  - **Fisiere noi de creat:**
    ```
    frontend/src/tests/Toast.test.tsx              — success/error/warning/info variants
    frontend/src/tests/ErrorBoundary.test.tsx      — error thrown → fallback UI
    frontend/src/tests/api.test.ts                 — mock fetch, error codes, retry
    frontend/src/tests/Companies.test.tsx          — filters, pagination, favorite toggle
    frontend/src/tests/ReportView.test.tsx         — tabs rendering, download buttons
    frontend/src/tests/cui-validator.test.ts       — MOD11 edge cases (existent, extinde)
    ```
  - **Comanda validare:** `npm run test -- --coverage`
  - **Verificare:** `Coverage: XX%` ≥ 20% in output
  - Sursa: R5 F4-2 [ ], R4 F3.1 [ ], Audit_R5.md TEST-COVERAGE-002, info.txt [P0]

- [ ] **F8-3** `[T]` Bundle Analysis — code splitting per pagina
  - **Instalare:** `npm install --save-dev rollup-plugin-visualizer`
  - **Config:** `vite.config.ts` → adauga visualizer plugin in build mode
  - **Target:** Chunk principal < 50KB; fiecare pagina = chunk separat (React.lazy existent)
  - **Comanda:** `npm run build -- --mode production` → deschide `dist/stats.html`
  - **Verificare:** Niciun chunk > 200KB; pagini lazy-loaded confirmate
  - Sursa: R5 F4-4 [ ], info.txt [P1]

- [x] **F8-4** `[T]` Test integrare Portal Just — mock SOAP | **IMPLEMENTAT 2026-04-07**
  - **Fisier nou:** `tests/test_just_client.py`
  - **Mock:** `unittest.mock.patch("zeep.Client")` → raspuns simulat cu 3 dosare
  - **Scenarii:** 0 dosare, 1 dosar reclamant, 5 dosare mixte, timeout 30s, SOAP error
  - **Verificare:** Toate 5 scenarii trec; timeout returneaza `{"dosare": [], "error": "timeout"}`
  - Sursa: F1-1 (Portal Just)

- [x] **F8-5** `[T]` Test modele predictive — formule matematice
  - **Fisier nou:** `tests/test_predictive_models.py`
  - **Scenarii:**
    - Firma sanatoasa → Altman Z > 2.60, Piotroski F ≥ 7, Beneish M < -2.22
    - Firma in distress → Altman Z < 1.10, Zmijewski X > 0
    - Date insuficiente (1 an bilant) → Piotroski = None cu mesaj clar
    - Active zero → nu crapa cu ZeroDivision, returneaza `{"zone": "INDISPONIBIL"}`
  - **Verificare:** Toate 4 scenarii trec; formule matematice corecte (validat cu valori cunoscute)
  - Sursa: F2-1..F2-4 | **IMPLEMENTAT 2026-04-07** (29 teste, 100% PASSED)

---

# FAZA 9 — REFACTORING + OPTIMIZARE

> Calitatea codului si scalabilitatea. Nu blocheaza functionalitatea, dar e necesar pentru 93/100.
> Efort total: ~2 zile | Risc: MEDIUM | Sursa: R4 F6.x, Audit_Intern_Roland.md §12

- [ ] **F9-1** `[T]` Split fisiere frontend > 500 LOC
  - **Fisiere afectate:**
    - `ReportView.tsx` (619 LOC) → `ReportOverview.tsx` + `ReportRisk.tsx` + `ReportCharts.tsx`
    - `CompanyDetail.tsx` (551 LOC) → `CompanyHeader.tsx` + `CompanyScoring.tsx` + `CompanyHistory.tsx`
    - `Dashboard.tsx` (521 LOC) → extrage `DashboardStats.tsx` + `DashboardActivity.tsx`
    - `NewAnalysis.tsx` (500 LOC) → extrage `WizardStep1.tsx` + `WizardStep2.tsx` + `WizardStep3.tsx`
  - **Regula:** Fiecare fisier rezultat < 200 LOC
  - **Verificare:** `npm run build` fara erori; UI functional identical
  - Sursa: R4 F2.4 [P1]

- [ ] **F9-2** `[T]` Refactor god functions — scoring + synthesis
  - **Fisiere:**
    - `scoring.py` (832 LOC) → extrage `RiskScoreCalculator` class + `SolvencyAnalyzer` class
    - `agent_synthesis.py` (1113 LOC) → extrage `ProviderRouter` + `SectionPromptBuilder` + `TokenBudgetChecker`
  - **Target:** Nicio clasa > 300 LOC, nicio functie > 80 LOC
  - **Verificare:** Toate testele existente (184) trec dupa refactor
  - Sursa: R4 F6.1 [P2]

- [ ] **F9-3** Extract service layer din `routers/reports.py`
  - **Fisier nou:** `backend/services/report_file_service.py`
  - **Extrage:** Logica de acces fisiere, path validation, download headers
  - **Router:** Apeleaza service, nu acceseaza DB direct
  - **Verificare:** Ruter `reports.py` < 100 LOC; service testabil independent
  - Sursa: R4 F6.2 [P2]

- [ ] **F9-4** `[T]` NLQ "Ask RIS" — chatbot simplu pe date locale
  - **Endpoint:** `POST /api/ask` cu `{"question": "Care firma are cel mai mare risc?"}`
  - **Logica:** Intent classifier (rule-based sau LLM mic) → SQL query → raspuns natural
  - **UI:** Chat panel flotant in Dashboard (icon mesaj → expandabil)
  - **Exemple suportate:** "Top 5 firme risc rosu", "Companii din CAEN 6201", "Firma cu cel mai mic scor"
  - **Verificare:** 5 intrebari predefinite returneza raspunsuri corecte
  - Sursa: R4 F4.1 [P2]

- [ ] **F9-5** `[T]` Cohere Embed + Semantic Search companii similare
  - **Fisier nou:** `backend/services/semantic_service.py`
  - **Env Var:** `COHERE_API_KEY` (disponibil)
  - **Functie:** "Firme similare" devine semantic (nu doar acelasi CAEN exact)
  - **Endpoint:** `GET /api/companies/{cui}/similar?semantic=true`
  - **Verificare:** "Constructii drumuri" → returneaza firme CAEN 4211, 4212, 4213
  - Sursa: R4 F7.3 [P2]

- [ ] **F9-6** Dark/Light Theme Toggle
  - **Fisier:** `frontend/src/components/Layout.tsx` + `frontend/src/index.css`
  - **Implementare:** Toggle in header → `localStorage.setItem("theme", "light"|"dark")` → CSS class pe `<html>`
  - **Persistenta:** Citit la mount din localStorage
  - **Verificare:** Toggle comuta tema; dupa refresh, tema selectata e restaurata
  - Sursa: Audit_Intern_Roland.md §14.4

---

# FAZA 10 — SURSE VIITOARE + UPGRADES TEHNICE

> Items strategice si upgrade-uri planificate pentru urmatoarea sesiune.
> Efort total: ~3 zile | Risc: LOW-MEDIUM

- [ ] **F10-1** `[-]` Monitorul Oficial — scraping modificari statut
  - **Sursa:** `monitoruloficial.ro` (public) + `publicatii.mfinante.gov.ro`
  - **Efort:** 2-3 zile (scraper robust)
  - **Actiune:** Proiectat — implementare sesiunea urmatoare
  - Sursa: Audit_Intern_Roland.md §8 P1.1

- [ ] **F10-2** `[-]` AEGRM — garantii reale mobiliare
  - **Sursa:** `aegrm.ro` API REST public
  - **Efort:** 1-2 zile
  - **Actiune:** Proiectat — implementare sesiunea urmatoare
  - Sursa: Audit_Intern_Roland.md §8 P1.2

- [ ] **F10-3** `[-]` TanStack Query pentru data fetching
  - **Comanda:** `npm install @tanstack/react-query@^5.96.2`
  - **Migrare:** Treptat, pagini cu cel mai mult boilerplate first
  - **Elimina:** ~100 linii useEffect/useState boilerplate
  - Sursa: R5 F4-6 [ ], R4 F3.3 [ ], info.txt [P2]

- [ ] **F10-4** `[-]` Mistral OCR — procesare documente scanate
  - **Endpoint nou:** `POST /api/documents/ocr` — upload PDF → text structurat
  - **Model:** Mistral pixtral-12b sau mistral-ocr-latest
  - **Util:** Due diligence cu documente uploadate manual
  - Sursa: R4 F7.5 [P3]

- [ ] **F10-5** `[-]` Vite upgrade → v7.x
  - **Comanda:** `npm install vite@latest`
  - **Verifica:** `vite.config.ts` compatibil cu v7
  - Sursa: R4 F2.2 [P1]

- [ ] **F10-6** `[-]` Tailwind CSS v3 → v4
  - **Risc:** MEDIUM (CSS-first config, clase custom)
  - **Verifica:** `dark-card`, `dark-border`, `accent-primary` in v4
  - **Beneficiu:** Build 5-10x mai rapid (Oxide/Rust engine)
  - Sursa: R4 F2.3 [P1]

- [ ] **F10-7** `[-]` Bulk actions companii (multi-select)
  - **Fisier:** `frontend/src/pages/Companies.tsx`
  - **Feature:** Checkbox per card → toolbar cu "Export selectate", "Re-analizeaza selectate", "Taginare bulk"
  - Sursa: Audit_Intern_Roland.md §14.3

- [ ] **F10-8** `[-]` GlobalSearch accesibil pe mobile
  - **Fisier:** `frontend/src/components/Layout.tsx`
  - **Fix:** Buton lupa vizibil in mobile header → deschide modal search (existent pe desktop)
  - Sursa: Audit_Intern_Roland.md §14.4

---

---

# AGENT DE VERIFICARE — CHECKLIST COMPLETITUDINE R6

> **Scopul acestei sectiuni:** La finalul implementarii R6, parcurge fiecare item si confirma
> ca nimic nu a fost omis. Un item e `VALID` doar daca are: cod scris + test scris + manual testare.

---

## CHECKLIST FUNCTIONALITATI NOI (23 items)

| #   | ID   | Feature                                      | Cod | Test | Manual | Status |
| --- | ---- | -------------------------------------------- | --- | ---- | ------ | ------ |
| 1   | F1-1 | Portal Just SOAP client                      | [ ] | [ ]  | [ ]    |        |
| 2   | F1-2 | Tabel `company_administrators` SQL           | [ ] | [ ]  | [ ]    |        |
| 3   | F1-3 | Retea firme SQL recursive                    | [ ] | [ ]  | [ ]    |        |
| 4   | F1-4 | Endpoint `/api/companies/{cui}/network`      | [ ] | [ ]  | [ ]    |        |
| 5   | F1-5 | Penalizare retea firme insolvente in scoring | [ ] | [ ]  | [ ]    |        |
| 6   | F1-6 | Sectiune raport "Reteaua de Firme"           | [ ] | [ ]  | [ ]    |        |
| 7   | F2-1 | Altman Z''\_EMS formula                      | [ ] | [ ]  | [ ]    |        |
| 8   | F2-2 | Piotroski F-Score 9 criterii                 | [ ] | [ ]  | [ ]    |        |
| 9   | F2-3 | Beneish M-Score 5 variabile                  | [ ] | [ ]  | [ ]    |        |
| 10  | F2-4 | Zmijewski X-Score                            | [ ] | [ ]  | [ ]    |        |
| 11  | F2-5 | Endpoint `/api/scoring/{cui}/predictive`     | [ ] | [ ]  | [ ]    |        |
| 12  | F2-6 | Tab "Scoruri Predictive" ReportView          | [ ] | [ ]  | [ ]    |        |
| 13  | F3-1 | GitHub Models + Fireworks AI + SambaNova     | [x] | [ ]  | [ ]    | COD OK |
| 14  | F3-2 | OpenRouter safety net nivel 6                | [x] | [ ]  | [ ]    | COD OK |
| 15  | F4-3 | Endpoint monitoring audit-log                | [ ] | [ ]  | [ ]    |        |
| 16  | F4-4 | Alert suppression false positives            | [ ] | [ ]  | [ ]    |        |
| 17  | F5-1 | Modul Fonduri Real + JSON local              | [ ] | [ ]  | [ ]    |        |
| 18  | F5-2 | Google Maps scoring reputational             | [ ] | [ ]  | [ ]    |        |
| 19  | F5-3 | UBO beneficiari reali                        | [ ] | [ ]  | [ ]    |        |
| 20  | F6-6 | Auto-reanaliza programata (F3-4 amanat)      | [ ] | [ ]  | [ ]    |        |
| 21  | F6-7 | Raport multi-an aceeasi firma (F3-11 amanat) | [ ] | [ ]  | [ ]    |        |
| 22  | F9-4 | NLQ "Ask RIS" chatbot                        | [ ] | [ ]  | [ ]    |        |
| 23  | F9-5 | Cohere semantic search companii similare     | [ ] | [ ]  | [ ]    |        |

---

## CHECKLIST FIX-URI TEHNICE (20 items)

| #   | ID   | Fix                                 | Implementat | Verificat | Status |
| --- | ---- | ----------------------------------- | ----------- | --------- | ------ |
| 1   | F0-1 | Gemini model ID fix                 | [ ]         | [ ]       |        |
| 2   | F0-2 | Mistral API key update              | [ ]         | [ ]       |        |
| 3   | F0-3 | job_service.py split monolith       | [ ]         | [ ]       |        |
| 4   | F3-3 | Trust scoring ponderat              | [ ]         | [ ]       |        |
| 5   | F3-4 | Anomalie thresholds sector-ajustate | [ ]         | [ ]       |        |
| 6   | F3-5 | Token budget tiktoken               | [ ]         | [ ]       |        |
| 7   | F3-6 | Cross-section coherence real        | [ ]         | [ ]       |        |
| 8   | F3-7 | Section regeneration endpoint       | [ ]         | [ ]       |        |
| 9   | F3-8 | openapi.ro 429 WARNING explicit     | [ ]         | [ ]       |        |
| 10  | F4-1 | Severity escalation 2+ RED          | [ ]         | [ ]       |        |
| 11  | F4-2 | Sync companies.is_active la RADIAT  | [ ]         | [ ]       |        |
| 12  | F4-5 | config.py secret key persistent     | [ ]         | [ ]       |        |
| 13  | F5-4 | CAEN Rev.3 update                   | [ ]         | [ ]       |        |
| 14  | F6-1 | Risk badge pe Company Cards         | [ ]         | [ ]       |        |
| 15  | F6-2 | Radar chart 6 dimensiuni            | [ ]         | [ ]       |        |
| 16  | F6-3 | Warning completeness < 50%          | [ ]         | [ ]       |        |
| 17  | F6-4 | Sector benchmark bar                | [ ]         | [ ]       |        |
| 18  | F6-5 | Draft wizard localStorage           | [ ]         | [ ]       |        |
| 19  | F6-8 | Sterge widget duplicat Dashboard    | [ ]         | [ ]       |        |
| 20  | F7-1 | N+1 query fix batch                 | [ ]         | [ ]       |        |

---

## CHECKLIST TESTE (13 items)

| #   | Fisier test                                 | Coverage target      | Scris | Trec | Status |
| --- | ------------------------------------------- | -------------------- | ----- | ---- | ------ |
| 1   | `tests/test_job_service.py`                 | job lifecycle, state | [ ]   | [ ]  |        |
| 2   | `tests/test_cache_service.py`               | TTL, LRU, eviction   | [ ]   | [ ]  |        |
| 3   | `tests/test_routers_extended.py`            | 42 endpoints         | [ ]   | [ ]  |        |
| 4   | `tests/test_database.py`                    | migrations, WAL      | [ ]   | [ ]  |        |
| 5   | `tests/test_scoring.py`                     | 6 dim + predictive   | [ ]   | [ ]  |        |
| 6   | `tests/test_just_client.py`                 | SOAP mock 5 scenarii | [ ]   | [ ]  |        |
| 7   | `tests/test_network_client.py`              | SQL recursive        | [ ]   | [ ]  |        |
| 8   | `tests/test_funding_programs.py`            | matching 5 scenarii  | [ ]   | [ ]  |        |
| 9   | `tests/test_predictive_models.py`           | Altman, F, M, Z      | [ ]   | [ ]  |        |
| 10  | `frontend/src/tests/Toast.test.tsx`         | 4 variante           | [ ]   | [ ]  |        |
| 11  | `frontend/src/tests/ErrorBoundary.test.tsx` | throw + fallback     | [ ]   | [ ]  |        |
| 12  | `frontend/src/tests/api.test.ts`            | mock fetch, retry    | [ ]   | [ ]  |        |
| 13  | `frontend/src/tests/Companies.test.tsx`     | filters + favorites  | [ ]   | [ ]  |        |

---

## CHECKLIST CARRYOVER R4 (9 items)

| #   | ID      | Item                             | Implementat | Status |
| --- | ------- | -------------------------------- | ----------- | ------ |
| 1   | R4-F7-5 | CSV streaming memory fix         | [ ]         |        |
| 2   | R4-F6-4 | Type hints functii publice       | [ ]         |        |
| 3   | R4-F5-2 | FUNCTII_SISTEM.md actualizat     | [ ]         |        |
| 4   | R4-F1-2 | lucide-react upgrade             | [ ]         |        |
| 5   | R4-F2-4 | Split fisiere frontend >500 LOC  | [ ]         |        |
| 6   | R4-F6-1 | God functions refactor           | [ ]         |        |
| 7   | R4-F6-2 | Service layer extras din routere | [ ]         |        |
| 8   | R4-F4-1 | N+1 query batch (F7-1 R6)        | [ ]         |        |
| 9   | R4-F3-3 | TanStack Query (F10-3 R6)        | [ ]         |        |

---

## VERIFICARE FINALA — CRITERII DE ACCEPTANTA R6

```
[ ] pytest tests/ --cov=backend --cov-report=term-missing
    → Coverage ≥ 30%

[ ] npm run test -- --coverage
    → Coverage ≥ 20%

[ ] npm run build
    → 0 erori TypeScript, 0 erori build

[ ] python -m backend.main (start backend)
    → 0 erori la startup, toate routerele inregistrate

[ ] Analiza test CUI=26313362
    → completeness ≥ 85%, scor calculat, retea firme in raport
    → Altman Z / Piotroski F / Beneish M calculate si afisate
    → Portal Just returneaza date (sau "0 dosare gasite" — nu eroare)
    → Provider chain: Gemini activ (nu 404), Mistral activ (nu 401)

[ ] Verificare logs dupa analiza:
    → ZERO "gemini-2.5-flash-preview-05-20" in ris_runtime.log
    → ZERO "401 Unauthorized" Mistral in ris_runtime.log
    → noi provideri (GitHub/Fireworks/SambaNova) in `_provider_methods`; Mistral fara 401; Gemini fara 404

[ ] Scor audit estimat post-R6: ≥ 93/100
```

---

## NOTE IMPLEMENTARE GLOBALE

1. **Ordinea obligatorie:** F0 → F1 → F2 → F3-F4 (paralel) → F5 → F6 → F7 → F8 → F9-F10 (optional)
2. **Dependinte critice:**
   - F1-3 (retea firme) depinde de F1-2 (tabel SQL)
   - F2-6 (tab frontend) depinde de F2-1..F2-4 (backend modele)
   - F3-1 + F3-2 (provideri noi) — independente, pot fi paralele
   - F8-5 (teste predictive) depinde de F2-1..F2-4
3. **Provideri AI activi dupa R6 (sesiunea 2026-04-07):**
   - Stack existent: Claude CLI → Groq → Gemini → Cerebras → Mistral (fixed) → OpenRouter (fixed)
   - Adaugati R6: GitHub Models + Fireworks AI + SambaNova (all in `_PROVIDERS` + `_concurrent_fallback`)
   - **ELIMINATI (non-free):** xAI Grok ($25 credit signup ≠ permanent free), OpenAI (pay-per-use)
4. **GDPR / Securitate:** DeepSeek (`DEEPSEEK_API_KEY`) — NU folosit in productie cu date reale (servere China)
5. **Chei adaugate in `.env` (2026-04-07):** `GITHUB_TOKEN`, `FIREWORKS_API_KEY`, `SAMBANOVA_API_KEY`, `MISTRAL_API_KEY` (updated)
   **Chei disponibile dar neadaugate:** `GOOGLE_CLOUD_API_KEY`, `JINA_API_KEY`, `COHERE_API_KEY` — in `API_KEYS.md`
6. **Migration SQL:** Toate modificarile de schema → fisiere noi in `backend/migrations/` (nu ALTER TABLE direct)
7. **CAEN Rev.3 deadline:** 25 septembrie 2026 — daca R6 se executa dupa iulie 2026, F5-4 devine F0

---

_Plan creat: 7 Aprilie 2026 | Versiune: R6.0_
_Surse: Audit_Intern_Roland.md v1.3 + R4 carryover (18 items) + R5 [ ] si [-] (6 items) + Audit_R5.md + info.txt_
_Total items activi: 57 | Total items amanati [-]: 8 | Total teste noi: 13_
_Autor: Roland Petrila + Claude Code (claude-sonnet-4-6)_
