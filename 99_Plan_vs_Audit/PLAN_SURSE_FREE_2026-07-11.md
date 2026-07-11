# PLAN — Surse externe gratuite: cea mai bună combinație pentru RIS

**Data:** 2026-07-11
**Autor:** Claude (Opus) + 3 clustere de cercetare la sursă primară + validare advisor
**Status:** PROPUNERE — se implementează DOAR după ce user-ul răspunde la Q1 + Q2 (deciziile de scop de mai jos)
**Regulă:** FREE-ONLY (fără abonament, fără billing obligatoriu) — `feedback_free_only_policy.md`

---

## 0. Obiectiv

> „Vreau active sursele gratuite cele mai capabile și performante pe care le-aș putea conecta. Gândește cele mai bune combinații posibile încât să acoperi și să extinzi toate sursele de verificare și de analiză completă." — user, 2026-07-11

Toate limitele/licențele de mai jos au fost **verificate la sursa primară pe 2026-07-11** (nu din memorie).

---

## 1. DECIZII DE SCOP (gating) — răspunde ÎNAINTE de implementare

### Q1 — RIS e produs comercial?

Rapoartele sunt livrate/vândute către clienți, sau strict uz intern?

- **Decide:** dacă **OpenSanctions** (singura sursă serioasă de **PEP**) e free sau plătit.
- OpenSanctions = licență **CC BY-NC 4.0** → uz comercial interzis fără licență plătită (€0.10/apel API sau flat pe ofertă). FAQ-ul lor tratează și **uz intern al unei firme for-profit** ca fiind comercial.
- **Consecință onestă:** cu listele oficiale free (OFAC/UE/ONU) obții **screening SANCȚIUNI, ZERO PEP**. PEP e singurul gap real pe care banii l-ar închide.

### Q2 — Volumul lunar + vrei funcții de portofoliu/sector?

Câte firme analizezi pe lună? Vrei interogări bulk (toate firmele dintr-un CAEN/județ/status)?

- **Decide:** dacă merită importul dump-ului ONRC local (674 MB).
- Valoarea dump-ului are **două props**, nu una:
  - (a) elimină plafonul 100 req/lună openapi.ro — **condiționat de volum** (dacă analizezi <100/lună, plafonul nu te încurcă → dump = întreținere fără câștig);
  - (b) deblochează lucruri pe care openapi.ro NU le poate face per-request: **interogări bulk/sector/portofoliu + FTS local**.
- Dacă vrei (b) → importul se justifică indiferent de volum. Dacă nici (a) nici (b) → skip 674 MB.

---

## 2. STARE ACTUALĂ vs. PROPUNERE — arhitectura pe dimensiuni

| Dimensiune analiză           | Sursă actuală RIS              | Cea mai bună combinație free                                   | Acțiune                    |
| ---------------------------- | ------------------------------ | -------------------------------------------------------------- | -------------------------- |
| Identitate & registru (ONRC) | openapi.ro (100/lună)          | openapi.ro (live) **+ dump data.gov.ro local** (bulk/fallback) | 🟡 Q2                      |
| Financiar                    | ANAF Bilant (oficial)          | — (ești la sursă)                                              | ✅ nimic                   |
| Fiscal (TVA/stare)           | ANAF v9                        | ANAF **+ VIES** (TVA firme UE)                                 | 🟢 ADAUGĂ                  |
| Litigii                      | Portal Just (SOAP)             | — (oficial)                                                    | ✅ nimic                   |
| Insolvență                   | BPI                            | — (oficial)                                                    | ✅ nimic                   |
| **Sancțiuni**                | **ABSENT**                     | **OFAC + UE FSF + ONU** (oficiale, free, comercial OK)         | 🟢 **ADAUGĂ (gap real)**   |
| PEP                          | ABSENT                         | OpenSanctions (plătit pt comercial)                            | 🔴 Q1                      |
| Acționariat / UBO            | reprezentanți legali (parțial) | **niciuna free** — RBR blocat legal                            | ⚫ documentăm limitarea    |
| Garanții mobiliare           | `aegrm_client` (DNS mort)      | RNPM = web-only, fără API                                      | 🟠 link manual, nu scraper |
| Sector RO                    | INS TEMPO                      | INS TEMPO **+ Eurostat** (benchmark UE)                        | 🟢 ADAUGĂ                  |
| Licitații                    | SEAP (RO)                      | SEAP + TED (UE)                                                | 🟡 amânat                  |
| Identitate cross-border      | —                              | GLEIF LEI (free CC0)                                           | 🟡 amânat (valoare mică)   |
| FX / macro                   | BNR                            | — (BNR suficient); ECB/World Bank opțional                     | ✅ nimic                   |
| Geocodare/reputație          | Google Maps                    | Nominatim/OpenCage (dacă vrei zero-billing)                    | ✅ ok cu credit            |
| Sinteză AI                   | Claude CLI + 8 fallback        | —                                                              | ✅ ești în top             |

