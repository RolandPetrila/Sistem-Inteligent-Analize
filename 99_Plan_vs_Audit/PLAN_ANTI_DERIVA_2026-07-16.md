# PLAN ANTI-DERIVĂ — Mecanisme care fac clasa de bug IMPOSIBILĂ

> **Creat:** 2026-07-16 · **Autor:** Opus 4.8 (advisor) · **Aprobat de Roland:** ⬜ NU ÎNCĂ
> **Regulă absolută:** NU se scrie cod până Roland bifează „APROBAT" la §12.
> **Fișier LIVE** — Claude îl actualizează după FIECARE sub-task. Nu e document, e tablou de bord.

---

## 1. DE CE EXISTĂ ACEST PLAN (diagnosticul, în 6 rânduri)

Pe 2026-07-16 s-au reparat 20+ bug-uri. **Toate sunt UN SINGUR bug:**

```
stare_firma vs stare_inregistrare · numar_mediu_salariati vs numar_angajati
anaf_inactive vs inactiv · 'COMPLETED' vs 'DONE' · company_id vs company_cui
gaps: string[] vs object[] · title lipsă din SELECT · country='RO' (enum fără RO)
Number(uuid) vs UUID · maps_rating/key_takeaways/sector_position nerandate
```

**Fiecare = o cheie-string care trece o graniță fără contract.** `.get(cheie, default)` transformă
orice typo în tăcere. Testele nu le prind **prin construcție**: fixture-urile stau de o parte,
producătorii de alta, nu se întâlnesc niciodată. Azi s-au găsit **4 fixture-uri** care codificau
aceeași presupunere greșită ca și codul + **1 golden care înghețase un crash ca adevăr**.

**Scopul planului:** nu „a repara bug-uri" — ci **a face clasa imposibilă**, mecanic.

---

## 2. TABLOU DE BORD LIVE

> Claude actualizează după fiecare sub-task. Roland citește DOAR asta ca să știe unde suntem.

| Fază | Titlu                            | Status       | Progres |
| ---- | -------------------------------- | ------------ | ------- |
| 0    | Fundația de dovadă               | ⬜ NEÎNCEPUT | 0/3     |
| 1    | Detector chei moarte             | ⬜ NEÎNCEPUT | 0/6     |
| 2    | Fixture-uri din producție        | ⬜ NEÎNCEPUT | 0/4     |
| 3    | Ping-uri oneste                  | ⬜ NEÎNCEPUT | 0/4     |
| 4    | Gardă anti-drift mediu           | ⬜ NEÎNCEPUT | 0/3     |
| 5    | Documentație care nu poate minți | ⬜ NEÎNCEPUT | 0/5     |
| 6    | Testare exhaustivă + gate 95%    | ⬜ NEÎNCEPUT | 0/7     |
| 7    | Bug-uri rămase + cod mort        | ⬜ NEÎNCEPUT | 0/8     |

| **8** | **API-uri, credentiale, fallback + AUDIT_FUNCTII** | NEINCEPUT | 0/9 |
| **9** | **Surse & unelte NOI (calitate + acoperire)** | NEINCEPUT | 0/8 |

**Fisiere insotitoare (generate 2026-07-16):**
- `docs/GHID_CREDENTIALE_API.md` — audit credentiale + link direct per serviciu + procedura + fallback
- `99_Plan_vs_Audit/PLAN_SURSE_NOI_2026-07-16.md` — surse noi, fonduri UE, licitatii, dubluri, gate de integrare
**Legendă status:** ⬜ NEÎNCEPUT · 🔄 ÎN LUCRU · ✅ FĂCUT+VERIFICAT · ⚠️ FĂCUT, NEVERIFICABIL LIVE
· ❌ BLOCAT · 🚫 CLAUDE NU POATE (necesită Roland) · ⏭️ SĂRIT (cu motiv)

**Gate curent:** —
**Ultima actualizare:** 2026-07-16 (creare plan)
**Teste:** 814 pytest · ruff 0 · tsc 0 · vitest 43 · **actualizat 2026-07-17**

---

## 3. REGULI DE EXECUȚIE (nenegociabile, se aplică la FIECARE sub-task)

