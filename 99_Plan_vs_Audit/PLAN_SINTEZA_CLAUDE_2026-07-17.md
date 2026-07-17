# PLAN — Claude Opus scrie raportul final + toate uneltele functionale + harta pasilor

Data: 2026-07-17 · Autor: sesiune Opus · Status: **IMPLEMENTAT + VERIFICAT LIVE 2026-07-18**

## REZULTAT (verificat live)

Job TAROM `328981d8` (CUI 477647, FULL_COMPANY_PROFILE nivel 3, `--effort max`): **4/4 sectiuni quality
scrise de Claude Opus** (`provider=claude`, fara fallback) — executive_summary 264s, financial_analysis
269s, risk_assessment 324s, recommendations 250s. Toate 8 formatele generate (vs `none` inainte). Risc
Verde, completeness 94%, total 1170s (~19.5 min). Continut persistat + substantial (specific TAROM).
Uneltele: **17/20 verzi** prin ping live (3 moarte extern: BPI/AEGRM DNS, INS TEMPO offline). Bonus:
reparat butonul de test Tavily (importa clasa inexistenta `TavilyClient` -> raporta FAIL desi merge).
832 pytest. Alegere effort NElansata de Roland (a dat constrangeri, nu optiune) -> ales `max`
(interpretare "exhaustive" + "stau la laptop"), configurabil oricand din `.env`.

**Deferat (documentat, pas urmator):** progres WS per-sectiune (PWA pare blocat pe sinteze lungi de
~17 min — `current_step` nu se actualizeaza per-sectiune). Nu blocheaza; harta/log-ul arata progresul real.

## Cererea

1. Toate uneltele/conexiunile din pipeline-ul de analiza — functionale.
2. **Claude Code Opus (Max) sa scrie efectiv raportul final** (nu fallback tacut).
3. La final: raport + ghid complet (cum deschid, de unde) + **harta pasilor exacti per provider**.

## Diagnostic confirmat cu DOVADA (nu presupunere)

### Cauzele 1-4 (din 2026-07-17 `32f725d`) — REPARATE, verificat live acum:

- Serviciul `RIS-Backend` ruleaza ca **`.\ALIENWARE`** (nu LocalSystem) → `sc qc` confirmat.
- `CLAUDE_CLI_PATH` = cale absoluta in `.env`; `claude` CLI v2.1.212 functional.
- `SYNTHESIS_MODE=claude_code`.
- Garda `conftest.py` impotriva rescrierii `.env`.

### Cauza #5 (nereparata) — RADACINA reala, mai grava decat se credea:

**Claude Opus NU scrie NIMIC azi.** Dovada — job TAROM real `job_bdad3555` (646s):

```
SYNTHESIS | executive_summary  | provider=cerebras (FALLBACK) | 754w | 183542ms
SYNTHESIS | financial_analysis | provider=groq (FALLBACK)     | 257w | 181743ms
SYNTHESIS | risk_assessment    | provider=cerebras (FALLBACK) | 465w | 183474ms
AGENT_SYNTHESIS | END | 0 sections | 600.0s
Report formats: none
```

Doua bug-uri suprapuse:

1. **Timeout per-secientiune 180s < durata reala Claude.** Masurat live (MEGA IMAGE, prompt
   productie 46.113 char): `--effort max` = **252.0s** (1128 cuvinte, rc=0). Deci Claude
   depaseste MEREU 180s → fallback tacut pe groq/cerebras. `agent_synthesis...` per-call
   `subprocess.run(timeout=180)` + `asyncio.wait_for(timeout=200)`.
2. **Timeout global 600s ARUNCA secientiunile deja scrise.** `base.py::run()` inveleste
   `execute()` in `asyncio.wait_for(timeout=600)`; la `TimeoutError` returneaza DOAR
   `{"errors":[...]}` — dict-ul local `report_sections` (cu 4-6 sectiuni gata) e pierdut →
   0 sectiuni → niciun format. `run()` NU are retry (ruleaza o data).