---

## 3. CONSTATĂRI VERIFICATE (2026-07-11) — pe scurt

### ✅ Free pt uz comercial, gata de integrat

| Sursă                       | Endpoint                                                                            | Cheie             | Licență        | Note                                                                            |
| --------------------------- | ----------------------------------------------------------------------------------- | ----------------- | -------------- | ------------------------------------------------------------------------------- |
| **VIES** (validare TVA UE)  | REST `ec.europa.eu/taxation_customs/vies/rest-api/ms/{MS}/vat/{nr}` + SOAP fallback | NU                | reuse EU       | rate-limited, per-tranzacție, nu bulk; păstrează `consultationNumber` ca dovadă |
| **OFAC SDN** (sancțiuni US) | `sanctionslistservice.ofac.treas.gov/api/download/{file}`                           | NU                | domeniu public | trimite `User-Agent`; matching îl faci tu                                       |
| **UE FSF** (sancțiuni UE)   | `webgate.ec.europa.eu/fsd/fsf/public/files/.../content?token=token-2017`            | NU (token public) | reuse EU       | verificat live: XML >10MB fără login                                            |
| **ONU** (sancțiuni)         | `scsanctions.un.org/resources/xml/en/consolidated.xml`                              | NU                | oficial        | migrare UNSOL în curs — confirmă calea periodic                                 |
| **Eurostat**                | `ec.europa.eu/eurostat/api/dissemination/statistics/...` (JSON-stat)                | NU                | reuse EU       | filtrezi pe dimensiunea `NACE_R2`; cap pe mărimea query-ului                    |
| **data.gov.ro ONRC dump**   | `data.gov.ro/dataset/firme-08-12-2025` (cel mai nou)                                | NU                | CC BY 4.0      | 6 CSV, OD_FIRME 674,6 MB; **rezolvă slug-ul cel mai nou dinamic**               |
| **GLEIF LEI**               | `api.gleif.org/api/v1/lei-records`                                                  | NU                | CC0            | doar firme cu LEI (puține IMM RO)                                               |
| **TED** (licitații UE)      | `POST api.ted.europa.eu/v3/notices/search`                                          | NU                | open data EU   | RO acoperit; fair-usage 700 req/min                                             |

### 🔴 Excluse (nu sunt free pt RIS comercial)

| Sursă                            | Motiv                                                                                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **OpenSanctions**                | CC BY-NC → comercial = plătit (chiar și self-host `yente`: datele ≠ softul). €0.10/apel sau flat pe ofertă. Singura sursă PEP serioasă → vezi Q1 |
| **Termene.ro**                   | free tier = **1.200 interogări/AN** (confirmat la sursă), date bogate = add-on plătit → inutilizabil producție                                   |
| **OpenCorporates**               | cheie obligatorie; comercial de la £2.250/an                                                                                                     |
| **Creditsafe / D&B / IBISWorld** | abonament plătit (la nevoie reală viitoare, nu acum)                                                                                             |

### ⚫ Blocate legal / fără API (nu din vina arhitecturii)

- **RBR (beneficiari reali)** — după CJEU C-37/20 + **Legea 86/2025** (mai 2025): acces doar cu interes legitim + taxă + semnătură electronică + 5 zile, per firmă. Fără API/bulk. **Nu există sursă free pt UBO în RO.** Proxy = reprezentanți legali/administratori (deja colectați).
- **RNPM (ex-AEGRM)** — consultare gratuită, dar **web-only, fără API**. Automatizare = scraper fragil pe `mj.rnpm.ro`. → link manual în raport, NU scraper de întreținut.

