# SPEC V2 — Roland Intelligence System (RIS)

> **Versiune:** 2.0 — Revizuire tehnica completa
> **Data:** 2026-03-20
> **Autor original:** Roland Petrila + Claude claude.ai
> **Revizuire:** Claude Code (Opus, Max effort)
> **Baza:** SPEC_INTELLIGENCE_SYSTEM.md v1.0 din 2026-03-19
> **Scop:** Specificatii complete, fezabile, implementabile — toate lacunele tehnice din V1 completate

---

## CHANGELOG V1 → V2

| # | Tip | Descriere |
|---|-----|-----------|
| 1 | CRITICA | Clarificare Claude Max vs Claude API — impact arhitectura |
| 2 | CRITICA | Realitatea API-urilor romanesti (ONRC, portal.just.ro, BPI) — ce merge si ce nu |
| 3 | NOU | LangGraph State Machine — schema completa cu stari si tranzitii |
| 4 | NOU | Structura completa de foldere si fisiere (tree) |
| 5 | NOU | Requirements.txt cu versiuni exacte |
| 6 | NOU | Package.json complet pentru frontend |
| 7 | NOU | Playwright Configuration Windows 10 |
| 8 | NOU | WebSocket Protocol — format mesaje, reconnect, events |
| 9 | NOU | Error Handling & Recovery Strategy per agent |
| 10 | NOU | Caching Strategy cu TTL per tip sursa |
| 11 | NOU | Prompt Templates per tip analiza pentru Synthesis Agent |
| 12 | NOU | Evaluare fezabilitate per TIP 1-9 |
| 13 | NOU | Riscuri tehnice identificate cu solutii |
| 14 | NOU | Estimare efort implementare per faza |
| 15 | COMPLETAT | Definitia nivelurilor de raport (1/2/3) — lipsea din V1 |
| 16 | CORECTAT | Ordinea agentilor: Agent 1 PRIMUL, apoi 2+3 paralel (dependenta CAEN) |
| 17 | COMPLETAT | SQLite — WAL mode, indexuri, connection strategy |
| 18 | COMPLETAT | Tavily quota management |

---

## CUPRINS

