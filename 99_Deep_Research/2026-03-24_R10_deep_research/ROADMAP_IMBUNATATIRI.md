# R10 Roadmap Imbunatatiri — Roland Intelligence System (RIS)
Data: 2026-03-24 | Sursa: Deep Research R10 (6 agenti paraleli + audit manual) | Total: 18 items

---

## Prioritizare: BLOC-uri de implementare

Recomandam implementare in 4 BLOC-uri, fiecare testabil independent.

---

## BLOC 0 — Security + Scoring Refactor (URGENT)
**Efort total: 5-6h | Impact: HIGH | Blocheaza: securitate WebSocket + maintainability scoring**

| ID | Fisier:Linie | Descriere | Sev | Efort |
|----|-------------|----------|-----|-------|
| SEC-01 | main.py:~480 | WebSocket auth: valideaza X-RIS-Key la WS upgrade sau token in query param `?token=...`. Daca `settings.ris_api_key` e setat si token lipseste/gresit → close(4001, "Unauthorized") | HIGH | 30min |
| SEC-02 | main.py:232 | CORS: inlocuieste `100\.\d+\.\d+\.\d+` cu IP-ul Tailscale specific sau FQDN. Daca nu e nevoie de Tailscale → sterge pattern-ul complet | MED | 5min |
| SCORE-01 | scoring.py:68-619 | Split `calculate_risk_score()` (551 LOC, 72 branches) in 6 sub-functii: `_score_financial()`, `_score_legal()`, `_score_fiscal()`, `_score_operational()`, `_score_reputational()`, `_score_market()` + `_aggregate_scores()`. Fiecare < 80 LOC | HIGH | 3h |
| SCORE-02 | scoring.py:91-227 | Extract magic numbers in constante: `SCORING_THRESHOLDS = {"ca_excellent": 10_000_000, "growth_excellent": 50, ...}` la inceputul fisierului | MED | 1h |
| PERF-03 | routers/reports.py:49-50 | Fix sync Path.exists() in async route: stocheaza format flags in DB la generare raport sau cache-uieste la startup | MED | 30min |

**Criteriu reusita:** WebSocket respinge conectari fara token valid. `calculate_risk_score()` split in 6+ functii, fiecare < 80 LOC. `pytest tests/test_scoring.py -v` — 0 failures.

---

## BLOC 1 — Test Coverage Expansion (URGENT)
**Efort total: 8-12h | Impact: HIGH | Blocheaza: incredere in sistem pentru productie**

| ID | Fisier:Linie | Descriere | Sev | Efort |
|----|-------------|----------|-----|-------|
| TST-01 | tests/test_services.py (NOU) | Teste servicii: job_service (create/complete/fail/retry), cache_service (set/get/expire/LRU eviction), notification (send/fail), scheduler (start/stop/run cycle), monitoring_service (check company/alert/throttle), delta_service (calculate/empty). Target: 25+ teste | HIGH | 4h |
| TST-02 | tests/test_routers.py (NOU) | Teste routere cu TestClient: jobs (POST+GET+status), reports (list+download), companies (list+search), compare (POST+error), monitoring (CRUD), batch (upload+progress), settings (GET+PUT). Target: 20+ teste | HIGH | 4h |
| TST-03 | tests/test_integration.py (NOU) | Integration test: full pipeline mock (CUI → orchestrator → agents mock → reports mock → verify output structure). Verifica ca state machine LangGraph produce output valid end-to-end. Target: 3-5 teste | HIGH | 2h |
| TST-04 | tests/test_tools.py (NOU) | Teste tools lipsa: tavily_client (search/quota), seap_client (fetch/empty/cache), openapi_client (fetch/error/rate limit). Target: 10+ teste | MED | 2h |

**Criteriu reusita:** `pytest tests/ -v` — 220+ teste, 0 failures. Test coverage estimat > 50%.

---

## BLOC 2 — Quick Wins + Deprecation Fix (IMPORTANT)
**Efort total: 2-3h | Impact: MED-HIGH | Blocheaza: deprecation warnings, minor bugs**

| ID | Fisier:Linie | Descriere | Sev | Efort |
|----|-------------|----------|-----|-------|
| DT-01 | 20+ fisiere backend | Migreaza TOATE `datetime.utcnow()` la `datetime.now(UTC)`. Fisiere: base.py (5x), agent_official.py (2x), agent_verification.py (2x), batch.py (5x), jobs.py, generator.py (2x), job_service.py (3x), scheduler.py (3x), job_logger.py (3x). Import `from datetime import datetime, UTC` | MED | 1h |
| DB-01 | database.py:68-69 | Inlocuieste `except Exception: pass` cu `except Exception as e: logger.debug(f"Migration column check: {e}")` | MED | 5min |
| CMP-02 | compare_generator.py:155-158 | Fix barele vizuale: cand va sau vb is None, skip desenare bar si afiseaza "[Date insuficiente]" in loc de 0 | MED | 30min |
| CMP-04 | routers/compare.py | Adauga UUID in filename PDF comparativ: `f"comparativ_{uuid4().hex[:8]}.pdf"` — previne overwrite | MED | 10min |
| CLEAN-01 | agent_verification.py:626-627 | Sterge cele 2 linii de comment rezidual (SPLIT-02 reference) | LOW | 1min |