1. **Non-vacuitate obligatorie.** Pentru un FIX: testul nou trebuie să **PICE pe codul vechi**, cu
   output real copiat în jurnal. Pentru un REFACTOR: mutation (strici ceva → golden pică) + golden
   IDENTIC. **Nu confunda cele două criterii.**
2. **NU folosi `git stash`** pentru izolare. E stack **global pe repo** — cu agenți paraleli,
   ferestrele se falsifică reciproc (dovedit 2026-07-16). Metodă sigură:
   `git show HEAD:fisier > backup` → suprascrie → testează → restaurează din backup propriu →
   verifică byte-identic.
3. **Ierarhia dovezilor:** `reports.full_data` (joburi reale) **>** ping live (rulează ÎN serviciu)
   **>** cod/teste. Codul și testele sunt dovadă **SLABĂ**.
4. **Nu scrie „verificat live" pe ce n-ai verificat live.** Marchează ⚠️ și spune de ce.
5. **Fixture-uri numai cu formă reală** din producție. Niciodată inventate.
6. **Job live înainte de push** la orice cale reînviată.
7. **Agenții NU comit.** Opus comite serializat, după verificare la sursă.
8. **În fiecare brief:** „dacă brief-ul contrazice codul real, codul real câștigă."
9. **Nu declara nicio sursă externă „moartă" din shell** — 4 chei diferă de producție
   (`GOOGLE_CLOUD_API_KEY`, `GOOGLE_AI_API_KEY`, `TELEGRAM_CHAT_ID`, `XAI_API_KEY`).
10. **Gate RIS după fiecare fază:** `pytest` verde + `ruff check backend/` = 0 + (`tsc --noEmit` +
    `npm run build` unde atingi frontend) + vitest. **Gate PASS ≠ dovadă de reparare.**

---

## 4. FAZA 0 — Fundația de dovadă

> Fără asta, restul planului n-are pe ce să se sprijine.

| #   | Task                                                                                                                                                                                             | Status | Dovadă cerută                               |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | ------------------------------------------- |
| 0.1 | `tools/dump_production_shape.py` — extrage forma REALĂ (chei + tipuri, recursiv) din `reports.full_data` al ultimelor N joburi DONE                                                              | ⬜     | fișier JSON cu ~25 chei nivel 1 + subarbori |
| 0.2 | Inventar granițe: listă exhaustivă a dict-urilor care trec granițe (`verified_data`, `official_data`, `risk_score`, ieșirea fiecărui client de sursă, `company`, `financial`, `jobs.input_data`) | ⬜     | tabel în §11                                |
| 0.3 | Baseline chei moarte: rulează detectorul (F1) pe codul curent și **catalogează** ce mai e mort azi                                                                                               | ⬜     | listă, cu verdict per cheie                 |

**Gate F0:** forma reală e extrasă din **producție**, nu din fixture. Verifică pe ≥3 firme diferite
(TAROM 477647 = pierdere, MEGA IMAGE 6719278 = bogat, CFL SOLUTION 49104500 = mic).

---

## 5. FAZA 1 — Detector automat de chei moarte ⭐ (cel mai bun raport valoare/efort)

> Ar fi prins azi: `stare_firma`, `numar_angajati` în compare, `anaf_inactive`, `company_id`,
> `maps_rating` nerandat, `gaps` formă greșită. **Adică majoritatea zilei, mecanic.**

| #   | Task                                                                                                                                            | Status | Dovadă cerută                |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---------------------------- |
| 1.1 | `tools/find_dead_keys.py` — parser AST care extrage TOATE accesele `.get("X")`, `["X"]`, `.get("X", default)` pe dict-urile din inventar (§0.2) | ⬜     | listă cheie→fișier:linie     |
| 1.2 | Confruntare mecanică: fiecare cheie citită vs forma reală din §0.1                                                                              | ⬜     | raport FALSE/OK per cheie    |
| 1.3 | `tests/test_no_dead_keys.py` — **PICĂ** dacă o cheie citită nu există în producție                                                              | ⬜     | test verde pe codul curent   |
| 1.4 | **DOVADĂ DE NON-VACUITATE:** reintrodu temporar `stare_firma` → testul TREBUIE să pice                                                          | ⬜     | output real copiat în jurnal |
| 1.5 | Allowlist explicit pentru absențe **legitime** (ex. `aegrm` gol fiindcă sursa e DNS-dead), fiecare cu **motiv scris**                           | ⬜     | fiecare intrare justificată  |
| 1.6 | Extindere frontend: chei citite în `.tsx` vs forma reală a răspunsurilor API                                                                    | ⬜     | test/script echivalent       |

