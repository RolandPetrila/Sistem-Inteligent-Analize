# GHID CREDENȚIALE API — RIS

> **Creat:** 2026-07-16 · **Sursă:** audit live al `.env` RIS + catalogul central `~/.api-keys/catalog.md`
> **Regula de aur:** valorile trăiesc DOAR în `.env` (RIS) + master + Windows env vars. **Niciodată** în chat, cod, sau git.
> **Gotcha critic:** `pydantic-settings` citește **env var-urile ÎNAINTEA** lui `.env`. Serviciul rulează ca **SYSTEM** → nu vede env var-urile tale → folosește `.env`. **Un shell pornit ca tine poate testa ALTĂ cheie decât producția.**

---

## 0. EXPUNERI — STARE (actualizat 2026-07-17)

| # | Ce | Status | Ce s-a facut |
|---|-----|--------|--------------|
| E1 | `GOOGLE_CLOUD_API_KEY` in clar in `API_de_adaugat.md` (Google Drive) — era **cheia VIE** | **REZOLVAT 2026-07-17** | Cheie noua `RIS_NEW_17.07.2026` in proiectul `ultra-tube-427721-f9` (My Maps Project), restrictionata la **Places API (legacy)**. Cheia veche `RIS - Analize Roland` (Apr 7 2026) **STEARSA din consola**. Linia stearsa din `API_de_adaugat.md`. Master + env vars + `API_KEYS_PHONE.html` actualizate. **Verificat LIVE:** Maps `found=True` (TAROM 3.3/767, MEGA IMAGE 4/1165, CIP 5/349) |
| E3 | `MISTRAL_API_KEY` — aparuse intr-un output de sesiune | **REZOLVAT 2026-07-17** | Cheie noua rotita de user, propagata prin INBOX. **Bonus:** Mistral **pica** la ping inainte de rotire; acum raspunde `HTTP 200` — cheia veche era cauza. Fallback-ul sintezei: 3 -> **4 niveluri sanatoase** |
| E2 | Master-ul (`API_KEYS.md`) contine valori **prin design**, dar sta pe Google Drive = **sincronizat in cloud**; regula globala spune "master (**offline**)" | **DE DECIS (Roland)** | Optiuni: (a) master pe disc local / container criptat; (b) accepti riscul si **modifici regula** sa reflecte adevarul. Nu lasa o regula care spune altceva decat faci |

**Fals-pozitiv verificat si inchis:** `.env.example` (RIS, **git public**) — valorile sunt **goale**, urmate de comentarii (`GROQ_API_KEY=   # console.groq.com`). Un scan euristic le raportase drept "chei reale". **Nicio scurgere pe GitHub.**

---

## 1. AUDIT — ce are RIS ACUM

**Legendă:** ✅ cablat+funcțional · ⚠️ cheie prezentă, cod inexistent/greșit · ❌ mort · 🚫 blocaj extern

### 1.1 Provideri AI (sinteza rapoartelor)

