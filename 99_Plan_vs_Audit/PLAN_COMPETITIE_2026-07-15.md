# Plan — Sursa de date pentru analiza competitorilor (COMPETITION_ANALYSIS / MARKET_ENTRY_ANALYSIS)

> Document de RESEARCH, scris la cererea Opus 4.8 (Runda 2 / E, `Roland_Opus_Sonnet.md`).
> **ZERO cod implementat. ZERO commit in `backend/`.** Decizia de produs e a lui Roland.
> Verificat la sursa (cod real + memorie `project_ris_free_sources_decisions`), nu presupus.

---

## 1. Ce inseamna concret "competitor" pentru RIS AZI (verificat in cod, nu presupus)

### 1.1 Ce primesc sectiunile ca input de la utilizator

`ANALYSIS_TYPES_META` (`backend/models.py:66-146`) — ambele tipuri au campuri de formular
care **promit** o analiza de competitie ghidata:

| Camp                 | COMPETITION_ANALYSIS                                                          | MARKET_ENTRY_ANALYSIS                               |
| -------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------- |
| Identificare firma   | `cui` — "Firma client SAU domeniul de activitate" (text liber)                | `company` — "Descrierea afacerii (CUI daca exista)" |
| Zona                 | `area` — select Judet/Regiune/National                                        | `area` — select Judet/Regiune/National              |
| Definitie competitor | `scope` — select "Acelasi CAEN exact" / "CAEN similar" / "Intreaga industrie" | —                                                   |
| Focus                | `focus` — select Preturi/Servicii/Dimensiune/Prezenta online                  | `advantage` — select Pret/Calitate/Nisa/Inovatie    |
| Firme cunoscute      | `known_competitors` — text liber, optional                                    | —                                                   |

**Gasit prin grep exhaustiv (`known_competitors`, `scope`, cheile `input_params.get("scope"/"area")`):
NICIUNUL din aceste 5 campuri nu e citit NICAIERI in backend.** Ele exista doar in schema
formularului din wizard — utilizatorul le completeaza, dar valorile se pierd, nu ajung
niciodata in `input_params` folosit de agenti. Promisiune UI fara livrare in cod.

### 1.2 Ce se intampla azi cand rulezi efectiv sectiunea "competition"

Traseul complet, verificat linie cu linie:

1. **Prompt-ul** (`backend/prompts/section_prompts.py:90-108`) cere explicit modelului sa
   "prezinte competitorii identificati in format tabel" (nume, CUI, CAEN, zona, dimensiune),
   cu un exemplu concret in text — dar **nu exista niciun camp `verified_data["competitors"]`
   care sa alimenteze acest tabel cu date reale.**
2. **Gate-ul de generare** (`_has_sufficient_data`, `agent_synthesis.py:735-741`) verifica
   `verified_data["web_presence"]["competitors"]["results"]` — cere cel putin 1 rezultat.
