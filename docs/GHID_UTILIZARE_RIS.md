# Ghid de utilizare RIS — cum rulezi o analiză și cum vezi ce a făcut fiecare provider

> Scris 2026-07-17, după ce Claude Opus (Max) a fost făcut să scrie efectiv raportul final.
> Pentru context tehnic complet vezi `CLAUDE.md` + `99_Plan_vs_Audit/PLAN_SINTEZA_CLAUDE_2026-07-17.md`.

---

## 1. Cum deschizi RIS (de unde)

RIS e **local**, rulează pe laptopul tău. Nu ai nevoie de internet pentru interfață (doar
sursele externe cer net).

- **Backend**: serviciu Windows `RIS-Backend`, pornește automat la boot, ascultă pe **portul 8001**.
  - Verifici că merge: în browser `http://localhost:8001/api/health` → trebuie `{"status":"ok"}`.
  - Pornire/oprire manuală (rar necesar): `sc start RIS-Backend` / `sc stop RIS-Backend`.
- **Interfața (PWA)**: iconița de pe desktop (deschide Chrome către `http://localhost:8001`), sau
  direct `http://localhost:8001` în browser. De pe telefon (aceeași rețea Tailscale): tot portul 8001.

**Claude Opus care scrie raportul NU trebuie ținut deschis în VS Code.** Backend-ul îl invocă singur
ca subproces (`claude --print`), folosind login-ul tău Max (`~/.claude/.credentials.json`) — $0, fără
API key. Contează doar ca login-ul Max să fie valid (dacă expiră, deschizi Claude Code o dată și te
reloghezi). Am forțat în cod ca subprocesul să folosească **DOAR** abonamentul Max, niciodată
`ANTHROPIC_API_KEY` (care ar factura) — vezi §6.

---

## 2. Cum rulezi o analiză

1. Deschide `http://localhost:8001` → pagina **Analiză nouă** (`/new-analysis`).
2. Introdu **CUI-ul** firmei (ex. `477647` = TAROM) sau denumirea.
3. Alege **tipul** (ex. `FULL_COMPANY_PROFILE` = profil complet) și **nivelul** (1 rapid / 2 standard /
   **3 exhaustiv**).
4. Pornește. Analiza rulează în fundal; poți da refresh oricând.

**Cât durează:** la nivel 3 cu `--effort max`, o analiză completă durează **~15–18 minute** — pentru
că Claude Opus scrie efectiv 4 secțiuni „grele" (~250s fiecare, măsurat live). E normal și așteptat.
Dacă vrei mai rapid (~10–11 min, calitate aproape identică), comută pe `--effort high` — vezi §5.

> **Notă UX (limitare cunoscută):** în timpul sintezei lungi, bara de progres din PWA poate rămâne
> aparent „blocată" la un pas anterior (nu se actualizează per-secțiune încă). Analiza NU e blocată —
> vezi harta/log-ul (§4) pentru progresul real. Îmbunătățirea progresului per-secțiune e listată ca
> pas următor.

---

## 2b. Cum te asiguri că TOTUL e conectat înainte de o analiză

Ai **trei** feluri, de la cel mai sigur la cel mai rapid:

1. **Preflight live (cel mai sigur)** — dublu-click pe **`Verifica conexiuni RIS`** (desktop), sau în
   terminal `python tools/preflight_check.py`. Testează **efectiv** fiecare sursă + provider AI prin
   serviciul real (cu cheile de producție) și îți spune clar **„GATA DE EXECUȚIE"** sau ce e picat.
   E singurul care confirmă că o conexiune chiar răspunde acum, nu doar că e configurată.
2. **Cardul „Health Status (Live)" din Dashboard** — verde/roșu la o privire. _(Reparat 2026-07-18: până
   acum arăta fals FAIL roșu la `ai providers` și `http pool` — era un bug de randare, conexiunile
   funcționau. Acum reflectă starea reală.)_
3. **Butoanele „Testează" din Settings** — test individual per serviciu, când vrei să verifici doar unul.

> **Cele 3 surse mereu roșii sunt normale și nu te împiedică:** BPI, AEGRM (DNS mort la furnizor),
> INS TEMPO (offline). Nu sunt vina ta și nu se pot repara din cod. Preflight-ul le marchează explicit
> ca „ignoră".

## 2c. Starterul (dublu-click)

- **`Deschide RIS`** (desktop) — starter **silențios**: se asigură că serviciul e pornit, apoi deschide
  aplicația într-o fereastră curată (Chrome app-mode). Fără ferestre de terminal; te avertizează doar
  dacă serviciul chiar nu pornește.
- `RIS.vbs` (în folderul proiectului) — starterul „greu" existent: rebuild frontend + restart serviciu +
  deschide. Folosește-l după ce s-au schimbat lucruri în cod; pentru deschidere zilnică, `Deschide RIS`
  e mai rapid.

## 3. Ce face fiecare provider (pipeline-ul, pe scurt)

Analiza trece prin 5 agenți. Fiecare pas e logat (vezi §4).

| Agent                    | Ce face                                                          | Provideri/surse folosite                                                                                                                                |
| ------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent 1 — Oficial**    | Date oficiale firmă                                              | ANAF (TVA/stare), ANAF Bilanț (CA/profit/angajați), BNR (curs), openapi.ro (ONRC), Portal Just (dosare), CAEN, Monitorul Oficial, sancțiuni OFAC/UE/ONU |
| **Agent 2 — Piață**      | Contracte publice                                                | SEAP (licitații + achiziții directe)                                                                                                                    |
| **Agent 3 — Web**        | Prezență online                                                  | Tavily (știri/recenzii), Google Maps, Brave/Jina                                                                                                        |
| **Agent 4 — Verificare** | Scor risc 0-100 pe 6 dimensiuni + due diligence + early warnings | intern (calcul)                                                                                                                                         |
| **Agent 5 — Sinteză**    | **Scrie raportul narativ**                                       | **Claude Opus (secțiunile grele)** → Groq/Gemini/Mistral/Cerebras (secțiuni scurte + fallback)                                                          |

