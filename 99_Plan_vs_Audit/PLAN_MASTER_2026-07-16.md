# PLAN MASTER — restante REALE, verificate in cod (2026-07-16)

> **De ce exista acest fisier:** la 2026-07-16 **nu exista niciun plan activ**. Toate cele 8 planuri
> din `99_Plan_vs_Audit/` sunt inchise sau blocate pe decizii. Restantele erau imprastiate in 6 surse.
> **Toate cele 17 bug-uri reale gasite pe 07-15/16 nu erau in niciunul dintre planuri** — au venit din
> vanatoarea de CLASA de bug, nu din backlog.
>
> **Metoda:** 4 agenti pe surse disjuncte (`.claude-outputs/`, `99_Plan_vs_Audit/`, `99_Deep_Research/`+
> `Gemini_Documentatie/`, restante auto-declarate), fiecare obligat sa **verifice IN COD** ca itemul
> chiar nu e implementat, cu dovada. **Rezultat: ~64 itemi din liste erau DEJA FACUTI.** Un audit
> fara acest pas ar fi produs o lista in care jumatate e zgomot.

## Clasificare (NU prioritatea din documentele originale)

**A** = afecteaza utilizator real, **TACUT** (rezultat gresit/lipsa fara sa se planga) · **B** = afecteaza,
zgomotos · **C** = **mina armata** (cod mort care se activeaza cand il reinvii — dovedit de 3 ori) ·
**D** = igiena interna · **E** = strategic (decizia lui Roland).

**Regula:** un item D marcat "MEDIUM" intr-un audit e mai putin important decat unul A marcat "LOW".
Auditul din 07-13 a dat 63 findinguri numarand complexitate ciclomatica in timp ce jumatate din produs
nu rula, si **n-a prins niciunul** din cele 17 bug-uri reale.

---

## CLASA A — tacute, pe date reale (prioritate maxima)

| ID     | Problema                                                                                                                                                                                                                                                                                                                                                            | Fisier:linie                                                                   | Dovada                     |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------- |
| **A1** | `except Exception -> logger.debug` inghite calculul `predictive_scores` (toate 4 modelele) SI `credit_exposure`. Orice exceptie -> cheile dispar din raport, fara urma vizibila. **Periculos ACUM**: cele 4 modele au fost reinviate pe 07-15 si semnul profitului schimbat pe 07-16.                                                                               | `agent_verification.py:216-231`                                                | verificat de Opus la sursa |
| **A2** | `datetime.strptime(..., "%d.%m.%Y")` nu accepta ISO (`yyyy-mm-dd`), format trimis uneori de ANAF -> `ValueError` prins de except generic -> regula de anomalie "firma tanara + CA mare" **sarita silentios**.                                                                                                                                                       | `agent_verification.py:1151`                                                   | verificat de Opus la sursa |
| **A3** | Checklist due-diligence (10 verificari) exista in PDF/DOCX/Excel/1-pager + `RichDataTab`, dar **LIPSESTE din HTML**.                                                                                                                                                                                                                                                | `html_generator.py` (grep `due_diligence` = 0)                                 | INVENTAR_1                 |
| **A4** | **Nicio marcare cand scorul 6D diverge de modelele predictive de faliment.** Datele exista (`verified["predictive_scores"]`), nimic nu le compara -> user vede "Verde" fara avertisment de dezacord.                                                                                                                                                                | lipsa (feature)                                                                | INVENTAR_1                 |
| **A5** | `cui = meta.get("company_name","")` — cheie/dict gresite -> **CUI-ul real nu apare NICIODATA** in header-ul PDF 1-pager.                                                                                                                                                                                                                                            | `one_pager_generator.py:52`                                                    | F841 ruff, confirmat       |
| **A6** | `tavily_quota_exhausted` scris, **citit NICAIERI** -> quota epuizata randeaza identic cu "firma curata". **Absenta dovezii prezentata ca dovada a absentei** — cel mai periculos mod de esec pt un produs de risc.                                                                                                                                                  | scris `agent_official.py:522`, grep cititori = 0                               | INVENTAR_4                 |
| **A7** | `extract_and_validate_cui` **moarta**; 2 locuri de PRODUCTIE reimplementeaza inline un regex mai slab, **fara validare MOD11**.                                                                                                                                                                                                                                     | `cui_validator.py:53` mort; `routers/analysis.py:~71`, `agent_official.py:~68` | INVENTAR_4                 |
| **A8** | `_JSON_DROP_PRIORITY` taie `tender_opportunities`/`market` **primele**, exact pt sectiunea "opportunities" (route "fast", limita 20K) -> sectiunea se poate goli fix cand ar avea cel mai mult de spus.                                                                                                                                                             | `agent_synthesis.py:~35-41`, `:400-406`                                        | INVENTAR_3/4               |
| **A9** | Sectiunea **"Reteaua de Firme" exista DOAR in HTML**; PDF+DOCX = 0 referinte. Refactorul DRY `rich_fields.py` (07-14) a sarit peste `company_network`. **Azi inofensiv** (reteaua e goala pt orice firma), dar **mina armata**: devine vizibil exact cand se cableaza o sursa de administratori. **Se repara IMPREUNA cu decizia demoanaf.ro, INAINTE de inviere.** | `html_generator.py:367` exista; `pdf_generator.py`/`docx_generator.py` = 0     | INVENTAR_2                 |

