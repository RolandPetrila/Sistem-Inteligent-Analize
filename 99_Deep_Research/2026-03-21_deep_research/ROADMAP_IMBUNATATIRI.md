# Roadmap Imbunatatiri RIS — 2026-03-21

Generat de Deep Research v2.0. Toate itemele au ROI calculat (Impact/Efort).

---

## SAPTAMANA 1 — Quick Wins (5 min - 30 min fiecare)

| # | Actiune | Fisier | Efort | Impact | ROI | Status |
|---|---------|--------|-------|--------|-----|--------|
| QW0 | Fix PATH TRAVERSAL: validate path in outputs/ | backend/routers/reports.py:140 | 15 min | CRITICAL | 10 | ❌ |
| QW1 | `pip freeze > requirements.txt` | requirements.txt | 5 min | CRITICAL | 10 | ❌ |
| QW2 | Adauga `backups/` in .gitignore | .gitignore | 1 min | CRITICAL | 9 | ❌ |
| QW3 | PRAGMA synchronous=NORMAL + mmap_size=268435456 | backend/database.py:21 | 5 min | MEDIUM | 6 | ❌ |
| QW4 | Inlocuieste shutil.copy2 cu sqlite3.backup() | backend/services/scheduler.py:109 | 30 min | HIGH | 9 | ❌ |
| QW5 | Toast pe catch-uri goale (7 locuri) | Dashboard, NewAnalysis, BatchAnalysis, Monitoring, Settings | 30 min | MEDIUM | 7 | ❌ |
| QW6 | Route 404 catch-all | frontend/src/App.tsx | 15 min | MEDIUM | 4 | ❌ |
| QW7 | uvicorn reload conditionat | backend/main.py:276 | 5 min | LOW | 4 | ❌ |
| QW8 | Secret key obligatoriu (fara default) | backend/config.py:32 | 15 min | MEDIUM | 5 | ❌ |

**Toate independente — executa in orice ordine.**

---

## SAPTAMANA 2 — Securitate & Stabilitate

| # | Actiune | Efort | Impact | ROI | Depinde de | Status |
|---|---------|-------|--------|-----|------------|--------|
| S1 | Batch progress persistent in DB (nu in-memory) | 30 min | HIGH | 9 | - | ❌ |
| S2 | Rate limiting cu slowapi pe POST | 1h | HIGH | 7 | - | ❌ |
| S3 | API key simplu (X-RIS-Key header) | 2-3h | HIGH | 6 | recomandat DUPA QW-uri | ❌ |
| S4 | Extinde api.ts (compare, batch, monitoring, trend) | 2h | MEDIUM | 7 | - | ❌ |
| S5 | Chart.js in bundle + elimina unsafe-eval din CSP | 1-2h | MEDIUM | 5 | - | ❌ |
| S6 | Cache SEAP client + cache in compare.py/monitoring | 30 min | MEDIUM | 7 | - | ❌ |
| S7 | Few-shot examples in AI prompts | 1h | MEDIUM | 6 | - | ❌ |

---

## SAPTAMANA 3-4 — Testare & Refactorizare

| # | Actiune | Efort | Impact | ROI | Depinde de | Status |
|---|---------|-------|--------|-----|------------|--------|
| T1 | pytest: CUI validator, ANAF mock, scoring | 4-8h | HIGH | 8 | - (dar INAINTE de A1!) | ❌ |
| T2 | vitest: CUI validator, api.ts | 2-4h | MEDIUM | 5 | - | ❌ |
| A1 | Split agent_verification.py (scoring, dd, ew, bench) | 2-4h | MEDIUM | 7 | T1 | ❌ |
| A2 | React.lazy() pe 8+ pagini | 30 min | MEDIUM | 5 | - | ❌ |
| A3 | Retry logic in clienti API externi | 2h | MEDIUM | 4 | T1 | ❌ |

---

## VIITOR (nice to have)

| # | Actiune | Efort | Impact | ROI | Conditie |
|---|---------|-------|--------|-----|----------|
| V1 | Split NewAnalysis.tsx in sub-componente | MARE | LOW | 2 | Doar daca se adauga pasi |
| V2 | Structured logging cu structlog | MARE | LOW | 2 | Doar cu monitoring extern |
| V3 | tsconfig strict unused vars | MIC | LOW | 3 | Cosmetic |
| V4 | CI/CD GitHub Actions | MARE | MEDIUM | 3 | Doar cu deployment automat |

---

## Grafic Dependinte

```
QW0-QW8 (independent, paralel — incepe cu QW0 PATH TRAVERSAL!)
    │
    ├─→ S1 (batch persistent), S4, S5, S6, S7 (independent)
    │
    ├─→ S2 (rate limiting), S3 (auth) — recomandat dupa QW-uri
    │
    └─→ T1 (teste backend)
          │
          ├─→ A1 (split agent_verification)
          └─→ A3 (retry logic)

T2 (teste frontend) → independent

A2 (React.lazy) → independent
```

**REGULA DE AUR:** Niciodata refactorizare fara teste. T1 INAINTE de A1 si A3.