**Împărțirea în Agent 5** (rutare per secțiune):

- **Claude Opus (Max)** scrie: rezumat executiv, analiză financiară, evaluare risc, recomandări (secțiuni „quality").
- **Groq** (rapid, gratuit) scrie: profil firmă, competiție, oportunități, SWOT (secțiuni „fast" scurte).
- Dacă Claude eșuează dintr-un motiv, se cade automat pe Gemini/Groq/Mistral/Cerebras (marcat `FALLBACK`).

---

## 4. Cum vezi HARTA cu pașii exacți per provider

Fiecare analiză produce un **log complet** cu fiecare pas: ce sursă a fost interogată, OK/FAIL, cât a
durat, ce a returnat, și **CE provider AI a scris fiecare secțiune**.

### 4a. Harta vizuală (HTML) — recomandat

Rulează în terminal, din folderul proiectului:

```
python tools/render_job_map.py            # ultima analiză
python tools/render_job_map.py <job_id>   # o analiză anume
```

Generează `outputs/<job_id>/execution_map.html` — deschide-l în browser. Vezi:

- **Secțiunea 1** — toate sursele interogate (verde = OK, roșu = FAIL) cu durata și ce au returnat.
- **Secțiunea 2** — fiecare secțiune de raport cu **cine a scris-o**: verde = **Claude Opus**,
  portocaliu = fallback. Un banner sus spune „Claude Opus a scris N/N secțiuni".

### 4b. Log-ul brut (text)

`logs/job_<job_id>.log` — deschide cu orice editor. Liniile cheie:

- `SOURCE | <sursă> | OK/FAIL | <ms> | fields=[...]` — fiecare sursă.
- `SYNTHESIS | <secțiune> | provider=claude | OK | N words | Nms` — **cine a scris fiecare secțiune**.
  Dacă vezi `provider=claude` (fără `(FALLBACK)`) → Claude Opus a scris-o. Dacă vezi
  `provider=groq (FALLBACK)` → Claude a eșuat și a preluat altul.

> **De reținut:** durata unei secțiuni (`Nms`) e TOTAL pe cascadă, atribuită câștigătorului. Ex.
> `provider=cerebras | 183542ms` însemna „Claude a încercat 180s, a fost tăiat, cerebras a răspuns
> instant" — NU „cerebras e lent". Acum, cu timeout-ul reparat, `provider=claude | 264472ms` înseamnă
> „Claude a scris în 264s".

---

## 5. Cum comuți calitate ↔ viteză (max / high)

În `.env` (rădăcina proiectului), reglabile fără cod:

```
SYNTHESIS_EFFORT=max          # max (calitate vârf, ~17 min) | high (~11 min, ~identic) | medium | low
SYNTHESIS_CLAUDE_TIMEOUT=360  # secunde per secțiune Claude (măsurat: max=252s, high=143s)
SYNTHESIS_TOTAL_TIMEOUT=2400  # plafon global sinteză (plasă de siguranță)
```

După orice schimbare: **restart serviciu** → `tools\RIS-Backend.exe restart` (sau `sc stop/start RIS-Backend`).

> **Prag minim (important dacă schimbi valorile):** păstrează `SYNTHESIS_TOTAL_TIMEOUT` cel puțin
> `2 × SYNTHESIS_CLAUDE_TIMEOUT + 120` (la default: 2×360+120 = 840; 2400 e mult peste). Dacă îl setezi
> prea mic, sinteza poate depăși plafonul global și pierde secțiuni. Default-urile sunt sigure.

> **Butonul „Regenerează" o secțiune** (din pagina raportului) funcționează acum și cu Claude la `max` —
> plafonul lui se mișcă automat cu `SYNTHESIS_CLAUDE_TIMEOUT` (+120s). O regenerare de secțiune „grea"
> durează 264–324s la `max`; ai răbdare, nu e blocat.

---

## 6. Cost — de ce e $0

Claude Opus scrie prin **abonamentul tău Max**, nu prin API. Codul forțează subprocesul `claude --print`
să ignore `ANTHROPIC_API_KEY` (care ar factura prin API) și să folosească login-ul Max. Tu ai variabila
`ANTHROPIC_API_KEY` setată în Windows, dar RIS o **elimină din mediul subprocesului** — deci zero cost,
garantat prin cod. Nu atinge variabila ta globală.

---

## 7. Dacă ceva pare greșit

- **Raportul apare fără text narativ / „Formate: none"** → sinteza a fost tăiată. Verifică log-ul (§4);
  dacă vezi mereu `FALLBACK`, Claude nu scrie — verifică login-ul Max (deschide Claude Code, reloghează-te).
- **O sursă apare FAIL constant** → unele sunt moarte extern, nereparabile din cod: **BPI/buletinul.ro**
  (DNS mort), **AEGRM** (DNS mort), **INS TEMPO** (offline). Restul trebuie să fie verzi.
- **Vrei să verifici toate conexiunile** → pagina **Settings** are butoane „Testează" per serviciu, sau
  dashboard-ul `http://localhost:8001/audit.html` (doar de pe laptop). Verificarea automată a acestei
  sesiuni a testat **20 de unelte** (surse de date + provideri AI): 17 verzi, 3 moarte extern (mai sus).
  **Cele 3 canale de notificare — Telegram, Email, Webhook — NU au fost în sweep** (ar trimite mesaje
  reale); testează-le individual din **Settings** când vrei (butoanele lor trimit un mesaj de test real).
