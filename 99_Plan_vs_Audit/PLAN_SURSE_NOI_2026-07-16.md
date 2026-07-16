# PLAN SURSE & UNELTE NOI — analize mai profunde, fonduri UE, licitații, oportunități

> **Creat:** 2026-07-16 · **Stare:** ⬜ PROPUNERE — așteaptă aprobare Roland
> **Însoțește:** `PLAN_ANTI_DERIVA_2026-07-16.md` (F8–F9) · `docs/GHID_CREDENTIALE_API.md`
> **Regula R3:** fiecare propunere e marcată **[CERT]** (verificat de mine) / **[PROBABIL]** / **[INCERT]** (necesită verificare la sursă ÎNAINTE de integrare).
> **Regula de bază a acestui proiect:** nicio sursă nu se integrează fără să confruntăm **ce EMITE** cu **ce CITEȘTE codul**. openapi.ro a stat ani întregi „integrat" fără să livreze niciodată `asociati`/`administratori`.

---

## 1. CÂȘTIGURI IMEDIATE — ai deja cheile, zero înregistrări

> Toate verificate ca **SETAT** pe mașina ta (2026-07-16). Nu trebuie să obții nimic.

| #      | Ce                                                                 | Impact                                                                                                                                                    | Efort      | Status |
| ------ | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------ |
| **N1** | **Serviciul RIS sa ruleze ca USER (nu LocalSystem)** — `tools/RIS-Backend.xml` / services.msc | 🔴 **CEL MAI MARE.** Deblocheaza `SYNTHESIS_MODE=claude_code` -> rapoartele scrise de **Claude Opus pe abonamentul Max**, **cost API ZERO**. Cauza reala: serviciul ruleaza ca **LocalSystem**, iar auth-ul Claude e un fisier in profilul TAU (`~/.claude/.credentials.json`) -> SYSTEM nu-l vede -> cade tacut pe Groq. **DOVEDIT 2026-07-17:** `claude --print --model claude-opus-4-6` raspunde corect headless din context user. **DECIZIE ROLAND: NU cumparam API — Max acopera deja.** | ~0,5 | ⬜ |
| **N1b** | **Upgrade model: `claude-opus-4-6` -> `claude-opus-4-8`** (`synthesis_providers.py:47`) | Platesti Max — n-are rost sa primesti Opus vechi. **Ambele testate live 2026-07-17: raspund OK.** Fix de o linie, dupa N1 | ~0,1 | ⬜ |
| **N2** | **Cohere Rerank** (`COHERE_API_KEY`, deja în `.env`, **zero cod**) | 🔴 **Cel mai mare salt de CALITATE.** Rerankează rezultatele Tavily+Brave înainte să ajungă la AI → AI-ul primește ce e relevant, nu ce a nimerit motorul | ~0,5       | ⬜     |
| **N3** | **Firecrawl** (`FIRECRAWL_API_KEY`)                                | Repară **Monitorul Oficial**, azi inert structural (Tavily trunchiază → regex-urile nu prind nimic, indiferent de firmă)                                  | ~0,5       | ⬜     |
| **N4** | **GitHub Models token corect** (`GITHUB_MODELS_TOKEN`)             | Fix de o linie: RIS folosește `github_token` = tokenul de CLI. De-aia providerul n-a mers niciodată                                                       | ~0,1       | ⬜     |
| **N5** | **DeepL** (`DEEPL_API_KEY`)                                        | Rapoarte EN **reale** — `i18n.py` există, traducerea lipsește. 500K caractere/lună                                                                        | ~0,5       | ⬜     |
| **N6** | **Azure Document Intelligence** (`AZURE_DOC_INTEL_KEY`)            | Fallback OCR (azi: **zero** fallback). 500 pagini/lună                                                                                                    | ~0,5       | ⬜     |
| **N7** | **TENDERS-RO Supabase** (`TENDERS_RO_SUPABASE_URL` + `_ANON_KEY`)  | **Baza ta proprie de licitații**, prin API. CLAUDE.md respinsese integrarea prin „symbiote" — dar prin API e trivial                                      | ~1         | ⬜     |

**N1 + N2 = cel mai bun raport calitate/efort din tot documentul.** Unul repara _cine scrie_ rapoartele (Claude Opus, gratis via Max), celalalt _ce citeste_ AI-ul inainte sa scrie. **`ANTHROPIC_API_KEY` RESPINSA de Roland (2026-07-17): abonamentul Max face acelasi lucru, platit deja. Corect — API-ul ar fi fost cost dublu pe aceeasi capabilitate.**

---

## 2. SURSE NOI PENTRU DOMENIUL TĂU — fonduri UE, licitații, oportunități

> ⚠️ **Toate [INCERT] până la verificare la sursă.** Le-am listat din cunoștințe, **nu le-am testat azi**. Regula proiectului: verifică setul REAL de chei emis, nu documentația. Faza F9.1 din plan e exact asta.

