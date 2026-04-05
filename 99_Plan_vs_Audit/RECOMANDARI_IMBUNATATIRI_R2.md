# RECOMANDARI IMBUNATATIRI R2 — RIS (Post-Implementare)
**Data:** 2026-04-01 | **Versiune:** 2.0 | **Mod:** complet
**Context:** Runda 2, dupa implementarea tuturor 40 items din R1 (2026-03-31)
**Focus:** Bug-uri din implementare + features neacoperite in R1 + tendinte noi 2026

---

## COMPARATIE CU R1 (SNAPSHOT ANTERIOR)

| Aspect | R1 (31.03) | R2 (01.04) | Status |
|--------|-----------|-----------|--------|
| Scoring confidence | Linear → power-law | Bug edge case gasit (#7) | NEEDS FIX |
| Zombie detection | Implementat | False positive pe inactive (#8) | NEEDS FIX |
| Circuit breaker | Definit in orchestrator | NICIODATA apelat (#3) | BROKEN |
| L1 Cache | Implementat | Nu e async-safe (#5) | NEEDS FIX |
| Notifications | Router + migration | create_notification() neapelat (#1) | 40% BROKEN |
| Global Search | Component functional | ARIA accessibility lipsa (#F1) | NEEDS FIX |
| ETA Progress | Implementat | Race condition pe WS (#F2) | NEEDS FIX |
| CSV Batch Preview | Implementat | Nu detecteaza header row (#F5) | NEEDS FIX |
| Notification Bell UI | Backend exista | Frontend LIPSESTE (#M1) | MISSING |
| Favorites UI | Backend exista | Frontend LIPSESTE (#M2) | MISSING |
| Risk Movers Widget | Endpoint exista | Frontend LIPSESTE (#M3) | MISSING |
| Timeline UI | Endpoint exista | Frontend LIPSESTE (#M4) | MISSING |
| Email Send Modal | Endpoint exista | Frontend LIPSESTE (#M5) | MISSING |

---

## PARTEA I — FIX-URI IMPLEMENTARI R1 (Bugs din sesiunea anterioara)

---

### 1. Notifications: `create_notification()` neapelat din nicaieri

**Fisier:** `backend/routers/notifications.py` + `backend/services/job_service.py`
**Problema actuala:** Functia `create_notification()` e definita ca helper dar NIMENI nu o apeleaza. Job-urile finalizate trimit Telegram dar NU creeaza notificari in DB. Feature-ul Notifications e 40% functional — utilizatorul poate citi notificari dar nu se creeaza niciodata.

**Imbunatatire propusa:**
- Import `create_notification` in `job_service.py`
- Apeleaza la finalizarea fiecarui job (success + failure)
- Apeleaza din `monitoring_service.py` la fiecare alerta detectata

**Exemplu implementare:**
```python
# job_service.py — dupa notify_job_complete(), adauga:
from backend.routers.notifications import create_notification

# In run_analysis_job(), dupa job DONE:
await create_notification(
    type="job_complete",
    title=f"Analiza finalizata: {company_name}",
    message=f"Scor risc: {risk_score}. Raport disponibil.",
    link=f"/report/{report_id}",
    severity="success" if risk_score >= 70 else "warning" if risk_score >= 40 else "error",
)

# In run_analysis_job(), dupa job FAILED:
await create_notification(
    type="job_failed",
    title=f"Analiza esuata: {company_name}",
    message=str(error)[:200],
    link=f"/analysis/{job_id}",
    severity="error",
)
```

```python
# monitoring_service.py — dupa _send_telegram_with_retry(), adauga:
from backend.routers.notifications import create_notification

await create_notification(
    type="monitoring_alert",
    title=f"Alerta [{max_severity}]: {company_name}",
    message="; ".join(f"{c['field']}: {c['old']}→{c['new']}" for c in changes),
    link=f"/company/{alert['company_id']}",
    severity="error" if max_severity == "RED" else "warning",
)
```

**Complexitate:** Mica | **Impact:** Maxim — fara asta, Notification Center e gol

---

### 2. Circuit Breaker: definit dar neapelat

**Fisier:** `backend/agents/orchestrator.py`
**Problema actuala:** `is_provider_circuit_open()`, `record_provider_failure()`, `reset_provider_circuit()` sunt definite dar neapelate nicaieri. Providerii care esueaza repetat NU sunt skip-ati.

**Imbunatatire propusa:**
- Integreaza in `agent_synthesis.py` (cel mai important — synthesis e cel mai lent)
- Check circuit inainte de fiecare provider call
- Record failure la esec, reset la succes

**Exemplu implementare:**
```python
# agent_synthesis.py — in metoda de generare per provider:
from backend.agents.orchestrator import (
    is_provider_circuit_open, record_provider_failure, reset_provider_circuit
)

async def _generate_with_groq(self, prompt: str, ...) -> str:
    if is_provider_circuit_open("groq"):
        logger.info("[synthesis] Groq circuit OPEN, skipping to next provider")
        raise Exception("Circuit breaker: Groq skipped")
    try:
        result = await self._call_groq(prompt)
        reset_provider_circuit("groq")
        return result
    except Exception as e:
        record_provider_failure("groq")
        raise

# Analog pentru: _generate_with_gemini, _generate_with_cerebras, _generate_with_mistral
```

**Complexitate:** Mica | **Impact:** Mare — reduce timpii de procesare cu 10-30s cand un provider e down

---

### 3. L1 Cache: race condition pe async concurrent

**Fisier:** `backend/services/cache_service.py`
**Problema actuala:** `_L1Cache` foloseste `OrderedDict` fara asyncio.Lock. In scenarii concurente (2 agenti acceseaza aceeasi cheie simultan), posibila coruptie de date.

**Imbunatatire propusa:**
- Transforma `get()`/`put()` in metode async cu Lock
- SAU: accepta ca race condition e benigna (worst case: double read din L2) si documenteaza

**Exemplu implementare (varianta pragmatica):**
```python
# cache_service.py — _L1Cache
# Adauga nota + threading.Lock (nu asyncio.Lock — OrderedDict e CPU-bound, nu I/O)
import threading

class _L1Cache:
    def __init__(self, max_size: int = 50, ttl_seconds: int = 300):
        self._store: _LRUDict[str, tuple[float, dict]] = _LRUDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> dict | None:
        with self._lock:
            if key in self._store:
                ts, value = self._store[key]
                if _time_now() - ts < self._ttl:
                    self._store.move_to_end(key)
                    return value
                del self._store[key]
            return None

    def put(self, key: str, value: dict):
        with self._lock:
            self._store[key] = (_time_now(), value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)
```

**Complexitate:** Mica | **Impact:** Mediu — previne data corruption in scenarii high-concurrency

---

### 4. Email send: lipsa validare format email

**Fisier:** `backend/routers/reports.py`
**Problema actuala:** `SendEmailRequest.to` e doar `str` — utilizatorul poate trimite "not-an-email" si primeste eroare silentioasa de la SMTP.

**Imbunatatire propusa:**
- Adauga regex validare email in Pydantic model

**Exemplu implementare:**
```python
# reports.py — SendEmailRequest
import re

class SendEmailRequest(BaseModel):
    to: str
    subject: str | None = None
    message: str | None = None

    @validator("to")
    def validate_email(cls, v):
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Format email invalid")
        return v
```

**Complexitate:** Mica | **Impact:** Mediu — previne erori silentioase

---

### 5. Zombie detection: false positive pe firme inactive

**Fisier:** `backend/agents/verification/scoring.py`
**Problema actuala:** Zombie check trateaza firme cu status gol/lipsa ca "ACTIV". Dar firme cu status explicit "DIZOLVATA"/"RADIATA" care au CA=0 + angajati=0 NU sunt zombie — sunt legal inactive.

**Imbunatatire propusa:**
- Adauga exclusie explicita pentru statusuri de inchidere

**Exemplu implementare:**
```python
# scoring.py — in blocul zombie detection
INACTIVE_STATUSES = {"INACTIV", "DIZOLVATA", "RADIATA", "STINS", "RADIAT"}

if ca_val is not None and ca_val == 0 and angajati_val is not None and angajati_val == 0:
    stare = company.get("stare_firma", {})
    stare_val = stare.get("value", stare) if isinstance(stare, dict) else stare
    stare_upper = str(stare_val).upper() if stare_val else ""
    if stare_upper not in INACTIVE_STATUSES:
        is_zombie = True
        dimensions["operational"]["score"] = 10
        risk_factors.append(("ZOMBIE: CA=0 + angajati=0 + status activ", "CRITICAL"))
```

**Complexitate:** Mica | **Impact:** Mediu — previne false positive-uri

---

### 6. GlobalSearch: ARIA accessibility lipsa

**Fisier:** `frontend/src/components/GlobalSearch.tsx`
**Problema actuala:** Dialog-ul nu are `role="dialog"`, `aria-modal`, `aria-label` pe input, `role="listbox"` pe rezultate. Screen reader-ele nu il pot interpreta.

**Imbunatatire propusa:**
- Adauga atribute ARIA pe container, input si lista de rezultate
- Dezactiveaza Ctrl+K pe mobile (nu e utilizabil)

**Complexitate:** Mica | **Impact:** Mediu — accesibilitate

---

### 7. CSV Batch Preview: nu detecteaza header row

**Fisier:** `frontend/src/pages/BatchAnalysis.tsx`
**Problema actuala:** Daca CSV are header row ("CUI,Nume,Status"), prima linie e interpretata ca CUI, esueaza validarea, apare ca invalid. Majoritatea utilizatorilor exporta CSV cu headers din Excel.

**Imbunatatire propusa:**
- Detecteaza si skip-eaza header row (daca prima linie contine "CUI", "FIRMA", "COMPANY", "DENUMIRE")
- Afiseaza nota "(header detectat si omis)"

**Complexitate:** Mica | **Impact:** Mare — batch e feature principal

---

### 8. api.ts: AbortController nu se recreeaza pe retry

**Fisier:** `frontend/src/lib/api.ts`
**Problema actuala:** La retry dupa timeout, acelasi AbortController (deja abortat) se reutilizeaza. Request-ul nou esueaza instant.

**Imbunatatire propusa:**
- Creeaza AbortController NOU la fiecare attempt

**Complexitate:** Mica | **Impact:** Mare — retry-ul e complet nefunctional acum

---

### 9. AnalysisProgress: ETA race condition cand progress scade

**Fisier:** `frontend/src/pages/AnalysisProgress.tsx`
**Problema actuala:** Daca WebSocket trimite progress 30% dupa ce a fost la 50% (rebalansare), ETA devine negativ.

**Imbunatatire propusa:**
- Guard: `Math.max(msg.percent, prev.progress_percent)` — progress nu scade niciodata

**Complexitate:** Mica | **Impact:** Mediu — ETA e pur cosmetic dar confuzia e vizibila

---

### 10. CompanyDetail: butoane fara loading state

**Fisier:** `frontend/src/pages/CompanyDetail.tsx`
**Problema actuala:** "Monitorizeaza" nu are loading state. Click multiplu creeaza duplicate.

**Imbunatatire propusa:**
- Adauga `monitoringLoading` state
- Disable buton in timpul request-ului

**Complexitate:** Mica | **Impact:** Mediu — UX polish

---

## PARTEA II — FUNCTII NOI (Neacoperite in R1)

---

### N1. Notification Bell UI — Frontend pentru Notification Center

**Descriere:** Icon bell in Layout header cu badge count (numarul de notificari necitite). Click deschide dropdown cu lista notificari. Mark-as-read on click. Backend-ul exista deja complet.

**De ce e util:** Backend-ul de notificari e implementat dar utilizatorul nu poate vedea notificarile fara un frontend. Feature-ul e 40% complet.

**Complexitate:** Medie | **Impact:** Maxim

---

### N2. Favorites UI — Star pe companii + lista pe Dashboard

**Descriere:** Star icon pe CompanyDetail si Companies list. Widget "Companii Favorite" pe Dashboard. Backend-ul (toggle + list) exista deja.

**De ce e util:** Operatorul lucreaza cu 5-10 firme recurente. Fara favorites, trebuie sa caute de fiecare data.

**Complexitate:** Mica | **Impact:** Mare

---

### N3. Risk Movers Widget — Top 5 scor deteriorat pe Dashboard

**Descriere:** Widget pe Dashboard care arata top 5 firme cu scorul cel mai scazut in ultima luna. Endpoint-ul `/api/companies/stats/risk-movers` exista deja.

**De ce e util:** Proactiv — utilizatorul nu trebuie sa verifice manual fiecare firma.

**Complexitate:** Mica | **Impact:** Mare

---

### N4. Timeline UI — Istoric cronologic in CompanyDetail

**Descriere:** Componenta timeline in CompanyDetail care arata evenimente cronologic: analize, schimbari scor, alerte. Endpoint-ul `/api/companies/{id}/timeline` exista deja.

**De ce e util:** Inlocuieste navigarea manuala intre rapoarte.

**Complexitate:** Medie | **Impact:** Mediu

---

### N5. Email Send Modal — In ReportView

**Descriere:** Modal cu input email + subiect + mesaj. Trimite PDF atasat prin endpoint-ul existent POST /api/reports/{id}/send-email.

**De ce e util:** Reduce 3 pasi (descarca, deschide mail, ataseaza) la 1 click.

**Complexitate:** Mica | **Impact:** Mare

---

### N6. SQLite FTS5 — Full-text search pe rapoarte + companii

**Descriere:** Tabel FTS5 pentru cautare text in rapoarte si companii. Autocomplete pe nume/CUI. Cautare "insolventa" returneaza toate rapoartele relevante.

**De ce e util:** Global Search existent cauta doar dupa nume companie. FTS5 permite cautare in CONTINUTUL rapoartelor.

**Complexitate:** Medie | **Impact:** Mare

---

### N7. PWA — Instalare ca aplicatie desktop + offline rapoarte

**Descriere:** Adaugare `vite-plugin-pwa` cu manifest.json, service worker, cache strategy. RIS devine instalabil ca app desktop (fara browser vizibil). Rapoartele HTML se cache-uiesc offline.

**De ce e util:** Utilizatorul face dublu-click pe icon desktop in loc de browser. Rapoartele vechi se consulta fara internet.

**Complexitate:** Mica | **Impact:** Mediu

---

### N8. Automated Event Triage — Mini-agent de triaj la alerte monitoring

**Descriere:** Cand monitoring detecteaza o schimbare (scor scazut, status schimbat), un agent clasifica automat daca necesita: (A) re-analiza completa, (B) doar notificare, (C) ignorare (false positive). Bazat pe best practices pKYC 2026.

**De ce e util:** Reduce noise-ul de alerte. Monitorizarea 10 firme poate genera 50+ alerte/luna, dar doar 3-5 sunt actionabile.

**Complexitate:** Mare | **Impact:** Mare

---

### N9. Prompt-level i18n — Rapoarte in engleza

**Descriere:** Parametru `language: "en"` pe job. Agent 5 (Synthesis) primeste instructiune sa genereze raport in engleza. Template-uri duale RO/EN pentru header-uri, disclaimer, sectiuni fixe.

**De ce e util:** Investitori straini, parteneri europeni cer rapoarte in engleza. Fara asta, Roland trebuie sa traduca manual.

**Complexitate:** Medie | **Impact:** Mediu

---

### N10. Webhook Subscriptions — Push notificari la sisteme externe

**Descriere:** Tabel `webhook_subscriptions(url, event_type, secret, active)`. La finalizarea analizei sau alerta monitoring, POST webhook cu payload JSON. Retry 3x cu backoff.

**De ce e util:** Integrare cu ERP, CRM, Slack — analiza finalizata apare automat in alt sistem.

**Complexitate:** Medie | **Impact:** Mediu

---

## PARTEA III — IMBUNATATIRI TEHNICE

---

### T1. Teste pentru features noi R1 — 40% neacoperite

**Problema:** Niciun test pentru: notifications, favorites, timeline, risk-movers, send-email, L1 cache, circuit breaker, monitoring combos, zombie detection
**Solutie:** Fisier `tests/test_new_features.py` cu ~15 teste noi
**Complexitate:** Medie | **Impact:** Calitate — test coverage scazut pe cod nou

---

### T2. React 19.2 Activity Component

**Problema:** Navigare intre pagini pierde starea (scroll, tab selectat, input). React 19.2 ofera `<Activity>` care mentine starea in background.
**Solutie:** Wrap paginile frecvente (CompanyDetail, ReportView) cu `<Activity mode={visible/hidden}>`
**Complexitate:** Medie | **Impact:** Performanta + UX

---

### T3. SQLite FTS5 index pe reports + companies

**Problema:** Cautarea e limitata la LIKE pe nume companie. Nu poti cauta in continutul rapoartelor.
**Solutie:** Tabel virtual `reports_fts USING fts5(company_name, summary)` cu triggere sync
**Complexitate:** Medie | **Impact:** Performanta cautare

---

### T4. Contrast audit pe dark theme

**Problema:** Textul gri pe fond inchis (#94a3b8 pe #1a1a2e) poate fi sub WCAG AA (4.5:1). Neverificat.
**Solutie:** Audit automat cu axe-core/Lighthouse. Fix culorile sub-contrast.
**Complexitate:** Mica | **Impact:** Accesibilitate

---

### T5. Optimistic UI updates

**Problema:** Actiuni ca "toggle favorite", "start monitoring", "retry source" asteapta raspunsul serverului inainte de feedback vizual.
**Solutie:** Pattern optimistic: update UI instant, revert daca request esueaza.
**Complexitate:** Medie | **Impact:** UX snappier

---

### T6. PDF language attribute

**Problema:** PDF-urile generate nu au `/Lang (ro)` in metadata. Non-compliant cu WCAG 2.2.
**Solutie:** Adaugare `pdf.set_lang("ro")` in pdf_generator.py (fpdf2 suporta nativ).
**Complexitate:** Mica | **Impact:** Accesibilitate + compliance

---

### T7. AnalysisProgress polling fallback

**Problema:** Daca WebSocket se deconecteaza, utilizatorul vede progress inghetat fara feedback.
**Solutie:** Polling fallback la 5s cand WS e deconectat: `api.getJob(id)` periodic.
**Complexitate:** Mica | **Impact:** Rezilienta

---

## SUMAR PRIORITATI

| Prioritate | # | Nume | Complexitate | Impact | Categorie |
|---|---|---|---|---|---|
| **P0 — URGENT** | 1 | Notifications: create neapelat | Mica | Maxim | Fix R1 — Backend |
| **P0 — URGENT** | 2 | Circuit breaker: neintegrat | Mica | Mare | Fix R1 — Backend |
| **P0 — URGENT** | 8 | api.ts: AbortController retry broken | Mica | Mare | Fix R1 — Frontend |
| **P0 — URGENT** | N1 | Notification Bell UI | Medie | Maxim | Frontend missing |
| **P1 — IMPORTANT** | 3 | L1 Cache: threading lock | Mica | Mediu | Fix R1 — Backend |
| **P1 — IMPORTANT** | 4 | Email: validare format | Mica | Mediu | Fix R1 — Backend |
| **P1 — IMPORTANT** | 5 | Zombie: false positive inactive | Mica | Mediu | Fix R1 — Scoring |
| **P1 — IMPORTANT** | 7 | CSV header detection | Mica | Mare | Fix R1 — Frontend |
| **P1 — IMPORTANT** | 9 | ETA race condition guard | Mica | Mediu | Fix R1 — Frontend |
| **P1 — IMPORTANT** | 10 | Company buttons loading state | Mica | Mediu | Fix R1 — Frontend |
| **P1 — IMPORTANT** | N2 | Favorites UI | Mica | Mare | Frontend missing |
| **P1 — IMPORTANT** | N3 | Risk Movers Widget | Mica | Mare | Frontend missing |
| **P1 — IMPORTANT** | N5 | Email Send Modal | Mica | Mare | Frontend missing |
| **P1 — IMPORTANT** | T1 | Teste features noi | Medie | Mare | Calitate |
| **P2 — VALOROS** | 6 | GlobalSearch ARIA | Mica | Mediu | Accesibilitate |
| **P2 — VALOROS** | N4 | Timeline UI | Medie | Mediu | Frontend missing |
| **P2 — VALOROS** | N6 | SQLite FTS5 | Medie | Mare | Feature nou |
| **P2 — VALOROS** | N7 | PWA (vite-plugin-pwa) | Mica | Mediu | Feature nou |
| **P2 — VALOROS** | T4 | Contrast audit | Mica | Mediu | Accesibilitate |
| **P2 — VALOROS** | T6 | PDF lang attribute | Mica | Mica | Compliance |
| **P2 — VALOROS** | T7 | WS polling fallback | Mica | Mediu | Rezilienta |
| **P3 — STRATEGIC** | N8 | Event Triage Agent | Mare | Mare | AI Feature |
| **P3 — STRATEGIC** | N9 | i18n rapoarte EN | Medie | Mediu | Feature nou |
| **P3 — STRATEGIC** | N10 | Webhooks | Medie | Mediu | Integrare |
| **P3 — STRATEGIC** | T2 | React 19.2 Activity | Medie | Mediu | Performanta |
| **P3 — STRATEGIC** | T3 | FTS5 index | Medie | Mare | Performanta |
| **P4 — NICE-TO-HAVE** | T5 | Optimistic UI | Medie | Mediu | UX |

**Total recomandari R2: 27** (10 fix-uri R1 + 10 functii noi + 7 tehnice)

---

## NOTE IMPLEMENTARE

1. **Prioritate absoluta:** Items 1, 2, 8 si N1 — fara acesti fix-uri, 3 features majore din R1 sunt nefunctionale (notifications, circuit breaker, retry).

2. **Backend-uri existente, frontend-uri lipsa:** N1-N5 au backend-ul complet dar lipseste UI-ul. Sunt cele mai rapide de implementat — doar frontend.

3. **Dependinte:** N1 (Notification Bell) depinde de #1 (notifications create). T1 (teste) ar trebui facut dupa toate fix-urile P0/P1.

4. **Ce NU se schimba:** Stack, tema, limba, structura agentilor, scoring formula (doar fix edge cases).

5. **Surse web research R2:** MCP patterns (Anthropic), pKYC trends (Fintech Global), React 19.2 (react.dev), SQLite FTS5 (sqlite.org), PWA (vite-pwa), piata BI Romania (Romania Insider), ANAF digitalizare (portalpersoanefizice.ro) — toate [CERT].
