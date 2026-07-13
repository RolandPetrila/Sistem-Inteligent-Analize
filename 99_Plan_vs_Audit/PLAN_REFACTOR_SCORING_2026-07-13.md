# PLAN — Refactor `calculate_risk_score` (CRITICA #4, audit 2026-07-13)

> Status: **PROPUS — asteapta confirmare user inainte de orice cod.**
> Fisier: `backend/agents/verification/scoring.py:160-967`
> Nu incepe implementarea pana randul "CONFIRMAT" e bifat mai jos.

---

## 0. Context si constrangeri (confirmate cu userul)

- E motorul central de scoring 0-100 al RIS (6 dimensiuni ponderate). Toate cele
  9 tipuri de analiza + toate cele 8 formate de raport depind de output-ul lui.
- E **exact clasa de bug** care a produs `UnboundLocalError('litigation')` reparat
  cu 2 zile in urma (variabila asignata doar intr-o ramura, folosita neconditionat
  mai jos — bug latent 100% pana cand sursa externa mereu-picata a inceput sa mearga).
- Userul a cerut explicit: **NU implementare inainte de /plan**. Abordarea de start
  ("extragere per dimensiune") trebuie **validata**, nu asumata.
- Nu atinge: venv dedicat (M25), side-effect gradio/starlette — taskuri separate, deferred.
- Criteriu succes: 443 pytest PASSED + job real DONE pe serviciul live (pattern deja
  folosit la CRITICA #1-#3 din aceeasi sesiune).

---

## 1. Ce am gasit citind codul (nu presupuneri)

### 1.1 Complexitatea — verificata INDEPENDENT (nu doar preluata din audit)

```
ruff check scoring.py --select C901 --config "lint.mccabe.max-complexity=1"
```

```
calculate_risk_score           167  <- CONFIRMAT identic cu auditul
_calculate_financial_ratios     10
apply_dynamic_thresholds         4
_fv / _fval / _dim_conf_for_warning   3 fiecare
```

Proiectul **nu** are `C901`/mccabe activat in `pyproject.toml` (`select = ["E","F","W","I","N","UP","B"]`)
— complexitatea nu e verificata automat la fiecare commit, doar cand cineva ruleaza manual.

### 1.2 De ce "6 functii independente, cate una per dimensiune" NU e suficient

Codul are dependente REALE intre dimensiuni, nu doar in aparenta:

| Variabila calculata in blocul...                               | Refolosita mai jos in...                                         | Linii         |
| -------------------------------------------------------------- | ---------------------------------------------------------------- | ------------- |
| `ca_val`, `profit_val`, `cap_val`, `trend_val` (FINANCIAR)     | blocul OPERATIONAL (age-adjusted scoring, 0-angajati+CA suspect) | 613, 640, 649 |
| `ca_val`, `profit_val`, `cap_val`, `trend_val`, `angajati_val` | bucla de **confidence** (peste toate cele 6 dimensiuni)          | 774-811       |
| `insolvency`, `litigation` (JURIDIC)                           | confidence["juridic"]                                            | 780-782       |
| `anaf_inactive` (FISCAL)                                       | confidence["fiscal"]                                             | 784           |
| `angajati_val`, `company_age_years` (OPERATIONAL)              | confidence["operational"]                                        | 786           |
| `web` (REPUTATIONAL)                                           | confidence["reputational"]                                       | 788           |
| `market` (PIATA)                                               | confidence["piata"]                                              | 790           |
| `ca_val`, `angajati_val`, `company`                            | zombie detection (dupa toate dimensiunile)                       | 830-844       |
| `ca_val`, `profit_val`, `cap_val`, `angajati_val`              | anomalies (dupa zombie)                                          | 846-855       |
| `ca_val`, `confidence`, anomalies                              | early_warning_confidence (dupa anomalies)                        | 857-936       |

**Concluzie:** o extragere naiva "1 functie = 1 dimensiune, fara parametri in plus"
ar recrea EXACT tiparul de bug `litigation` — variabile calculate intr-o functie,
folosite implicit in alta. Extragerea trebuie sa faca dependentele **explicite**
(parametri de intrare / valori de retur), nu sa le ascunda intr-un closure comun.

### 1.3 Contractul de retur — NU se poate schimba fara sa rupem 6 consumatori

`dimensions{financiar/juridic/fiscal/operational/reputational/piata: {score, weight,
reasons, confidence, raw_score, insufficient_data, data_available}}`, `score`,
`numeric_score`, `factors`, `factor_count`, `recommendation`, `company_age_years`,
`anomalies`, `confidence`, `sector_position`, `solvency_matrix`,
`early_warning_confidence`, `financial_ratios` — citite direct de:
`html_generator.py`, `excel_generator.py`, `pdf_generator.py`, `pptx_generator.py`,
`one_pager_generator.py`, `generator.py`, `compare.py`, toate cele 27 teste din
`test_scoring.py`. **Shape-ul dict-ului de retur ramane 100% identic.**

### 1.4 Descoperire critica pentru strategia de verificare: acoperire teste = 39%

```
pytest tests/test_scoring.py --cov=backend.agents.verification.scoring --cov-report=term-missing
-> 620 statements, 378 missing, 39% coverage, 27 passed
```

Ramuri **neatinse de niciun test**: trend decomposition multi-an (227-362), solvency
stress matrix (399-443), cash-flow proxy (447-455), fallback litigation Tavily
(520-534), dosare_just Portal Just (489-512), AEGRM (539-542), Monitorul Oficial
(547-555), age-adjusted scoring (623-654), angajati trend (658-665), reputational
nuantat (676-711), piata/benchmark/sector position (720-769), zombie detection
(834-844), anomalies (849-855), early warning confidence (876-916).

**Asta inseamna ca "443 pytest raman verzi" NU e suficienta dovada de corectitudine**
pentru un refactor al acestei functii — 61% din logica nu e verificata de niciun test,
deci un refactor care sparge una din ramurile astea trece testele oricum. Regula
globala R2 ("nu declara functional daca ai testat doar nivel MINIM") se aplica direct.

**Mitigare obligatorie (indiferent de optiunea aleasa mai jos): pasul 2 (golden
snapshot) inainte de orice extragere de cod.**

---

## 2. Pasul 0 (OBLIGATORIU, indiferent de optiune) — Golden Snapshot / Characterization Test

Inainte de a muta orice linie de cod:

1. Aduna 5-6 fixture-uri `verified` REALE (nu inventate) acoperind:
   - firma sanatoasa completa (CUI 49104500 sau 26313362 — deja analizate azi, date live)
   - firma cu date sparse/partiale (CUI 43978110 — completeness mixt, unele surse FAIL)
   - `verified={}` complet gol (deja acoperit de `test_empty_verified_data`)
   - caz "everything triggers" ADVERSARIAL (nou, NU exista azi): insolventa GASITA +
     BPI GASIT + dosare_just>10 + AEGRM + Monitorul Oficial + ANAF inactiv + split TVA +
     zombie (CA=0+angajati=0+activ) — combinatie care azi nu e testata deloc si exercita
     cele mai multe ramuri simultan
   - caz volatilitate/trend multi-an (exercita trend decomposition + sector volatility)
2. Ruleaza `calculate_risk_score()` ACTUAL (neatins) pe fiecare fixture, salveaza
   output-ul complet ca JSON in `tests/fixtures/scoring_golden/*.json`.
3. Scrie UN test nou `test_scoring_golden_snapshot.py`: pentru fiecare fixture,
   `assert calculate_risk_score(fixture) == golden_json` (deep dict equality).
4. Verifica ca acest test e verde PE CODUL ACTUAL (inainte de orice modificare) —
   confirma ca golden-urile sunt corecte, nu doar "ce a iesit din bug-uri".

Acest pas transforma verificarea din "27 teste + citire manuala" in "diff exact
byte-cu-byte pe intreg contractul de output, pe cazuri care azi n-au NICIO acoperire".
E pasul care face restul planului sigur de executat.

---

## 3. Optiuni de abordare (dupa Pasul 0)

### Optiunea A — Extragere per dimensiune cu contract explicit de "facts" (RECOMANDAT)

Fiecare dimensiune devine o functie separata **in acelasi fisier** (nu fisier nou —
807 linii reorganizate in ~8 functii tot in `scoring.py`, fara sa multiplicam module):

```python
def _score_financiar(financial, company, thresholds) -> tuple[dict, FinancialFacts]: ...
def _score_juridic(risk_data) -> tuple[dict, JuridicFacts]: ...
def _score_fiscal(financial, risk_data) -> tuple[dict, FiscalFacts]: ...
def _score_operational(financial, company, fin_facts: FinancialFacts) -> tuple[dict, OperationalFacts]: ...
def _score_reputational(verified) -> tuple[dict, ReputationalFacts]: ...
def _score_piata(verified) -> tuple[dict, PiataFacts]: ...

def _compute_confidence(dimensions, facts: AllFacts) -> dict: ...
def _detect_zombie_and_anomalies(facts: AllFacts, dimensions, company) -> tuple[bool, list]: ...
def _build_early_warnings(anomalies, risk_factors, facts: AllFacts, confidence) -> list: ...

def calculate_risk_score(verified, dynamic_thresholds=None) -> dict:
    # orchestrator ~100-150 linii: apeleaza functiile de mai sus in ordine,
    # asambleaza dict-ul de retur IDENTIC cu azi
```

`*Facts` = `@dataclass` mici (sau `TypedDict`) cu campuri explicite (`ca_val: float | None`,
etc.) — **nu** dict-uri libere. `_score_operational` primeste `fin_facts` ca parametru
explicit (dependenta reala financiar→operational, nu ascunsa). `calculate_risk_score`
ramane orchestratorul, dar devine ~100-150 linii in loc de 807.

**Pro:**

- Rezolva RADACINA clasei de bug `litigation`: o functie care are nevoie de o valoare
  calculata in alta parte trebuie sa o primeasca EXPLICIT ca parametru sau sa o citeasca
  dintr-un `Facts` returnat — Python arunca `TypeError`/`AttributeError` IMEDIAT la
  apel daca lipseste, nu un `UnboundLocalError` ingropat la 400 de linii distanta.
- Complexitatea (167) se distribuie pe ~9 functii mici — fiecare独 verificabila si
  recenzabila separat, fara sa citesti 807 linii dintr-o suflare.
- `dataclass` cu type hints documenteaza explicit ce e opțional (`| None`) — utile
  chiar fara mypy in proiect (Python insusi verifica la call-time).

**Contra:**

- Diff mare (tot fisierul se reorganizeaza) — efort de review mai mare intr-o singura trecere.
- Trebuie enumerate TOATE dependentele cross-dimensiune existente azi (le-am mapat
  in tabelul 1.2 — risc daca ratez una: prins imediat de golden snapshot, nu silentios).

**LIMITE:** functioneaza doar daca Pasul 0 (golden snapshot) e facut INTAI — fara el,
un diff de aceasta marime pe cod cu 39% acoperire e nesigur de validat.

### Optiunea B — Restructurare in-place, minimal-diff (NU RECOMANDAT pentru CRITICA #4)

Pastreaza O SINGURA functie `calculate_risk_score`, dar in loc de variabile libere
foloseste un dict `shared = {}` populat progresiv, citit explicit (`shared["ca_val"]`)
in loc de nume libere (`ca_val`). Diff mic, risc mic pe termen scurt.

**Pro:** cel mai mic diff, cel mai mic risc imediat de regresie.

**Contra (motivul respingerii):** ramane O SINGURA functie → `ruff --select C901`
raporteaza in continuare complexitate ~167 (poate putin mai mica, dar tot in zeci)
— **nu rezolva metrica din audit care a generat acest CRITICA**. Acceseaza chei de
dict prin string (`shared["ca_val"]`) — un typo (`shared["ca_vall"]`) da `KeyError`
la fel de ingropat ca azi, fara avantajul semnaturilor explicite de functie.

**[NU RECOMANDAT]** — rezolva simptomul (lizibilitate marginal mai buna) dar nu cauza
(o singura functie responsabila de tot ramane un magnet pentru viitoare bug-uri de tip
`litigation`).

### Optiunea C — Clasa `RiskScorer` cu metode + atribute de instanta (respinsa, nu detaliata ca optiune principala)

Aceeasi extragere ca A, dar cu `self.ca_val` etc. in loc de parametri/retur explicit.
**Respinsa**: atributele de instanta sunt la fel de "implicite" ca variabilele libere
de azi — o metoda poate presupune ca alta metoda a rulat deja si a populat `self.x`,
acelasi tipar de bug, doar mutat de la "closure de functie" la "stare de obiect".
Optiunea A (parametri/retur explicit) e strict mai sigura.

---

## 4. Validare pe 3 niveluri (R2, obligatoriu inainte de a declara "functional")

| Nivel                  | Scenariu                                                                                             | Optiunea A                                                                                | Optiunea B                                                        |
| ---------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **MINIM** (demo)       | firma sanatoasa, toate sursele OK                                                                    | OK — scor identic (golden snapshot)                                                       | OK                                                                |
| **TIPIC** (zi de zi)   | date sparse, unele surse FAIL (cazul REAL cel mai comun, vezi `project_ris_e2e_sweep_2026-07-12`)    | OK, cu conditia Pasul 0 sa includa fixture sparse (CUI 43978110)                          | OK, dar nu rezolva complexitatea — [NU RECOMANDAT] ramane valabil |
| **MAXIM** (worst case) | "everything triggers" adversarial (insolventa+BPI+AEGRM+MO+zombie simultan) — NU exista azi in teste | Necesita fixture nou (Pasul 0) — fara el, NICIUNA din optiuni e verificata la acest nivel | idem                                                              |

---

## 5. Task breakdown (ordine de executie, DUPA confirmare)

1. **Pasul 0** — golden snapshot (sectiunea 2): 5-6 fixture-uri reale + test nou +
   verde pe codul ACTUAL neatins. _(fara asta, nu trecem la pasul 2)_
2. Extrage `_score_juridic`, `_score_fiscal`, `_score_reputational`, `_score_piata`
   (cuplare mica/zero intre ele) — dimensiunile cu risc mai mic intai, ca sa validam
   patternul inainte de a atinge financiar/operational (cuplate real).
   → ruleaza golden snapshot dupa fiecare, nu doar la final.
3. Extrage `_score_financiar` (cel mai mare bloc, ~270 linii) — expune `FinancialFacts`.
4. Extrage `_score_operational`, primind `FinancialFacts` ca parametru explicit.
5. Extrage `_compute_confidence`, `_detect_zombie_and_anomalies`, `_build_early_warnings`.
6. `calculate_risk_score` ramane orchestratorul — verifica ca return dict e byte-identic
   (golden snapshot + cele 27 teste existente + `pip check`-echivalent pt import-uri).
7. Ruleaza `ruff --select C901` din nou — confirma ca fiecare functie noua e sub un
   prag rezonabil (propunere: <20; de negociat, nu impus).
8. 443 pytest PASSED + job real DONE (acelasi pattern ca CRITICA #1-#3: creeaza job
   `FULL_COMPANY_PROFILE` pe un CUI real, poll pana DONE, verifica raportul generat
   contine toate campurile — dimensions/solvency_matrix/early_warning_confidence etc. —
   nemodificate fata de inainte).
9. (Optional, propunere separata — nu parte din scope-ul CRITICA #4): adauga
   `[tool.ruff.lint.mccabe] max-complexity = N` in `pyproject.toml` + `C901` in
   `select`, ca sa previi reaparitia unei functii-monstru pe viitor. De discutat
   separat dupa ce refactorul e gata — nu il bag acum ca sa nu extind scope-ul.

---

## 6. Riscuri si mitigare

| Risc                                               | Mitigare                                                                                                |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Acoperire teste 39% → regresie silentioasa         | Golden snapshot (Pasul 0) — obligatoriu, non-negociabil                                                 |
| Dependenta cross-dimensiune omisa la extragere     | Mapata explicit in tabelul 1.2; orice omisiune → `TypeError` imediat la apel (fail-fast), nu bug latent |
| Diff mare, greu de revizuit intr-o singura trecere | Executie in etape (sectiunea 5), golden snapshot rulat dupa fiecare etapa, nu doar la final             |
| Shape-ul dict-ului de retur se schimba accidental  | Golden snapshot = `assert ... == golden_json` (egalitate stricta pe tot dict-ul)                        |
| Regresie in productie nedetectata de pytest        | Job real DONE pe serviciul live dupa refactor (pattern deja folosit la #1-#3)                           |

---

## 7. Criteriu de succes final

- [ ] Pasul 0 (golden snapshot) verde PE CODUL NEATINS
- [ ] Toate functiile extrase, `calculate_risk_score` orchestrator ~100-150 linii
- [ ] Golden snapshot INCA verde dupa refactor (dict identic, nu doar "teste trec")
- [ ] 443 (+golden snapshot nou) pytest PASSED
- [ ] Job real `FULL_COMPANY_PROFILE` DONE pe serviciul live, raport verificat cu
      toate campurile scoring prezente si neschimbate
- [ ] `ruff --select C901` — nicio functie noua peste un prag rezonabil (de confirmat)

---

## Jurnal executie

_(se completeaza pe masura ce se executa, dupa confirmare)_

- 2026-07-13: Plan scris, in asteptare confirmare user. Niciun cod atins inca.