### 2.1 Licitații & achiziții publice

| Sursă                                   | Ce aduce peste SEAP                                                             | Cost                | Marcaj                 | Link de verificat                                                          |
| --------------------------------------- | ------------------------------------------------------------------------------- | ------------------- | ---------------------- | -------------------------------------------------------------------------- |
| **TED — Tenders Electronic Daily**      | **Licitații din TOATĂ UE**, nu doar RO. Firmele tale pot licita transfrontalier | gratuit, oficial UE | [PROBABIL] API oficial | https://ted.europa.eu/ · https://docs.ted.europa.eu/                       |
| **EU Funding & Tenders Portal (SEDIA)** | Licitații + granturi direct de la Comisie                                       | gratuit             | [INCERT]               | https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home |
| **OpenTender.eu**                       | Date istorice + indicatori de integritate/risc                                  | gratuit             | [INCERT] acoperire RO  | https://opentender.eu/                                                     |
| **data.gov.ro**                         | Seturi deschise RO (inclusiv achiziții)                                         | gratuit             | [PROBABIL]             | https://data.gov.ro/                                                       |

### 2.2 Fonduri europene

| Sursă                                | Ce aduce                                                                                         | Cost    | Marcaj              | Link                          |
| ------------------------------------ | ------------------------------------------------------------------------------------------------ | ------- | ------------------- | ----------------------------- |
| **Kohesio**                          | Proiecte finanțate UE — **cine a primit bani, cât, pentru ce**. Aur pentru „a primit finanțare?" | gratuit | [INCERT] API        | https://kohesio.ec.europa.eu/ |
| **MySMIS2021 / MIPE**                | Fonduri UE România — apeluri + beneficiari                                                       | gratuit | [INCERT] API public | https://mfe.gov.ro/           |
| **EU Open Data Portal**              | Catalog general date UE                                                                          | gratuit | [PROBABIL]          | https://data.europa.eu/       |
| _(existent)_ `funding_programs.json` | 8 programe hardcodate                                                                            | —       | ✅ funcțional       | —                             |

