# PLAN — Integrare RIS ↔ TENDERS-RO („Licitații Publice RO")

**Data:** 2026-07-12
**Autor:** Claude (Opus) + audit tehnic subagent pe `C:\Proiecte\Licitatii` (schema + RPC + auth, verificat pe cod)
**Status:** DESIGN — fără cod; se implementează DOAR după decizie user pe direcție (Angle A / B) + aprobare pe partea TENDERS (regula lor §3B)
**Verdict symbiote:** ❌ irelevant (symbiote = instalator de module de cod într-un stack, nu punte între o app Python și una Next.js/Supabase/Vercel). Integrarea = **API service-to-service**, ambele apps rămân separate.

---

## ⚠️ FAZA 0 — REZULTAT (2026-07-12): verificarea a răsturnat recomandarea

**Descoperire:** RIS **face deja Angle B** — `seap_client.get_contracts_won(cui)` interoghează SEAP pe CUI → contracte + achiziții directe câștigate, **cablat în orchestrator (Agent 3 Market, linia 346) + scorat (`scoring.py:719`, +10 Piață)**. Integrarea TENDERS pt Angle B = **redundanță**.

**Dar:** e colectat + scorat, **NU randat în raport** (grep seap/market pe generatoare = 0) → pattern „backend colectează > expune".

**Verificare 2:** TENDERS `contracte` = probabil **nepopulat** (Faza 1 = discovery; `contracte` = intel competitor §7B, ulterior).

### ✅ Recomandare corectată (înlocuiește secțiunile de mai jos)

1. **⭐ IMEDIAT (doar RIS):** randează `verified["market"]["seap"]` → secțiune „Istoric Achiziții Publice (SICAP)" în HTML/PDF/DOCX. ~half-day, zero TENDERS. **ROI maxim** — expune ce RIS deja are.
2. **TENDERS Angle B = amânat** (redundant + nepopulat).
3. **Angle A (oportunități viitoare)** = ✅ **LIVRAT** (v1 `06988f0` + **v2 `ce86fde`**) în clientul SEAP propriu RIS (fără TENDERS). `caen_cpv_map.py` (mapare orientativă CAEN→CPV) + `seap_client.search_open_tenders` (SICAP `GetCNoticeList`, filtrare locală pe prefix CPV). **v2:** matching pe **CPV-uri reale câștigate** (competențe dovedite, marker `precise`, afișate primele) + fallback CAEN; `basis: istoric_real|caen_orientativ`; fetch cache-uit per-fereastră. Secțiune „Oportunități de Contracte (SICAP)". Confirmat live (CAEN 4120→15/15 precise).
4. **TENDERS separat** — deep-link RIS→dashboard TENDERS al firmei (Mosslein), nu merge.

> Secțiunile 2-5 de mai jos rămân ca referință pt scenariul API-TENDERS, dar NU mai sunt calea recomandată după Faza 0.

---

---

## 0. Insight-ul cheie din audit — DOUĂ direcții, nu una

„Posibilitatea firmei de a prinde contracte" se poate ataca din 2 unghiuri, cu costuri/valori foarte diferite:

| Unghi                                                            | Ce arată în raportul RIS                                   | Cheie de join          | Mapare CAEN→CPV?      | Încredere                          | Suprapunere cu ce ai deja                      |
| ---------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------- | --------------------- | ---------------------------------- | ---------------------------------------------- |
| **A. Înainte — „licitații deschise pe care le-ar putea licita"** | Oportunități viitoare pe sectorul firmei                   | **CAEN → CPV** (fuzzy) | **DA — și e crux-ul** | scăzută-medie (taxonomii diferite) | RIS are deja client SEAP care poate face ~asta |
| **B. Înapoi — „istoricul firmei în achiziții publice"**          | Contracte câștigate: câte, ce valoare, de la ce autorități | **CUI** (exact)        | **NU**                | mare (match exact pe CUI)          | semnal nou de due-diligence                    |