## CLASA B — zgomotoase

| ID     | Problema                                                                                                                                                                                   | Fisier:linie                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| **B1** | `asyncio.create_task` fara referinta retinuta -> task-uri colectate de GC. **4 situri** (nu 2).                                                                                            | `jobs.py:149`, `scheduler.py:272`, `batch.py:209`, `batch.py:284` |
| **B2** | Ramurile `except` web/market **nu trimit `agent_complete` pe eroare** -> frontend nu primeste semnal de finalizare pt Agent 2/3 daca pica.                                                 | `orchestrator.py`                                                 |
| **B3** | `icon` calculat per severitate anomalie, **niciodata randat** pe slide.                                                                                                                    | `pptx_generator.py:182` (F841)                                    |
| **B4** | **`RIS_TEST.bat` ruleaza `npx vitest run` bare** (fara `--pool=threads`) -> `Companies.test.tsx` da hang -> **feedback loop-ul FE al lui Roland (dublu-click) moare**. Unealta LUI, rupta. | `RIS_TEST.bat:55`                                                 |
| **B5** | README trimite la `START_RIS.vbs` (**inexistent**, real e `RIS.vbs`) + cifre invechite (156 pytest vs ~586 real, 43 endpoints vs ~90, 12 pagini vs 16).                                    | `README.md:30,40,45-46`                                           |

## CLASA C — mine armate / valoare neexploatata

| ID     | Problema                                                                                                                                                                                                                                                                                 | Note                            |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| **C1** | `agent_verification.execute()` complexitate **F52** (a CRESCUT de la F46 la auditul 07-14). **Acelasi profil ca cele 3 crash-uri anterioare** (`calculate_risk_score` 167, `agent_official` 81, bug-ul `litigation`). Ruleaza la FIECARE analiza.                                        | refactor cu golden, ca la #1/#4 |
| **C2** | `EBIT = bilant.get("profit_brut", bilant.get("profit_net",0))` — `profit_brut` e mereu prezent (chiar 0), deci fallback-ul **nu se declanseaza niciodata** -> EBIT = 0 pt firme pe pierdere in loc de negativ. **Inert azi** (Altman INDISPONIBIL) — mina pt ziua in care Altman revine. | `predictive_models.py:80`       |
| **C3** | 3 endpoint-uri backend functionale **fara UI** (metode in `api.ts`, zero call-sites): `GET /jobs/{id}/diagnostics`, `POST /batch/{id}/resume`, `POST /monitoring/{id}/suppress`.                                                                                                         | valoare deja platita            |
| **C4** | Cohere "firme similare" semantic — niciodata implementat; `cohere_api_key` gol. Fallback pe filtru CAEN **functioneaza**, deci nu e tacut.                                                                                                                                               | blocat pe cheie                 |

## CLASA D — igiena (NU se amesteca cu A/B/C)

`ruff check backend/` = **10 erori** (2 F841 = A5+B3 de mai sus, 4 E402, 2 B905, 2 E741) · `_score_financiar`
complexitate **95, grad F** (agravat de la 63) · `total_score` calculat inainte de zombie detection (override-ul
zombie nu se reflecta) · **M25** venv dedicat pt serviciu (ruleaza pe Python global; `gradio` cere starlette<1.0)
· Vite 6.2 (plan cerea 7.x), Tailwind 3.4 (plan cerea v4) · "split-urile" raportate (ReportView, CompanyDetail,
agent_synthesis, scoring, agent_official) au **recrescut** peste 500-1000 LOC — obiectiv erodat, efectiv moot.

## DECIZII PENDINTE (Roland — NU sunt itemi de cod)