Lant cauzal complet: 180s taie Claude → toate quality pe fallback → cele 4 quality × ~180s +
recommendations împing peste 600s → `wait_for` anuleaza `execute()` → 0 sectiuni → `Formats: none`.

## Fixul (3 parti — NUCLEU obligatoriu, indiferent de decizie)

1. **Pastreaza munca partiala.** Muta gestiunea deadline-ului IN `execute()`: buget intern;
   dupa fiecare sectiune, daca s-a depasit bugetul, umple sectiunile ramase determinist
   (fara AI, `_degraded_fallback`) si returneaza ce exista. `execute()` returneaza MEREU un
   `report_sections` complet → outer `wait_for` nu mai anuleaza nimic. O sectiune lenta nu mai
   poate zero-iza raportul NICIODATA.
2. **Timeout per-secientiune real pt Claude.** 180s → ~330s (252 masurat + marja variabilitate
   - sectiuni mai lungi). Configurabil in `.env` (`SYNTHESIS_CLAUDE_TIMEOUT`). `asyncio.wait_for`
     outer > subprocess timeout.
3. **Aliniaza timeout-ul global.** `total_timeout` (agent) = buget intern + marja 1 sectiune,
   ca plasa de ultima instanta care practic nu se mai declanseaza.

Plus: `CLAUDE_EFFORT` configurabil in `.env`; **progres WS per-secientiune** (azi WS e per-agent →
PWA pare blocat 15+ min).

## DECIZIA TA (tradeoff calitate/timp/cota Max) — cu numere reale

| Optiune                                        | Claude scrie       | Timp/job               | Cota Max      | Risc                                                        |
| ---------------------------------------------- | ------------------ | ---------------------- | ------------- | ----------------------------------------------------------- |
| A. `--effort max` + secvential                 | 4 sectiuni quality | ~15-18 min (252s/sect) | maxim         | zero (cel mai sigur)                                        |
| B. `--effort high` + secvential (RECOMANDAT)   | 4 sectiuni quality | ~10-11 min (143s/sect) | mediu         | zero                                                        |
| C. concurent (quality in paralel)              | 4 sectiuni quality | ~6-7 min               | maxim (burst) | throttling Max → fallback tacut (detectat de log_synthesis) |
| D. hibrid (Claude doar exec+risk, restul Groq) | 2 sectiuni cheie   | ~8-9 min               | redus         | zero                                                        |

## Uneltele/conexiunile (asa fac "functionale")

Live-ping toate 15+ sursele via `POST /api/settings/test/{service}` (ruleaza IN serviciu, nu shell).
Raportez verde/mort. **Mort extern, NEreparabil prin cod** (confirmat repetat): BPI/buletinul.ro
(DNS), AEGRM (DNS), INS TEMPO (offline). "Functional" = cablat corect + verde unde sursa traieste.

## Harta pasilor per provider

Exista deja structural in `logs/job_{id}.log`: `SOURCE | <sursa> | OK/FAIL | <ms> | fields=[...]`

- `SYNTHESIS | <sectiune> | provider=<X> (FALLBACK) | <words> | <ms>`. Livrez randare lizibila
  (vizualizare) dintr-un job real + ghid ce inseamna fiecare linie.

## Verificare (acceptanta — NU "job DONE")

Job LIVE pe **CUI 477647 (TAROM)** — declansatorul caii "pierdere". Acceptanta:
`provider=claude` (NU FALLBACK) pe sectiunile quality in log-ul SYNTHESIS + toate 8 formatele scrise.
"DONE + formate" NU dovedeste ca a scris Claude — se verifica PROVIDER-ul.

## Risc (R-RISK)

- Editare cale centrala sinteza = **HIGH** (scenariu "reinvie cale moarta").
- Restart serviciu `RIS-Backend` = **HIGH** (config globala) → cerut confirmare.
- Mitigare: golden pe forma de retur inainte, job live dupa, verificare provider.