**Recomandare: începe cu B.** E exact (join pe CUI, pe care RIS îl are nativ), nu cere mapare CAEN→CPV, folosește doar tabelul GLOBAL `contracte`, și adaugă o dimensiune reală de analiză („firma asta câștigă contracte publice? cât? de la cine?") — direct pe misiunea RIS. Unghiul A e speculativ (CAEN↔CPV n-are crosswalk oficial) și se suprapune cu clientul SEAP existent.

---

## 1. Fapte verificate (audit pe cod TENDERS-RO)

- **Stack:** Next.js 16 + Supabase Postgres + pgvector + Drizzle + Vercel. LIVE la `tenders-ro.vercel.app`.
- **Tabele GLOBALE** (RLS: `SELECT` pt orice authenticated, scriere doar service_role): `licitatii`, `loturi`, **`contracte`**, `cpv_codes`, `sicap_nomenclator`. → **safe de citit cross-service** (fără date de tenant).
- **Tabele FIRM-SCOPED** (RLS `firma_id in app.user_firme()`): `matching`, `firma_*`, `oferte`, `alerte`. → **NU** se pot servi cross-tenant.
- **`matching`** (verdict `GO/NO_GO/PARTIAL` + `gap_json`) = **Faza 2, NEPOPULAT + firm-scoped** → valoarea „poate câștiga + ce lipsește" NU e construită încă și e per-tenant. Integrarea pt ea acum = prematură.
- **`search_licitatii` RPC** = doar text+semantic (RRF FTS+pgvector), **NU ia CPV sau firma_id**. Nu servește „licitații pe listă CPV".
- **Niciun endpoint REST nu întoarce date de licitații** — doar `cron/*` + `health` + `ingestion/status`. Un endpoint nou trebuie construit pe partea TENDERS.
- **CAEN↔CPV: NU există în repo** (doar `cpv_crosswalk` = CPV↔CPV). RIS trebuie să dețină traducerea.
- **`contracte`** (GLOBAL): `winner_cui`, `winner_nume`, `contract_value` + (verifică) autoritate, dată, licitatie_id. **Join pe `winner_cui` = exact.** ⚠️ **De verificat: e populat?** (depinde de ingestia „da"/darea de atribuire în TENDERS — Faza 1 ingerează notice-uri; award-parsing poate să nu fie încă activ).
- **CPV pe licitație:** `licitatii.cpv_principal` (char8) + `loturi.cpv_principal` + `loturi.cpv_secundare_json`. Ierarhie via `cpv_codes.division/grp/cls/category` (prefix indexat).
- **„Deschis" nu e boolean:** `deadline > now()` + `stare_sicap` într-o listă de stări valide din `sicap_nomenclator` (dinamic, nu enum static). Fără coloană `county` pe licitatii (doar `loturi.locatie`).
- **Embedding Cohere NU e necesar** pt filtrare CPV/CUI (doar pt semantic, opțional, degradează la FTS).
- **Auth cross-service curat:** route Next.js nou păzit cu `Bearer <secret>` (reutilizează tiparul `CRON_SECRET`), care interoghează **doar tabele GLOBALE** via service_role → zero scurgere de tenant (garantată de scope-ul query-ului, nu de RLS).

---

## 2. Contractul API — Angle B (RECOMANDAT: istoric achiziții pe CUI)

**Pe partea TENDERS (endpoint nou, sub §3B — semnalare + aprobare + deploy preview→prod):**

```
GET /api/public/procurement-history?cui=<CUI>[&limit=50]
Authorization: Bearer <RIS_READ_TOKEN>            # tipar CRON_SECRET

200 → {
  "cui": "26313362",
  "won_count": 12,
  "total_value": 4830000, "currency_mix": {"RON": 10, "EUR": 2},
  "first_award": "2019-03", "last_award": "2026-05",
  "top_authorities": [{"name":"Primaria X","count":4,"value":1200000}, ...],
  "contracts": [ {"titlu","autoritate","contract_value","moneda","data","licitatie_id","sicap_id"} ... up to limit ]
}
```

- Query: `contracte JOIN licitatii` (ambele GLOBALE) `WHERE winner_cui = :cui`, agregări + listă. Allow-list explicit de coloane. **Nicicând** tabele firm-scoped.

**Pe partea RIS:**

- `backend/agents/tools/tenders_client.py` — client httpx, `get_procurement_history(cui)`, cheie din sistemul central (`TENDERS_RO_API_URL` + `TENDERS_RO_READ_TOKEN`, prin INBOX → „proceseaza inbox"; citit cu `os.environ.get`).
- Cablare în `agent_verification` (rezilient, timeout ~15s): `verified["procurement_history"] = ...`.
- Randare secțiune „Istoric Achiziții Publice (SICAP)" în HTML+PDF+DOCX: nr. contracte, valoare totală, top autorități, trend. **Semnal de scoring** posibil: firmă cu istoric solid de contracte = pozitiv operațional/piață.

---

## 3. Contractul API — Angle A (opțional, ulterior: oportunități pe CPV)

**Pe partea TENDERS (endpoint nou):**

```
GET /api/public/opportunities?cpv=45000000,71000000[&limit=50]
Authorization: Bearer <RIS_READ_TOKEN>

200 → { "opportunities": [ {"id","titlu","autoritate","cpv_principal","valoare_estimata",
        "moneda","data_publicare","deadline","stare_sicap","sicap_id","tip"} ... ] }
```

- Filtru: CPV prefix-match pe `licitatii.cpv_principal` **și** `loturi.cpv_principal`/`cpv_secundare_json` (via `cpv_codes.division/grp/cls`); `deadline > now()`; `stare_sicap` ∈ stări-deschise din `sicap_nomenclator`; order by `deadline`. Doar tabele GLOBALE.
- (Upgrade Faza 2 pe TENDERS: pasează label-ul CAEN ca `query_text` la `search_licitatii` pt ranking semantic — deja au Cohere.)

**Crux-ul CAEN→CPV (RIS îl deține):** CAEN (ce FACE firma) și CPV (ce se ACHIZIȚIONEAZĂ) sunt taxonomii diferite, **fără crosswalk oficial**. Strategie:

1. **v1 — hartă curată la nivel divizie** (`caen_to_cpv.json` în RIS): pt diviziile CAEN uzuale → set mic de diviziuni/grupe CPV (ex. CAEN 41-43 construcții → CPV 45; CAEN 62 IT → CPV 72; CAEN 49 transport → CPV 60; CAEN 10-11 alimente → CPV 15). Marcat explicit „orientativ".
2. **v2 — rafinare** din date reale: pt firmele cu istoric (Angle B!), învață ce CPV-uri a câștigat efectiv firma → cel mai bun „CPV real" per CAEN (feedback loop B→A).
3. Alternativ: pt firme care sunt tenant TENDERS (ex. Mosslein), folosește direct `firma_cpv` (CPV-uri confirmate uman) în loc de mapare.

---

## 4. Auth, guvernanță, riscuri

- **Auth:** `Bearer` shared secret (tipar `CRON_SECRET`), endpoint atinge doar tabele GLOBALE. Secret în sistemul central de chei, nu în cod.
- **Guvernanță TENDERS (§3B):** orice endpoint nou pe partea lor = semnalat + aprobat înainte, deploy preview→prod, sub regulile lor (RLS, GDPR scrub, effort MAX audit la fază).
- **Riscuri/caveats oneste:**
  - ⚠️ **`contracte` populat?** — dacă TENDERS nu ingerează încă award-uri („da"), Angle B e blocat până o fac. **De verificat primul lucru.**
  - ⚠️ **Suprapunere SEAP** — RIS are deja client SEAP („licitatii + achizitii directe"). De verificat ce oferă deja (poate acoperă parțial Angle A/B fără TENDERS). Nu duplica.
  - ⚠️ **Matching GO/NO_GO** (cea mai tare valoare) = Faza 2 TENDERS, nepopulat + firm-scoped → nu se poate servi cross-tenant. Pt asta, integrarea corectă e la nivel de FIRMĂ (deep-link către dashboard-ul TENDERS al firmei), nu service-to-service.
  - CAEN→CPV rămâne aproximativ — marchează rezultatele Angle A ca „orientative".

---

## 5. Faze + efort

| Fază  | Parte      | Ce                                                                                              | Efort     |
| ----- | ---------- | ----------------------------------------------------------------------------------------------- | --------- |
| **0** | verificare | `contracte` populat? + ce oferă deja clientul SEAP RIS                                          | ~1-2h     |
| **1** | TENDERS    | endpoint `/api/public/procurement-history` (Angle B) + secret (sub §3B)                         | ~0.5 zi   |
| **2** | RIS        | `tenders_client.py` + `verified["procurement_history"]` + secțiune raport HTML/PDF/DOCX + teste | ~1 zi     |
| **3** | opțional   | Angle A: endpoint opportunities + `caen_to_cpv.json` v1 + secțiune raport                       | ~1-1.5 zi |
| **4** | opțional   | deep-link firmă → dashboard TENDERS (pt matching GO/NO_GO Faza 2)                               | ~2h       |

**Recomandare finală:** Fază 0 (verificare) → Fază 1+2 (Angle B, istoric pe CUI — cel mai curat/valoros) → apoi decizi pe A.