**Gate F1 (blocant):** testul pică pe ≥3 bug-uri cunoscute reintroduse (`stare_firma`,
`numar_mediu_salariati` în compare, `company_id` în monitoring_audit). **Dacă nu pică pe toate 3,
detectorul e decorativ — nu trece mai departe.**

⚠️ **Limită onestă:** detectorul prinde chei **citite și inexistente**. NU prinde chei **scrise și
necitite** (`brave_reputation` nerandat) — pentru alea e nevoie de F6 (inventar de randare).

---

## 6. FAZA 2 — Fixture-uri însămânțate DIN producție

> Azi `tools/generate_*_golden.py` rulează **codul** → îngheață ce face codul, **inclusiv crash-uri**
> (dovedit: `rich_full_lead_generation.json` avea `error:true` + 4 modele „Eroare interna" ca
> „output așteptat"). Un fixture generat din producție **nu poate** codifica o formă greșită.

| #   | Task                                                                                                                                                       | Status | Dovadă cerută                              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------ |
| 2.1 | `tools/seed_fixtures_from_production.py` — construiește fixture-uri din `reports.full_data` real (anonimizat dacă e nevoie)                                | ⬜     | fixture generat, diff vs cel scris de mână |
| 2.2 | Migrează fixture-urile existente la forma reală; **catalogează divergențele găsite** (fiecare = un bug potențial)                                          | ⬜     | listă divergențe                           |
| 2.3 | `tests/test_fixtures_match_production.py` — fixture-urile trebuie să aibă **același set de chei** ca producția                                             | ⬜     | test verde                                 |
| 2.4 | **Regulă în generatorul de golden:** dacă baseline-ul conține `error:true` / „Eroare interna" / INDISPONIBIL peste tot → **refuză să scrie** + avertizează | ⬜     | test: golden cu crash e respins            |

**Gate F2 (blocant):** 2.4 e nenegociabil. Un golden care poate îngheța un crash e mai rău decât
niciun golden — a stat verde peste un `ZeroDivisionError` și a „validat" fiecare refactor de după.

---

## 7. FAZA 3 — Ping-uri care nu pot minți

> Brave: ping-ul zicea „OK" trimițând un GET **fără `country`**; producția trimitea `country='RO'`
> → 422 pe **fiecare** apel real, 0/78 rapoarte. Gate verde peste funcție 100% moartă.

| #   | Task                                                                                                                                | Status | Dovadă cerută                             |
| --- | ----------------------------------------------------------------------------------------------------------------------------------- | ------ | ----------------------------------------- |
| 3.1 | `tests/test_pings_call_production_path.py` — fiecare ping din `PING_REGISTRY` trebuie să apeleze funcția reală de client (spy/mock) | ⬜     | test verde                                |
| 3.2 | Repară `ping_monitorul_oficial` (testează homepage; producția folosește Tavily)                                                     | ⬜     | non-vacuitate: bug reintrodus → ping pică |
| 3.3 | Repară `ping_just` (verifică doar că `zeep` se importă; nu atinge SOAP-ul real)                                                     | ⬜     | idem                                      |
| 3.4 | Audit toate cele 15 ping-uri: care mai testează altceva decât producția?                                                            | ⬜     | tabel per ping                            |

**Gate F3 (blocant):** pentru fiecare ping reparat — cu bug-ul reintrodus, **ping-ul trebuie să
raporteze PICAT**. Dacă zice „OK" și cu bug-ul prezent, e tot decorativ.

---

## 8. FAZA 4 — Gardă anti-drift de mediu

> Mecanismul care **m-a păcălit pe mine** și a băgat „Google Maps e MORT" în CLAUDE.md ca fapt
> „verificat la sursă". Maps funcționa perfect. Ți s-a dat și o sarcină manuală inutilă.

| #   | Task                                                                                                         | Status | Dovadă cerută               |
| --- | ------------------------------------------------------------------------------------------------------------ | ------ | --------------------------- |
| 4.1 | `tools/check_env_drift.py` — raportează care chei diferă între env vars și `.env` (**NUME, nu valori**)      | ⬜     | detectează cele 4 cunoscute |
| 4.2 | `config.py`: WARNING zgomotos la pornire când o cheie din env var diferă de `.env`                           | ⬜     | log real la boot            |
| 4.3 | Documentează în CLAUDE.md metoda corectă de testare a cheilor (forțează din `.env`, sau folosește ping live) | ⬜     | secțiune scrisă             |

⚠️ **NU rezolvă** drift-ul (alea sunt cheile tale) — doar îl face **imposibil de ratat**.

---

## 9. FAZA 5 — Documentația care nu poate minți

> Rata reală măsurată: **din ~36 afirmații verificabile din CLAUDE.md, 17 sunt FALSE sau expirate.**
> Greșește în **ambele sensuri**. Cauza: e scrisă de mână, deci derivă.

| #   | Task                                                                                                                                                                                                                         | Status | Dovadă cerută              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------------------------- |
| 5.1 | **Scoate din CLAUDE.md TOATE afirmațiile „X funcționează".** Rămân doar **decizii** + **gotchas** (lucruri care NU pot fi generate)                                                                                          | ⬜     | diff; CLAUDE.md ≤ jumătate |
| 5.2 | `AUDIT_FUNCTII.html` devine **sursa de adevăr** pt status, generat din producție (ping live + `reports.full_data`)                                                                                                           | ⬜     | regenerat, verificat       |
| 5.3 | **Redefinește „COMPLETATĂ"** în CLAUDE.md: necesită **dovadă că a produs ceva pe date reale** (job_id / rând DB / fragment din raport). Fără dovadă → „SCRIS", nu „COMPLETAT"                                                | ⬜     | regulă scrisă              |
| 5.4 | Registry de provenance: per feature, `job_id`-ul care dovedește că a rulat                                                                                                                                                   | ⬜     | tabel generat              |
| 5.5 | Corectează cele 17 afirmații false rămase (`88+ endpoints`→86, `563 pytest`→814, PPTX 7→7 ✅ acum, Excel 4→7, INS TEMPO „timeout"→404, Monitorul Oficial „firme curate"→inert structural, ONRC local „COMPLETATA"→0 rânduri) | ⬜     | diff                       |

**Gate F5:** după 5.1, CLAUDE.md **nu mai poate minți despre funcționalitate** — pentru că nu mai
face afirmații despre ea.

---

## 10. FAZA 6 — Testare exhaustivă + gate 95% (cerută explicit)

> „Testează fiecare modul/funcție/comandă și continuă doar după validare, 95% sigur că totul e
> funcțional și sincronizat."

**Definiție măsurabilă a lui „95% sigur"** (altfel e o senzație, nu un gate):

| Dimensiune           | Total real | Prag                               | Cum se măsoară                         |
| -------------------- | ---------- | ---------------------------------- | -------------------------------------- |
| Endpoint-uri REST+WS | 86         | ≥95% testate live                  | apel real, status + formă răspuns      |
| Pagini frontend      | 16         | 100% cablare verificată            | chei citite vs răspuns real            |
| Tipuri de analiză    | 9          | ≥95% rulate real                   | job real, `reports` în DB              |
| Surse externe        | 19         | 100% clasificate                   | MERGE / GOL LEGITIM / PICAT, cu dovadă |
| Formate raport       | 8          | 100% generate + conținut extras    | grep/pdfplumber/docx/pptx              |
| Provideri AI         | 5          | 100% clasificați                   | ping live + urme în log                |
| Task-uri scheduler   | 7          | 100%                               | `scheduler_state` + artefacte          |
| Detector chei moarte | —          | **0 findinguri noi**               | F1 verde                               |
| Suite                | —          | pytest+vitest verzi, ruff 0, tsc 0 | gate RIS                               |

| #   | Task                                                                              | Status | Dovadă |
| --- | --------------------------------------------------------------------------------- | ------ | ------ |
| 6.1 | Inventar exhaustiv generat automat (nu scris de mână)                             | ⬜     |        |
| 6.2 | Testare live 86 endpoint-uri                                                      | ⬜     |        |
| 6.3 | Cablare 16 pagini (chei reale)                                                    | ⬜     |        |
| 6.4 | 9 tipuri analiză — job real per tip                                               | ⬜     |        |
| 6.5 | 8 formate — conținut extras din fișier real                                       | ⬜     |        |
| 6.6 | Raport de acoperire vs pragurile de mai sus                                       | ⬜     |        |
| 6.7 | **GATE 95%** — dacă vreo dimensiune e sub prag: **STOP**, raportează, nu continua | ⬜     |        |

⚠️ **Ce NU poate fi validat de Claude, niciodată:** randarea vizuală și clicurile reale în browser.
Rămân la Roland (**TAB NOU** — service worker-ul servește bundle vechi la refresh).

---

## 11. FAZA 7 — Bug-uri rămase + cod mort

| #   | Task                                                                                                                          | Status | Notă                                                                  |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ------ | --------------------------------------------------------------------- |
| 7.1 | `verified_data["anomalies"]` gol 78/78 — `_detect_anomalies` pare să nu se declanșeze niciodată                               | ⬜     | posibil nepotrivire de chei; **investighează înainte de a repara**    |
| 7.2 | Brave `freshness="pm"` → 0-1 rezultate vs 3-5 fără; gol des chiar și după fix                                                 | ⬜     | decizie: relaxare vs acceptare                                        |
| 7.3 | `benchmark` gol în **63%** din rapoarte (`CAEN_BENCHMARK` static, ~21 secțiuni; CAEN 51 lipsește) → cade și `sector_position` | ⬜     | extindere tabel vs mesaj onest                                        |
| 7.4 | `ris_runtime.log` **dublează fiecare linie** (sink dublu) + poluat cu artefacte pytest                                        | ⬜     | ieftin, impact real la debug                                          |
| 7.5 | **Cod mort (R-MINIMAL):** 5 provideri AI niciodată apelați (DeepSeek, OpenRouter, GitHub Models, Fireworks, SambaNova)        | ⬜     | șterge sau cablează                                                   |
| 7.6 | `request dedup` (orchestrator) — implementat complet, **zero apelanți**                                                       | ⬜     | idem                                                                  |
| 7.7 | `log_synthesis()` — funcția care ar înregistra ce provider a generat fiecare secțiune, **niciodată apelată**                  | ⬜     | **cablează** — ne-ar fi răspuns azi la „cine scrie rapoartele"        |
| 7.8 | `network_client` întreg (Toxic PageRank, Conflict Interese, Rețeaua de Firme) + ONRC local (0 rânduri)                        | ⬜     | **blocaj de DATE, nu de cod** — decizie: șterge vs INDISPONIBIL onest |

---

## 11-BIS. FAZA 8 — API-uri, credentiale, fallback + AUDIT_FUNCTII

> Detalii complete: `docs/GHID_CREDENTIALE_API.md`. Aici doar checklist-ul de executie.

| # | Task | Status | Dovada ceruta |
|---|------|--------|---------------|
| 8.1 | ROTIRE `GOOGLE_CLOUD_API_KEY` — expusa in CLAR pe Google Drive (`API_de_adaugat.md`), **confirmat identica cu cheia din `.env` = cheia VIE** | NU POATE CLAUDE | Roland: consola Google + sters din fisier + istoric Drive |
| 8.2 | ROTIRE `MISTRAL_API_KEY` (aparuta intr-un output de sesiune; local, gitignored) | NU POATE CLAUDE | Roland |
| 8.3 | DECIZIE master pe Google Drive — regula ta spune "master (**offline**)", realitatea e `G:\My Drive` sincronizat in cloud | NU POATE CLAUDE | Roland |
| 8.4 | `tools/audit_credentials.py` — per cheie din `.env`: declarata in config? cablata in cod? ping live? fallback? | | tabel generat, nu scris de mana |
| 8.5 | FIX: `GITHUB_MODELS_TOKEN` — `synthesis_providers.py:114` foloseste `github_token` (tokenul de CLI `gh`, NU LLM) | | non-vacuitate + apel live real |
| 8.6 | FIX/DECIZIE: `COHERE_API_KEY` in `.env`, **ZERO cod** — rerank+embeddings neatinse | | vezi F9 (N2) |
| 8.7 | Matrice de fallback per capabilitate + **acopera cele 2 cu ZERO fallback** (OCR, traducere) | | tabel + cod |
| 8.8 | `AUDIT_FUNCTII.html` — regenerat din PRODUCTIE + buton per credentiala + **coloana fallback** | | dashboard live verificat |
| 8.9 | Sterge/cabeaza cei 5 provideri AI configurati si NICIODATA apelati (DeepSeek, OpenRouter, GitHub Models, Fireworks, SambaNova) + xAI (doar camp in config) | | R-MINIMAL |

**Gate F8 (blocant):** 8.1 e **prima**, inaintea oricarui cod. O cheie vie in clar, sincronizata in cloud, bate orice prioritate tehnica.

⚠️ **Onest:** `AUDIT_FUNCTII.html` **avea DREPTATE** cand documentatia mintea (Google Maps). Dashboard-ul generat din productie e mai de incredere decat orice fisier scris de mana — **inclusiv decat acest plan**.

---

## 11-TER. FAZA 9 — Surse & unelte NOI

> Detalii, link-uri si marcaje [CERT]/[PROBABIL]/[INCERT]: `99_Plan_vs_Audit/PLAN_SURSE_NOI_2026-07-16.md`

| # | Task | Status | Impact |
|---|------|--------|--------|
| 9.1 | **VERIFICARE LA SURSA** inainte de orice cod: TED, Kohesio, GLEIF, data.gov.ro, EU Funding Portal — ce chei emit REAL, pe 3 firme reale | | evita al doilea openapi.ro |
| 9.2 | **N1 — serviciul RIS sa ruleze ca USER, nu LocalSystem** (`services.msc` / `tools/RIS-Backend.xml`) | | 🔴 **REZOLVA `SYNTHESIS_MODE` FARA NICIUN COST.** Cauza reala: serviciul = **LocalSystem**, auth-ul Claude = fisier in profilul userului (`~/.claude/.credentials.json`) -> SYSTEM nu-l vede -> fallback tacut pe Groq. **DOVEDIT LIVE 2026-07-17:** `claude --print` raspunde corect headless din context user. **`ANTHROPIC_API_KEY` RESPINSA de Roland — abonamentul Max acopera deja; API = plata dubla pe aceeasi capabilitate.** |
| 9.2b | **Upgrade model `claude-opus-4-6` -> `claude-opus-4-8`** (`synthesis_providers.py:47`) | | ambele testate live (raspund OK); platesti Max, primesti Opus vechi. Fix de o linie |
| 9.3 | **N2 — Cohere Rerank** peste Tavily+Brave | | cel mai mare salt de CALITATE la ce citeste AI-ul |
| 9.4 | **N3 — Firecrawl** → repara Monitorul Oficial (azi inert structural) | | sursa moarta -> vie |
| 9.5 | **N5 — DeepL** + **N6 — Azure Doc Intel** | | acopera capabilitatile cu ZERO fallback |
| 9.6 | **N7 — TENDERS-RO Supabase** (baza ta proprie de licitatii, prin API) | | |
| 9.7 | **Q2 — RAG pe rapoartele proprii** (embeddings + rerank) | | "ce firme seamana cu asta?" |
| 9.8 | GLEIF — **[INCERT]** posibila reparatie pt `network_client` (mort structural: openapi.ro nu livreaza asociati) | | verifica acoperirea firmelor mici RO INAINTE |

**Gate F9 (blocant):** **9.1 inaintea oricarei integrari.** Fiecare sursa noua trece cele 8 puncte din §7 al `PLAN_SURSE_NOI` — inclusiv "**randare**: daca datele nu ajung in raport, sursa e decor" (`maps_rating` a fost colectat corect luni de zile si n-a aparut in NICIUNUL din cele 8 formate).

---

## 12. CE TREBUIE SĂ FACĂ ROLAND MANUAL (Claude NU poate)

| #   | Task                                                                                                                                                                             | Status        | De ce doar tu                                                   |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | --------------------------------------------------------------- |
| M1  | **Decizia `SYNTHESIS_MODE`** — rapoartele sunt scrise de Groq/Gemini, nu de Opus, deși „Decizia tehnică #1" spune altceva. Afectează **calitatea produsului**, nu corectitudinea | 🚫            | decizie de produs                                               |
| M2  | **Rotire cheie Mistral** — a apărut într-un output de sesiune (local, gitignored, NU pe GitHub)                                                                                  | 🚫            | acces la consola Mistral                                        |
| M3  | **Verificare vizuală în TAB NOU** — descărcări, panouri, culori                                                                                                                  | 🚫            | doar ochi omenești                                              |
| M4  | Aprobare ștergere artefacte din root: `C:UsersALIENWARE...tarom_dump1.txt`, `UsersALIENWAREDesktopRoly_WORK_cachepytest/`                                                        | 🚫            | regula ta la ștergeri                                           |
| M5  | ONRC local: import CSV (~660MB) — dacă vrem sursa vie                                                                                                                            | 🚫            | fișiere pe disc                                                 |
| M6  | ~~Google Cloud Places API (New)~~                                                                                                                                                | ✅ **ANULAT** | **Maps funcționează** — sarcina era bazată pe o afirmație falsă |

**APROBARE PLAN:** ⬜ Roland aprobă execuția · ⬜ Roland cere modificări (scrie mai jos)

---

## 13. ÎMBUNĂTĂȚIRI NOTABILE PROPUSE (dincolo de reparat)

| #   | Propunere                                                                                                                                                                                           | Valoare                  | Status    |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | --------- |
| I1  | **Contracte tipizate (Pydantic `extra="forbid"`) la granițe** — soluția DEFINITIVĂ; ar fi ucis fiecare bug de azi _la scriere_. Cost: proiect, nu sesiune; se face pe etaje, cu golden după fiecare | omoară clasa 100%        | ⬜ propus |
| I2  | Detector de chei **scrise și necitite** (invers față de F1) — ar prinde `brave_reputation`, `maps_rating` nerandat                                                                                  | acoperă gaura F1         | ⬜ propus |
| I3  | CI local: hook pre-push care rulează F1 + F3                                                                                                                                                        | previne regresia         | ⬜ propus |
| I4  | `venv` dedicat pentru serviciu (azi: Python global; `gradio` deja în conflict)                                                                                                                      | izolare                  | ⬜ propus |
| I5  | Contract test frontend↔backend (tipuri TS generate din OpenAPI)                                                                                                                                     | omoară clasa pe frontend | ⬜ propus |

---

## 14. JURNAL DE EXECUȚIE

> Claude adaugă o linie după FIECARE sub-task. Format: dată · task · rezultat · dovadă · commit.

| Data       | Task        | Rezultat                          | Dovadă | Commit |
| ---------- | ----------- | --------------------------------- | ------ | ------ |
| 2026-07-16 | Creare plan | Plan scris, **așteaptă aprobare** | —      | —      |

---

## 15. ORDINE RECOMANDATĂ + COST ESTIMAT

1. **F0 + F1** (~1,5 sesiuni) — detectorul. **Cel mai mare câștig.** După el, clasa nu mai poate intra tăcut.
2. **F2** (~0,5) — fixture-urile nu mai pot minți.
3. **F3** (~0,5) — ping-urile nu mai pot minți.
4. **F4** (~0,3) — drift-ul de mediu devine imposibil de ratat.
5. **F5** (~1) — documentația nu mai poate minți.
6. **F6** (~1,5) — testarea exhaustivă + gate 95%.
7. **F7** (~1) — bug-urile rămase + cod mort.
8. **I1** (proiect separat) — contractele tipizate, dacă vrei definitiv-definitiv.

**Total F0-F7: ~6-7 sesiuni.** După ele: **clasa dominantă de bug nu mai poate intra nedetectată.**

---

## 16. CRITERIUL DE SUCCES AL ÎNTREGULUI PLAN

> Nu „zero bug-uri" — ăla e o minciună. Ci:

**Orice cheie citită și nescrisă, orice fixture care minte, orice ping decorativ și orice afirmație
falsă din documentație devin IMPOSIBIL DE INTRODUS FĂRĂ SĂ PICE UN TEST.**

Iar la întrebarea „cât % din sistem funcționează?" să existe un răspuns **generat**, nu estimat.