1. [Descrierea produsului si modelul de business](#1-descrierea-produsului-si-modelul-de-business)
2. [Arhitectura tehnica](#2-arhitectura-tehnica)
3. [Cei 5 agenti — responsabilitati exacte](#3-cei-5-agenti--responsabilitati-exacte)
4. [Tipurile de analiza predefinite](#4-tipurile-de-analiza-predefinite)
5. [Structura bazei de date si sistemul de memorie](#5-structura-bazei-de-date-si-sistemul-de-memorie)
6. [Sursele de date — liste complete si limite REALE](#6-sursele-de-date--liste-complete-si-limite-reale)
7. [Formatele de raport si livrarea](#7-formatele-de-raport-si-livrarea)
8. [Filtrarea calitatii datelor](#8-filtrarea-calitatii-datelor)
9. [Interfata utilizator](#9-interfata-utilizator)
10. [Ordinea de implementare (recalibrata)](#10-ordinea-de-implementare-recalibrata)
11. [Configurare si variabile de mediu](#11-configurare-si-variabile-de-mediu)
12. [Limitele etice si GDPR](#12-limitele-etice-si-gdpr)
13. [Structura proiect — tree complet](#13-structura-proiect--tree-complet) **[NOU]**
14. [Dependinte exacte — requirements.txt + package.json](#14-dependinte-exacte) **[NOU]**
15. [LangGraph State Machine — schema completa](#15-langgraph-state-machine--schema-completa) **[NOU]**
16. [WebSocket Protocol](#16-websocket-protocol) **[NOU]**
17. [Caching Strategy](#17-caching-strategy) **[NOU]**
18. [Error Handling & Recovery Strategy](#18-error-handling--recovery-strategy) **[NOU]**
19. [Playwright Configuration Windows 10](#19-playwright-configuration-windows-10) **[NOU]**
20. [Prompt Templates per tip analiza](#20-prompt-templates-per-tip-analiza) **[NOU]**
21. [Riscuri tehnice identificate](#21-riscuri-tehnice-identificate) **[NOU]**
22. [Estimare efort implementare](#22-estimare-efort-implementare) **[NOU]**
23. [Intrebari pentru Roland](#23-intrebari-pentru-roland) **[NOU]**
24. [Reguli globale aplicate](#24-reguli-globale-aplicate) **[NOU]**

---

## 1. Descrierea produsului si modelul de business

### Ce este RIS

Roland Intelligence System este un sistem local de Business Intelligence care ruleaza pe Windows 10. Operatorul (Roland) introduce o cerere de analiza, sistemul extrage automat date din surse publice verificate, le proceseaza prin agenti AI specializati si produce rapoarte profesionale in toate formatele necesare.

### Modelul de business

- **Operatorul:** Exclusiv Roland — sistemul nu e accesat de clienti
- **Clientii** primesc doar raportul final livrat de Roland (PDF/DOCX/HTML/etc.)
- **Servicii oferite:** Rapoarte punctuale la cerere + potential abonamente de monitorizare
- **Tariful** se stabileste printr-o functie de calcul bazata pe: tipul analizei, numarul de sectiuni, complexitate, date colectate de sistem din oferte similare de pe piata

### Principiul fundamental

> **Zero toleranta pentru date false.** Daca o informatie nu poate fi verificata dintr-o sursa oficiala sau verificabila, sistemul nu o include — si mentioneaza explicit ca informatia nu a fost gasita.

### Infrastructura

- **Ruleaza pe:** Windows 10 desktop (PC Roland)
- **Accesat prin:** Browser local sau Tailscale de pe Android
- **Volume:** ~10 rapoarte/luna initial
- **Scalabilitate:** Arhitectura permite migrare pe VPS cloud ulterior fara refactorizare majora

### **[V2] Nivelurile de raport — definitie clara**

Nivelurile de raport determina profunzimea analizei. V1 mentiona niveluri 1/2/3 fara a le defini:

| Aspect | Nivel 1 — Rapid | Nivel 2 — Standard | Nivel 3 — Complet |
|--------|-----------------|--------------------|--------------------|
| Surse accesate | Doar Nivel 1 (oficiale) | Nivel 1 + Nivel 2 | Nivel 1 + 2 + 3 |
| Agenti activi | Agent 1 + Agent 4 | Agent 1 + 2 + 4 | Toti (1+2+3+4) |
| Sectiuni raport | Doar blocurile esentiale | Blocuri standard | Toate blocurile + anexe |
| Synthesis depth | Sumar executiv (500-1000 cuvinte) | Analiza completa (2000-4000 cuvinte) | Analiza exhaustiva (4000-8000 cuvinte) |
| Grafice/tabele | 0-2 | 3-6 | 8-15 |
| Formate generate | PDF only | PDF + DOCX + HTML | Toate (PDF+DOCX+Excel+HTML+PPTX) |
| Timp estimat | 10-30 min | 30-120 min | 1-4 ore |
| Consum Tavily | 0 queries | 5-15 queries | 15-50 queries |
| Cost estimat API | ~$0.05-0.15 | ~$0.30-0.80 | ~$1.00-3.00 |

---

## 2. Arhitectura tehnica

### Stack principal

```
Backend:  Python 3.13 + FastAPI + SQLite (aiosqlite, WAL mode)
Frontend: React 18 + Vite + Tailwind CSS
Agenti:   LangGraph (orchestrare) + LangChain (tools)
AI:       Claude Code (Opus) — provider principal [Roland prezent, calitate maxima, $0]
          Gemini Flash API — fallback autonom pentru task-uri simple (gratuit)
          Cerebras API — fallback rapid autonom (1M tokeni/zi gratuit)
Scraping: Playwright (Chromium headless, Windows 10)
Search:   Tavily API (1.000 req/luna gratuit) — web search verificat cu surse
Export:   WeasyPrint (HTML→PDF) + python-docx (DOCX) + openpyxl (Excel) + Jinja2 (HTML)
Notif:    Telegram Bot API (gratuit, nelimitat)
```

**[V2] Modificare fata de V1:** `reportlab` inlocuit cu `WeasyPrint` pentru generare PDF.
- **De ce:** WeasyPrint converteste HTML→PDF, ceea ce inseamna ca template-ul Jinja2 folosit pentru HTML interactiv poate fi reutilizat (cu CSS print-specific) si pentru PDF. Un singur template = consistenta vizuala si efort de mentenanta redus.
- **Alternativa pastrata:** Daca WeasyPrint cauzeaza probleme pe Windows (depinde de GTK), fallback pe `fpdf2` (mai simplu decat reportlab, API modern).

### **[V2] Fluxul principal de executie — CORECTAT**

```
[INPUT utilizator]
       |
[Wizard / Chatbot / Dashboard]
       |
[Job Manager] --> creeaza job in SQLite, status: PENDING
       |
[Orchestrator LangGraph] --> porneste graful de executie
       |
[Agent 1 — Date Oficiale] --> RULEAZA PRIMUL (output necesar pt Agent 3)
       |
       +--> [PARALEL]
       |       |
       |    Agent 2 (Web Intelligence)
       |    Agent 3 (Market Research) -- primeste CAEN/dimensiune de la Agent 1
       |       |
       +-------+
       |
[Agent 4 — Verification] --> filtreaza, valideaza, rezolva contradictii
       |
[Synthesis Agent — Claude Code (Opus, Roland prezent)]  --> text narativ per sectiune
       |
[Report Generator] --> genereaza toate formatele
       |
[PDF + DOCX + Excel + HTML + PPTX]
       |
[Stocare in SQLite + notificare Telegram]
       |
[Dashboard — raport disponibil pentru descarcare]
```

**[V2] Corectare critica:** In V1, toti agentii (1,2,3) erau aratati in paralel. Dar Agent 3 (Market Research) depinde de output-ul Agent 1 (cod CAEN, dimensiune firma, regiune) pentru:
- Matching fonduri europene (eligibilitate)
- Identificare competitori (acelasi CAEN + zona)
- Filtrare licitatii SEAP (profil firma)

**Fluxul corect:** Agent 1 → apoi Agent 2 + Agent 3 in paralel → Agent 4 → Synthesis → Report.

### Principii arhitecturale

- **Izolare completa** fata de Command Center — proiect separat, port separat, DB separata
- **Async tot** — FastAPI async + aiosqlite + agenti async
- **Job queue in SQLite** — un tabel `jobs` cu status tracking + WebSocket progress in browser
- **Idempotenta** — daca un job crapa la mijloc, poate fi reluat de la ultimul checkpoint (vezi Sectiunea 18)
- **Config via `.env`** — nicio cheie API hardcodata in cod
- **[V2] Graceful degradation** — daca un agent esueaza, sistemul continua cu datele disponibile

---

## 3. Cei 5 agenti — responsabilitati exacte

> **[V2] Nota:** V1 mentiona "4 agenti" + Synthesis Agent separat = 5 componente. V2 le numeroteaza clar pe toate 5 pentru claritate in LangGraph.

### Agent 1 — Date Oficiale (`agent_official.py`)

**Responsabilitate:** Extrage date din registre si API-uri guvernamentale romanesti.

**Surse accesate si [V2] starea lor REALA:**

| Sursa | Metoda | Status real | Note |
|-------|--------|-------------|------|
| ANAF — date fiscale | REST API (`webservicesp.anaf.ro`) | FUNCTIONAL | API public documentat, rate limit 1 req/2 sec |
| ONRC — date firma | Playwright scraping (`recom.onrc.ro`) | PARTIAL | NU are API public. Serviciul SOAP necesita uneori certificat. Alternativa: scraping interfata web |
| SEAP/SICAP — licitatii | REST API (`sicap.anap.ro`) | FUNCTIONAL | API public, paginatie problematica la volume mari |
| BPI — insolvente | Playwright scraping (`bpi.ro`) | DIFICIL | Nu are API, CAPTCHA frecvent, rate limit agresiv |
| portal.just.ro — dosare | Playwright scraping | DIFICIL | CAPTCHA pe cautare, anti-bot activ |
| data.gov.ro | REST API | FUNCTIONAL | API public documentat |
| INS — statistici | Playwright/HTTP | PARTIAL | Interfata veche, date in format non-standard |
| BNR — cursuri | HTTP XML (`bnr.ro/nbrfxrates.xml`) | FUNCTIONAL | XML simplu, stabil |
| fonduri-ue.ro | Playwright | PARTIAL | Site dinamic, structura se schimba frecvent |
| mfe.gov.ro | Playwright | PARTIAL | Similar fonduri-ue.ro |

**[V2] Strategie pentru surse cu CAPTCHA:**
- **portal.just.ro:** Folosim Tavily search cu query `site:portal.just.ro "[nume firma]"` ca alternativa. Rezultate mai putin structurate dar fara CAPTCHA.
- **bpi.ro:** Similar — Tavily search `site:bpi.ro "[CUI]"`. Daca gaseste rezultate, le parseaza. Daca nu, marcheaza ca INDISPONIBIL.
- **ONRC:** Incercam recom.onrc.ro cu Playwright. Daca esueaza, fallback pe `listafirme.ro` (date publice agregate din ONRC).

**Output:** JSON structurat cu toate campurile disponibile + URL sursa + timestamp acces per camp.

**[V2] Error handling specific:**
```python
class OfficialAgentConfig:
    max_retries = 3
    retry_backoff = [2, 5, 15]  # secunde intre retry-uri
    timeout_per_source = 30      # secunde
    total_timeout = 300          # 5 minute pentru tot agentul
    on_source_fail = "mark_unavailable_and_continue"
```

**Rate limiting:** Maxim 1 request/2 secunde per domeniu guvernamental.

---

### Agent 2 — Web Intelligence (`agent_web.py`)

**Responsabilitate:** Extrage informatii din prezenta publica online a entitatii analizate.

**Ce extrage:**
- Site-ul oficial al firmei: descriere servicii, produse, preturi publice, contact, locatii
- Pagina de Facebook publica: numar urmaritori, frecventa postari, tip continut (via Tavily, nu scraping direct)
- LinkedIn Company Page (via Tavily search, nu scraping direct): angajati, industrie, dimensiune
- Google Maps: rating, numar recenzii, categorii, program, adrese multiple (via Tavily)
- Mentiuni in presa: articole din ultimele 12 luni (via Tavily search cu filtre de data)
- Anunturi de angajare publice (ejobs.ro, bestjobs.ro — via Tavily)

**Cum acceseaza:**
- **Playwright** pentru site-ul oficial al firmei (JavaScript rendering necesar)
- **Tavily API** pentru LinkedIn, presa, anunturi — returneaza date indexate public cu surse citate
- **HTTP direct** (httpx) pentru pagini simple fara JS

**NU acceseaza:**
- Nicio platforma care necesita autentificare
- Facebook prin scraping direct (bot detection avansat — risc ban IP)
- Date din spatele unui login (intranet, zone membre, etc.)

**[V2] Error handling specific:**
```python
class WebAgentConfig:
    max_retries = 2
    retry_backoff = [3, 10]
    timeout_playwright = 30       # per pagina
    timeout_tavily = 15           # per query
    total_timeout = 600           # 10 minute
    max_tavily_queries = 10       # per executie agent (quota management)
    on_source_fail = "mark_unavailable_and_continue"
```

**Rate limiting:** Maxim 1 request/3 secunde per domeniu. Playwright cu delay random 2-5 secunde intre actiuni.

---

### Agent 3 — Market Research (`agent_market.py`)

**Responsabilitate:** Cerceteaza piata, competitia, oportunitatile de business.

**[V2] Dependinte:** Primeste de la Agent 1: `cui`, `caen_code`, `caen_description`, `county`, `company_size`.

**Ce produce:**
- Lista competitorilor directi (acelasi CAEN + aceeasi zona geografica) cu profil sumar
- Licitatii active pe SEAP compatibile cu profilul firmei (filtrare automata)
- Fonduri europene aplicabile (matching pe criterii: marime firma, CAEN, regiune, tip investitie)
- Programe nationale active: PNRR, IMM Invest, Start-Up Nation, Saligny, granturi MIPE
- Tendinte de piata din publicatii de specialitate si rapoarte publice
- Clienti potentiali identificabili din contracte publice SEAP

**Sursele principale:**
- `sicap.anap.ro/web/pub/notice/list` — licitatii active (API public)
- `mfe.gov.ro` + `fonduri-ue.ro` — finantari europene
- Tavily API cu query-uri specializate per domeniu
- `insse.ro` — statistici INS publice per industrie

**Logica de matching fonduri:**
```
Pentru fiecare program de finantare activ:
  - Verifica eligibilitate: dimensiune firma (micro/mica/medie/mare)
  - Verifica eligibilitate: cod CAEN in lista eligibila a programului
  - Verifica eligibilitate: regiune de dezvoltare
  - Daca toate match --> include in raport cu scor de potrivire (%)
  - Daca partial match --> include cu nota de eligibilitate conditionata
```

**[V2] Error handling specific:**
```python
class MarketAgentConfig:
    max_retries = 2
    retry_backoff = [3, 10]
    timeout_seap = 30
    timeout_tavily = 15
    total_timeout = 900           # 15 minute (cautari extensive)
    max_tavily_queries = 15       # per executie
    max_competitors = 20          # limita competitori analizati
    on_source_fail = "mark_unavailable_and_continue"
```

---

### Agent 4 — Verification (`agent_verification.py`)

**Responsabilitate:** Filtrul de calitate al intregului sistem. Ultimul agent inainte de sinteza.

**Reguli stricte:**

**Regula 1 — Prioritatea surselor:**
```
Nivel 1 (AUTORITATE MAXIMA): .gov.ro, ANAF, ONRC, SEAP, BNR, portal.just.ro
Nivel 2 (VERIFICAT): Site oficial firma, LinkedIn public indexat, Google Maps
Nivel 3 (ESTIMAT): Presa online, mentiuni web, anunturi job
Nivel 4 (EXCLUS): Forumuri, opinii anonime, surse fara autor identificabil
```

**Regula 2 — Contradictii:**
```
Daca informatie din Nivel 1 != informatie din Nivel 2/3:
  --> Pastreaza EXCLUSIV informatia din Nivel 1
  --> Adauga nota: "Sursa secundara indica [X] — invalidata de date oficiale ANAF/ONRC"
```

**Regula 3 — Date lipsa:**
```
Daca informatie nu exista in nicio sursa disponibila:
  --> NU inventeaza, NU estimeaza fara baza
  --> Include: "Informatie indisponibila din surse publice verificabile la data [timestamp]"
```

**Regula 4 — Etichete de incredere:**
Fiecare camp din raport primeste o eticheta:
- `OFICIAL` — din sursa Nivel 1
- `VERIFICAT` — din sursa Nivel 2, consistent cu Nivel 1
- `ESTIMAT` — din sursa Nivel 3, mentionata explicit
- `NECONCLUDENT` — surse contradictorii, prezentat cu ambele variante si sursele lor
- `INDISPONIBIL` — nu exista date publice verificabile

**[V2] Regula 5 — Deduplicare:**
```
Daca aceeasi informatie vine din surse multiple:
  --> Pastreaza sursa cu Nivelul cel mai inalt
  --> Mentioneaza "Confirmat si de: [sursa 2], [sursa 3]"
  --> Creste implicit trust-ul (cross-validation)
```

---

### Agent 5 — Synthesis (`agent_synthesis.py`)

> **[V2] Renumerotat:** In V1 era "Synthesis Agent" fara numar. Acum e Agent 5 pentru claritate in LangGraph.
> **[V2-DECIZIE]** Synthesis-ul ruleaza prin Claude Code (Opus) cu Roland prezent. Calitate maxima, $0 cost.

**Model principal:** Claude Code (Opus) — Roland prezent la executie
**Fallback autonom (fara Roland):** `gemini-2.0-flash` (gratuit) → `cerebras/llama-3.3-70b` (gratuit)

**Responsabilitate:** Primeste JSON structurat verificat de Agent 4 si produce text narativ coerent per sectiune de raport.

**Modul de operare:**
1. Agentii 1-4 ruleaza automat si produc `verified_data.json`
2. Sistemul pregateste un **prompt structurat** per sectiune cu datele verificate
3. **Modul Claude Code (default):** Prompt-ul e prezentat in terminal → Claude Code genereaza textul → salvat automat in raport
4. **Modul autonom (fallback):** Daca Roland nu e prezent, sistemul poate rula autonom cu Gemini Flash/Cerebras (calitate mai scazuta)

**System prompt:**
```
Esti un analist de business senior specializat in analiza firmelor romanesti.
Primesti date structurate colectate si verificate din surse publice oficiale.
Scrii analize clare, precise, fara jargon inutil, intelese de oricine.
REGULI STRICTE:
- Nu adaugi nicio informatie care nu exista in datele primite
- Mentionezi explicit sursa pentru fiecare afirmatie importanta
- Daca o sectiune are date insuficiente, spui explicit ca datele sunt limitate
- Scrii in romana, ton profesional dar accesibil
- Nu faci predictii fara baza de date concreta
- Pastreaza etichetele de incredere (OFICIAL/VERIFICAT/ESTIMAT) in text
```

**[V2] Synthesis mode selection:**
```python
class SynthesisConfig:
    mode: str = "claude_code"     # "claude_code" | "autonomous"
    # Claude Code mode: pregateste prompt, asteapta output de la Claude Code
    # Autonomous mode: apeleaza Gemini/Cerebras API direct
    autonomous_fallback_chain = ["gemini-2.0-flash", "llama-3.3-70b"]
    timeout_per_section = 120     # secunde (mai lung pt Claude Code interaction)
    max_tokens_per_section = 4000
```

---

## 4. Tipurile de analiza predefinite

Sistemul are un catalog de tipuri de analiza predefinite. La selectarea unui tip, sistemul pune automat intrebari specifice inainte de a porni. Fiecare tip e adaptabil la orice firma sau domeniu.

---

### TIP 1 — Profil Complet Firma (`FULL_COMPANY_PROFILE`)

**Descriere:** Analiza exhaustiva a unei firme specifice — tot ce e disponibil public.
**Timp estimat:** Nivel 1: 15-30 min | Nivel 2: 1-2 ore | Nivel 3: 2-4 ore
**Intrebari automate:**
1. CUI sau denumire exacta a firmei?
2. Judetul/localitatea sediului? (pentru contextualizare locala)
3. Care este scopul analizei? (due diligence / parteneriat / concurenta / altul)
4. Exista aspecte specifice de investigat prioritar? (ex: situatie financiara, litigii, asociati)
5. Perioada de interes pentru date financiare? (ultimii 3 ani / 5 ani / alt interval)

**Sectiuni generate:** Toate 10 blocurile din raportul standard.

**[V2] Evaluare fezabilitate: 85%**
- Date oficiale (ANAF, SEAP): COMPLET automatizabil
- Date ONRC: PARTIAL — depinde de accesibilitatea recom.onrc.ro la momentul executiei
- Litigii (portal.just.ro): DIFICIL — CAPTCHA, fallback pe Tavily
- Web intelligence: BUN — Playwright + Tavily acopera majoritate
- **Limitare principala:** Datele financiare detaliate (bilant, cont profit/pierdere) nu sunt publice gratuit. ANAF ofera doar status TVA si datorii, nu cifra de afaceri. Pentru date financiare detaliate: Tavily search pe listafirme.ro sau topfirme.com (date publice agregate).

---

### TIP 2 — Analiza Competitie (`COMPETITION_ANALYSIS`)

**Descriere:** Identifica si analizeaza toti competitorii directi dintr-un domeniu si zona geografica.
**Timp estimat:** 1-3 ore (depinde de numarul competitorilor gasiti)
**Intrebari automate:**
1. Firma client sau domeniul de activitate? (CUI sau descriere)
2. Zona geografica de interes? (judet / regiune / national)
3. Cat de larg definim "competitor direct"? (acelasi CAEN exact / CAEN similar / intreaga industrie)
4. Ce aspect al competitiei intereseaza mai mult? (preturi / servicii / dimensiune / online)
5. Exista firme specifice pe care le stii deja si vrei incluse obligatoriu?

**Sectiuni generate:** Bloc 1 (sumar) + Bloc 4 (competitie extinsa) + Bloc 8 (SWOT comparativ) + Bloc 9 (recomandari).

**[V2] Evaluare fezabilitate: 70%**
- Identificarea competitorilor pe CAEN+zona: BUN via SEAP contracte + Tavily
- Profil sumar per competitor: MEDIU — depinde de prezenta online a fiecaruia
- Date financiare comparative: LIMITAT — aceleasi limitari ca TIP 1
- **Limitare principala:** Calitatea depinde de cati competitori au prezenta online. Firme mici fara site/social media vor avea profil minimal.

---

### TIP 3 — Evaluare Risc Partener (`PARTNER_RISK_ASSESSMENT`)

**Descriere:** Verificare rapida inainte de a semna un contract sau a intra intr-un parteneriat.
**Timp estimat:** 15-45 minute
**Intrebari automate:**
1. CUI sau denumirea firmei de verificat?
2. Tipul parteneriatului planificat? (furnizor / client / asociat / joint-venture)
3. Valoarea estimata a contractului sau parteneriatului? (RON)
4. Exista ingrijorari specifice pe care le ai deja?
5. Termenul de decizie? (urgent sub 24h / normal 2-3 zile)

**Sectiuni generate:** Bloc 1 (date firma) + Bloc 2 (financiar) + Bloc 5 (litigii/risc) + scor risc final (Verde/Galben/Rosu) + recomandare clara DA/NU/CONDITIONAT.

**[V2] Evaluare fezabilitate: 80%**
- Cel mai simplu tip — focus pe date oficiale
- ANAF datorii: DA | ONRC date firma: PARTIAL | BPI insolventa: VIA TAVILY | Litigii: VIA TAVILY
- **Puncte forte:** Rapid, surse oficiale mostly, scor de risc calculabil algoritmic
- **Limitare:** Fara date financiare detaliate, riscul financiar e evaluat indirect (datorii ANAF + insolventa)

---

### TIP 4 — Oportunitati Licitatii & Contracte (`TENDER_OPPORTUNITIES`)

**Descriere:** Gaseste licitatii publice active si contracte castigabile pentru profilul dat.
**Timp estimat:** 30-60 minute
**Intrebari automate:**
1. CUI sau profilul firmei care cauta oportunitati?
2. Tipul de servicii/produse oferite? (cod CAEN + descriere libera)
3. Zona geografica preferata pentru contracte? (local / regional / national)
4. Valoarea minima si maxima a contractelor de interes? (RON)
5. Exista experienta anterioara cu licitatii publice? (DA/NU)
6. Termen de livrare maxim acceptat?

**Sectiuni generate:** Bloc 6 (oportunitati) extins + track record SEAP al firmei + recomandari de pozitionare.

**[V2] Evaluare fezabilitate: 75%**
- SEAP API functional pentru licitatii active
- Matching pe CPV codes (SEAP) vs CAEN codes (firma) necesita tabel de mapare
- **Limitare:** Paginatia SEAP API e problematica la volume mari. Filtram doar ultimele 100 licitatii active relevante.

---

### TIP 5 — Fonduri & Finantari Disponibile (`FUNDING_OPPORTUNITIES`)

**Descriere:** Identifica toate programele de finantare europene si nationale aplicabile.
**Timp estimat:** 45-90 minute
**Intrebari automate:**
1. CUI sau profilul firmei?
2. Tipul de investitie planificata? (echipamente / digitalizare / angajari / export / cercetare / altul)
3. Suma necesara de finantat? (RON)
4. Firma are datorii la ANAF? (DA/NU)
5. Numarul actual de angajati? (micro <10 / mica <50 / medie <250 / mare)
6. Regiunea de dezvoltare?

**Sectiuni generate:** Bloc 7 extins + tabel comparativ programe.

**[V2] Evaluare fezabilitate: 60%**
- Identificarea programelor active: BUN via mfe.gov.ro + fonduri-ue.ro
- Verificarea eligibilitatii automate: PARTIAL — criteriile de eligibilitate sunt in PDF-uri/pagini complexe, greu de parsat automat
- **Limitare principala:** Eligibilitatea reala necesita verificare manuala. Sistemul poate identifica programe POTENTIAL aplicabile, dar nu poate garanta eligibilitatea. Trebuie marcat clar ca ESTIMAT.
- **Solutie:** Mentioneaza un tabel cu link-uri directe catre ghidurile oficiale pentru verificare manuala

---

### TIP 6 — Analiza Intrare pe Piata (`MARKET_ENTRY_ANALYSIS`)

**Descriere:** Analiza completa pentru o firma care vrea sa intre pe o piata noua.
**Timp estimat:** 2-4 ore
**Intrebari automate:**
1. Descrierea afacerii client (CUI daca exista sau profil nou)?
2. Piata/domeniul tinta? (descriere + cod CAEN estimat)
3. Zona geografica de intrare? (judet / regiune / national)
4. Care e avantajul competitiv? (pret / calitate / nisa / inovatie)
5. Buget estimat pentru intrarea pe piata?
6. Exista restrictii legale sau de licentiere cunoscute?

**Sectiuni generate:** Bloc 4 (competitie detaliata) + Bloc 6 (oportunitati) + Bloc 7 (fonduri) + Bloc 8 (SWOT piata) + Bloc 9 (strategie intrare).

**[V2] Evaluare fezabilitate: 65%**
- Dependent de calitatea datelor de piata disponibile
- **Limitare:** Analiza de piata calitativa (tendinte, bariere intrare) depinde mult de AI interpretation. Datele cantitative sunt limitate la ce ofera INS si SEAP.

---

### TIP 7 — Prospectare Clienti Potentiali (`LEAD_GENERATION`)

**Descriere:** Identifica firme din domeniul X, zona Y, care ar putea deveni clienti.
**Timp estimat:** 1-2 ore
**Intrebari automate:**
1. Profilul firmei care cauta clienti? (CUI sau descriere servicii oferite)
2. Profilul clientului ideal? (industrie, dimensiune, zona geografica)
3. Criteriu de prioritizare? (firme in crestere / firme cu licitatii active / firme cu probleme cunoscute)
4. Cate firme tinta sa identifice? (10 / 25 / 50 / cat gaseste)
5. Ce informatii de contact sa includa? (date publice ONRC)

**Sectiuni generate:** Lista firme cu profil sumar + date contact publice + scor de potrivire estimat + recomandare de abordare per firma.

**[V2] Evaluare fezabilitate: 55%**
- Identificarea firmelor pe CAEN+zona: MEDIU via Tavily + SEAP
- Date de contact: LIMITAT — ONRC are doar sediu social, nu email/telefon intotdeauna
- **Limitare principala:** "Lead scoring" e in mare parte AI-driven, nu data-driven. Calitatea depinde de cat de bine Tavily gaseste informatii despre firmele tinta.

---

### TIP 8 — Monitorizare Periodica (`MONITORING_SETUP`)

**Descriere:** Configureaza monitorizarea continua pentru o firma sau un domeniu.
**Status:** DEFERRED — implementat in Faza 5

---

### TIP 9 — Raport Personalizat (`CUSTOM_REPORT`)

**Descriere:** Orice combinatie de sectiuni, orice cerere care nu se incadreaza in tipurile de mai sus.
**Timp estimat:** Variabil
**Cum functioneaza:** Sistemul pune intrebari deschise, extrage structura cererii, propune un plan de sectiuni cu estimare de timp, utilizatorul confirma sau modifica, apoi porneste analiza.

**[V2] Evaluare fezabilitate: 70%**
- Depinde complet de cerere. Flexibilitatea e un avantaj dar si un risc — cereri foarte specifice pot avea surse insuficiente.

---

## 5. Structura bazei de date si sistemul de memorie

### Filozofia de memorare

Sistemul construieste in timp o **baza de date proprie cu cunostinte** despre firmele si pietele analizate. La fiecare noua analiza pe o entitate existenta, sistemul:
1. Incarca automat raportul anterior
2. Identifica ce s-a schimbat fata de ultima analiza
3. Marcheaza schimbarile ca `MODIFICAT_DIN [data]`
4. Prezinta un "delta report" inainte de raportul complet

### **[V2] Tabelele SQLite — completate cu indexuri si WAL mode**

```sql
-- PRAGMA obligatorii la connect
PRAGMA journal_mode=WAL;          -- Write-Ahead Logging — permite citiri concurente cu scrieri
PRAGMA busy_timeout=5000;         -- Asteapta 5 sec la lock inainte de eroare
PRAGMA foreign_keys=ON;           -- Enforceaza referential integrity
PRAGMA cache_size=-20000;         -- 20MB cache in memorie

-- Joburi de analiza
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,           -- UUID
    type TEXT NOT NULL,            -- TIP 1-9
    status TEXT NOT NULL,          -- PENDING/RUNNING/PAUSED/DONE/FAILED
    input_data TEXT,               -- JSON cu parametrii cererii
    report_level INTEGER,          -- 1/2/3
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    progress_percent INTEGER DEFAULT 0,
    current_step TEXT,             -- descriere pas curent
    checkpoint_data TEXT           -- [V2] JSON cu starea pentru recovery
);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created ON jobs(created_at DESC);

-- Companii analizate
CREATE TABLE companies (
    id TEXT PRIMARY KEY,           -- UUID intern
    cui TEXT UNIQUE,               -- CUI Romania
    name TEXT NOT NULL,
    caen_code TEXT,
    caen_description TEXT,
    county TEXT,
    city TEXT,
    first_analyzed_at DATETIME,
    last_analyzed_at DATETIME,
    analysis_count INTEGER DEFAULT 0
);
CREATE INDEX idx_companies_cui ON companies(cui);
CREATE INDEX idx_companies_caen ON companies(caen_code);
CREATE INDEX idx_companies_county ON companies(county);

-- Rapoarte generate
CREATE TABLE reports (
    id TEXT PRIMARY KEY,           -- UUID
    job_id TEXT REFERENCES jobs(id),
    company_id TEXT REFERENCES companies(id),  -- NULL pentru analize de piata
    report_type TEXT,              -- TIP 1-9
    report_level INTEGER,          -- 1/2/3
    title TEXT,
    summary TEXT,                  -- rezumat executiv (text scurt)
    full_data TEXT,                -- JSON complet cu toate datele colectate
    risk_score TEXT,               -- Verde/Galben/Rosu (unde aplicabil)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    pdf_path TEXT,
    docx_path TEXT,
    excel_path TEXT,
    html_path TEXT,
    pptx_path TEXT
);
CREATE INDEX idx_reports_company ON reports(company_id);
CREATE INDEX idx_reports_type ON reports(report_type);
CREATE INDEX idx_reports_created ON reports(created_at DESC);

-- Surse de date accesate per raport
CREATE TABLE report_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT REFERENCES reports(id),
    source_name TEXT,              -- ex: "ANAF", "ONRC", "Tavily"
    source_url TEXT,
    accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT,                   -- OK/TIMEOUT/BLOCKED/ERROR/CAPTCHA
    data_found BOOLEAN,
    response_time_ms INTEGER       -- [V2] pentru monitorizare performanta
);
CREATE INDEX idx_sources_report ON report_sources(report_id);

-- Piete si domenii analizate (pentru TIP 2, 6, 7)
CREATE TABLE markets (
    id TEXT PRIMARY KEY,
    caen_code TEXT,
    description TEXT,
    county TEXT,
    last_analyzed_at DATETIME,
    competitor_count INTEGER,
    analysis_count INTEGER DEFAULT 0
);

-- Alerte configurate (pentru monitorizare — Faza 5)
CREATE TABLE monitoring_alerts (
    id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES companies(id),
    alert_type TEXT,               -- INSOLVENCY/TENDER/FUNDING/COMPETITOR_CONTRACT
    is_active BOOLEAN DEFAULT TRUE,
    check_frequency TEXT,          -- DAILY/WEEKLY
    last_checked_at DATETIME,
    telegram_notify BOOLEAN DEFAULT TRUE
);

-- Istoricul compararilor (delta intre rapoarte)
CREATE TABLE report_deltas (
    id TEXT PRIMARY KEY,
    report_id_new TEXT REFERENCES reports(id),
    report_id_old TEXT REFERENCES reports(id),
    delta_summary TEXT,            -- JSON cu campurile schimbate
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Cache pentru date frecvent accesate
CREATE TABLE data_cache (
    cache_key TEXT PRIMARY KEY,    -- ex: "anaf_cui_12345678"
    data TEXT,                     -- JSON
    source TEXT,
    cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME
);
CREATE INDEX idx_cache_expires ON data_cache(expires_at);
```

### **[V2] SQLite Connection Strategy**

```python
# O singura conexiune aiosqlite cu WAL mode
# NU folosim connection pool — aiosqlite gestioneaza intern
# WAL permite citiri concurente cu o singura scriere

import aiosqlite

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA busy_timeout=5000")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.execute("PRAGMA cache_size=-20000")
        self._db.row_factory = aiosqlite.Row

    async def close(self):
        if self._db:
            await self._db.close()
```

### Scenariile de utilizare a memoriei

**Scenariu 1 — Re-analiza firma existenta:**
```
Utilizator: "Analizeaza din nou Mosslein SRL"
Sistem: "Am un raport anterior din [data]. Fac analiza noua completa
         sau vrei doar ce s-a schimbat fata de ultimul raport?"
```

**Scenariu 2 — Cautare in istoricul propriu:**
```
Utilizator: "Arata-mi toate firmele din constructii analizate in Arad"
Sistem: returneaza lista din tabelul companies filtrat dupa county + caen
```

**Scenariu 3 — Pattern recognition:**
```
La Tip 7 (Lead Generation): sistemul poate compara noul target cu
firmele deja in baza de date proprie pentru a identifica similaritati
```

---

## 6. Sursele de date — liste complete si limite REALE

### **[V2] Surse oficiale romanesti — cu STATUS REAL**

| Sursa | URL | Metoda | Status | Limitari reale |
|-------|-----|--------|--------|----------------|
| ANAF — date fiscale | `webservicesp.anaf.ro` | REST API | FUNCTIONAL | Doar TVA, datorii, sediu fiscal. NU ofera cifra afaceri/bilant |
| ONRC — date firma | `recom.onrc.ro` | SOAP/Playwright | INSTABIL | Nu are API public stabil. Necesita scraping, uneori CAPTCHA |
| SEAP/SICAP | `sicap.anap.ro` | REST API | FUNCTIONAL | Paginatie max 100 rezultate. API documentat partial |
| BPI — insolvente | `bpi.ro` | Playwright/Tavily | DIFICIL | CAPTCHA frecvent. Tavily ca fallback |
| portal.just.ro | `portal.just.ro` | Playwright/Tavily | DIFICIL | CAPTCHA, anti-bot. Tavily search ca fallback |
| data.gov.ro | `data.gov.ro/api` | REST API | FUNCTIONAL | Date vechi uneori, nu toate seturile sunt actualizate |
| INS | `insse.ro` | Playwright/HTTP | PARTIAL | Interfata veche, date in formate variate |
| BNR | `bnr.ro/nbrfxrates.xml` | HTTP XML | FUNCTIONAL | Stabil, date zilnice |
| fonduri-ue.ro | `fonduri-ue.ro` | Playwright | PARTIAL | Structura se schimba, necesita mentenanta scraper |
| mfe.gov.ro | `mfe.gov.ro` | Playwright | PARTIAL | Similar fonduri-ue.ro |

### **[V2] Surse alternative pentru date financiare (IMPORTANT)**

ANAF API-ul public NU ofera date financiare detaliate (cifra de afaceri, profit, bilant). Aceste date sunt publice dar disponibile doar prin:

| Sursa alternativa | Metoda | Ce ofera | Fiabilitate |
|-------------------|--------|----------|-------------|
| listafirme.ro | Tavily search / Playwright | Cifra afaceri, profit, angajati, istoric | BUNA — date agregate din ONRC/MF |
| topfirme.com | Tavily search | Ranking, cifra afaceri, profit | BUNA |
| risco.ro | Tavily search | Profil firmei, date financiare sumare | MEDIE |

**Nota:** Aceste surse agrega date publice din Ministerul Finantelor. Sunt Nivel 2 (VERIFICAT), nu Nivel 1.

### Surse web publice (Nivel 2)

| Sursa | Metoda de acces | Ce extrage |
|-------|-----------------|------------|
| Site-ul oficial al firmei | Playwright | Servicii, preturi publice, contact, locatii |
| Google Maps / Business | Tavily search | Rating, recenzii, program, adresa |
| LinkedIn Company | Tavily search | Angajati estimati, industrie, descriere |
| Pagini Facebook publice | Tavily search | Urmaritori, activitate recenta |
| Anunturi job (ejobs, bestjobs) | Tavily search | Roluri disponibile, crestere echipa |

### Surse presa si web (Nivel 3)

- Tavily search cu filtre: site:ziare.com, site:digi24.ro, site:economica.net etc.
- Google News indexat (via Tavily)
- Publicatii de specialitate indexate public

### Ce NU acceseaza sistemul (NICIODATA)

- Platforme cu paywall sau login obligatoriu
- Baze de date private (ex: Termene.ro fara API key, Dosar.ro cu abonament)
- Retele sociale prin scraping direct (bot detection — risc ban IP)
- Orice date cu caracter personal ale persoanelor fizice in afara celor din registre publice
- Dark web sau surse anonime neverificabile

---

## 7. Formatele de raport si livrarea

### Formatele generate automat

**PDF Profesional** (`WeasyPrint` — HTML→PDF conversion)
- Template Jinja2 partajat cu versiunea HTML (un singur template, 2 output-uri)
- Antet cu logo placeholder + data generarii + versiunea
- Cuprins automat
- Grafice incorporate (matplotlib → SVG inline)
- Footer cu disclaimer
- CSS print-specific pentru page breaks, headers, footers
- Watermark configurabil (CONFIDENTIAL / DRAFT / FINAL)

**DOCX Editabil** (`python-docx` + template Jinja2)
- Stiluri Word definite (Heading 1/2/3, Normal, Tabel, Caption)
- Tabele native Word (editabile de client)
- Imagini grafice incorporate
- Track Changes dezactivat implicit

**Excel cu Date Brute** (`openpyxl`)
- Sheet 1: Rezumat executiv (date cheie)
- Sheet 2: Date financiare multi-an (grafice native Excel)
- Sheet 3: Lista competitori cu toate campurile
- Sheet 4: Licitatii/contracte identificate
- Sheet 5: Fonduri disponibile cu eligibilitate
- Sheet 6: Surse accesate (audit trail complet)

**HTML Interactiv** (`Jinja2` + `Chart.js` inline)
- Pagina web single-file (tot inclus — CSS + JS + date)
- Grafice interactive (hover, zoom, filtrare)
- Tabel competitori sortabil/filtrabil
- Harta geografica competitie (`Leaflet.js` cu OpenStreetMap — gratuit)

**PowerPoint** (`python-pptx`)
- 9 slide-uri standard (vezi V1 pentru detalii)
- Template: design profesional (albastru corporate / alb)

### Sistemul de livrare

1. **Local:** Toate fisierele salvate in `outputs/[job_id]/` pe PC
2. **Dashboard:** Buton de download per format disponibil imediat in interfata
3. **Email:** Trimitere automata via Gmail SMTP cu PDF + link HTML
4. **Telegram:** Notificare automata la finalizare

---

## 8. Filtrarea calitatii datelor

### Sistemul de etichete

```python
TRUST_LEVELS = {
    "OFICIAL": {
        "icon": "check_circle",   # Material icon — fara emoji in cod
        "color": "#00AA00",
        "description": "Sursa oficiala guvernamentala verificata"
    },
    "VERIFICAT": {
        "icon": "verified",
        "color": "#0066CC",
        "description": "Sursa publica verificabila, consistenta cu datele oficiale"
    },
    "ESTIMAT": {
        "icon": "help_outline",
        "color": "#FF8800",
        "description": "Sursa terta, mentionata explicit — necesita verificare suplimentara"
    },
    "NECONCLUDENT": {
        "icon": "warning",
        "color": "#CC0000",
        "description": "Surse contradictorii — prezentate ambele variante"
    },
    "INDISPONIBIL": {
        "icon": "block",
        "color": "#888888",
        "description": "Informatie indisponibila din surse publice la data analizei"
    }
}
```

### Regula de aur

```python
def resolve_contradiction(official_data, secondary_data, field_name):
    if official_data != secondary_data:
        return {
            "value": official_data,
            "trust": "OFICIAL",
            "note": f"Sursa secundara indica '{secondary_data}' — invalidata de date oficiale",
            "source": "ANAF/ONRC"
        }
    return {"value": official_data, "trust": "OFICIAL"}
```

### Disclaimer obligatoriu in fiecare raport

> "Acest raport a fost generat automat la data [timestamp] folosind exclusiv date disponibile public din surse verificabile. Acuratetea datelor depinde de corectitudinea informatiilor din registrele publice accesate. Datele marcate ca NECONCLUDENT sau INDISPONIBIL necesita verificare manuala suplimentara inainte de utilizare in decizii juridice sau financiare majore. Roland Intelligence System nu isi asuma responsabilitatea pentru decizii bazate exclusiv pe acest raport fara verificare independenta."

---

## 9. Interfata utilizator

### Cele 3 moduri de interactiune

**Modul 1 — Wizard (recomandat)**
- Pas 1: Selectezi tipul de analiza (TIP 1-9) din lista cu descrieri
- Pas 2: Sistemul pune automat intrebarile specifice (3-6 intrebari)
- Pas 3: Selectezi nivelul raportului (1/2/3) cu estimare de timp si cost
- Pas 4: Confirmi si pornesti analiza
- Pas 5: Progress bar in timp real + log al pasilor executati
- Pas 6: Raport disponibil — butoane de download per format

**Modul 2 — Chatbot natural**
- Camp text liber: "Analizeaza firma Mosslein SRL din Nadlac, CUI 12345678"
- AI parseaza cererea, identifica tipul de analiza, pune intrebarile lipsa
- Trece automat in fluxul Wizard de la Pas 3

**Modul 3 — Dashboard rapid**
- Butoane directe per tip de analiza
- Form pre-completat cu ultimele valori folosite

### Paginile aplicatiei

```
/ (Dashboard)           -> Statistici generale, ultimele rapoarte, joburi active
/new-analysis           -> Wizard / Chatbot / Dashboard rapid
/analysis/:id           -> Progresul unui job activ (WebSocket real-time)
/report/:id             -> Vizualizarea completa a unui raport
/reports                -> Lista tuturor rapoartelor (cautabile, filtrabile)
/companies              -> Baza de date proprie cu firmele analizate
/settings               -> Configurare API keys, template-uri, preferinte
```

### Componentele UI cheie

- **JobProgressCard:** WebSocket real-time, step curent, procent, ETA
- **ReportViewer:** Tabs per sectiune, grafice interactive, toggle etichete de incredere
- **CompanyCard:** Mini-profil firma cu history de analize
- **AnalysisTypeSelector:** Grid cu cards per tip de analiza, iconita + descriere + timp estimat
- **SourceAuditPanel:** Expandabil in fiecare raport — lista completa a surselor accesate

---

## 10. Ordinea de implementare (recalibrata)

### Faza 1 — Fundatie (prioritate maxima)

| # | Task | Descriere | Efort relativ |
|---|------|-----------|---------------|
| 1 | Structura proiect | `backend/` + `frontend/` + `.env` + config | Mic |
| 2 | FastAPI app | CORS + WebSocket + health check + lifespan | Mic |
| 3 | SQLite setup | Toate tabelele + PRAGMA + migrare | Mic |
| 4 | React app | Vite + Tailwind + React Router + layout | Mic |
| 5 | Pagini de baza | Dashboard + New Analysis + Reports list (skeleton) | Mediu |
| 6 | Job system | Creare job + tracking status + WebSocket progress | Mediu |

**Criteriu de completare Faza 1:** Pot crea un job din UI, il vad in dashboard cu status PENDING, WebSocket trimite progres simulat.

### Faza 2 — Agentii de date

| # | Task | Descriere | Efort relativ |
|---|------|-----------|---------------|
| 7 | Agent 1 (Oficial) | ANAF API + ONRC scraping + SEAP | Mare |
| 8 | Agent 4 (Verification) | Logica filtrare + etichete trust | Mediu |
| 9 | Test TIP 3 | Job complet cu Risc Partener — cel mai simplu | Mic |
| 10 | Agent 2 (Web) | Playwright setup + Tavily integration | Mare |
| 11 | Agent 3 (Market) | SEAP licitatii + fonduri + competitori | Mare |
| 12 | LangGraph orchestrare | State machine + parallelism + checkpoints | Mediu |

**Criteriu de completare Faza 2:** TIP 3 (Risc Partener) produce JSON cu date reale de la ANAF + verificare.

### Faza 3 — Sinteza si rapoartele

| # | Task | Descriere | Efort relativ |
|---|------|-----------|---------------|
| 13 | Synthesis Agent | Claude Code integration + prompt engineering | Mediu |
| 14 | Report Generator | PDF (WeasyPrint) + DOCX (python-docx) | Mediu |
| 15 | Test TIP 1 Nivel 2 | Job complet Profil Firma cu raport generat | Mic |
| 16 | Excel + HTML generators | openpyxl + Jinja2 + Chart.js | Mediu |

**Criteriu de completare Faza 3:** TIP 1 Nivel 2 produce raport PDF + DOCX + HTML cu date reale.

### Faza 4 — UI complet si livrare

| # | Task | Descriere | Efort relativ |
|---|------|-----------|---------------|
| 17 | Wizard complet | Toate tipurile TIP 1-7 + 9 cu intrebari | Mediu |
| 18 | Chatbot parser | Parser cereri in limba naturala | Mediu |
| 19 | PPTX generator | python-pptx cu template profesional | Mic |
| 20 | Email delivery | Gmail SMTP integration | Mic |
| 21 | Telegram notifications | Bot API integration | Mic |

**Criteriu de completare Faza 4:** Toate TIP-urile functioneaza din UI, rapoarte livrate in toate formatele.

### Faza 5 — Memorie si optimizare

| # | Task | Descriere | Efort relativ |
|---|------|-----------|---------------|
| 22 | Delta reports | Comparare raport nou vs vechi | Mediu |
| 23 | Company database UI | Search + filtrare + CompanyCard | Mic |
| 24 | Caching layer | TTL per sursa + cache invalidation | Mic |
| 25 | Pricing intelligence | Colectare automat preturi piata | Mediu |
| 26 | Monitoring (TIP 8) | Cron jobs + alerte Telegram | Mare |

---

## 11. Configurare si variabile de mediu

```env
# AI Providers
# ANTHROPIC_API_KEY=         # NU e necesar — Synthesis ruleaza prin Claude Code (Roland prezent)
GOOGLE_AI_API_KEY=           # Gemini Flash (fallback autonom, gratuit)
CEREBRAS_API_KEY=            # Cerebras (fallback autonom, gratuit, 1M tokeni/zi)
SYNTHESIS_MODE=claude_code   # "claude_code" (default) | "autonomous" (Gemini/Cerebras)

# Web Search
TAVILY_API_KEY=              # Search verificat cu surse (1000 req/luna gratuit)

# Notificari
TELEGRAM_BOT_TOKEN=          # Bot token de la @BotFather
TELEGRAM_CHAT_ID=            # Chat ID personal Roland

# Email
GMAIL_USER=                  # adresa gmail
GMAIL_APP_PASSWORD=          # App Password Gmail (nu parola contului!)

# Aplicatie
APP_SECRET_KEY=              # cheie pentru sesiuni (generat random la setup)
DATABASE_PATH=./data/ris.db  # calea catre SQLite
OUTPUTS_DIR=./outputs/       # folderul cu rapoartele generate
LOG_LEVEL=INFO
BACKEND_PORT=8001            # [V2] port explicit (evita conflict cu alte servicii)
FRONTEND_PORT=5173           # [V2] port Vite default

# Rate limiting
MAX_CONCURRENT_JOBS=2        # maxim 2 joburi simultan pe PC local
REQUEST_DELAY_GOV=2          # secunde intre cereri pe .gov.ro
REQUEST_DELAY_WEB=3          # secunde intre cereri Playwright

# [V2] Tavily quota
TAVILY_MONTHLY_QUOTA=1000    # quota lunara
TAVILY_WARN_AT=800           # avertizare la 80% consum
```

---

## 12. Limitele etice si GDPR

### Ce face sistemul

- Acceseaza EXCLUSIV date disponibile public fara autentificare
- Citeaza sursa pentru fiecare informatie inclusa in raport
- Respecta `robots.txt` al siturilor accesate via Playwright
- Adauga delay intre cereri pentru a nu supraincarca serverele

### Ce NU face sistemul (hardcodat in logica agentilor)

- Nu incearca niciodata autentificarea pe niciun site
- Nu stocheaza date personale ale persoanelor fizice in afara celor publice din ONRC/ANAF
- Nu acceseaza retele sociale prin scraping direct
- Nu produce rapoarte despre persoane fizice private
- Nu foloseste date obtinute prin metode care violeaza ToS ale platformelor

### Disclaimer GDPR integrat automat

Orice raport care contine date despre persoane fizice (asociati, administratori) include automat:
> "Datele despre persoanele fizice incluse in acest raport provin exclusiv din registrele publice oficiale (ONRC, ANAF) si sunt disponibile public conform legislatiei romane. Utilizarea acestor date trebuie sa respecte prevederile GDPR (Regulamentul UE 2016/679)."

---

## 13. Structura proiect — tree complet **[NOU]**

```
Sistem_Inteligent_Analize/
|
|-- backend/
|   |-- main.py                    # FastAPI app entry point + lifespan
|   |-- config.py                  # Settings din .env (pydantic-settings)
|   |-- database.py                # SQLite connection + PRAGMA + helpers
|   |-- models.py                  # Pydantic models (request/response schemas)
|   |
|   |-- agents/
|   |   |-- __init__.py
|   |   |-- base.py                # BaseAgent abstract class (retry, timeout, logging)
|   |   |-- agent_official.py      # Agent 1 — Date oficiale
|   |   |-- agent_web.py           # Agent 2 — Web Intelligence
|   |   |-- agent_market.py        # Agent 3 — Market Research
|   |   |-- agent_verification.py  # Agent 4 — Verification
|   |   |-- agent_synthesis.py     # Agent 5 — Synthesis (Claude Code / Gemini / Cerebras)
|   |   |-- orchestrator.py        # LangGraph state machine
|   |   |-- state.py               # AnalysisState TypedDict
|   |   |
|   |   |-- tools/
|   |       |-- __init__.py
|   |       |-- anaf_client.py     # Client ANAF REST API
|   |       |-- onrc_scraper.py    # Scraper ONRC via Playwright
|   |       |-- seap_client.py     # Client SEAP/SICAP API
|   |       |-- tavily_client.py   # Wrapper Tavily cu quota tracking
|   |       |-- playwright_pool.py # Browser pool management
|   |       |-- bnr_client.py      # Parser BNR XML cursuri
|   |
|   |-- reports/
|   |   |-- __init__.py
|   |   |-- generator.py           # Report orchestrator (apeleaza fiecare format)
|   |   |-- pdf_generator.py       # WeasyPrint HTML→PDF
|   |   |-- docx_generator.py      # python-docx
|   |   |-- excel_generator.py     # openpyxl
|   |   |-- html_generator.py      # Jinja2 + Chart.js
|   |   |-- pptx_generator.py      # python-pptx
|   |   |-- templates/
|   |       |-- report_base.html   # Template Jinja2 partajat (HTML + PDF)
|   |       |-- report_print.css   # CSS specific print/PDF
|   |       |-- report_screen.css  # CSS specific ecran
|   |       |-- charts.js          # Chart.js config per tip grafic
|   |
|   |-- routers/
|   |   |-- __init__.py
|   |   |-- jobs.py                # /api/jobs — CRUD + start/stop
|   |   |-- reports.py             # /api/reports — list/get/download
|   |   |-- companies.py           # /api/companies — search/list
|   |   |-- analysis.py            # /api/analysis — tipuri + intrebari
|   |   |-- settings.py            # /api/settings — config UI
|   |   |-- ws.py                  # /ws/jobs/{job_id} — WebSocket progress
|   |
|   |-- services/
|   |   |-- __init__.py
|   |   |-- job_service.py         # Business logic joburi
|   |   |-- cache_service.py       # Cache layer cu TTL
|   |   |-- notification.py        # Telegram + Email
|   |   |-- pricing.py             # Calcul pret automat
|   |
|   |-- prompts/
|   |   |-- system_prompt.py       # System prompt Synthesis
|   |   |-- section_prompts.py     # Prompt per sectiune raport
|   |   |-- analysis_prompts.py    # Prompt per TIP analiza
|   |
|   |-- migrations/
|       |-- 001_initial.sql        # Schema initiala
|
|-- frontend/
|   |-- index.html
|   |-- package.json
|   |-- vite.config.ts
|   |-- tailwind.config.js
|   |-- tsconfig.json
|   |
|   |-- src/
|   |   |-- main.tsx               # Entry point React
|   |   |-- App.tsx                # Router + Layout
|   |   |
|   |   |-- pages/
|   |   |   |-- Dashboard.tsx      # / — statistici, ultimele rapoarte
|   |   |   |-- NewAnalysis.tsx    # /new-analysis — Wizard + Chatbot
|   |   |   |-- AnalysisProgress.tsx # /analysis/:id — WebSocket progress
|   |   |   |-- ReportView.tsx     # /report/:id — vizualizare raport
|   |   |   |-- ReportsList.tsx    # /reports — lista rapoarte
|   |   |   |-- Companies.tsx      # /companies — baza de date firme
|   |   |   |-- Settings.tsx       # /settings — configurare
|   |   |
|   |   |-- components/
|   |   |   |-- Layout.tsx         # Sidebar + Header + Content
|   |   |   |-- JobProgressCard.tsx
|   |   |   |-- ReportViewer.tsx
|   |   |   |-- CompanyCard.tsx
|   |   |   |-- AnalysisTypeSelector.tsx
|   |   |   |-- SourceAuditPanel.tsx
|   |   |   |-- WizardFlow.tsx     # Wizard step-by-step
|   |   |   |-- ChatInput.tsx      # Chatbot natural language
|   |   |   |-- TrustBadge.tsx     # Eticheta trust (OFICIAL/VERIFICAT/etc)
|   |   |
|   |   |-- hooks/
|   |   |   |-- useWebSocket.ts    # Hook WebSocket cu reconnect
|   |   |   |-- useApi.ts          # Hook fetch wrapper
|   |   |
|   |   |-- lib/
|   |   |   |-- api.ts             # API client (fetch wrapper)
|   |   |   |-- types.ts           # TypeScript types
|   |   |   |-- constants.ts       # Constante (analysis types, trust levels)
|   |   |
|   |   |-- styles/
|   |       |-- globals.css        # Tailwind imports + custom styles
|
|-- data/                          # SQLite DB (gitignored)
|   |-- ris.db
|
|-- outputs/                       # Rapoarte generate (gitignored)
|   |-- [job_id]/
|       |-- report.pdf
|       |-- report.docx
|       |-- report.xlsx
|       |-- report.html
|       |-- report.pptx
|
|-- .env                           # Variabile de mediu (gitignored)
|-- .env.example                   # Template .env (comitat in git)
|-- .gitignore
|-- requirements.txt               # Python dependencies
|-- README.md
|-- SPEC_INTELLIGENCE_SYSTEM.md    # Spec V1 (referinta)
|-- SPEC_INTELLIGENCE_SYSTEM_V2.md # Spec V2 (acest document)
|-- CLAUDE.md                      # Instructiuni per-proiect Claude Code
```

---

## 14. Dependinte exacte **[NOU]**

### requirements.txt

```txt
# Core
fastapi==0.115.12
uvicorn[standard]==0.34.0
pydantic==2.11.1
pydantic-settings==2.8.1
python-dotenv==1.1.0

# Database
aiosqlite==0.21.0

# AI / LLM
langchain==0.3.23
langchain-anthropic==0.3.14
langchain-google-genai==2.1.3
langgraph==0.3.30
anthropic==0.49.0
google-genai==1.14.0

# Web Scraping
playwright==1.51.0
httpx==0.28.1
beautifulsoup4==4.13.3

# Web Search
tavily-python==0.5.0

# Report Generation
weasyprint==63.1
python-docx==1.1.2
openpyxl==3.1.5
python-pptx==1.0.2
jinja2==3.1.6
matplotlib==3.10.1

# Notifications
python-telegram-bot==22.0
aiosmtplib==3.0.2

# Utilities
loguru==0.7.3
uuid7==0.1.0
```

**Nota WeasyPrint pe Windows:** WeasyPrint necesita GTK3 runtime. Instalare:
```bash
# Optiunea 1 — MSYS2 (recomandat)
# Instaleaza MSYS2, apoi: pacman -S mingw-w64-x86_64-pango

# Optiunea 2 — Daca WeasyPrint nu merge pe Windows
# Fallback: fpdf2==2.8.3 (inlocuieste weasyprint in pdf_generator.py)
```

### package.json

```json
{
  "name": "ris-frontend",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^7.4.0",
    "chart.js": "^4.4.8",
    "react-chartjs-2": "^5.3.0",
    "leaflet": "^1.9.4",
    "react-leaflet": "^5.0.0",
    "lucide-react": "^0.474.0",
    "clsx": "^2.1.1",
    "date-fns": "^4.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.18",
    "@types/react-dom": "^18.3.5",
    "@types/leaflet": "^1.9.16",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.5.3",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.7.3",
    "vite": "^6.2.4"
  }
}
```

---

## 15. LangGraph State Machine — schema completa **[NOU]**

### State Schema

```python
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

class AnalysisState(TypedDict):
    # Input (setat la creare)
    job_id: str
    analysis_type: str              # FULL_COMPANY_PROFILE, COMPETITION_ANALYSIS, etc.
    report_level: int               # 1, 2, 3
    input_params: dict              # Raspunsurile la intrebarile wizard-ului

    # Date colectate per agent
    official_data: Optional[dict]   # Agent 1 output
    web_data: Optional[dict]        # Agent 2 output
    market_data: Optional[dict]     # Agent 3 output

    # Post-verificare
    verified_data: Optional[dict]   # Agent 4 output

    # Sinteza
    report_sections: Optional[dict] # Agent 5 output (text per sectiune)

    # Raport generat
    report_paths: Optional[dict]    # {pdf: "...", docx: "...", ...}

    # Control flow
    errors: list                    # Erori per agent [{agent, error, recoverable}]
    progress: float                 # 0.0 - 1.0
    current_step: str               # Descriere pas curent (afisat in UI)

    # Config per tip analiza (setat la creare)
    agents_needed: list             # ["official", "web", "market"] — depinde de TIP + Nivel
```

### Graph Definition

```python
def build_analysis_graph() -> StateGraph:
    graph = StateGraph(AnalysisState)

    # Noduri
    graph.add_node("agent_official", run_official_agent)
    graph.add_node("agent_web", run_web_agent)
    graph.add_node("agent_market", run_market_agent)
    graph.add_node("agent_verification", run_verification_agent)
    graph.add_node("agent_synthesis", run_synthesis_agent)
    graph.add_node("report_generator", run_report_generator)

    # Edges
    graph.add_edge(START, "agent_official")           # Agent 1 ruleaza MEREU primul
    graph.add_conditional_edges(
        "agent_official",
        route_after_official,                          # Decide ce agenti urmeaza
        {
            "parallel_web_market": ["agent_web", "agent_market"],
            "web_only": ["agent_web"],
            "market_only": ["agent_market"],
            "skip_to_verification": ["agent_verification"],
        }
    )
    graph.add_edge("agent_web", "agent_verification")
    graph.add_edge("agent_market", "agent_verification")
    graph.add_edge("agent_verification", "agent_synthesis")
    graph.add_edge("agent_synthesis", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile(checkpointer=SqliteCheckpointer())
```

### Routing Logic

```python
def route_after_official(state: AnalysisState) -> str:
    level = state["report_level"]
    atype = state["analysis_type"]

    # Nivel 1: doar date oficiale -> verificare directa
    if level == 1:
        return "skip_to_verification"

    # TIP 3 (Risc Partener): nu are nevoie de web intelligence
    if atype == "PARTNER_RISK_ASSESSMENT":
        return "skip_to_verification"

    # TIP 4 (Licitatii): doar market research (SEAP)
    if atype == "TENDER_OPPORTUNITIES":
        return "market_only"

    # Nivel 2: oficial + web (fara market research extensiv)
    if level == 2 and atype not in ("COMPETITION_ANALYSIS", "MARKET_ENTRY_ANALYSIS"):
        return "web_only"

    # Default: toate in paralel
    return "parallel_web_market"
```

### Checkpoint Strategy

```python
# LangGraph SqliteCheckpointer salveaza starea dupa FIECARE nod
# La crash: se reia de la ultimul nod completat cu succes

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

checkpointer = AsyncSqliteSaver.from_conn_string("data/ris.db")

# La retry job:
config = {"configurable": {"thread_id": job_id}}
result = await graph.ainvoke(state, config=config)
# LangGraph reia automat de la checkpoint-ul salvat
```

### Progress Mapping

```python
# Fiecare nod are un weight in progresul total
PROGRESS_WEIGHTS = {
    "agent_official": 0.20,    # 0% -> 20%
    "agent_web": 0.20,         # 20% -> 40%
    "agent_market": 0.20,      # 20% -> 40% (paralel cu web)
    "agent_verification": 0.10, # 40% -> 50%
    "agent_synthesis": 0.25,   # 50% -> 75%
    "report_generator": 0.25,  # 75% -> 100%
}
# Nota: web + market ruleaza paralel, deci se suprapun la 20-40%
```

---

## 16. WebSocket Protocol **[NOU]**

### Endpoint

```
ws://localhost:8001/ws/jobs/{job_id}
```

### Client → Server Messages

```json
{"type": "subscribe", "job_id": "abc-123"}
```

### Server → Client Messages

```json
// Progres update (trimis la fiecare schimbare de pas)
{
    "type": "progress",
    "job_id": "abc-123",
    "percent": 35,
    "step": "Agent 1: Extragere date ANAF pentru CUI 12345678",
    "eta_seconds": 120
}

// Agent finalizat
{
    "type": "agent_complete",
    "job_id": "abc-123",
    "agent": "official",
    "status": "ok",
    "sources_found": 5,
    "sources_failed": 1,
    "duration_seconds": 45
}

// Agent eroare (non-fatala — sistemul continua)
{
    "type": "agent_warning",
    "job_id": "abc-123",
    "agent": "web",
    "message": "Timeout pe site-ul firmei — marcat ca INDISPONIBIL",
    "recoverable": true
}

// Job finalizat cu succes
{
    "type": "job_complete",
    "job_id": "abc-123",
    "report_id": "rpt-456",
    "formats": ["pdf", "docx", "html"],
    "duration_seconds": 340,
    "sources_total": 12,
    "sources_ok": 10
}

// Job esuat (eroare fatala)
{
    "type": "job_failed",
    "job_id": "abc-123",
    "error": "Toti providerii AI au esuat — sinteza imposibila",
    "retry_available": true,
    "failed_at_step": "agent_synthesis"
}
```

### Reconnect Strategy (Frontend)

```typescript
// useWebSocket.ts — hook React
const RECONNECT_DELAYS = [2000, 5000, 10000, 30000]; // ms

function useJobWebSocket(jobId: string) {
    // La conectare/reconectare: serverul trimite ULTIMUL state complet
    // Progresul se salveaza in SQLite — nu se pierde la disconnect
    // Dupa 4 retry-uri esuate: afiseaza "Conexiune pierduta" + buton manual retry
}
```

---

## 17. Caching Strategy **[NOU]**

### TTL per tip sursa

| Sursa | Cache key format | TTL | Motivare |
|-------|-----------------|-----|----------|
| BNR cursuri | `bnr_rates_{date}` | 24h | Se schimba zilnic |
| ANAF date fiscale | `anaf_{cui}_{query}` | 12h | Rare updates |
| ONRC date firma | `onrc_{cui}` | 7 zile | Schimbari foarte rare |
| SEAP licitatii active | `seap_active_{query_hash}` | 2h | Se actualizeaza frecvent |
| SEAP contracte istorice | `seap_history_{cui}` | 30 zile | Nu se schimba |
| Tavily web search | `tavily_{query_hash}` | 6h | Continut dinamic |
| Playwright scrape | `scrape_{url_hash}` | 12h | Site-uri se schimba rar |
| INS statistici | `ins_{indicator}` | 30 zile | Actualizari lunare |
| Fonduri europene | `funds_{program}` | 24h | Deadline-uri se schimba |

### Cache API

```python
class CacheService:
    async def get(self, key: str) -> dict | None:
        """Returneaza date din cache daca nu au expirat."""

    async def set(self, key: str, data: dict, source: str, ttl_hours: int):
        """Salveaza date in cache cu TTL specificat."""

    async def invalidate(self, pattern: str):
        """Invalideaza toate cheile care se potrivesc pattern-ului."""

    async def cleanup_expired(self):
        """Sterge toate intrarile expirate. Rulat la startup + periodic."""
```

### Comportament la re-analiza

- **Default:** Foloseste cache-ul valid
- **Buton "Forteaza refresh":** Ignora cache-ul, re-extrage totul
- **Delta report:** Forteaza refresh doar pe datele oficiale (Nivel 1)

---

## 18. Error Handling & Recovery Strategy **[NOU]**

### Principiu: Graceful Degradation

Daca un agent esueaza, sistemul **NU se opreste**. Continua cu datele disponibile si marcheaza sectiunile afectate ca INDISPONIBIL.

### Error handling per nivel

```
Nivel 1 — Source Error (un endpoint nu raspunde)
  -> Retry 3x cu backoff [2, 5, 15] sec
  -> Daca tot esueaza: marcheaza campul ca INDISPONIBIL, continua

Nivel 2 — Agent Error (un agent crapa complet)
  -> Log eroarea, notifica WebSocket cu "agent_warning"
  -> Continua cu ceilalti agenti
  -> Sectiunile dependente de agentul esuat: marcate INDISPONIBIL in raport

Nivel 3 — Synthesis Error (Claude Code indisponibil sau mod autonom)
  -> Default: Claude Code (Roland prezent) — fara fallback necesar
  -> Mod autonom: Gemini Flash -> Cerebras (daca Roland nu e prezent)
  -> Daca toti esueaza: job status = PAUSED, asteapta Roland

Nivel 4 — Job Error (crash neasteptat, OOM, etc.)
  -> LangGraph checkpoint salveaza starea dupa fiecare nod
  -> La retry: reia de la ultimul checkpoint valid
  -> Daca job-ul e RUNNING de >2x timpul estimat: auto-timeout + notificare
```

### Recovery la restart PC

```python
# La startup aplicatie:
# 1. Verifica daca exista joburi cu status RUNNING
# 2. Daca da: le seteaza pe PAUSED + notifica pe Telegram
# 3. In dashboard: arata buton "Reia job" care re-porneste de la checkpoint

async def recover_interrupted_jobs():
    jobs = await db.fetch("SELECT * FROM jobs WHERE status = 'RUNNING'")
    for job in jobs:
        await db.execute(
            "UPDATE jobs SET status = 'PAUSED', "
            "current_step = 'Intrerupt — necesita reluare manuala' "
            "WHERE id = ?", (job["id"],)
        )
        await notify_telegram(f"Job {job['id']} intrerupt. Reia din dashboard.")
```

### Windows Sleep Prevention

```python
# In timpul executiei unui job, prevenim Windows sleep
import ctypes

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

def prevent_sleep():
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    )

def allow_sleep():
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
```

---

## 19. Playwright Configuration Windows 10 **[NOU]**

### Setup initial (o singura data)

```bash
pip install playwright
playwright install chromium
# Descarca ~200MB Chromium browser
```

### Configurare browser

```python
from playwright.async_api import async_playwright

class PlaywrightPool:
    """Gestioneaza un singur browser Chromium partajat intre agenti."""

    def __init__(self):
        self._playwright = None
        self._browser = None

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',      # Previne OOM pe Windows
                '--no-sandbox',
            ]
        )

    async def new_context(self):
        return await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            locale='ro-RO',
            timezone_id='Europe/Bucharest',
        )

    async def scrape_page(self, url: str, wait_for: str = None) -> str:
        context = await self.new_context()
        page = await context.new_page()

        # Blocam resursele inutile pentru viteza
        await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}",
                         lambda route: route.abort())

        try:
            await page.goto(url, timeout=30000, wait_until='domcontentloaded')
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)

            # Delay random anti-bot
            await page.wait_for_timeout(random.randint(2000, 5000))

            return await page.content()
        finally:
            await context.close()

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
```

### Limitari cunoscute pe Windows 10

1. **Anti-bot detection:** Unele site-uri .gov.ro detecteaza headless Chromium. Solutie: user-agent realist + `--disable-blink-features=AutomationControlled`
2. **CAPTCHA:** portal.just.ro si bpi.ro au CAPTCHA. NU incercam sa le rezolvam — fallback pe Tavily search.
3. **Memorie:** Un context Playwright consuma ~50-100MB. Cu 2 agenti activi simultan: ~200MB. Acceptabil pe PC desktop.
4. **robots.txt:** Respectam MEREU robots.txt. Daca un site interzice scraping: fallback pe Tavily.

---

## 20. Prompt Templates per tip analiza **[NOU]**

### System Prompt (comun tuturor)

```python
SYSTEM_PROMPT = """
Esti un analist de business senior specializat in analiza firmelor romanesti.
Primesti date structurate colectate si verificate din surse publice oficiale.

REGULI ABSOLUTE:
1. Nu adaugi NICIO informatie care nu exista in datele primite
2. Mentionezi sursa pentru fiecare afirmatie importanta inline: (Sursa: ANAF)
3. Pastreaza etichetele de incredere: [OFICIAL], [VERIFICAT], [ESTIMAT], [INDISPONIBIL]
4. Daca o sectiune are date insuficiente, spui explicit
5. Scrii in romana, ton profesional dar accesibil
6. Nu faci predictii fara baza de date concreta
7. La contradictii: prezinta AMBELE variante cu sursele lor
"""
```

### Prompt per sectiune raport

```python
SECTION_PROMPTS = {
    "executive_summary": """
        Scrie un rezumat executiv de {word_count} cuvinte.
        Include: cine e firma, ce face, starea financiara pe scurt, riscuri cheie,
        oportunitate principala. Tonul: decisiv, concis, actionabil.
    """,

    "company_profile": """
        Descrie firma pe baza datelor oficiale ONRC/ANAF.
        Include: denumire, CUI, CAEN, data infiintare, asociati, administrator,
        capital social, sediu, puncte de lucru. Marcheaza fiecare camp cu eticheta trust.
    """,

    "financial_analysis": """
        Analizeaza situatia financiara cu datele disponibile.
        Daca ai cifra de afaceri multi-an: trend si interpretare.
        Daca ai doar datorii ANAF: focuseaza pe solvabilitate.
        Daca datele sunt limitate: spune EXPLICIT ce lipseste si de ce.
    """,

    "competition": """
        Prezinta competitorii identificati in format tabel + analiza narativa.
        Per competitor: nume, CUI, CAEN, zona, dimensiune estimata.
        Pozitionarea firmei analizate vs competitie: puncte tari/slabe relative.
    """,

    "risk_assessment": """
        Evalueaza riscurile pe categorii: financiar, juridic, operational, reputational.
        Scor final: VERDE (risc scazut) / GALBEN (risc mediu) / ROSU (risc ridicat).
        Fiecare risc: descriere + sursa + severitate + recomandare.
    """,

    "opportunities": """
        Prezinta oportunitatile identificate: licitatii active, fonduri, piete noi.
        Per oportunitate: descriere, valoare, deadline, eligibilitate, link sursa.
        Prioritizeaza dupa: urgenta (deadline) > valoare > grad potrivire.
    """,

    "swot": """
        Genereaza analiza SWOT structurata pe 4 cadrane.
        Fiecare punct: max 2 randuri, bazat pe DATE din raport (nu generic).
        Strengths/Weaknesses: din date interne (financiar, profil, online).
        Opportunities/Threats: din date externe (piata, competitie, reglementari).
    """,

    "recommendations": """
        3-5 recomandari strategice CONCRETE si ACTIONABILE.
        Fiecare: ce sa faca, de ce, cum, cu ce resurse estimate.
        Ordinea: urgenta (risc imediat) > oportunitate rapida > strategie termen lung.
        Baza EXCLUSIV pe datele din raport. Fara sfaturi generice.
    """,
}
```

---

## 21. Riscuri tehnice identificate **[NOU]**

| # | Risc | Probabilitate | Impact | Mitigare |
|---|------|---------------|--------|----------|
| R1 | ~~Claude Max NU include API access~~ **REZOLVAT** | — | — | **DECIZIE:** Synthesis ruleaza prin Claude Code (Opus) cu Roland prezent. $0 cost. |
| R2 | ONRC nu are API public stabil — scraping fragil | RIDICATA | MARE | Fallback pe listafirme.ro + retry logic robust |
| R3 | portal.just.ro CAPTCHA — litigii inaccesibile | RIDICATA | MEDIU | Tavily search ca alternativa. Marcheaza ca ESTIMAT/INDISPONIBIL |
| R4 | WeasyPrint problematic pe Windows (depende de GTK) | MEDIE | MEDIU | Test la setup. Fallback: fpdf2 |
| R5 | Tavily 1000 req/luna insuficient cu utilizare intensa | MEDIE | MEDIU | Quota tracking + avertizare la 80% + optional plan platit ($50/luna) |
| R6 | Analize 1-4 ore pot fi intrerupte (restart PC, sleep) | MEDIE | MARE | Checkpoint LangGraph + recovery la startup + sleep prevention |
| R7 | Date financiare detaliate indisponibile gratuit | CERT | MEDIU | Surse alternative (listafirme.ro, topfirme.com). Marcat ca Nivel 2 |
| R8 | Site-uri .gov.ro lente sau temporar offline | RIDICATA | MEDIU | Timeout generos (30s) + retry + cache agresiv |
| R9 | SEAP API paginatie problematica la volume mari | MEDIE | SCAZUT | Limitam la 100 rezultate per query |
| R10 | Playwright memorie excesiva cu multiple contexte | SCAZUTA | MEDIU | Un singur browser partajat, contexte inchise dupa folosire |

---

## 22. Estimare efort implementare **[NOU]**

| Faza | Efort relativ | Complexitate | Dependinte |
|------|---------------|--------------|------------|
| Faza 1 — Fundatie | Mic-Mediu | Scazuta | Niciuna |
| Faza 2 — Agenti | Mare | Ridicata | Faza 1 + API keys configurate |
| Faza 3 — Sinteza + Rapoarte | Mediu | Medie | Faza 2 + cel putin un AI provider functional |
| Faza 4 — UI complet | Mediu | Medie | Faza 3 |
| Faza 5 — Memorie | Mediu | Medie | Faza 4 |

**Nota:** Efortul depinde de cate probleme apar cu API-urile romanesti (ONRC, SEAP, BPI). Faza 2 e cea mai imprevizibila — site-urile .gov.ro pot schimba structura fara avertisment.

**Recomandare:** Implementare incrementala cu test pe date reale dupa fiecare agent. Nu astepta finalizarea tuturor agentilor pentru a testa.

---

## 23. Decizii confirmate de Roland — 2026-03-20

Toate intrebarile au fost clarificate. Deciziile sunt finale si ghideaza implementarea:

### Decizie 1 — AI Provider pentru Synthesis: CLAUDE CODE (Opus)

**Decizie:** Synthesis Agent ruleaza prin Claude Code cu Roland prezent la executie.
- Calitate maxima (Opus), cost $0 extra
- Fluxul NU e 100% autonom — necesita prezenta Roland pentru pasul de sinteza
- Fallback autonom disponibil cu Gemini Flash / Cerebras (calitate mai scazuta)
- `SYNTHESIS_MODE=claude_code` in `.env`

### Decizie 2 — Date financiare: listafirme.ro (gratuit)

**Decizie:** Folosim listafirme.ro si topfirme.com ca surse de date financiare.
- Gratuit, date publice agregate din Ministerul Finantelor
- Nivel 2 trust (VERIFICAT) — nu Nivel 1
- Suficient pentru 10 rapoarte/luna

### Decizie 3 — Litigii: Tavily search fallback

**Decizie:** Tavily search cu `site:portal.just.ro` ca alternativa la scraping direct.
- Rezultate partiale, marcate ca ESTIMAT
- Zero cost, zero risc ban IP
- Daca Tavily nu gaseste nimic → marcat INDISPONIBIL

### Decizie 4 — Buget lunar: ~$0

**Decizie:** Toate serviciile gratuite:
- AI: Claude Code (inclus in Claude Max) + Gemini Flash + Cerebras = $0
- Search: Tavily gratuit (1000 req/luna) = $0
- Date: listafirme.ro gratuit = $0
- Notificari: Telegram + Gmail SMTP = $0

### Decizie 5 — Prioritate implementare: TIP 3 primul, apoi TOATE

**Decizie:** Incepem cu TIP 3 (Risc Partener) ca proof of concept.
- Dupa implementare completa: TOATE TIP-urile (1-7, 9) trebuie sa fie functionale
- TIP 8 (Monitorizare) ramine DEFERRED pentru Faza 5

---

## 24. Reguli globale aplicate **[NOU]**

Urmatoarele reguli din regulamentul global CLAUDE.md au influentat deciziile din acest document V2:

| Regula | Cum a influentat V2 |
|--------|----------------------|
| **R1 — Refuz cerinte gresite** | Am semnalat problema Claude Max vs API ca potentiala eroare in spec V1 |
| **R2 — Solutia optima** | Am oferit alternative (WeasyPrint vs reportlab, fpdf2 ca fallback) cu pro/contra |
| **R3 — Informatii reale** | Am marcat fiecare API romanesc cu statusul sau REAL (FUNCTIONAL/PARTIAL/DIFICIL) in loc sa presupun ca toate merg |
| **R5 — Sugestii proactive** | Am identificat 10 riscuri tehnice + mitigari fara sa fiu intrebat |
| **R6 — Scan inainte de modificare** | Am citit integral spec V1 inainte de orice propunere |
| **R-RISK — Clasificare risc** | Am clasificat fiecare risc tehnic cu Probabilitate + Impact |
| **R-COMPLET — Informatii complete** | Am prezentat TOATE variantele la fiecare decizie tehnica, marcate cu [RECOMANDAT] |
| **SECURITATE** | .env cu chei API e gitignored, nicio cheie hardcodata, App Password Gmail (nu parola reala) |
| **LIMBA ROMANA** | Tot documentul e in romana (exceptie: cod si comenzi tehnice) |
| **NIVEL EXPLICATIE** | Explicatii accesibile, fara jargon excesiv, analogii unde e util |
| **Regula Suprema 95%** | Sectiunea 23 (Intrebari pentru Roland) asigura clarificarea aspectelor sub 95% claritate INAINTE de implementare |

---

*Document v2.0 — Generat 2026-03-20 — Roland Petrila + Claude Code (Opus, Max effort)*
*Baza: SPEC_INTELLIGENCE_SYSTEM.md v1.0 din 2026-03-19*
*Decizii confirmate: 2026-03-20. Toate intrebarile rezolvate. Gata de implementare Faza 1.*