1. **`demoanaf.ro`** pt administratori -> reinvie `network_client.py` intreg (Toxic PageRank, Conflict Interese,
   migrarea 008, sectiunea Reteaua de Firme). **Verificat live de Opus pe 3 firme** (1/5/7 admini, cu `personId`
   = legatura intre firme). Contra: sursa **neoficiala**, fara SLA, **ToS neverificat**, `asociati` tot lipsa.
   **Recomandare Opus:** DA, cu tratament best-effort (pica -> INDISPONIBIL onest, niciodata fabricat) + **A9
   reparat in acelasi val** + verifica ToS INAINTE.
2. **openapi.ro = INCHIS DEFINITIV** — schema documentata (API Blueprint brut) **nu contine** `asociati`/
   `administratori`/`capital_social` **la niciun tier**; tier-urile cumpara doar volum (99/199/499 RON).
   Ipoteza "feature de plata" **infirmata**, nu doar neconfirmata. **Nu re-cerceta.**
3. **Brave + Jina** (`web_intelligence`, `brave_reputation`) — 100% orfane, consuma quota per firma pt date
   aruncate. Cablare in RAPORT (nu in scor — risc de dubla-numarare cu `web_presence`+`maps_rating`) sau oprire.
4. **D5 — Piotroski F2/F3 -> `None`** (ca F5/F7). Cu `cfo = profit*1.1` fabricat, F2/F3 se reduc la semnul
   profitului, identic cu F1 -> **43% din scor decis de un singur fapt**. `cfo = profit_net*1.1` **se elimina**,
   nu se eticheteaza "proxy". (D4 CFO INDISPONIBIL + D6 Beneish blocat de a doua cheie = constatari de fapt.)
5. **Google Cloud Console** — migrare Places API (New). Maps e MORT (`REQUEST_DENIED`, legacy). Pana atunci
   reputational ruleaza pe o singura intrare. **Doar Roland are acces.**
6. **`PLAN_COMPETITIE_2026-07-15.md`** — import ONRC bulk (~660MB, slug lunar, **descarcare manuala de Roland**).
   Sectiunea "competition" **nu ajunge NICIODATA la un provider AI**, pt nicio firma.
7. **Ponderare:** TAROM = **74.5/Verde/"parteneriat recomandat"** cu capitaluri proprii NEGATIVE, 5 ani de
   pierdere, 709 dosare — profitul din 2024 domina. Nu e bug, e alegere de produs. Aceeasi familie cu D2/D3.
8. Chei neobtinute (cod gata): DeepSeek, OpenRouter, xAI, Cohere, Gmail.

## CLASA E — strategice (din Deep Research, decizia lui Roland)

Knowledge Graph multi-hop grad 2-4 (azi `network_client` e **grad-1 only**) · ML survival pe tot dataset-ul
ONRC/ANAF (**diferit** de XGBoost-pe-`score_history`, inchis MOOT) · OCR+LLM pe PDF-uri bilant MFP (Note
Explicative -> DD nivel Big-4) · Rapoarte de cohorta / meta-sinteza sector (azi `/sector` = stats fara narativa)
· OSINT job boards (**risc ToS**). Surse noi verificate deschise, dar nisate (clasa C/D): Consiliul Concurentei,
ANPC, ANCPI (**INCERT** — documentul sursa nu citeaza API public verificabil).

## INCHISE CU DOVADA — nu re-cerceta

CFO real (blocaj **legal** OMFP 1802/2014 -> max ~2% acoperire; vezi `PLAN_CASHFLOW_2026-07-15.md`) · Altman
(ANAF nu expune split datorii curente/necurente) · openapi.ro administratori (vezi #2) · PostgreSQL (SQLite WAL
suficient) · XGBoost pe `score_history` (date insuficiente) · Termene.ro / OpenCorporates / OpenSanctions / D&B /
IBISWorld (platit / licenta) · RBR/UBO (**blocat legal**, CJEU C-37/20 + L.86/2025).

## NEVERIFICAT EXHAUSTIV (declarat, nu presupus curat)

`ROLAND_PLANIFICARI_MODULE.md` (97 items pretinsi) · `Audit_FULL.md` / `AUDIT_REPORT.md` / `Audit_R5.md` /
`CHECKPOINT_2026-04-05.md` · `RECOMANDARI_IMBUNATATIRI.md` + `_R2`/`_R3`/`_R4`/`_R5`/`_R7`/`_R8` (marcate
COMPLETATA per faza; itemii individuali **nu** au fost re-verificati cum a fost R6 — unde s-a dovedit ca
"45/65 implementate" era **depasit**, marea majoritate fiind de fapt facuta).