3. **Nicaieri in pipeline nu se seteaza vreodata aceasta cheie.** Grep exhaustiv pe
   `backend/agents/*.py` + `backend/agents/tools/*.py` pentru `"competitors"`: apare DOAR in
   `agent_synthesis.py` (gate-ul de la #2, plus un guard anti-halucinare la #4) — niciun
   `agent_official.py`, `agent_verification.py`, sau nodurile Agent 2 (`web`)/Agent 3 (`market`)
   din `orchestrator.py:264-396` nu scriu vreodata aceasta cheie. Agent 2 populeaza DOAR
   `online_presence`/`reviews`/`news` (Tavily), Agent 3 DOAR `market_data["seap"]`.
4. **Consecinta directa, verificata (nu dedusa):** `_has_sufficient_data("competition", ...)`
   returneaza `False` **de fiecare data, pe orice firma, in orice job** — sectiunea "competition"
   **NU ajunge NICIODATA la un provider AI**. Cade mereu pe fallback-ul generic de la
   `generate_section` (`agent_synthesis.py:96-107`): _"Sectiunea 'Analiza Competitie' nu a putut
   fi generata din cauza datelor insuficiente..."_. Confirmat empiric: pe ambele joburi MEGA
   IMAGE rulate in aceasta sesiune (Runda 1 si Runda 2/C), `report_sections["competition"]`
   are `word_count: 0` de ambele dati.
5. **Exista un guard anti-halucinare deja scris** (AH-04, `agent_synthesis.py:548-565`) care
   ar verifica numele de firme mentionate in text contra `web_presence.competitors.results` —
   dar niciodata nu ruleaza cu continut real, pentru ca sectiunea nu ajunge niciodata sa
   genereze text (#4).

**Concluzie sectiune 1:** situatia nu e "promptul face LLM-ul sa halucineze" (ipoteza initiala
rezonabila, dar falsa la verificare) — e "infrastructura de gating + anti-halucinare e deja
construita si CORECTA, dar asteapta o cheie care nu vine niciodata". Asta schimba radical
efortul de implementare: **nu trebuie rescris promptul sau gate-ul, trebuie DOAR populata
`verified_data["web_presence"]["competitors"]["results"]` cu date reale, in forma pe care
codul deja o asteapta.**

---

## 2. Optiuni de sursa — verificate la sursa (cost, limita legala, acoperire, efort)

**Regula aplicata:** FREE + utilizabil comercial + legal. Verdictele de mai jos pentru
Termene/OpenCorporates/OpenSanctions/RBR sunt preluate din memoria
`project_ris_free_sources_decisions` (cercetate la sursa pe 2026-07-11) — **NU re-cercetate**,
per instructiune explicita.

### (a) Tabela proprie `companies` filtrata pe CAEN+judet

- **Cost:** 0 (date deja in DB).
- **Acoperire:** DOAR firmele deja analizate manual de RIS pe aceasta masina — la data scrierii,
  **8 firme** in `companies` (verificat: `SELECT COUNT(*) FROM companies`). Practic inutilizabil
  ca sursa de descoperire — orice cautare CAEN+judet pe un sector nou returneaza aproape sigur 0
  rezultate.
- **Legal:** date proprii, fara restrictie.
- **Efort:** ZERO — pattern-ul exista deja complet functional, `backend/agents/tools/lead_search.py`
  (scris pt LEAD_GENERATION, dar generic: filtrare SQL determinista pe `county`+`caen_description`,
  fara niciun apel AI pt extragerea faptelor).
- **Verdict:** [NU RECOMANDAT ca sursa unica] — acoperire prea mica ca sa fie utila singura, dar
  **codul e reutilizabil 1:1** ca template pt (b).

### (b) Dataset bulk ONRC (data.gov.ro) — `onrc_companies`

- **Cost:** 0, licenta CC BY 4.0 (verificat in memorie, sursa primara data.gov.ro).
- **Acoperire:** **TOATE** firmele active din Romania (~660MB CSV activ + ~392MB radiate, per
  documentatia `tools/import_onrc.py`) — CUI, denumire, CAEN, judet, localitate, data
  inregistrare, forma juridica, cod postal. **NU contine** asociati/administratori/UBO (deja
  documentat in memorie) si **NU contine** date financiare (CA, angajati) — doar identificare +
  clasificare.
- **Legal:** OK, licenta permisiva, fara restrictie comerciala.
- **Efort — REEVALUAT explicit, cum a cerut Opus:**
  - Scriptul de import **exista deja, complet, netestat cu date reale** (`tools/import_onrc.py`
    — detecteaza automat coloanele CSV, creeaza tabela + 3 indexuri, inclusiv **index pe `caen`
    SI pe `judet`** deja pregatite exact pentru genul de query pe care l-ar face o cautare de
    competitori). Migratia SQL (`009_onrc_local.sql`) e deja aplicata — tabela `onrc_companies`
    exista in schema, dar **0 randuri** (confirmat live, `SELECT COUNT(*) FROM onrc_companies`).
  - Motivul deferrarii anterioare (conform memoriei, "volum mic" la momentul respectiv) **nu mai
    e valabil ca argument de blocare** — infrastructura de import e deja scrisa, testata partial
    (autodetectie coloane), doar niciodata rulata cu fisierele CSV reale descarcate manual de pe
    data.gov.ro (proces manual, slug-ul URL se schimba lunar — motiv pt care importul nu e
    automatizat integral).
  - Adaptarea `lead_search.py` -> cautare competitori: schimbare de o linie (`FROM companies` ->
    `FROM onrc_companies`) + maparea `scope` (vezi 2.3 mai jos) pe prefix CAEN, **zero cod nou de
    infrastructura**.
- **Verdict:** **[RECOMANDAT]** — singura optiune care acopera intreaga piata, cu infrastructura
  deja construita.

### (c) openapi.ro

- **Cost:** deja folosit in RIS (100 req/luna gratuit, per CLAUDE.md).
- **Acoperire:** confirmat in cod (`backend/agents/tools/openapi_client.py:12,15`) — **DOAR
  lookup pe un singur CUI cunoscut** (`GET /api/companies/{cui}`). **Fara endpoint de cautare
  bulk dupa CAEN/judet.**
- **Legal:** OK (deja folosit comercial in RIS).
- **Efort:** irelevant — nu rezolva problema de DESCOPERIRE (nu poti gasi competitori
  necunoscuti prin CUI-lookup), doar de IMBOGATIRE a unor candidati deja identificati altfel.
- **Verdict:** [RELEVANT, dar NU ca sursa primara] — util DOAR pt a imbogati (asociati,
  administratori) un candidat deja gasit prin (b), si doar pt un numar mic (quota lunara mica,
  deja consumata de fluxul normal RIS).

### (d) Eurostat / INS TEMPO (deja integrate in RIS)

- **Cost:** 0, keyless (confirmat in memorie + `eurostat_client.py`/`caen_context.py` existente).
- **Acoperire:** **agregat pe sector** (nr. firme, angajati/firma, CA medie) — **NU nume de
  firme individuale**. Nu poate produce un tabel "Nume | CUI | CAEN" cerut de prompt.
- **Legal:** OK.
- **Efort:** deja integrat, zero efort suplimentar.
- **Verdict:** [RELEVANT ca supliment] — util pt a contextualiza ("in acest sector sunt in
  medie N firme cu M angajati"), NU pt identificarea competitorilor concreti. Deja folosit in
  `verified["eurostat_sector"]` — de reutilizat ca atare in narativa, nu de re-cercetat.

### (e) Alte optiuni verificate/excluse (din memorie, nu re-cercetate)

- **Termene.ro** — [NU RECOMANDAT] 1200 interogari/AN gratuit, insuficient pt cautari repetate
  de competitori la scara productiei.
- **OpenCorporates** — [NU RECOMANDAT] cheie + comercial de la £2.250/an.
- **OpenSanctions** — irelevant aici (sanctiuni, nu discovery de competitori); deja acoperit
  separat de `sanctions_client.py`.
- **D&B / IBISWorld / Creditsafe** — [OVERKILL] enterprise/abonament, disproportionat fata de
  nevoie.

---

## 3. Recomandare

**(Recomandat) Optiunea (b) — dataset ONRC local, cu (a) ca fallback silentios pt firmele deja
in pool-ul RIS si (c) ca imbogatire optionala pt un numar mic de candidati de top.**

**1 motiv concret:** e **singura** optiune free-si-legala care acopera intreaga piata din
Romania (nu doar cele 8 firme deja analizate), si infrastructura de import + indexare **exista
deja scrisa** (`tools/import_onrc.py` + migratia `009_onrc_local.sql`) — costul real de
implementare e "ruleaza importul o data + adapteaza un query SQL deja existent", nu "construieste
de la zero".

Nicio alta optiune nu e "aproape la fel de buna": (a) singura are acoperire de <10 firme, (c) nu
suporta cautare bulk deloc, (d) nu are nume de firme deloc.

---

## 4. Ce NU se poate face cu aceste date (limita onesta)

Chiar cu (b) complet implementat, urmatoarele raman **imposibil de livrat cu date reale, free**:

- **Preturi/tarife competitori** — nicio sursa free identificata (nici in cercetarea originala
  din memorie). Ramane [INDISPONIBIL] permanent pt `focus: "Preturi"`.
- **Descrierea detaliata a serviciilor** — dataset-ul ONRC nu are camp de "obiect de activitate"
  text liber, doar codul CAEN (4 cifre) + descrierea generica de sectiune. `focus: "Servicii"`
  poate primi cel mult descrierea CAEN, nu o comparatie reala de portofoliu.
- **Dimensiune (CA/angajati) pt competitori din afara pool-ului RIS** — dataset-ul ONRC nu are
  date financiare. Singura sursa ar fi ANAF Bilant per-CUI, rate-limitat la 1 request/2 secunde
  (`anaf_bilant_client.py`) — pt 20-30 candidati, asta inseamna 40-60 secunde suplimentare DOAR
  pt aceasta imbogatire, pe un flux deja lung. `focus: "Dimensiune"` ar trebui limitat explicit
  la maxim 5-10 candidati de top, cu avertisment clar in raport ca restul raman [INDISPONIBIL].
- **UBO/beneficiari reali ai competitorilor** — blocat legal (CJEU C-37/20 + Legea 86/2025, deja
  documentat in memorie). Nu exista sursa free pt asta, nici pt firma analizata, nici pt
  competitori.
- **Prezenta online detaliata (recenzii, rating) pt multi competitori** — Tavily/Google Maps au
  quota lunara limitata (1000 Tavily, cost per Google Maps call); scanarea a zeci de candidati
  ar epuiza rapid quota partajata cu restul analizelor RIS. Fezabil DOAR pt un numar mic de
  candidati de top, nu pt tot pool-ul.

---

## 5. Lectia LEAD_GENERATION — obligatorie aici (per instructiune Opus)

Precedent direct, verificat, nu ipotetic: la implementarea LEAD_GENERATION (memorie
`project_ris_lead_generation_deterministic`), lasarea AI-ului sa "identifice" firme candidate
din propria cunostinta a dus la **amestecarea CUI-ului firmei solicitante cu CUI-uri ale
firmelor candidate** — halucinatie confirmata pe **4 reproduceri**, inclusiv cu prompt dovedit
curat (izolare completa context/JSON verificata direct, halucinatia a persistat). 3 incercari pe
calea AI (prompt mai strict, route "quality", izolare context) NU au oprit halucinarea. Fix-ul
real a fost **randare 100% deterministica in Python** (`_render_lead_candidates_content`,
`agent_synthesis.py:991-1036`) — CUI/CAEN/scor vin direct din date, zero apel AI, imposibil de
halucinat.

**Aceeasi regula se aplica identic aici — orice propunere care lasa un LLM sa "identifice
competitori" din memoria proprie a modelului e RESPINSA din start.** Design-ul corect (daca
Roland decide sa implementeze):

1. **Descoperire + identificare (CUI, denumire, CAEN, judet)** — 100% Python determinist, query
   SQL pe `onrc_companies` (dupa `scope`: `caen = ?` exact, `caen LIKE ?` cu prefix 2-3 cifre pt
   "similar", grupare pe sectiune CAEN literala pt "intreaga industrie" — mecanismul de grupare
   `CAEN_SECTIONS` exista deja in `caen_context.py:139`). Daca `known_competitors` e completat,
   rezolva acele nume specifice PRIMUL, prin cautare `denumire LIKE` — potrivire directa, nu
   ghicita.
2. **Rezultatul se scrie in `verified_data["web_presence"]["competitors"]["results"]`** — exact
   forma pe care gate-ul `_has_sufficient_data` si guard-ul anti-halucinare AH-04 deja o asteapta
   (vezi sectiunea 1.2) — zero schimbare la codul de gating existent.
3. **Randarea tabelului (Nume/CUI/CAEN/Judet)** — determinista, dupa acelasi pattern ca
   `_render_lead_candidates_content` — NU generata de LLM.
4. **DOAR narativa de "Pozitionare"** (comparatia calitativa, puncte tari/slabe relative) poate
   ramane generata de LLM — dar STRICT pe baza listei deterministe deja injectate in prompt, cu
   aceeasi regula "[INDISPONIBIL]" pt orice camp fara date (deja in prompt-ul existent,
   `section_prompts.py:96-98`).

---

## Rezumat pt decizie

| #   | Optiune                                | Verdict                                                          |
| --- | -------------------------------------- | ---------------------------------------------------------------- |
| 1   | `companies` proprie (CAEN+judet)       | NU RECOMANDAT singur — acoperire <10 firme, dar cod reutilizabil |
| 2   | **ONRC bulk local (`onrc_companies`)** | **RECOMANDAT** — acoperire completa, infra deja scrisa           |
| 3   | openapi.ro                             | RELEVANT doar ca imbogatire, nu discovery                        |
| 4   | Eurostat/INS                           | RELEVANT ca supliment agregat, nu nume de firme                  |
| 5   | Termene/OpenCorporates/D&B             | NU RECOMANDAT / OVERKILL — platit                                |

**Ce ramane de decis de Roland (NU implementat aici):** (1) merita rulat importul ONRC manual
acum (proces manual, slug URL lunar) — da/nu/cand; (2) cat efort pt maparea exacta `scope`->SQL
si `focus`->prioritizare candidati; (3) daca se accepta limitele din sectiunea 4 ca atare sau se
cere alta abordare pt Preturi/Servicii/Dimensiune.

**STOP — niciun cod nu a fost scris pentru acest plan.**