**Observație onestă:** `funding_programs` merge azi (CFL primește „Granturi IMM"), dar e un **JSON static de 8 programe**. O sursă live ar transforma feature-ul din decorativ în util.

### 2.3 Date despre firme (peste ANAF/ONRC)

| Sursă                 | Ce aduce                                          | Cost                    | Marcaj                 | Link                                        |
| --------------------- | ------------------------------------------------- | ----------------------- | ---------------------- | ------------------------------------------- |
| **VIES** _(existent)_ | validare TVA UE                                   | gratuit                 | ✅                     | —                                           |
| **EBR / BRIS**        | Registrul comerțului la nivel UE (interconectare) | [INCERT]                | [INCERT]               | https://e-justice.europa.eu/                |
| **GLEIF (LEI)**       | Identificator legal global + structură de grup    | gratuit                 | [PROBABIL] API deschis | https://www.gleif.org/en/lei-data/gleif-api |
| **OpenCorporates**    | structură corporativă                             | ❌ **plătit comercial** | [CERT] respins         | —                                           |
| **Termene.ro**        | date RO bogate                                    | ❌ 1.200/an             | [CERT] respins         | —                                           |

🔴 **GLEIF merită atenție specială:** e **exact gaura din RIS** — `network_client` (Toxic PageRank, Conflict Interese, Rețeaua de Firme) e **mort structural** fiindcă openapi.ro nu livrează niciodată asociați/administratori. GLEIF publică relații de proprietate (parent/child LEI). **[INCERT] acoperirea firmelor mici RO** — de verificat pe MOSSLEIN/CFL înainte de orice cod.

---

## 3. UNELTE care cresc CALITATEA execuțiilor (nu doar volumul de date)

| #      | Unealtă                                                           | Ce schimbă                                                                                                                                                                                    | Marcaj                   |
| ------ | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **Q1** | **Cohere Rerank**                                                 | AI-ul primește top-5 **relevante**, nu top-20 „ce a nimerit motorul". Cel mai ieftin salt de calitate                                                                                         | [CERT] cheie disponibilă |
| **Q2** | **Embeddings + RAG pe rapoartele proprii** (Cohere/Scaleway/Jina) | „Ce firme din baza mea seamănă cu asta?", „Ce am mai văzut la CAEN 4711?" — RIS își folosește propria istorie. Cercetarea ta din `TOP20_AI_API_GRATUITE_2026.md` descrie exact acest pipeline | [PROBABIL]               |
| **Q3** | **Claude prin API** (N1)                                          | Nivelul 1 de calitate, azi mort                                                                                                                                                               | [CERT]                   |
| **Q4** | **Pollinations.AI**                                               | Proxy gratuit spre GPT-5/Claude/Gemini, fără signup — fallback „premium"                                                                                                                      | [INCERT] stabilitate     |
| **Q5** | **Firecrawl**                                                     | Scraping real acolo unde Tavily trunchiază                                                                                                                                                    | [CERT] cheie disponibilă |

---

## 4. DUBLURI RECOMANDATE (cerința ta: „un alt API ca dublură")

**Principiu:** dublură **numai** unde absența doare și sursa e single-point-of-failure.

| Capabilitate   | Primar azi       | Dublura recomandată                                                          | De ce                                                                |
| -------------- | ---------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Sinteză AI** | Groq             | **Claude API (N1)** + Z.ai/Qwen                                              | Nivelul 1 e mort; Mistral pică azi → fallback real de 3 nivele, nu 5 |
| **OCR**        | Mistral          | **Azure Doc Intel** _(ai cheia)_ + Google Doc AI _(aceeași cheie ca Gemini)_ | **Zero fallback azi**                                                |
| **Căutare**    | Tavily 1000/lună | Brave ✅ + **Firecrawl**                                                     | Quota Tavily e singura barieră reală                                 |
| **Traducere**  | —                | **DeepL** + Azure Translator _(ai ambele)_                                   | i18n există fără traducere                                           |
| **Litigii**    | Portal Just      | ❌ niciuna                                                                   | Fără alternativă cunoscută                                           |

**NU recomand dublură** pentru: ANAF (unic oficial), BNR (unic), Sancțiuni (deja 3 liste), Eurostat (unic).

---

## 5. CE **NU** RECOMAND (și de ce — ca să nu se repropună)

| Respins                                       | Motiv                                                   | Marcaj   |
| --------------------------------------------- | ------------------------------------------------------- | -------- |
| OpenCorporates / D&B / IBISWorld / Termene.ro | plătit comercial                                        | [CERT]   |
| OpenSanctions                                 | CC BY-NC = plătit comercial                             | [CERT]   |
| RBR / UBO (beneficiari reali)                 | **blocat legal** — CJEU C-37/20 + L.86/2025             | [CERT]   |
| RNPM                                          | web-only, fără API                                      | [CERT]   |
| Dump ONRC 674MB                               | tabela e goală de luni; volum mic de firme nu justifică | [CERT]   |
| ApiFreeLLM                                    | „forever free" fără model de business = risc            | [INCERT] |

---

## 6. ORDINE RECOMANDATĂ

1. 🔴 **Securitate** — rotește `GOOGLE_CLOUD_API_KEY` (expusă în clar pe Drive, **confirmat cheia vie**) + Mistral
2. **N1** Serviciul ca USER -> Claude Opus via Max (**cost zero**) + **N1b** upgrade la opus-4-8
3. **N2** Cohere Rerank — repară _ce citește_ AI-ul
4. **N4** GitHub Models (o linie) + **N3** Firecrawl (repară Monitorul Oficial)
5. **N6** Azure OCR + **N5** DeepL — acoperă cele două capabilități cu zero fallback
6. **F9.1** Verificare la sursă: TED, Kohesio, GLEIF, data.gov.ro → **abia apoi** integrare
7. **N7** TENDERS-RO + **Q2** RAG pe istoria proprie

**Estimare N1–N6: ~3-4 sesiuni.** Ordinea nu e negociabilă la punctul 1.

---

## 7. GATE DE INTEGRARE (obligatoriu pentru FIECARE sursă nouă)

> Scris ca să nu repetăm openapi.ro — „integrat" ani de zile fără să livreze ce credea codul.

1. **Verifică setul REAL de chei emis** de API pe **≥3 entități reale** (TAROM 477647, MEGA IMAGE 6719278, CFL 49104500). **Nu documentația** — răspunsul real.
2. **Distinge „gol legitim" de „mort"** — o firmă curată fără litigii ≠ un client rupt.
3. **Ping care apelează calea REALĂ** de producție + dovadă că **poate pica** (bug reintrodus → ping PICAT).
4. **Fixture din răspunsul real**, niciodată inventat.
5. **Non-vacuitate** — testul pică pe codul dinainte.
6. **Job live** pe o firmă reală înainte de push.
7. **Randare** — dacă datele nu ajung în raport, sursa e decor. (`maps_rating` a fost colectat corect luni de zile și n-a apărut în **niciunul** din cele 8 formate.)
8. **Fallback declarat** — ce se întâmplă când sursa pică?

---

## 8. JURNAL

| Data       | Acțiune                                                        | Rezultat                                                                                                          |
| ---------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 2026-07-16 | Audit inventar `~/.api-keys` + `.env` RIS + folderul `API_Key` | 11 credențiale disponibile și nefolosite · 3 expuneri · 2 chei cablate greșit (`github_token`, `cohere` fără cod) |