| Cheie `.env`         | Serviciu                | Status | Dovadă (2026-07-16)                                                                                                                                                                |
| -------------------- | ----------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GROQ_API_KEY`       | Groq (Llama 4 Scout)    | ✅     | ping live OK; probabil generează majoritatea secțiunilor                                                                                                                           |
| `GOOGLE_AI_API_KEY`  | Gemini 2.5 Flash        | ✅     | ping live OK                                                                                                                                                                       |
| `CEREBRAS_API_KEY`   | Cerebras (gpt-oss-120b) | ✅     | ping live OK                                                                                                                                                                       |
| `MISTRAL_API_KEY`    | Mistral Small 3 + OCR   | ✅     | **REPARAT prin rotire 2026-07-17** — ping `HTTP 200`. Cauza era cheia veche, nu codul                                                                                                                                            |
| — (lipsește)         | **Claude / Anthropic**  | ❌     | `SYNTHESIS_MODE=autonomous` → `synthesis_providers.py:33` blochează Claude CLI. `/api/health/deep`: `claude_cli:false`. **„Decizia tehnică #1" din CLAUDE.md e falsă în practică** |
| `GITHUB_TOKEN`       | GitHub Models           | ❌     | **CHEIE GREȘITĂ**: `synthesis_providers.py:114` folosește `github_token` = tokenul de **CLI (`gh`)**, nu `GITHUB_MODELS_TOKEN` (cel de LLM). De-aia n-a mers niciodată             |
| `DEEPSEEK_API_KEY`   | DeepSeek                | ❌     | metodă scrisă, **zero apelanți**                                                                                                                                                   |
| `OPENROUTER_API_KEY` | OpenRouter              | ❌     | idem                                                                                                                                                                               |
| `FIREWORKS_API_KEY`  | Fireworks               | ❌     | idem                                                                                                                                                                               |
| `SAMBANOVA_API_KEY`  | SambaNova               | ❌     | idem                                                                                                                                                                               |
| `XAI_API_KEY`        | xAI Grok                | ❌     | **doar câmpul în config** — zero cod de integrare                                                                                                                                  |
| `COHERE_API_KEY`     | Cohere                  | ⚠️     | **cheie în `.env`, ZERO cod.** (Hit-urile „cohere" din backend sunt `coherence` — alt cuvânt.) **Rerank + embeddings neatinse**                                                    |

### 1.2 Surse de date

| Cheie                  | Serviciu                                                           | Status                     | Dovadă                                                                                                                    |
| ---------------------- | ------------------------------------------------------------------ | -------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `TAVILY_API_KEY`       | Tavily Search                                                      | ✅                         | rezultate reale în fiecare raport                                                                                         |
| `BRAVE_API_KEY`        | Brave Search                                                       | ✅ (reparat azi `79bee2e`) | era 0/78 — `country="RO"`, respins de Brave                                                                               |
| `JINA_API_KEY`         | Jina Reader                                                        | ✅                         | 6/78 rapoarte cu conținut extras real                                                                                     |
| `OPENAPI_RO_KEY`       | openapi.ro (ONRC)                                                  | ⚠️                         | livrează identificare; **NU livrează NICIODATĂ** `asociati`/`administratori` (72/72) → Rețeaua de Firme moartă structural |
| `GOOGLE_CLOUD_API_KEY` | Google Maps Places                                                 | ✅                         | TAROM rating 3.3/767 recenzii (**documentația zicea „mort" — fals**)                                                      |
| —                      | ANAF TVA/Bilanț, BNR, SEAP, Portal Just, VIES, Sancțiuni, Eurostat | ✅                         | fără cheie, publice                                                                                                       |
| —                      | BPI, AEGRM                                                         | 🚫                         | DNS-dead la sursă                                                                                                         |
| —                      | INS TEMPO                                                          | 🚫                         | HTTP **404** (endpoint retras — nu „timeout" cum zice documentația)                                                       |
| —                      | Monitorul Oficial                                                  | ❌                         | inert structural: Tavily întoarce conținut trunchiat → regex-urile nu prind nimic                                         |
| —                      | ONRC local                                                         | ❌                         | `onrc_companies` = **0 rânduri**, niciun CSV pe disc                                                                      |

### 1.3 Infrastructură

| Cheie                                     | Serviciu     | Status                   |
| ----------------------------------------- | ------------ | ------------------------ |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram     | ✅ 69 notificări trimise |
| `GMAIL_USER` + `GMAIL_APP_PASSWORD`       | Gmail SMTP   | ⚠️ neverificat live      |
| `RIS_API_KEY`                             | auth internă | ✅                       |
| `APP_SECRET_KEY`                          | sesiune      | ✅                       |

---

## 2. 🎯 DISPONIBILE ÎN INVENTARUL TĂU, NEFOLOSITE DE RIS

> Toate **există deja ca env var pe mașina ta** (verificat: SETAT). Nu trebuie să obții nimic — doar să le adaugi în `.env` RIS + să cablezi codul.

| Prioritate | Env var                                                        | Ce deblochează în RIS                 | De ce contează                                                                                                                                                                                        |
| ---------- | -------------------------------------------------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🥇 **1**   | `ANTHROPIC_API_KEY_2`                                          | **Sinteza cu Claude, prin API**       | **Rezolvă definitiv `SYNTHESIS_MODE`.** Problema era că serviciul rulează ca SYSTEM și nu vede auth-ul Claude CLI. **O cheie API nu depinde de profil.** Rapoartele scrise de Claude, fără subprocess |
| 🥈 **2**   | `GITHUB_MODELS_TOKEN`                                          | Provider GitHub Models **real**       | RIS folosește tokenul greșit (CLI). Un fix de o linie                                                                                                                                                 |
| 🥉 **3**   | `FIRECRAWL_API_KEY`                                            | **Monitorul Oficial** + scraping real | Azi e inert fiindcă Tavily trunchiază. Firecrawl face scraping adevărat. 500 credite/lună                                                                                                             |
| 4          | `COHERE_API_KEY` (deja în `.env`)                              | **Rerank + embeddings**               | Cel mai mare salt de **calitate** la căutare: rerankează rezultatele Tavily/Brave înainte să ajungă la AI. 1000 req/lună                                                                              |
| 5          | `AZURE_DOC_INTEL_KEY` + `_ENDPOINT`                            | OCR bilanțuri scanate                 | 500 pagini/lună; alternativă/dublură la Mistral OCR                                                                                                                                                   |
| 6          | `DEEPL_API_KEY`                                                | Rapoarte EN reale                     | `i18n.py` există; traducerea reală lipsește. 500K caractere/lună                                                                                                                                      |
| 7          | `TENDERS_RO_SUPABASE_URL` + `_ANON_KEY`                        | **Baza ta proprie de licitații**      | Ai deja proiectul TENDERS-RO cu Supabase. CLAUDE.md respinsese integrarea prin „symbiote" — dar **prin API e trivial**                                                                                |
| 8          | `GOOGLE_API_KEY`                                               | Gemini + **Document AI** + Translate  | 1000 req/zi Flash + 1000 pagini OCR/lună + 500K chars translate — **o cheie, 3 capabilități**                                                                                                         |
| 9          | `SCALEWAY_ACCESS_KEY` + `SCALEWAY_API_KEY`                     | LLM + **embeddings**                  | 1M tokens, fără card                                                                                                                                                                                  |
| 10         | `NVIDIA_API_KEY` · `REKA_API_KEY` · `HF_TOKEN` · `CF_AI_TOKEN` | Fallback-uri suplimentare             | REKA are **$10/lună recurent**; CF 10K neurons/zi                                                                                                                                                     |
| 11         | `ADOBE_API_KEY` + `ADOBE_CLIENT_SECRET`                        | PDF processing                        | 500 tranzacții/lună                                                                                                                                                                                   |

---

## 3. 🆕 DE OBȚINUT — link direct pentru fiecare

> Recomandate în `API_de_adaugat.md` (cercetarea ta, aprilie 2026). **[INCERT]** = limitele se schimbă des; verifică la sursă înainte de integrare.

| #   | Provider             | Signup (link direct)                          | Docs                                                                     | Free tier                                                | Card?        | Verdict                                                 |
| --- | -------------------- | --------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------- | ------------ | ------------------------------------------------------- |
| 1   | **Z.ai (Zhipu GLM)** | https://z.ai/                                 | https://docs.z.ai/                                                       | GLM-4.7-Flash + 4.5-Flash **gratis permanent** + credite | NU           | [RECOMANDAT]                                            |
| 2   | **Alibaba Qwen**     | https://modelstudio.console.alibabacloud.com/ | https://www.alibabacloud.com/help/en/model-studio/first-api-call-to-qwen | 1M in + 1M out /90 zile per model, OpenAI-compat         | NU           | [RECOMANDAT]                                            |
| 3   | **Pollinations.AI**  | https://enter.pollinations.ai/                | https://github.com/pollinations/pollinations/blob/main/APIDOCS.md        | proxy GPT-5/Claude/Gemini **fără signup**                | NU           | [RECOMANDAT] ca fallback premium — [INCERT] stabilitate |
| 4   | **Together AI**      | https://api.together.ai/                      | https://docs.together.ai/docs/                                           | $1–25 credit, 200+ modele OS                             | NU la signup | [RELEVANT]                                              |
| 5   | **ApiFreeLLM**       | https://apifreellm.com/                       | https://www.apifreellm.com/docs                                          | „forever free"                                           | NU           | [INCERT] stabilitate                                    |

**Pentru credențialele pe care le ai deja** (secțiunea 2) — **nu trebuie să obții nimic**. Rulează `~/.api-keys/verify.ps1` ca să confirmi că sunt SET, apoi copiază-le în `.env` RIS.

---

## 4. PROCEDURA DE ADĂUGARE ÎN RIS (pas cu pas)

Pentru **fiecare** cheie nouă:

1. **Valoarea** — o iei din master (`API_KEYS.md`) sau din env var. **Nu o pui în chat, nu o comiți.**
2. **`.env` RIS** (root proiect) — adaugi `NUME_CHEIE=valoare`. Fișierul e gitignored.
   ⚠️ **Serviciul rulează ca SYSTEM** → citește `.env`, **nu** env var-ul tău. `.env` e sursa de adevăr pentru producție.
3. **`backend/config.py`** — declari câmpul: `nume_cheie: str = ""  # link_obtinere`
4. **Cablezi codul** — clientul care o folosește.
5. **Ping** — adaugi în `PING_REGISTRY` (`backend/agents/tools/connectivity.py`).
   🔴 **Ping-ul TREBUIE să apeleze calea REALĂ de producție**, nu o cerere simplificată. (Brave zicea „OK" testând un GET fără `country`, în timp ce producția murea cu 422 pe **fiecare** apel. Un ping care nu poate pica nu e dovadă, e zgomot.)
6. **Verificare** — `POST /api/settings/test/{service}` cu header `X-RIS-Key`. **Nu testa din shell** dacă cheia e printre cele divergente.
7. **Dashboard** — regenerezi `python tools/generate_audit_dashboard.py` + restart serviciu.
8. **Restart** — `tools\RIS-Backend.exe restart` (obligatoriu; serviciul nu recitește `.env` la cald).

---

## 5. FALLBACK — starea reală și ce lipsește

| Capabilitate         | Primar                  | Fallback existent              | Ce lipsește                                                                       |
| -------------------- | ----------------------- | ------------------------------ | --------------------------------------------------------------------------------- |
| **Sinteză AI**       | Groq                    | Gemini → Cerebras → Mistral    | 🔴 **Claude (nivelul 1 e MORT)**. Fallback real: 3 nivele, nu 5. Mistral pică azi |
| **Căutare web**      | Tavily (1000/lună)      | Brave (2000/lună, reparat azi) | Firecrawl ca al 3-lea + **Cohere rerank** peste ambele                            |
| **Date firmă**       | ANAF                    | openapi.ro (parțial)           | ONRC local (0 rânduri)                                                            |
| **Insolvență**       | BPI (DNS-dead)          | Tavily ✅                      | — funcționează prin fallback                                                      |
| **Litigii**          | Portal Just SOAP ✅     | —                              | fără fallback                                                                     |
| **OCR**              | Mistral                 | ❌ niciunul                    | Azure Doc Intel + Google Doc AI (ai ambele)                                       |
| **Traducere**        | ❌ niciuna              | —                              | DeepL + Azure Translator (ai ambele)                                              |
| **Reputație**        | Google Maps ✅          | web_presence                   | Brave (reparat)                                                                   |
| **Benchmark sector** | `CAEN_BENCHMARK` static | INS TEMPO (404)                | Eurostat ✅ · gol în **63%** din rapoarte                                         |

**Principiu de fallback pentru RIS:** fiecare capabilitate ar trebui să aibă **≥2 surse independente**, iar absența să fie **explicită** (INDISPONIBIL cu motiv), niciodată tăcută. Azi: OCR și traducere au **zero** fallback; sinteza are un nivel 1 mort.

---

## 6. VERIFICARE — comenzi utile

```powershell
# Ce chei sunt SET (nume + lungime, FĂRĂ valori)
powershell -File "$env:USERPROFILE\.api-keys\verify.ps1"

# Drift shell vs producție (4 chei diferă — cauza minciunii „Maps e mort")
python tools\check_env_drift.py        # ⬜ DE CONSTRUIT (Faza 4 din PLAN_ANTI_DERIVA)

# Ping live per sursă (rulează ÎN serviciu, cu cheile reale)
# POST /api/settings/test/{service}  cu header X-RIS-Key
```

**Nu rula niciodată** comenzi care afișează valori (`Get-ChildItem Env:`, `echo $env:X`, `grep` pe `.env` fără filtru pe câmp).