---

## 4. PLAN DE IMPLEMENTARE — pe valuri (tier)

### 🟢 VALUL 1 — free-pt-comercial, valoare mare, efort mic (RECOMANDAT să începem aici)

- [ ] **VIES** — `backend/agents/tools/vies_client.py` (httpx async + `with_retry`, REST cu fallback SOAP). Cablare în `agent_official.py`: se declanșează când apare un TVA/partener UE. Randare: „TVA UE valid ✔ (ref. consultare X)". **Efort: ~0,5 zi.**
- [ ] **Sancțiuni oficiale** — `backend/agents/tools/sanctions_client.py` (OFAC + UE FSF + ONU: fetch + parse + cache local cu refresh zilnic/6h prin scheduler). Screening în `agent_verification.py` pe: **administratori/asociați** (deja colectați) + **contrapărți străine** — NU doar numele firmei (yield ~0 pt IMM RO). Randare: checklist due-diligence „Screening sancțiuni: CURAT / HIT" + hit real = early warning. Matching **fuzzy pe entități, cu prag** (nu substring naiv → false pozitive). **Efort: ~1–1,5 zi.**
- [ ] **Eurostat** — `backend/agents/tools/eurostat_client.py` + mapare CAEN→NACE_R2. Cablare în `caen_context.py`/benchmark: „firma vs. media sector RO (INS TEMPO) vs. media UE (Eurostat)". **Efort: ~0,5 zi.**

### 🟡 VALUL 2 — amânat (valoare marginală sau gated pe Q2)

- [ ] **dump ONRC local** — rulează `tools/import_onrc.py` pe `firme-08-12-2025` + **slug resolver dinamic** (UUID-urile se schimbă lunar) + refresh lunar prin scheduler + cablare ca fallback/bulk. **DOAR dacă Q2 = volum mare / vrei portofoliu.** **Efort: ~1 zi.**
- [ ] **TED** — licitații UE. SEAP acoperă deja RO; TED adaugă doar nivel UE. **Efort: ~0,5 zi.**
- [ ] **GLEIF LEI** — trivial, dar valoare mică (puține IMM RO au LEI). **Efort: ~2h.**

### 🟠 VALUL 3 — decizii, nu cod-fire-and-forget

- [ ] **`aegrm_client.py` (mort)** — repointează ca **link manual RNPM** în raport SAU marchează/elimină. **Nu-l lăsa să emită secțiuni goale** (bug atins la TASK 2). **Efort: ~1–2h.**
- [ ] **UBO** — documentează limitarea legală în raport (o linie: „beneficiari reali — acces restricționat legal RBR"); folosește reprezentanții legali ca proxy. **Efort: ~1h.**

### 🔴 GATED pe Q1

- [ ] **PEP via OpenSanctions** — DOAR dacă accepți cost. Altfel: „PEP — în afara scopului (nu există sursă free-comercială)".

---

## 5. NOTE TEHNICE (din validarea advisor)

1. **Endpoint-uri [PROBABIL]/nedocumentate stabil:** VIES REST path, UE FSF `token-2017`, ONU XML path. **Construiește pe patternul existent retry/fallback** (VIES SOAP ca fallback la REST) → dacă un endpoint se schimbă silențios, raportul degradează grațios, nu se rupe.
2. **Sancțiuni = completeness checkmark, nu semnal frecvent.** Prezintă „screening efectuat → curat/hit", nu ca semnal des. Matching pe indivizi + contrapărți străine, cu prag anti-false-pozitiv.
3. **Chei API:** niciuna dintre sursele Valul 1 NU cere cheie. Zero atingere sistem `.api-keys`.
4. **Toate clienții noi** urmează tiparul existent (`anaf_client.py`, `bpi_client.py`): httpx singleton + `with_retry` + logging structurat + cache TTL.

---

## 6. Ce NU facem (și de ce)

- ❌ OpenSanctions fără licență (comercial) · ❌ Termene.ro (free tier 1.200/an) · ❌ OpenCorporates/D&B/IBISWorld/Creditsafe (plătite) · ❌ scraper RNPM (fragil, fără API) · ❌ integrare RBR (blocat legal).
