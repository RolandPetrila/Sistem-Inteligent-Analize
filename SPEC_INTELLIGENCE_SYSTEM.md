# SPEC — Roland Intelligence System (RIS)

> **Versiune:** 1.0 — Draft pentru revizuire Claude Code  
> **Data:** 2026-03-19  
> **Autor:** Roland Petrila + Claude claude.ai  
> **Scop:** Specificații complete pentru implementare cu Claude Code (Opus, Max effort)  
> **Instrucțiune pentru Claude Code:** Citește integral acest document, identifică toate lacunele tehnice, ambiguitățile și completările necesare, apoi generează `SPEC_INTELLIGENCE_SYSTEM_V2.md` cu varianta ta îmbunătățită înainte de a scrie orice cod.

---

## CUPRINS

1. [Descrierea produsului și modelul de business](#1-descrierea-produsului-și-modelul-de-business)
2. [Arhitectura tehnică](#2-arhitectura-tehnică)
3. [Cei 4 agenți — responsabilități exacte](#3-cei-4-agenți--responsabilități-exacte)
4. [Tipurile de analiză predefinite](#4-tipurile-de-analiză-predefinite)
5. [Structura bazei de date și sistemul de memorie](#5-structura-bazei-de-date-și-sistemul-de-memorie)
6. [Sursele de date — liste complete și limite](#6-sursele-de-date--liste-complete-și-limite)
7. [Formatele de raport și livrarea](#7-formatele-de-raport-și-livrarea)
8. [Filtrarea calității datelor](#8-filtrarea-calității-datelor)
9. [Interfața utilizator](#9-interfața-utilizator)
10. [Ordinea de implementare](#10-ordinea-de-implementare)
11. [Configurare și variabile de mediu](#11-configurare-și-variabile-de-mediu)
12. [Limitele etice și GDPR](#12-limitele-etice-și-gdpr)

---

## 1. Descrierea produsului și modelul de business

### Ce este RIS
Roland Intelligence System este un sistem local de Business Intelligence care rulează pe Windows 10. Operatorul (Roland) introduce o cerere de analiză, sistemul extrage automat date din surse publice verificate, le procesează prin agenți AI specializați și produce rapoarte profesionale în toate formatele necesare.

### Modelul de business
- **Operatorul:** Exclusiv Roland — sistemul nu e accesat de clienți
- **Clienții** primesc doar raportul final livrat de Roland (PDF/DOCX/HTML/etc.)
- **Servicii oferite:** Rapoarte punctuale la cerere + potențial abonamente de monitorizare
- **Tariful** se stabilește printr-o funcție de calcul bazată pe: tipul analizei, numărul de secțiuni, complexitate, date colectate de sistem din oferte similare de pe piață

### Principiul fundamental
> **Zero toleranță pentru date false.** Dacă o informație nu poate fi verificată dintr-o sursă oficială sau verificabilă, sistemul nu o include — și menționează explicit că informația nu a fost găsită.

### Infrastructura
- **Rulează pe:** Windows 10 desktop (PC Roland)
- **Accesat prin:** Browser local sau Tailscale de pe Android
- **Volume:** ~10 rapoarte/lună inițial
- **Scalabilitate:** Arhitectura permite migrare pe VPS cloud ulterior fără refactorizare majoră

---

## 2. Arhitectura tehnică

### Stack principal
```
Backend:  Python 3.13 + FastAPI + SQLite (aiosqlite)
Frontend: React 18 + Vite + Tailwind CSS
Agenți:   LangGraph (orchestrare) + LangChain (tools)
AI:       Claude API (Anthropic) — provider principal (Roland are Claude Max)
          Gemini Flash API — fallback și documente mari
          Cerebras API — fallback rapid (1M tokeni/zi gratuit)
Scraping: Playwright (browser automation local)
Search:   Tavily API (1.000 req/lună gratuit) — web search verificat cu surse
Export:   reportlab (PDF) + python-docx (DOCX) + openpyxl (Excel) + Jinja2 (HTML)
Notif:    Telegram Bot API (gratuit, nelimitat)
```

### Fluxul principal de execuție

```
[INPUT utilizator]
       ↓
[Wizard / Chatbot / Dashboard]
       ↓
[Job Manager] → creează job în SQLite, status: PENDING
       ↓
[Orchestrator LangGraph] → lansează agenții în paralel
       ↓
┌──────────────────────────────────────────────────────┐
│  Agent 1          Agent 2          Agent 3           │
│  Date Oficiale    Web Intelligence Market Research   │
│  (ANAF/ONRC/...)  (Playwright+Web)  (Tavily/SEAP/...)│
└──────────────────────────────────────────────────────┘
       ↓ (toate returnează date brute cu surse)
[Agent 4 — Verification]
       ↓ (date filtrate, surse validate, contradicții rezolvate)
[Synthesis Agent — Claude claude-sonnet-4-5]
       ↓ (text narativ complet per secțiune)
[Report Generator]
       ↓
[PDF + DOCX + Excel + HTML + PPTX]
       ↓
[Stocare în SQLite + notificare Telegram]
       ↓
[Dashboard — raport disponibil pentru descărcare]
```

### Principii arhitecturale
- **Izolare completă** față de Command Center — proiect separat, port separat, DB separată
- **Async tot** — FastAPI async + aiosqlite + agenți async în paralel
- **Job queue în SQLite** — un tabel `jobs` cu status tracking + WebSocket progress în browser
- **Idempotență** — dacă un job crapă la mijloc, poate fi reluat de la ultimul checkpoint
- **Config via `.env`** — nicio cheie API hardcodată în cod

---

## 3. Cei 4 agenți — responsabilități exacte

### Agent 1 — Date Oficiale (`agent_official.py`)

**Responsabilitate:** Extrage date din registre și API-uri guvernamentale române.

**Surse accesate:**
- `webservicesp.anaf.ro` — date fiscale CUI, status TVA, datorii
- `portal.onrc.ro` — date firmă, asociați, administrator, capital, sediu, CAEN
- `seap.anap.ro` / `sicap.anap.ro` — contracte câștigate + licitații active
- `bpi.ro` (Buletinul Procedurilor de Insolvență) — insolvențe, falimente
- `portal.just.ro` — dosare tribunal publice (litigii)
- `data.gov.ro` — seturi de date publice guvernamentale
- `fonduri-ue.ro` + `mfe.gov.ro` — fonduri europene active
- `mysmis2021.eu` — proiecte finanțate UE (public)
- `bnr.ro/nbrfxrates.xml` — cursuri valutare BNR (pentru calcule financiare)

**Output:** JSON structurat cu toate câmpurile disponibile + URL sursă + timestamp acces per câmp.

**Gestionarea erorilor:** Dacă un endpoint nu răspunde → retry de 3 ori cu backoff exponențial → dacă tot eșuează → marchează câmpul ca `"status": "unavailable"` și continuă.

**Rate limiting:** Maxim 1 request/2 secunde per domeniu guvernamental.

---

### Agent 2 — Web Intelligence (`agent_web.py`)

**Responsabilitate:** Extrage informații din prezența publică online a entității analizate.

**Ce extrage:**
- Site-ul oficial al firmei: descriere servicii, produse, prețuri publice, contact, locații
- Pagina de Facebook publică: număr urmăritori, frecvență postări, tip conținut (fără login)
- LinkedIn Company Page (via Tavily search, nu scraping direct): angajați, industrie, dimensiune
- Google Maps: rating, număr recenzii, categorii, program, adrese multiple
- Mențiuni în presă: articole din ultimele 12 luni (via Tavily search cu filtre de dată)
- Anunțuri de angajare publice (ejobs.ro, bestjobs.ro, linkedin.com/jobs — public)

**Cum accesează:**
- **Playwright** pentru site-ul oficial al firmei (JavaScript rendering necesar)
- **Tavily API** pentru LinkedIn, presă, anunțuri — returnează date indexate public cu surse citate
- **HTTP direct** (httpx) pentru pagini simple fără JS

**NU accesează:**
- Nicio platformă care necesită autentificare
- Facebook prin scraping direct (bot detection avansat — risc ban IP)
- Date din spatele unui login (intranet, zone membre, etc.)

**Rate limiting:** Maxim 1 request/3 secunde per domeniu. Playwright cu delay random 2-5 secunde între acțiuni.

---

### Agent 3 — Market Research (`agent_market.py`)

**Responsabilitate:** Cercetează piața, competiția, oportunitățile de business.

**Ce produce:**
- Lista competitorilor direcți (același CAEN + aceeași zonă geografică) cu profil sumar
- Licitații active pe SEAP compatibile cu profilul firmei (filtrare automată)
- Fonduri europene aplicabile (matching pe criterii: mărime firmă, CAEN, regiune, tip investiție)
- Programe naționale active: PNRR, IMM Invest, Start-Up Nation, Saligny, granturi MIPE
- Tendințe de piață din publicații de specialitate și rapoarte publice
- Clienți potențiali identificabili din contracte publice SEAP

**Sursele principale:**
- `sicap.anap.ro/web/pub/notice/list` — licitații active (API public)
- `mfe.gov.ro` + `fonduri-ue.ro` — finanțări europene
- Tavily API cu query-uri specializate per domeniu
- `insse.ro` — statistici INS publice per industrie

**Logica de matching fonduri:**
```
Pentru fiecare program de finanțare activ:
  - Verifică eligibilitate: dimensiune firmă (micro/mică/medie/mare)
  - Verifică eligibilitate: cod CAEN în lista eligibilă a programului
  - Verifică eligibilitate: regiune de dezvoltare
  - Dacă toate match → include în raport cu scor de potrivire (%)
  - Dacă parțial match → include cu notă de eligibilitate condiționată
```

---

### Agent 4 — Verification (`agent_verification.py`)

**Responsabilitate:** Filtrul de calitate al întregului sistem. Ultimul agent înainte de sinteză.

**Reguli stricte:**

**Regula 1 — Prioritatea surselor:**
```
Nivel 1 (AUTORITATE MAXIMĂ): .gov.ro, ANAF, ONRC, SEAP, BNR, portal.just.ro
Nivel 2 (VERIFICAT): Site oficial firmă, LinkedIn public indexat, Google Maps
Nivel 3 (ESTIMAT): Presă online, mențiuni web, anunțuri job
Nivel 4 (EXCLUS): Forumuri, opinii anonime, surse fără autor identificabil
```

**Regula 2 — Contradicții:**
```
Dacă informație din Nivel 1 ≠ informație din Nivel 2/3:
  → Păstrează EXCLUSIV informația din Nivel 1
  → Adaugă notă: "Sursă secundară indică [X] — invalidată de date oficiale ANAF/ONRC"
```

**Regula 3 — Date lipsă:**
```
Dacă informație nu există în nicio sursă disponibilă:
  → NU inventează, NU estimează fără bază
  → Include: "Informație indisponibilă din surse publice verificabile la data [timestamp]"
```

**Regula 4 — Etichete de încredere:**
Fiecare câmp din raport primește o etichetă:
- `✅ OFICIAL` — din sursă Nivel 1
- `✓ VERIFICAT` — din sursă Nivel 2, consistent cu Nivel 1
- `~ ESTIMAT` — din sursă Nivel 3, menționată explicit
- `⚠ NECONCLUDENT` — surse contradictorii, prezentat cu ambele variante și sursele lor
- `❌ INDISPONIBIL` — nu există date publice verificabile

---

### Synthesis Agent — Claude API (`agent_synthesis.py`)

**Model:** `claude-sonnet-4-5` (Roland are Claude Max — folosit ca provider principal)  
**Fallback:** `gemini-2.0-flash` (gratuit) → `cerebras/llama-3.3-70b` (gratuit)

**Responsabilitate:** Primește JSON structurat verificat de Agent 4 și produce text narativ coerent per secțiune de raport.

**Prompt system:**
```
Ești un analist de business senior specializat în analiza firmelor românești.
Primești date structurate colectate și verificate din surse publice oficiale.
Scrii analize clare, precise, fără jargon inutil, înțelese de oricine.
REGULI STRICTE:
- Nu adaugi nicio informație care nu există în datele primite
- Menționezi explicit sursa pentru fiecare afirmație importantă
- Dacă o secțiune are date insuficiente, spui explicit că datele sunt limitate
- Scrii în română, ton profesional dar accesibil
- Nu faci predicții fără bază de date concretă
```

---

## 4. Tipurile de analiză predefinite

Sistemul are un catalog de tipuri de analiză predefinite. La selectarea unui tip, sistemul pune automat întrebări specifice înainte de a porni. Fiecare tip e adaptabil la orice firmă sau domeniu.

---

### TIP 1 — Profil Complet Firmă (`FULL_COMPANY_PROFILE`)
**Descriere:** Analiză exhaustivă a unei firme specifice — tot ce e disponibil public.  
**Timp estimat:** Nivel 1: 15-30 min | Nivel 2: 1-2 ore | Nivel 3: 2-4 ore  
**Întrebări automate:**
1. CUI sau denumire exactă a firmei?
2. Județul/localitatea sediului? (pentru contextualizare locală)
3. Care este scopul analizei? (due diligence / parteneriat / concurență / altul)
4. Există aspecte specifice de investigat prioritar? (ex: situație financiară, litigii, asociați)
5. Perioada de interes pentru date financiare? (ultimii 3 ani / 5 ani / alt interval)

**Secțiuni generate:** Toate 10 blocurile din raportul standard.

---

### TIP 2 — Analiză Competiție (`COMPETITION_ANALYSIS`)
**Descriere:** Identifică și analizează toți competitorii direcți dintr-un domeniu și zonă geografică.  
**Timp estimat:** 1-3 ore (depinde de numărul competitorilor găsiți)  
**Întrebări automate:**
1. Firma client sau domeniul de activitate? (CUI sau descriere)
2. Zona geografică de interes? (județ / regiune / național)
3. Cât de larg definim "competitor direct"? (același CAEN exact / CAEN similar / întreaga industrie)
4. Ce aspect al competiției interesează mai mult? (prețuri / servicii / dimensiune / online)
5. Există firme specifice pe care le știi deja și vrei incluse obligatoriu?

**Secțiuni generate:** Bloc 1 (sumar) + Bloc 4 (competiție extinsă) + Bloc 8 (SWOT comparativ) + Bloc 9 (recomandări).

---

### TIP 3 — Evaluare Risc Partener (`PARTNER_RISK_ASSESSMENT`)
**Descriere:** Verificare rapidă înainte de a semna un contract sau a intra într-un parteneriat.  
**Timp estimat:** 15-45 minute  
**Întrebări automate:**
1. CUI sau denumirea firmei de verificat?
2. Tipul parteneriatului planificat? (furnizor / client / asociat / joint-venture)
3. Valoarea estimată a contractului sau parteneriatului? (RON)
4. Există îngrijorări specifice pe care le ai deja?
5. Termenul de decizie? (urgent sub 24h / normal 2-3 zile)

**Secțiuni generate:** Bloc 1 (date firmă) + Bloc 2 (financiar) + Bloc 5 (litigii/risc) + scor risc final (Verde/Galben/Roșu) + recomandare clară DA/NU/CONDIȚIONAT.

---

### TIP 4 — Oportunități Licitații & Contracte (`TENDER_OPPORTUNITIES`)
**Descriere:** Găsește licitații publice active și contracte câștigabile pentru profilul dat.  
**Timp estimat:** 30-60 minute  
**Întrebări automate:**
1. CUI sau profilul firmei care caută oportunități?
2. Tipul de servicii/produse oferite? (cod CAEN + descriere liberă)
3. Zona geografică preferată pentru contracte? (local / regional / național)
4. Valoarea minimă și maximă a contractelor de interes? (RON)
5. Există experiență anterioară cu licitații publice? (DA/NU — influențează filtrarea cerințelor)
6. Termen de livrare maxim acceptat? (pentru filtrare licitații urgente)

**Secțiuni generate:** Bloc 6 (oportunități) extins + track record SEAP al firmei + recomandări de poziționare.

---

### TIP 5 — Fonduri & Finanțări Disponibile (`FUNDING_OPPORTUNITIES`)
**Descriere:** Identifică toate programele de finanțare europene și naționale aplicabile.  
**Timp estimat:** 45-90 minute  
**Întrebări automate:**
1. CUI sau profilul firmei? (pentru verificarea eligibilității)
2. Tipul de investiție planificată? (echipamente / digitalizare / angajări / export / cercetare / altul)
3. Suma necesară de finanțat? (RON — pentru filtrarea programelor după plafon)
4. Firma are datorii la ANAF? (DA/NU — condiție de eligibilitate pentru multe programe)
5. Numărul actual de angajați? (micro <10 / mică <50 / medie <250 / mare)
6. Regiunea de dezvoltare? (influențează fondurile structurale disponibile)

**Secțiuni generate:** Bloc 7 extins + tabel comparativ programe (nume, buget, deadline, eligibilitate, procent finanțare, link oficial).

---

### TIP 6 — Analiză Intrare pe Piață (`MARKET_ENTRY_ANALYSIS`)
**Descriere:** Analiză completă pentru o firmă care vrea să intre pe o piață nouă sau să extindă activitatea.  
**Timp estimat:** 2-4 ore  
**Întrebări automate:**
1. Descrierea afacerii client (CUI dacă există sau profil nou)?
2. Piața/domeniul țintă? (descriere + cod CAEN estimat)
3. Zona geografică de intrare? (județ / regiune / național)
4. Care e avantajul competitiv pe care îl aduce? (preț / calitate / nișă / inovație)
5. Buget estimat pentru intrarea pe piață? (orientativ — pentru calibrarea recomandărilor)
6. Există restricții legale sau de licențiere cunoscute în domeniu?

**Secțiuni generate:** Bloc 4 (competiție detaliată) + Bloc 6 (oportunități) + Bloc 7 (fonduri aplicabile) + Bloc 8 (SWOT piață) + Bloc 9 (strategie intrare pas cu pas).

---

### TIP 7 — Prospectare Clienți Potențiali (`LEAD_GENERATION`)
**Descriere:** Identifică firme din domeniul X, zona Y, care ar putea deveni clienți.  
**Timp estimat:** 1-2 ore  
**Întrebări automate:**
1. Profilul firmei care caută clienți? (CUI sau descriere servicii oferite)
2. Profilul clientului ideal? (industrie, dimensiune, zonă geografică)
3. Criteriu de prioritizare? (firme în creștere / firme cu licitații active / firme cu probleme cunoscute)
4. Câte firme țintă să identifice? (10 / 25 / 50 / cât găsește)
5. Ce informații de contact să includă? (date publice ONRC — email/tel dacă sunt publice)

**Secțiuni generate:** Listă firme cu profil sumar + date contact publice + scor de potrivire estimat + recomandare de abordare per firmă.

---

### TIP 8 — Monitorizare Periodică (`MONITORING_SETUP`)
**Descriere:** Configurează monitorizarea continuă pentru o firmă sau un domeniu.  
**Status:** DEFERRED — implementat în faza 2  
**Întrebări automate:** (rezervate pentru implementare ulterioară)

---

### TIP 9 — Raport Personalizat (`CUSTOM_REPORT`)
**Descriere:** Orice combinație de secțiuni, orice tip de cerere care nu se încadrează în tipurile de mai sus.  
**Timp estimat:** Variabil — estimat după confirmarea cererii  
**Cum funcționează:** Sistemul pune o serie de întrebări deschise, extrage structura cererii, propune un plan de secțiuni cu estimare de timp, utilizatorul confirmă sau modifică, apoi pornește analiza.

---

## 5. Structura bazei de date și sistemul de memorie

### Filozofia de memorare (scenariul optim propus)

Sistemul construiește în timp o **bază de date proprie cu cunoștințe** despre firmele și piețele analizate. La fiecare nouă analiză pe o entitate existentă, sistemul:
1. Încarcă automat raportul anterior
2. Identifică ce s-a schimbat față de ultima analiză
3. Marchează schimbările ca `MODIFICAT_DIN [data]`
4. Prezintă un "delta report" înainte de raportul complet

### Tabelele SQLite

```sql
-- Joburi de analiză
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,           -- UUID
    type TEXT NOT NULL,            -- TIP 1-9
    status TEXT NOT NULL,          -- PENDING/RUNNING/DONE/FAILED
    input_data TEXT,               -- JSON cu parametrii cererii
    report_level INTEGER,          -- 1/2/3
    created_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    progress_percent INTEGER DEFAULT 0,
    current_step TEXT              -- descriere pas curent
);

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

-- Rapoarte generate
CREATE TABLE reports (
    id TEXT PRIMARY KEY,           -- UUID
    job_id TEXT REFERENCES jobs(id),
    company_id TEXT REFERENCES companies(id),  -- NULL pentru analize de piață
    report_type TEXT,              -- TIP 1-9
    report_level INTEGER,          -- 1/2/3
    title TEXT,
    summary TEXT,                  -- rezumat executiv (text scurt)
    full_data TEXT,                -- JSON complet cu toate datele colectate
    risk_score TEXT,               -- Verde/Galben/Roșu (unde aplicabil)
    created_at DATETIME,
    -- Fișierele generate
    pdf_path TEXT,
    docx_path TEXT,
    excel_path TEXT,
    html_path TEXT,
    pptx_path TEXT
);

-- Surse de date accesate per raport
CREATE TABLE report_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT REFERENCES reports(id),
    source_name TEXT,              -- ex: "ANAF", "ONRC", "Tavily"
    source_url TEXT,
    accessed_at DATETIME,
    status TEXT,                   -- OK/TIMEOUT/BLOCKED/ERROR
    data_found BOOLEAN
);

-- Piețe și domenii analizate (pentru TIP 2, 6, 7)
CREATE TABLE markets (
    id TEXT PRIMARY KEY,
    caen_code TEXT,
    description TEXT,
    county TEXT,
    last_analyzed_at DATETIME,
    competitor_count INTEGER,
    analysis_count INTEGER DEFAULT 0
);

-- Alerte configurate (pentru monitorizare — faza 2)
CREATE TABLE monitoring_alerts (
    id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES companies(id),
    alert_type TEXT,               -- INSOLVENCY/TENDER/FUNDING/COMPETITOR_CONTRACT
    is_active BOOLEAN DEFAULT TRUE,
    check_frequency TEXT,          -- DAILY/WEEKLY
    last_checked_at DATETIME,
    telegram_notify BOOLEAN DEFAULT TRUE
);

-- Istoricul comparărilor (delta între rapoarte)
CREATE TABLE report_deltas (
    id TEXT PRIMARY KEY,
    report_id_new TEXT REFERENCES reports(id),
    report_id_old TEXT REFERENCES reports(id),
    delta_summary TEXT,            -- JSON cu câmpurile schimbate
    created_at DATETIME
);

-- Cache pentru date frecvent accesate
CREATE TABLE data_cache (
    cache_key TEXT PRIMARY KEY,    -- ex: "anaf_cui_12345678"
    data TEXT,                     -- JSON
    source TEXT,
    cached_at DATETIME,
    expires_at DATETIME            -- TTL: date oficiale 24h, web 6h
);
```

### Scenariile de utilizare a memoriei

**Scenariu 1 — Re-analiză firmă existentă:**
```
Utilizator: "Analizează din nou Mosslein SRL"
Sistem: "Am un raport anterior din [data]. Fac analiză nouă completă 
         sau vrei doar ce s-a schimbat față de ultimul raport?"
```

**Scenariu 2 — Căutare în istoricul propriu:**
```
Utilizator: "Arată-mi toate firmele din construcții analizate în Arad"
Sistem: returnează lista din tabelul companies filtrat după county + caen
```

**Scenariu 3 — Pattern recognition:**
```
La Tip 7 (Lead Generation): sistemul poate compara noul target cu 
firmele deja în baza de date proprie pentru a identifica similarități
```

**Scenariu 4 — Pricing intelligence:**
```
Sistemul colectează automat din web oferte similare de business intelligence 
și le stochează în tabelul markets pentru calibrarea automată a prețurilor
```

---

## 6. Sursele de date — liste complete și limite

### Surse oficiale românești (Nivel 1 — AUTORITATE MAXIMĂ)

| Sursă | URL | Date disponibile | Rate limit recomandat |
|-------|-----|------------------|-----------------------|
| ANAF — date fiscale | `webservicesp.anaf.ro/PlatitorTvaRest/api/v8/ws/tva` | CUI, TVA, datorii, sediu fiscal | 1 req/2 sec |
| ONRC — date firmă | `recom.onrc.ro/services/recom/` | Asociați, admin, capital, CAEN, sediu | 1 req/3 sec |
| SEAP/SICAP — licitații | `sicap.anap.ro/web/pub/notice/list` | Licitații active + arhivă contracte | 1 req/2 sec |
| BPI — insolvențe | `bpi.ro` | Proceduri insolvență active + arhivă | 1 req/5 sec |
| portal.just.ro | `portal.just.ro/SitePages/cautare.aspx` | Dosare tribunal (public) | 1 req/5 sec |
| data.gov.ro | `data.gov.ro/api` | Seturi date publice diverse | 1 req/2 sec |
| INS — statistici | `insse.ro/cnp/riweb` | Statistici industrie, PIB, angajări | 1 req/3 sec |
| BNR — cursuri | `bnr.ro/nbrfxrates.xml` | Cursuri valutare zilnice | 1 req/oră (date statice) |
| MySmis | `mysmis2021.eu` | Proiecte UE finanțate (public) | 1 req/3 sec |
| fonduri-ue.ro | `fonduri-ue.ro` | Programe finanțare active | Playwright 1 req/5 sec |
| mfe.gov.ro | `mfe.gov.ro` | Fonduri europene, PNRR | 1 req/3 sec |

### Surse web publice (Nivel 2 — VERIFICAT prin Tavily)

| Sursă | Metoda de acces | Ce extrage |
|-------|-----------------|------------|
| Site-ul oficial al firmei | Playwright | Servicii, prețuri publice, contact, locații |
| Google Maps / Business | Tavily search | Rating, recenzii, program, adresă |
| LinkedIn Company | Tavily search (nu scraping direct) | Angajați estimați, industrie, descriere |
| Pagini Facebook publice | Tavily search (nu scraping direct) | Urmăritori, activitate recentă |
| Anunțuri job (ejobs, bestjobs) | Tavily search | Roluri disponibile, creștere echipă |

### Surse presă și web (Nivel 3 — ESTIMAT, cu citare obligatorie)

- Tavily search cu filtre: site:ziare.com, site:digi24.ro, site:economica.net etc.
- Google News indexat (via Tavily)
- Publicații de specialitate indexate public

### Ce NU accesează sistemul (NICIODATĂ)

- Platforme cu paywall sau login obligatoriu
- Baze de date private (ex: Termene.ro fără API key, Dosar.ro cu abonament)
- Rețele sociale prin scraping direct (bot detection — risc ban IP)
- Orice date cu caracter personal ale persoanelor fizice în afara celor din registre publice
- Dark web sau surse anonime neverificabile

---

## 7. Formatele de raport și livrarea

### Formatele generate automat

**PDF Profesional** (`reportlab` + template custom)
- Antet cu logo placeholder + data generării + versiunea
- Cuprins automat cu numere de pagini
- Grafice încorporate (matplotlib → PNG → PDF)
- Footer cu disclaimer: "Raport generat automat din surse publice — [data] — Roland Intelligence System"
- Watermark configurabil (CONFIDENTIAL / DRAFT / FINAL)

**DOCX Editabil** (`python-docx` + template Jinja2)
- Stiluri Word definite (Heading 1/2/3, Normal, Tabel, Caption)
- Tabele native Word (editabile de client)
- Imagini grafice incorporate
- Track Changes dezactivat implicit (document curat)

**Excel cu Date Brute** (`openpyxl`)
- Sheet 1: Rezumat executiv (date cheie)
- Sheet 2: Date financiare multi-an (grafice native Excel)
- Sheet 3: Lista competitori cu toate câmpurile
- Sheet 4: Licitații/contracte identificate
- Sheet 5: Fonduri disponibile cu eligibilitate
- Sheet 6: Surse accesate (audit trail complet)

**HTML Interactiv** (`Jinja2` + `Chart.js` inline)
- Pagină web single-file (tot inclus — CSS + JS + date)
- Grafice interactive (hover, zoom, filtrare)
- Tabel competitori sortabil/filtrabil
- Harta geografică competiție (`Leaflet.js` cu OpenStreetMap — gratuit)
- Poate fi trimis ca fișier .html sau hostat temporar via Tailscale Funnel

**PowerPoint** (`python-pptx`)
- Slide 1: Titlu + rezumat executiv
- Slide 2-3: Date firmă + situație financiară
- Slide 4-5: Analiză competiție + hartă
- Slide 6: SWOT vizual (caroiaj 2x2)
- Slide 7: Oportunități (licitații + fonduri)
- Slide 8: Recomandări strategice
- Slide 9: Surse și metodologie
- Template: design profesional (albastru corporate / alb)

### Sistemul de livrare

1. **Local:** Toate fișierele salvate în `outputs/[job_id]/` pe PC
2. **Dashboard:** Buton de download per format disponibil imediat în interfață
3. **Email:** Trimitere automată via Gmail SMTP (SMTP existent în Command Center — reutilizabil) cu PDF + link HTML
4. **Telegram:** Notificare automată la finalizare: "✅ Raport [TIP] pentru [FIRMA] gata — [link descărcare]"

---

## 8. Filtrarea calității datelor

### Sistemul de etichete (aplicat per câmp în JSON și vizibil în raport)

```python
TRUST_LEVELS = {
    "OFICIAL": {
        "icon": "✅",
        "color": "#00AA00",
        "description": "Sursă oficială guvernamentală verificată"
    },
    "VERIFICAT": {
        "icon": "✓",
        "color": "#0066CC",
        "description": "Sursă publică verificabilă, consistentă cu datele oficiale"
    },
    "ESTIMAT": {
        "icon": "~",
        "color": "#FF8800",
        "description": "Sursă terță, menționată explicit — necesită verificare suplimentară"
    },
    "NECONCLUDENT": {
        "icon": "⚠",
        "color": "#CC0000",
        "description": "Surse contradictorii — prezentate ambele variante"
    },
    "INDISPONIBIL": {
        "icon": "❌",
        "color": "#888888",
        "description": "Informație indisponibilă din surse publice la data analizei"
    }
}
```

### Regula de aur (implementată în cod, nu doar documentată)

```python
def resolve_contradiction(official_data, secondary_data, field_name):
    """
    Dacă datele oficiale și cele secundare sunt contradictorii,
    returnează ÎNTOTDEAUNA datele oficiale cu notă explicită.
    Nu există excepții de la această regulă.
    """
    if official_data != secondary_data:
        return {
            "value": official_data,
            "trust": "OFICIAL",
            "note": f"Sursă secundară indica '{secondary_data}' — invalidată de date oficiale",
            "source": "ANAF/ONRC"
        }
    return {"value": official_data, "trust": "OFICIAL"}
```

### Disclaimer obligatoriu în fiecare raport

> "Acest raport a fost generat automat la data [timestamp] folosind exclusiv date disponibile public din surse verificabile. Acuratețea datelor depinde de corectitudinea informațiilor din registrele publice accesate. Datele marcate cu ⚠ sau ❌ necesită verificare manuală suplimentară înainte de utilizare în decizii juridice sau financiare majore. Roland Intelligence System nu își asumă responsabilitatea pentru decizii bazate exclusiv pe acest raport fără verificare independentă."

---

## 9. Interfața utilizator

### Cele 3 moduri de interacțiune

**Modul 1 — Wizard (recomandat pentru utilizare standard)**
- Pas 1: Selectezi tipul de analiză (TIP 1-9) din listă cu descrieri
- Pas 2: Sistemul pune automat întrebările specifice tipului selectat (câte 3-6 întrebări)
- Pas 3: Selectezi nivelul raportului (1/2/3) cu estimare de timp și preț
- Pas 4: Confirmi și pornești analiza
- Pas 5: Progress bar în timp real + log al pașilor executați
- Pas 6: Raport disponibil — butoane de download per format

**Modul 2 — Chatbot natural**
- Câmp text liber: "Analizează firma Mosslein SRL din Nădlac, CUI 12345678"
- AI parsează cererea, identifică tipul de analiză, pune întrebările lipsă
- Trece automat în fluxul Wizard de la Pas 3

**Modul 3 — Dashboard rapid**
- Butoane directe per tip de analiză
- Form pre-completat cu ultimele valori folosite
- Potrivit pentru analize rapide repetitive

### Paginile aplicației

```
/ (Dashboard)           → Statistici generale, ultimele rapoarte, joburi active
/new-analysis           → Wizard / Chatbot / Dashboard rapid
/analysis/:id           → Progresul unui job activ (WebSocket real-time)
/report/:id             → Vizualizarea completă a unui raport
/reports                → Lista tuturor rapoartelor (căutabile, filtrabile)
/companies              → Baza de date proprie cu firmele analizate
/settings               → Configurare API keys, template-uri, preferințe
```

### Componentele UI cheie

- **JobProgressCard:** WebSocket real-time, step curent, procent, ETA
- **ReportViewer:** Tabs per secțiune, grafice interactive, toggle etichete de încredere
- **CompanyCard:** Mini-profil firmă cu history de analize
- **AnalysisTypeSelector:** Grid cu cards per tip de analiză, iconiță + descriere + timp estimat
- **SourceAuditPanel:** Expandabil în fiecare raport — lista completă a surselor accesate

---

## 10. Ordinea de implementare

### Faza 1 — Fundație (prioritate maximă)
1. Structura proiect: `backend/` + `frontend/` + `.env` + `requirements.txt`
2. FastAPI app cu CORS + WebSocket + health check
3. SQLite setup cu toate tabelele din Secțiunea 5
4. React app cu Vite + Tailwind + React Router
5. Paginile de bază: Dashboard + New Analysis + Reports list
6. Sistemul de jobs: creare job + tracking status + WebSocket progress

### Faza 2 — Agenții de date
7. Agent 1 (Date Oficiale): ANAF + ONRC + SEAP integration
8. Agent 4 (Verification): logica de filtrare + etichete trust
9. Test complet: job cu TIP 3 (Risc Partener) — cel mai simplu
10. Agent 2 (Web Intelligence): Playwright setup + Tavily integration
11. Agent 3 (Market Research): SEAP licitații + fonduri europene

### Faza 3 — Sinteza și rapoartele
12. Synthesis Agent: Claude API integration + prompt engineering
13. Report Generator: PDF (reportlab) + DOCX (python-docx)
14. Test complet: job cu TIP 1 (Profil Firmă) Nivel 2
15. Excel generator + HTML generator

### Faza 4 — UI complet și livrare
16. Wizard interactiv complet cu toate tipurile TIP 1-7
17. Chatbot natural (parser cereri libere)
18. PowerPoint generator
19. Email delivery (Gmail SMTP)
20. Telegram notifications

### Faza 5 — Memorie și optimizare
21. Delta reports (comparare raport nou vs. vechi)
22. Company database cu search și filtrare
23. Caching layer pentru date frecvent accesate
24. Pricing intelligence (colectare automată prețuri piață)
25. Monitoring & alerting (TIP 8 — faza 2 a proiectului)

---

## 11. Configurare și variabile de mediu

```env
# AI Providers
ANTHROPIC_API_KEY=           # Claude API (principal — Roland are Claude Max)
GOOGLE_AI_API_KEY=           # Gemini Flash (fallback)
CEREBRAS_API_KEY=            # Cerebras (fallback rapid gratuit)
GROQ_API_KEY=                # Groq (fallback)

# Web Search
TAVILY_API_KEY=              # Search verificat cu surse (1000 req/lună gratuit)

# Notificări
TELEGRAM_BOT_TOKEN=          # Bot token de la @BotFather
TELEGRAM_CHAT_ID=            # Chat ID personal Roland

# Email
GMAIL_USER=                  # adresa gmail
GMAIL_APP_PASSWORD=          # App Password Gmail

# Aplicație
APP_SECRET_KEY=              # cheie pentru sesiuni
DATABASE_PATH=./data/ris.db  # calea către SQLite
OUTPUTS_DIR=./outputs/       # folderul cu rapoartele generate
LOG_LEVEL=INFO

# Rate limiting
MAX_CONCURRENT_JOBS=2        # maxim 2 joburi simultan pe PC local
REQUEST_DELAY_GOV=2          # secunde între cereri pe .gov.ro
REQUEST_DELAY_WEB=3          # secunde între cereri Playwright
```

---

## 12. Limitele etice și GDPR

### Ce face sistemul

- Accesează EXCLUSIV date disponibile public fără autentificare
- Citează sursa pentru fiecare informație inclusă în raport
- Respectă `robots.txt` al siturilor accesate via Playwright
- Adaugă delay între cereri pentru a nu supraîncărca serverele

### Ce NU face sistemul (hardcodat în logica agenților, nu configurabil)

- Nu încearcă niciodată autentificarea pe niciun site
- Nu stochează date personale ale persoanelor fizice în afara celor publice din ONRC/ANAF
- Nu accesează rețele sociale prin scraping direct (risc ban IP + ToS violation)
- Nu produce rapoarte despre persoane fizice private (doar entități juridice și date publice despre reprezentanți legali)
- Nu folosește date obținute prin metode care violează ToS ale platformelor

### Disclaimer GDPR integrat automat

Orice raport care conține date despre persoane fizice (asociați, administratori) include automat:
> "Datele despre persoanele fizice incluse în acest raport provin exclusiv din registrele publice oficiale (ONRC, ANAF) și sunt disponibile public conform legislației române. Utilizarea acestor date trebuie să respecte prevederile GDPR (Regulamentul UE 2016/679)."

---

*Document v1.0 — Generat 2026-03-19 — Roland Petrila + Claude claude.ai*  
*Instrucțiune finală pentru Claude Code: Citește integral, completează lacunele tehnice identificate, propune îmbunătățiri arhitecturale, generează SPEC_INTELLIGENCE_SYSTEM_V2.md cu varianta ta îmbunătățită.*