**Criteriu reusita:** `grep utcnow backend/ -r` — 0 rezultate. `grep "except Exception: pass" backend/ -r` — 0 rezultate.

---

## BLOC 3 — Performance + Polish (NICE TO HAVE)
**Efort total: 5-8h | Impact: MED | Imbunatateste DX si calitate**

| ID | Fisier:Linie | Descriere | Sev | Efort |
|----|-------------|----------|-----|-------|
| PERF-02 | backend/main.py + imports | Investigheaza import time 11.97s: ruleaza `python -X importtime 2>&1 | sort -t: -k2 -n | tail -20`, identifica modulele lente, aplica lazy import unde posibil (ex: LangGraph, openpyxl, python-pptx) | HIGH | 2-4h |
| SYNTH-04 | agent_synthesis.py:467 | Separare exception handling: catch httpx.TimeoutException (retry), httpx.HTTPStatusError cu status 401 (skip provider) si 429 (backoff+retry) | MED | 1h |
| BPI-05 | bpi_client.py | Adauga retry cu exponential backoff pe HTTP 429: `for attempt in range(3): if resp.status_code == 429: await asyncio.sleep(2 ** attempt)` | MED | 30min |
| CMP-05 | compare_generator.py | Adauga trust labels in pagina comparativa: sursa date + data ultimei actualizari per firma | LOW | 1h |

**Criteriu reusita:** Backend import time < 8s. BPI retry functional pe 429.

---

## Sumar Roadmap

| BLOC | Items | HIGH | MED | LOW | Efort | Prioritate |
|------|-------|------|-----|-----|-------|-----------|
| 0 — Security + Scoring | 5 | 2 | 3 | 0 | 5-6h | URGENT |
| 1 — Test Coverage | 4 | 3 | 1 | 0 | 8-12h | URGENT |
| 2 — Quick Wins | 5 | 0 | 4 | 1 | 2-3h | IMPORTANT |
| 3 — Performance | 4 | 1 | 2 | 1 | 5-8h | NICE TO HAVE |
| **TOTAL** | **18** | **6** | **10** | **2** | **20-29h** | |

---

## Ordine Executie Recomandata

```
BLOC 0 (Security + Scoring) ── PRIMUL: fix WebSocket auth + split scoring
         |
BLOC 2 (Quick Wins) ────────── Rapid, ROI maxim, fara dependinte
         |
BLOC 1 (Test Coverage) ─────── Cel mai important, necesita timp
         |
BLOC 3 (Performance) ────────── Dependent de testele din BLOC 1
```

**Nota:** BLOC 0 trebuie PRIMUL (securitate). BLOC 2 poate fi paralel cu BLOC 0. BLOC 1 beneficiaza de scoring refactor din BLOC 0. BLOC 3 necesita testele din BLOC 1 ca safety net.

---

## Estimare Scor Post-R10

Daca se implementeaza BLOC 0+1+2:

| Aspect | R10 actual | R10 post-fix | Delta |
|--------|-----------|-------------|-------|
| Securitate | 9/10 | 10/10 | +1 (WS auth, CORS fix) |
| Calitate Cod | 8/10 | 9/10 | +1 (scoring split, utcnow fix, constants) |
| Arhitectura | 8/10 | 9/10 | +1 (scoring modular, 72→6 branches) |
| Testare | 7/10 | 9/10 | +2 (servicii + routere + integration) |
| Performanta | 8/10 | 8/10 | = |
| Documentatie | 8/10 | 8/10 | = |
| Dependente | 9/10 | 9/10 | = |
| Deploy Ready | 8/10 | 9/10 | +1 (incredere din teste + securitate) |
| **TOTAL** | **65/80** | **71/80** | **+6** |

**Cu BLOC 3 inclus: ~72-73/80. Target 70+/80 ATINS cu BLOC 0+1+2.**

---

## Delta R8 → R9 → R10 → R10+fix

```
R8:  55/80 ████████████████████████████░░░░░░░░░░░░░░
R9:  60/80 ██████████████████████████████░░░░░░░░░░░░
R10: 65/80 ████████████████████████████████░░░░░░░░░░
R10+: 70/80 ██████████████████████████████████░░░░░░░░  ← TARGET
```
