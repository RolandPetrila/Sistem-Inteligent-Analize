# ROLAND INTELLIGENCE SYSTEM (RIS)
## Audit Intern Complet — Prezentare, Arhitectura AI si Plan de Completare
**Data:** 7 Aprilie 2026 | **Versiune:** 1.3 | **Autor:** Roland Petrila + Claude Code
*v1.1 — Adaugat: Audit modul Fonduri/Granturi (sectiunea 3.1B), Infrastructura MCP Tools (sectiunea 10)*
*v1.2 — Adaugat: Inventar complet API Keys cu plan integrare (sectiunea 11), fix-uri urgente Gemini+Mistral*
*v1.3 — Adaugat: Audit tehnic profund backend/frontend (sec. 12+14), formule predictive complete (sec. 13), CAEN Rev.3 deadline CRITIC, Portal Just SOAP API oficial, data.gov.ro ONRC dataset, Piotroski F-Score, Beneish M-Score complet, Zmijewski X-Score*

---

> **Nota de citire:** Acest document este scris pentru utilizatorul de business, nu pentru programator.
> Termenii tehnici sunt explicati pe scurt acolo unde apar. Scopul e sa intelegi **ce face sistemul,
> cum gandeste, si ce mai are nevoie** pentru a deveni un instrument de analiza de top.

---

## CUPRINS

1. [Ce este RIS si ce problema rezolva](#1-ce-este-ris)
2. [Arhitectura generala — Cum functioneaza pe scurt](#2-arhitectura-generala)
3. [Module implementate — Fiecare componenta explicata](#3-module-implementate)
4. [Sistemul AI — Cine face ce, cat de sigur, cat de adanc](#4-sistemul-ai)
5. [Cum se foloseste — Ghid pas cu pas module principale](#5-ghid-utilizare)
6. [Ce lipseste — Gap analysis complet cu impact si solutii free](#6-gap-analysis)
7. [Comparatie cu sisteme similare de pe piata](#7-comparatie-piata)
8. [Roadmap de completare P0–P3 (100% free)](#8-roadmap)
9. [Concluzii si potential de dezvoltare](#9-concluzii)
10. [Infrastructura MCP Tools — Status si Utilizare](#10-infrastructura-mcp-tools)
11. [Infrastructura API Keys — Inventar Complet si Plan Integrare](#11-infrastructura-api-keys)
12. [Audit Tehnic Profund Backend — Probleme Concrete cu Numere de Linie](#12-audit-tehnic-profund-backend)
13. [Modele Predictive Avansate — Formule Complete si Implementare](#13-modele-predictive-avansate)
14. [Audit UI/Frontend — Gaps si Imbunatatiri Identificate](#14-audit-uifrontend)

---

## 1. CE ESTE RIS

### 1.1 Descriere simpla

**Roland Intelligence System (RIS)** este un sistem local de analiza a firmelor din Romania.
Functioneaza ca un „consultant de afaceri digital" care, in loc sa petreaca ore cautand informatii
pe internet si in registre oficiale, face totul automat in cateva minute.

**Ce poti face cu el:**
- Introduci codul unic de identificare (CUI) al unei firme
- Sistemul colecteaza automat date din 8+ surse oficiale si web
- 5 „agenti" AI analizeaza datele si genereaza un raport complet
- Primesti raportul in 6 formate diferite: PDF, Word, Excel, PowerPoint, HTML, format rezumat

**Exemple de intrebari la care RIS raspunde:**
- *„Aceasta firma cu care vreau sa colaborez e de incredere?"*
- *„Ce firme similare cu a mea au luat contracte de la stat?"*
- *„Firma X e in insolventa? A pierdut bani in ultimii ani?"*
- *„Care e riscul sa investesc intr-un parteneriat cu firma Y?"*

### 1.2 Cine poate folosi RIS

| Tip utilizator | Cum il ajuta RIS |
|---|---|
| **Antreprenor** | Verifica parteneri, clienti, furnizori inainte de a semna contracte |
| **Manager vanzari** | Identifica firme solvabile, cu contracte publice active |
| **Consultant financiar** | Rapoarte de due diligence rapide, scoring 0-100 |
| **Investitor** | Analiza comparativa a mai multor firme din acelasi sector |
| **Jurist / avocat** | Dosar rapid: litigii, insolventa, structura asociati |

### 1.3 Avantajul principal

Fara RIS, o analiza completa a unei firme ar dura **3-5 ore** si ar implica:
- Cautari manuale pe ANAF, ONRC, BPI
- Descarcari de bilanturi si interpretarea lor
- Cautari pe Google pentru stiri si litigii
- Scriere manuala a unui raport

Cu RIS: **aceleasi date, structurate si interpretate, in 2-3 minute**.

---

## 2. ARHITECTURA GENERALA

### 2.1 Viziunea de ansamblu — „Ce se intampla cand analizezi o firma"

Cand pornesti o analiza, sistemul urmeaza un flux precis, ca o linie de asamblare:

```
[TU introduci CUI]
       ↓
[AGENT 1: Colecteaza date din 8 surse oficiale]
  → ANAF (taxe, TVA, stare firma)
  → ANAF Bilant (cifra de afaceri, profit, angajati)
  → ONRC (asociati, administratori, cod CAEN)
  → BNR (cursuri valutare)
  → BPI (proceduri insolventa)
  → SEAP (contracte cu statul)
  → Tavily (search web: stiri, litigii, reputatie)
  → Brave Search (stiri suplimentare)
       ↓
[AGENT 2 + AGENT 3 ruleaza IN PARALEL]
  Agent 2: Informatii web suplimentare
  Agent 3: Analiza piata si competitie
       ↓
[AGENT 4: Verifica si Noteaza]
  → Elimina contradictiile dintre surse
  → Calculeaza Scorul de Risc 0-100
  → Genereaza lista „semnale de alarma"
  → Produce checklist Due Diligence
       ↓
[AGENT 5: Scrie Raportul]
  → Claude AI scrie textul narativ
  → Fiecare sectiune e scrisa de AI cu date reale
       ↓
[GENERATORUL DE RAPOARTE]
  → PDF, Word, Excel, PowerPoint, HTML, Rezumat 1 pagina
       ↓
[TU primesti raportul complet]
```

**Timp total:** 2-3 minute (prima analiza) / 10-30 secunde (daca firma a mai fost analizata)

### 2.2 Componente principale

| Componenta | Rol | Locatie tehnica |
|---|---|---|
| **Backend** | „Creierul" — primeste comenzi, coordoneaza agentii | Python / FastAPI |
| **Frontend** | Interfata web pe care o vezi in browser | React / TypeScript |
| **Baza de date** | Memoreaza toate analizele, rapoartele, setarile | SQLite |
| **Agentii AI** | Colecteaza, verifica si scriu rapoarte | Python + AI APIs |
| **Cache** | Memorie scurta: evita re-descarcarea datelor | In-memory + DB |

> **Ce inseamna „backend" si „frontend"?** Backend = partea invizibila, serverul care lucreaza.
> Frontend = interfata grafica pe care o vezi si o folosesti in browser.

---

## 3. MODULE IMPLEMENTATE

Sistemul are **13 module principale**. Mai jos fiecare e explicat: ce face, cum se porneste, ce produce.

---

### MODUL 1: Analiza Firma (Analiza noua)

**Ce face:** Porneste o analiza completa a oricărei firme din Romania dupa CUI.

**Cum functioneaza pas cu pas:**
1. Introduci CUI-ul firmei (ex: `12345678`)
2. Alegi tipul analizei (profil complet, risc partener, oportunitati licitatii etc.)
3. Alegi nivelul raportului: Rapid (1 min) / Standard (2 min) / Complet (3 min)
4. Sistemul porneste automat toti agentii
5. Vezi progresul in timp real (bara de progress live)
6. La final primesti raportul

**9 tipuri de analiza disponibile:**

| Tip | Ce produce | Cand il folosesti |
|---|---|---|
| **Profil Complet** | Tot ce se stie despre firma | Verificare generala |
| **Risc Partener** | Scor risc, semne de alarma, due diligence | Inainte de un contract |
| **Oportunitati Licitatii** | Contracte SEAP relevante, sectoare active | Daca vrei sa lucrezi cu statul |
| **Oportunitati Finantare** | Accesibilitate fonduri EU, eligibilitate | Daca vrei sa obtii finantare |
| **Analiza Intrare Piata** | Concurenta, pozitionare sector, bariere | Daca te gandesti sa intri intr-un sector |
| **Generare Leaduri** | Firme potentiale clienti dupa criterii | Prospectare comerciala |
| **Analiza Competitie** | Competitor direct, benchmark sector | Strategie competitiva |
| **Setup Monitorizare** | Urmarire continua a unei firme | Partener sau competitor important |
| **Raport Personalizat** | Intrebare libera in limbaj natural | Orice analiza specifica |

**Ce produce:**
- Raport complet cu scor 0-100, sectiuni narative, grafice
- Lista „semnale de alarma" (Early Warnings)
- Checklist Due Diligence (10 verificari)
- Benchmark vs media sectorului
- Comparatie cu raportul precedent (delta)

---

### MODUL 1B: Fonduri & Finantari Disponibile — AUDIT DETALIAT

> **Concluzie directa:** Modulul **exista ca interfata si tip de analiza**, dar in spate
> nu are nicio sursa dedicata de date despre fonduri. Este cel mai slab modul din sistem.

**Ce exista:**
- Tip de analiza `FUNDING_OPPORTUNITIES` declarat cu formular functional
- Formular colecteaza: CUI, tip investitie, suma necesara, datorii ANAF, angajati, regiune
- Sectiunile raportului: Rezumat executiv → Profil firma → Oportunitati → Recomandari
- `feasibility: 60%` — cel mai mic scor din toate tipurile (sistemul insusi recunoaste limitarea)

**Cum functioneaza in realitate:**
1. Preia profilul din ANAF + ONRC (CAEN, angajati, regiune)
2. Trimite o cautare Tavily generica (ex: *„fonduri europene constructii IMM Romania 2025"*)
3. AI-ul sintetizeaza ce gaseste pe web in ziua respectiva

**Instructiunea explicita din cod:**
> *„Prezinta DOAR oportunitati care apar in datele furnizate. Daca nu exista, scrie: Nu au fost identificate. NU INVENTA fonduri."*

**Ce LIPSESTE complet — surse neintegrate:**

| Sursa | Ce ar da | Status |
|---|---|---|
| `fonduri-ue.ro` (MFE) | Apeluri active FEDR/FSE/FC cu eligibilitate detaliata | ❌ neintegrat |
| `mfe.gov.ro/pnrr` | PNRR apeluri deschise, ghiduri solicitant, termene | ❌ neintegrat |
| `afir.ro` | Apeluri AFIR active (agricultua, rural, GAL per judet) | ❌ neintegrat |
| `startupnation.gov.ro` | Program Start-Up Nation — activ/inchis/conditii | ❌ neintegrat |
| `imm.gov.ro` | Granturi IMM, scheme de minimis | ❌ neintegrat |
| `ted.europa.eu` | Fonduri europene internationale, Horizon, EIC | ❌ neintegrat |
| Baza beneficiari UE | Firma a mai primit fonduri EU in trecut? | ❌ neintegrat |
| GAL-uri locale (150+) | Fonduri LEADER per judet/regiune (micro-granturi rural) | ❌ neintegrat |
| `antreprenoriat.gov.ro` | Programe nationale pentru antreprenori si startup | ❌ neintegrat |

**Tipuri de finantare neacoperite:**

| Tip fond | Exemple | Acoperit? |
|---|---|---|
| **Fonduri structurale EU** | POR, POCU, POC, POIM (2021-2027) | ❌ |
| **PNRR** | C1-C15, investitii, reforme | ❌ |
| **AFIR / FEADR** | Submasuri 4.1, 6.1, 6.2, Leader | ❌ |
| **GAL (Grupuri Actiune Locala)** | Micro-granturi rurale, sub 50.000 EUR | ❌ |
| **Start-Up Nation / Start-Up Plus** | Granturi 200.000 RON antreprenori | ❌ |
| **Granturi IMM (HG/OUG)** | Scheme de minimis, ajutor de stat | ❌ |
| **Horizon Europe** | Cercetare & inovare UE | ❌ |
| **EIC Accelerator** | Startup tech cu potential de scale-up | ❌ |
| **InvestEU** | Finantare pentru investitii durabile | ❌ |
| **BEI / FEI** | Imprumuturi si garantii pentru IMM | ❌ |

**Solutia recomandata (100% gratuita):**

**Varianta 1 — Baza locala JSON actualizata manual (efort MIC, impact MARE)**
Un fisier `funding_programs.json` cu toate programele active, actualizat lunar:
```json
{
  "program": "Start-Up Nation 2024",
  "eligibilitate": {
    "vechime_max_ani": 2,
    "fara_datorii_anaf": true,
    "angajati_max": 49,
    "caen_excluse": ["6420", "6491"]
  },
  "suma": {"min": 50000, "max": 200000, "moneda": "RON"},
  "termen": "2025-06-30",
  "regiuni": ["toate"],
  "link_ghid": "https://..."
}
```
Matching automat cu profilul firmei — fara API, fara costuri.

**Varianta 2 — Verificare eligibilitate automata pe datele existente**
Din ANAF stim deja: datorii (DA/NU), angajati, vechime, CAEN.
Putem filtra instantaneu: *„Firma X este eligibila pentru 3 din 12 programe active"*

**Varianta 3 — Integrare fonduri-ue.ro (beneficiari)**
API public gratuit — arata daca firma a mai primit fonduri EU.
Semnal pozitiv: capacitate administrativa demonstrata.

---

### MODUL 2: Rapoarte (Vizualizare si Descarcare)

**Ce face:** Afiseaza toate rapoartele generate si permite descarcarea lor in orice format.

**Formate disponibile:**

| Format | Continut | Folosit pentru |
|---|---|---|
| **PDF** | Raport complet cu watermark CONFIDENTIAL | Arhivare, trimitere profesionala |
| **Word (DOCX)** | Editabil, cu cuprins automat | Modificare manuala, prezentari |
| **Excel (XLSX)** | 4 foi: Overview, Financiar, Risc, Surse | Analiza numerica, grafice Excel |
| **PowerPoint (PPTX)** | 7 slide-uri executive | Prezentare la boardul de directori |
| **HTML** | Pagina web interactiva cu grafice | Vizualizare online, distributie link |
| **Rezumat 1 pagina** | Esentialul: scor, risc, concluzie | Brief rapid pentru management |
| **ZIP** | Toate formatele intr-un singur fisier | Download complet |

**Caracteristici speciale rapoarte:**
- Cuprins automat cu numere de pagina (PDF + Word)
- Grafice interactive (Excel + HTML)
- Watermark diagonal „CONFIDENTIAL" pe PDF
- Bookmark-uri de navigare in PDF
- Metadate document (data, versiune, autor)

---

### MODUL 3: Firme (Baza de Date Interna)

**Ce face:** Tine o baza de date cu toate firmele analizate, cu filtrare, sortare si export.

**Functii:**
- Lista tuturor firmelor analizate (cu scor, data ultima analiza, sector)
- Filtrare dupa: scor risc, sector CAEN, status TVA, data
- Sortare dupa: scor, CA, numar angajati
- Export CSV complet (pentru CRM sau Excel extern)
- Acces rapid la pagina firmei (detalii + re-analiza)
- **Favorite** — marcheaza firme importante cu stea
- **Tags si note** — adauga etichete si comentarii private per firma

**Informatii afisate per firma:**
- Denumire, CUI, CAEN (domeniu de activitate)
- Scor risc curent (0-100, culoare verde/galben/rosu)
- Cifra de afaceri ultima data disponibila
- Status ANAF (activ/inactiv/in insolventa)
- Data ultimei analize
- Trend scor (a crescut sau scazut fata de analiza anterioara)

---

### MODUL 4: Monitorizare (Urmarire Automata Firme)

**Ce face:** Urmareste automat firme selectate si te alerteaza cand se schimba ceva important.

**Cum functioneaza:**
1. Adaugi o firma la monitorizare (o data)
2. Sistemul verifica automat la fiecare 6 ore
3. Daca detecteaza schimbari, trimite alerta

**Ce detecteaza:**
- Schimbare scor risc (mai mare sau mai mic de X puncte)
- Firma devine inactiva la ANAF
- Aparitia in BPI (procedura insolventa deschisa)
- Scadere semnificativa cifra de afaceri (>30%)
- Schimbare administratori sau asociati
- Aparitie stiri negative (via Tavily)

**Canale de notificare:**
- Telegram (mesaj instant pe telefon)
- Email (configurabil)
- In-app (notificare in interfata web)

**Severity (nivel urgenta):**
- 🔴 **CRITIC** — insolventa, radiere, blocare ANAF
- 🟡 **ATENTIE** — scadere scor >15 puncte, pierdere angajati >30%
- 🟢 **INFO** — schimbare administratori, adauga SEAP

---

### MODUL 5: Comparatii (Analiza Side-by-Side)

**Ce face:** Compara 2-5 firme simultan, pe toate dimensiunile de analiza.

**Cum functioneaza:**
1. Introduci CUI-urile firmelor de comparat (2-5)
2. Sistemul analizeaza fiecare (sau foloseste date existente din cache)
3. Genereaza raport comparativ side-by-side

**Ce compara:**
- Scor risc total (0-100) per firma
- Cifra de afaceri si evolutie multi-an
- Profit / pierdere
- Numar angajati
- Benchmark sector (cum se pozitioneaza fata de media domeniului)
- Contracte SEAP (valoare totala)
- Semne de alarma per firma
- Due diligence checklist per firma

**Output:**
- PDF comparativ cu tabele side-by-side si concluzii narative
- Grafice comparatii (Chart.js in HTML)
- Recomanare: care firma prezinta riscul cel mai mic

---

### MODUL 6: Analiza Batch (Procesare in Masa)

**Ce face:** Analizeaza simultan zeci de firme dintr-un fisier CSV (lista CUI-uri).

**Cand il folosesti:**
- Ai o lista de 50 furnizori de analizat
- Vrei sa scorezi toti clientii activi din portofoliu
- Prospectezi o lista de potentiali parteneri

**Cum functioneaza:**
1. Pregatesti un fisier CSV cu coloana `cui` (si optional `name`)
2. Incarci fisierul in interfata Batch
3. Sistemul valideaza CUI-urile inainte de start (preview)
4. Porneste analizele in paralel (2 simultan pentru stabilitate)
5. Poti inchide browserul — procesarea continua in background
6. La final, descarci un ZIP cu toate rapoartele
7. Primesti si un CSV rezumat cu scorurile tuturor firmelor

**Limite:** Max 50 firme per batch, timeout 4 ore.

---

### MODUL 7: Dashboard (Pagina Principala)

**Ce face:** Ofera o vedere de ansamblu rapida asupra activitatii din sistem.

**Ce afiseaza:**
- Statistici: total analize, firme monitorizate, rapoarte generate
- Ultimele analize (lista rapida cu scor si status)
- Trend grafic (evolutia scorurilor in timp)
- Status surse de date (ANAF online? Tavily quota ok?)
- „Movers" — firme cu cea mai mare schimbare de scor recent
- Quick actions: „Analiza noua", „Comparatie", „Batch"

---

### MODUL 8: Setari (Configurare Sistem)

**Ce face:** Configureaza toate aspectele sistemului fara a edita fisiere tehnice.

**Ce poti configura:**
- API keys (Tavily, Groq, Gemini, Cerebras, Mistral, Telegram, Email)
- Vizualizare chei (ochiul toggle — arata/ascunde)
- Testare conexiune per serviciu (buton „Test")
- Watermark PDF (activat/dezactivat, text custom)
- Limite: max joburi simultane, delay-uri intre cereri
- Webhook URL (trimite notificari la sisteme externe)

---

### MODUL 9: Scoring 0-100 (Sistemul de Punctaj)

**Ce face:** Calculeaza un scor numeric de risc pentru fiecare firma analizata.

**Cum se calculeaza (simplificat):**

Scorul final este o medie ponderata din 6 dimensiuni:

| Dimensiune | Greutate | Ce masoara |
|---|---|---|
| **Financiar** | 30% | Cifra de afaceri, profit, evolutie, solvabilitate |
| **Juridic** | 20% | Litigii, proceduri insolventa, dosare judecatoresti |
| **Fiscal** | 15% | Stare TVA, datorii ANAF, risc fiscal |
| **Operational** | 15% | Angajati, vechime firma, stabilitate |
| **Reputational** | 10% | Prezenta online, recenzii, stiri |
| **Piata** | 10% | Contracte cu statul, pozitie vs competitori |

**Interpretare scor:**
- **70-100** → Verde — Firma solida, risc mic
- **40-69** → Galben — Firma acceptabila, risc moderat, atentie la detalii
- **0-39** → Rosu — Firma cu probleme serioase, risc mare

**Exemple practice:**
- O firma cu CA de 5M RON, profit pozitiv 3 ani consecutiv, fara litigii, cu contracte SEAP: **Scor 82 (Verde)**
- O firma cu pierderi 2 ani, in litigii, fara angajati dar cu CA mare: **Scor 28 (Rosu)**
- O firma noua (2 ani), fara bilant complet inca, prezenta online slaba: **Scor 47 (Galben)**

---

### MODUL 10: Early Warnings (Semnale de Alarma)

**Ce face:** Detecteaza automat combinatii de date care semnaleaza probleme.

**Reguli de detectare (exemple):**

| Semnalul | Ce inseamna | Nivel urgenta |
|---|---|---|
| 0 angajati + CA > 1M RON | Firma „fantoma" — nu produce cu oameni proprii | SUSPECT |
| Pierdere neta 2 ani consecutivi | Firma isi consuma capitalul | ATENTIE |
| Capital social 200 RON + CA > 500K | Subcapitalizare severa | ATENTIE |
| Firma inactiva la ANAF | Blocata de autoritati | CRITIC |
| Procedura insolventa deschisa | In pragul falimentului | CRITIC |
| Scadere CA > 30% intr-un an | Pierdere masiva de business | ATENTIE |
| Reducere angajati > 50% intr-un an | Restructurare dramatica | ATENTIE |
| Firma < 1 an + CA > 500K | Crestere anormala rapid | INFO |

---

### MODUL 11: Notificari (Centru Notificari)

**Ce face:** Centralizeaza toate alertele si notificarile din sistem.

**Functii:**
- Clopotel in interfata (badge cu numar necitiite)
- Dropdown cu ultimele notificari (click pe clopotel)
- Marcare citita / necitita
- Filtrare dupa severity (CRITIC / ATENTIE / INFO)
- Stergere notificari vechi
- Sincronizare cu Telegram si Email

---

### MODUL 12: Quick Score (Scor Rapid)

**Ce face:** Calculeaza un scor rapid (30 secunde) pentru pana la 20 CUI-uri simultan, fara AI, doar din ANAF.

**Cand il folosesti:**
- Vrei o pre-selectie rapida inainte de analiza completa
- Ai o lista scurta si vrei sa identifici rapid care merita analiza detaliata

**Limitare:** Nu include date web sau bilant complet — mai putin precis decat analiza completa.

---

### MODUL 13: Raport Comparativ Sectorial

**Ce face:** Compara o firma cu media firmelor din acelasi sector (CAEN).

**Date utilizate:**
- INS TEMPO (Institutul National de Statistica) — date oficiale pe sectoare
- ANAF Bilant — date financiare ale firmei analizate
- 122 coduri CAEN cu benchmark-uri precalculate

**Ce produce:**
- Pozitia firmei fata de media sectorului (percentila)
- Grafic comparativ CA, angajati, profit
- Concluzie: „firma e in top 25% din sector" sau „sub medie"

---

## 4. SISTEMUL AI

### 4.1 Cei 5 Agenti AI — Cine Face Ce

> **Ce inseamna „agent AI"?** Este un program care primeste o sarcina specifica,
> are acces la anumite instrumente (API-uri, baze de date) si ia decizii autonome
> pentru a-si indeplini sarcina. Nu e un singur AI omniscient — e o echipa de
> specialisti, fiecare cu rolul lui.

---

#### AGENT 1 — „Colectorul" (agent_official.py)

**Rol:** Merge la toate sursele oficiale si aduna date brute.

**Ce face concret:**
- Apeleaza simultan (in paralel) 8 surse de date
- Gestioneaza erorile (daca un API nu raspunde, continua cu restul)
- Aplica regula de asteptare (2 secunde intre cereri catre ANAF, pentru a nu fi blocat)
- Structureaza datele intr-un format comun pentru agentii urmatori

**Sursele pe care le apeleaza:**

| Sursa | Date obtinute | Certitudine |
|---|---|---|
| **ANAF API** | CUI valid, TVA activ/inactiv, adresa, stare firma, lista inactivi, risc fiscal | ★★★★★ OFICIAL |
| **ANAF Bilant** | Cifra de afaceri, profit net, angajati, capitaluri (2014-2024) | ★★★★★ OFICIAL |
| **openapi.ro (ONRC)** | Asociati, administratori, cod CAEN, data infiintare | ★★★★☆ STRUCTURAT |
| **BNR** | Cursuri EUR/RON (pentru conversii valutare) | ★★★★★ OFICIAL |
| **BPI (buletinul.ro)** | Proceduri insolventa deschise | ★★★★☆ OFICIAL |
| **SEAP** | Contracte publice castigate, licitatii active | ★★★★★ OFICIAL |
| **Tavily** | Stiri, litigii, reputatie web (search inteligent) | ★★★☆☆ ESTIMAT |
| **Brave Search** | Stiri suplimentare, prezenta brand | ★★★☆☆ ESTIMAT |

**Timeout:** Daca o sursa nu raspunde in 15 secunde, trece mai departe fara ea.

---

#### AGENT 2 — „Cercetasul Web" (agent nedenumit explicit)

**Rol:** Aduna informatii din spatiul public web care nu sunt in bazele de date oficiale.

**Ce cauta:**
- Recenzii si rating-uri ale firmei
- Profiluri LinkedIn ale directorilor
- Articole de presa business
- Prezenta social media
- Site-ul oficial al firmei

**Certitudine:** ★★★☆☆ (date estimate, nu oficiale)

---

#### AGENT 3 — „Analistul de Piata" (agent nedenumit explicit)

**Rol:** Analizeaza pozitia firmei in context de piata si competitie.

**Ce analizeaza:**
- Competitori directi (firme cu acelasi CAEN)
- Cota de piata estimata
- Tendinte sector
- Oportunitati si amenintari din piata

**Certitudine:** ★★★☆☆ (date estimate si interpretate)

---

#### AGENT 4 — „Arbitrul" (agent_verification.py)

**Rol:** Primeste datele de la Agentii 1, 2, 3 si le verifica, reconciliaza si noteaza.

**Ce face concret:**

1. **Rezolva contradictii:** Daca ANAF zice 50 angajati si un site zice 200, Agent 4 prioritizeaza ANAF (sursa officiala).

2. **Calculeaza scorul 0-100** pe 6 dimensiuni (detaliat la Modulul 9)

3. **Produce checklist Due Diligence** (10 verificari):
   - Firma activa la ANAF? DA/NU
   - CUI valid? DA/NU
   - TVA activ? DA/NU
   - Bilant disponibil ultimii 3 ani? DA/NU
   - Fara proceduri insolventa? DA/NU
   - Capital social > 1000 RON? DA/NU
   - Angajati declarati? DA/NU
   - Site web activ? DA/NU
   - Contracte publice (SEAP)? DA/NU
   - Fara litigii majore? DA/NU

4. **Detecteaza anomalii** (vezi Modulul 10 - Early Warnings)

5. **Calculeaza „completeness score"** — cat la suta din datele asteptate au fost gasite:
   - > 80%: Analiza completa, date de incredere
   - 50-80%: Analiza partiala, unele surse lipsesc
   - < 50%: Analiza incompleta — raportul va contine avertismente clare

**Regula de aur a Agent 4:** Daca datele sunt insuficiente, marcheaza explicit —
**NU inventeaza, NU estimeaza fara baza**.

---

#### AGENT 5 — „Scriitorul" (agent_synthesis.py)

**Rol:** Primeste toate datele verificate si scrie textul narativ al raportului.

**Cum scrie:**

```
Date verificate de Agent 4
         ↓
Alege furnizorul AI potrivit:
  - Sectiuni scurte (<200 cuvinte) → Groq (rapid, gratuit)
  - Sectiuni lungi si complexe → Claude AI (calitate maxima)
  - Fallback 1: Gemini 2.5 Flash
  - Fallback 2: Cerebras (Qwen 3 235B)
  - Fallback 3: Mistral Small
         ↓
Injecteaza instructiuni anti-halucinare:
  - „Nu inventa date care nu exista"
  - „Marcheaza explicit datele lipsa"
  - „Nu specula dincolo de datele disponibile"
         ↓
Genereaza text sectiune cu sectiune
         ↓
Valideaza: exista statistici imposibile? cifre inventate?
         ↓
Text final al raportului
```

**Sectiunile raportului scrise de AI:**
1. Prezentare generala firma
2. Profil financiar (evolutie multi-an)
3. Analiza risc
4. Pozitie in piata si competitie
5. Due diligence summary
6. Oportunitati identificate
7. Riscuri si recomandari
8. Concluzii si scor final

---

### 4.2 Sistemul de Furnizori AI — Fallback „5 niveluri"

> **Ce inseamna „fallback"?** Daca furnizorul principal AI nu functioneaza sau e ocupat,
> sistemul trece automat la urmatorul. Asa raportul se genereaza intotdeauna.

```
Nivel 1: CLAUDE (Anthropic) — calitate maxima, via CLI local
   ↓ daca nu raspunde in timp
Nivel 2: GROQ (Llama 4 Scout) — rapid, gratuit, bun pentru sectiuni scurte
   ↓ daca nu raspunde
Nivel 3: GEMINI 2.5 Flash (Google) — context 1 milion tokeni, gratuit
   ↓ daca nu raspunde
Nivel 4: CEREBRAS (Qwen 3 235B) — 1 milion tokeni/zi gratuit
   ↓ daca nu raspunde
Nivel 5: MISTRAL Small — server european, 1 miliard tokeni/luna gratuit
   ↓ daca nimic nu merge
Template text: „Date incomplete — analiza manuala recomandata"
```

**Toti 5 furnizori sunt gratuti** in limitele de utilizare configurate.

---

### 4.3 Certitudinea Datelor — Ce Poti Crede si Cat

Sistemul foloseste un sistem de „niveluri de incredere" pentru fiecare informatie:

| Nivel | Sursa | Ce inseamna in practica |
|---|---|---|
| ★★★★★ **OFICIAL** | ANAF, ONRC, BNR, SEAP, BPI | Dat de autoritate de stat. 100% legal. Nu se contesta. |
| ★★★★☆ **VERIFICAT** | listafirme.ro, topfirme.com, site oficial firma | Sursa recunoscuta, date de obicei corecte, posibile intarzieri |
| ★★★☆☆ **ESTIMAT** | Tavily, Google, presa, LinkedIn | Informatie publica dar neoficiala, poate fi depasita sau incompleta |
| ★☆☆☆☆ **EXCLUS** | Forumuri, comentarii anonime, opinii | Sistemul NU foloseste aceste surse |

**Cum apare certitudinea in raport:**
- Datele oficiale sunt prezentate direct: „Cifra de afaceri: 2.3M RON (ANAF Bilant 2023)"
- Datele estimate sunt marcate: „[ESTIMAT] Aproximativ 15 angajati conform LinkedIn"
- Datele lipsa sunt mentionate explicit: „[INDISPONIBIL] Nu s-au gasit date despre litigii"

---

### 4.4 Adancimea Executiei — Cat de „adanc" merge sistemul

**Nivel 1 — RAPID** (1 minut):
- Doar Agent 1 (surse oficiale)
- Scor risc calculat
- Raport 2-3 pagini
- Ideal pentru: verificare rapida, batch mari

**Nivel 2 — STANDARD** (2 minute):
- Agent 1 + Agent 2 + Agent 3
- Scor risc + Early Warnings + Benchmark sector
- Raport 6-8 pagini
- Ideal pentru: decizie de colaborare, verificare partener

**Nivel 3 — COMPLET** (3 minute):
- Toti 5 agentii
- Scor complet + Due Diligence + Analiza comparativa + Key Takeaways
- Raport 12-15 pagini in toate formatele
- Ideal pentru: investitii, due diligence profesional, dosar complet

---

## 5. GHID UTILIZARE — Cum Faci Analizele Principale

### 5.1 Analiza Noua (pas cu pas)

**Scenariu:** Vrei sa verifici firma „Construct SA" cu CUI 12345678, un potential furnizor.

**Pasul 1:** Mergi la „Analiza noua" din meniu (bara laterala stanga)

**Pasul 2:** Ecranul „Wizard" are 4 pasi:
- **Pas 1:** Introdu CUI-ul → sistemul valideaza automat (cifra de control MOD 11)
  - Daca CUI e invalid → avertisment imediat, nu mai continui degeaba
- **Pas 2:** Alege tipul analizei → „Risc Partener" pentru furnizori
- **Pas 3:** Alege nivelul → 2 (Standard) pentru o verificare serioasa dar rapida
- **Pas 4:** Confirma si porneste

**Pasul 3:** Ecranul de progres arata in timp real:
```
✅ Validare CUI — 1s
✅ ANAF — date obtinute (2.1s)
✅ ANAF Bilant — 3 ani date financiare (4.3s)
✅ ONRC — asociati si administratori (3.8s)
⏳ Tavily — cautare web...
✅ SEAP — 3 contracte publice gasite (5.1s)
✅ Verificare si scoring (2.2s)
✅ Sinteza AI — raport generat (28s)
✅ Raport PDF, Word, Excel generat (3.1s)
```

**Pasul 4:** Raportul e gata. Descarci PDF-ul si gasesti:
- Prima pagina: Scor 74/100 (Verde), rezumat executiv
- Pagina 2-3: Date financiare + grafic evolutie CA 3 ani
- Pagina 4: Due Diligence checklist — 8/10 checkuri trecute
- Pagina 5: Semnale de alarma (in acest caz: 0 — firma OK)
- Pagina 6: Analiza concurenta si pozitie sector
- Pagina 7: Recomandari AI si concluzii

---

### 5.2 Monitorizare (pas cu pas)

**Scenariu:** Ai semnat contractul cu Construct SA si vrei sa fii alertat daca situatia lor se schimba.

**Pasul 1:** Mergi la „Monitorizare" din meniu

**Pasul 2:** Click „Adauga firma" → introdu CUI-ul → set optiuni:
- Frecventa verificare: 6h / 12h / 24h
- Alertez daca scorul scade cu mai mult de: 10 puncte
- Alertez pentru: insolventa, inactivare ANAF, schimbare administratori

**Pasul 3:** Sistemul ruleaza automat. In background, la fiecare 6 ore:
- Re-verifica ANAF, BPI, scoringul
- Compara cu ultima verificare
- Daca ceva s-a schimbat → trimite alerta pe Telegram

**Exemplu alerta primita pe Telegram:**
```
🔴 ALERTA CRITICA — Construct SA (CUI: 12345678)
Procedura insolventa deschisa la Tribunalul Bucuresti
Data detectare: 07.04.2026 14:32
Scor risc: 74 → 12 (scadere 62 puncte)
[Vezi raport actualizat]
```

---

### 5.3 Comparatii (pas cu pas)

**Scenariu:** Ai 3 furnizori si vrei sa alegi cel mai sigur.

**Pasul 1:** Mergi la „Comparatii" → „Comparatie noua"

**Pasul 2:** Adauga cele 3 CUI-uri (unul pe rand)

**Pasul 3:** Sistemul genereaza raport comparativ cu:
- Tabel side-by-side: Scor / CA / Angajati / Litigii / SEAP
- Grafic bara comparativ
- Concluzie AI: „Firma B prezinta cel mai mic risc. Firma A are un litigiu major in curs."

**Pasul 4:** Descarci PDF comparativ — ideal pentru prezentari interne.

---

### 5.4 Batch Analysis (pas cu pas)

**Scenariu:** Departamentul de achizitii are o lista cu 30 de furnizori de verificat.

**Pasul 1:** Pregatesti un fisier Excel/CSV cu o coloana „cui":
```
cui
12345678
23456789
34567890
...
```

**Pasul 2:** Salvezi ca `.csv` → mergi la „Analiza Batch" → Upload

**Pasul 3:** Sistem arata preview: „30 CUI-uri valide, 0 invalide. Estimat: 25 minute."

**Pasul 4:** Pornesti → poti inchide browserul

**Pasul 5:** Primesti notificare (Telegram/Email) cand gata

**Pasul 6:** Descarci ZIP cu:
- 30 de rapoarte individuale (PDF fiecare)
- 1 fisier CSV rezumat: `CUI, Firma, Scor, Culoare, CA, Angajati, Status`

---

## 6. GAP ANALYSIS — Ce Lipseste si Ce Impact Are

Aceasta sectiune raspunde la intrebarea: **„Ce surse de date publice exista in Romania (si EU)
pe care sistemul nu le foloseste inca, si ce am pierde fara ele?"**

Analiza e structurata pe categorii de date.

---

### 6.1 DATE JURIDICE — Cel mai important gap

#### GAP 1: Portal Just — Dosare Judecatoresti Oficiale

**Ce lipseste:**
Sistemul actual cauta litigii prin Tavily (cautare web). Tavily gaseste ce apare in presa
sau pe site-uri, dar **NU are acces direct la Portal Just** (dosare.just.ro) — baza de date
oficala a tuturor dosarelor judecatoresti din Romania.

**Ce ar aduce:**
- Numarul exact de dosare (civil, comercial, penal) in care firma e parte
- Calitatea: reclamant sau parat?
- Stadiul dosarului (judecata, apel, fond)
- Valoarea litigiului (in unele dosare e publica)

**Impact fara el:** Scorul juridic se bazeaza pe date incomplete. O firma cu 20 de dosare
dar care nu apare in presa ar scori la fel ca una fara dosare.

**Cum se poate accesa:** Portal Just expune un **Web Service SOAP oficial si public** — NU necesita scraping fragil:
- Endpoint: `http://portalquery.just.ro/query.asmx`
- WSDL: `http://portalquery.just.ro/query.asmx?WSDL`
- Metoda: `CautareDosare(numeParte, obiect, numardosar, instanta)` → max 1.000 dosare/query
- Date returnate: numar dosar, instanta, sectie, categorie, stadiu procesual, parti, termene
- Implementare Python: `pip install zeep` + client SOAP (`zeep.Client(WSDL)`)
- Documentatie oficiala: `https://portal.just.ro/SitePages/acces.aspx`
- Servicii comerciale care il folosesc deja: alertacui.ro, termene.ro, lege5.ro

**Efort implementare:** MIC — endpoint SOAP public, gratuit, fara autentificare, biblioteca zeep disponibila.

**Concluzie:** [CRITIC — lipseste o sursa de nivel 1 — SOAP API OFICIAL DISPONIBIL]

---

#### GAP 2: Monitorul Oficial — Acte Constitutive si Schimbari

**Ce lipseste:**
Monitorul Oficial (`monitoruloficial.ro` si `publicatii.mfinante.gov.ro`) publica:
- Modificari de statut (schimbare sediu, obiect de activitate)
- Fuziuni si achizitii
- Dividende platite
- Dizolvari voluntare
- Acte de numire/revocare administratori (oficial, nu din ONRC)
- Sanctiuni administrative publice

**Impact fara el:**
- Nu stim daca firma si-a schimbat adresa recent (semnal de evitare fiscala)
- Nu stim de fuziuni (firma poate fi de fapt alta entitate acum)
- Nu stim de dizolvare voluntara in curs

**Cum se poate accesa:** Site public cu API de cautare. Parte din surse Termene.ro (competitor).

**Efort implementare:** MEDIU

**Concluzie:** [IMPORTANT — pierdere informatii structurale despre firma]

---

#### GAP 3: AEGRM — Arhiva Electronica de Garantii Reale Mobiliare

**Ce lipseste:**
`aegrm.ro` — baza de date publica cu toate garantiile reale inscrise pe active mobile:
ipoteci pe utilaje, gajuri pe stocuri, garantii pe conturi bancare.

**Ce ar spune despre o firma:**
- Are active ipotecate catre banci sau creditori? = firma cu datorii garantate
- Are garantii in favoarea altora? = resurse financiare angajate
- A primit executari silite?

**Impact fara el:**
Nu vedem daca firma are active sechestrate sau datorii garantate pe bunuri.
O firma poate parea OK pe ANAF dar sa aiba active total ipotecate.

**Efort implementare:** MIC-MEDIU (API REST public)

**Concluzie:** [IMPORTANT — vizibilitate financiara incompleta]

---

### 6.2 DATE FINANCIARE SUPLIMENTARE

#### GAP 4: Ministerul Finantelor — Publicatii Bilant

**Ce lipseste:**
Ministerul de Finante publica pe `mfinante.gov.ro` bilanturi complete in format XBRL/XML
inclusiv note explicative si detalierea contabila, mai detailata decat ANAF Bilant.

**Ce ar aduce:**
- Detalii cont: datorii pe termen scurt vs lung (nu doar total)
- Creante (ce i se datoreaza firmei)
- Stocuri (produse nevandute)
- Cash disponibil

**Impact fara el:**
Analiza financiara e bazata pe indicatori agregati (CA, profit, angajati).
Nu vede structura bilantului (lichiditate, indatorare detaliata).

**Efort implementare:** MEDIU (parsare XML XBRL)

**Concluzie:** [IMPORTANT pentru analiza financiara profunda]

---

#### GAP 5: AFIR / PNRR / Fonduri Europene Obtinute

**Ce lipseste:**
Sistemul nu stie daca firma a obtinut sau a aplicat pentru:
- Fonduri AFIR (agricultura si rural)
- Fonduri PNRR (investitii nationale)
- Fonduri FEDR / FSE (structural europene)
- Ajutoare de stat notificate la Consiliul Concurentei

**Ce ar spune:**
- Firma care a obtinut un grant PNRR de 500K EUR = firma cu capacitate de a implementa proiecte mari
- Firma care a pierdut finantare EU = potential probleme de conformitate

**Surse publice gratuite:**
- `fonduri-ue.ro` (MFE) — baza de date beneficiari UE
- `pnrr.gov.ro` — contracte PNRR publice
- `afir.info` — beneficiari AFIR

**Efort implementare:** MIC (API sau scraper)

**Concluzie:** [RELEVANT — adauga o dimensiune de finantare europeana complet absenta]

---

### 6.3 DATE PROPRIETATE SI ACTIVE

#### GAP 6: ANCPI — Proprietati Imobiliare (partial public)

**Ce lipseste:**
Agentia Nationala de Cadastru si Publicitate Imobiliara (`ancpi.ro`) —
informatii despre imobile detinute sau ipotecate de firme.

**Ce e public gratuit:**
- Numarul de imobile inregistrate pe un CUI (nu adresele complete)
- Existenta sarcinilor (ipoteci) pe imobile

**Impact:**
O firma cu 10 imobile proprietate = active reale, colateral solid.
O firma fara imobile proprii dar cu ipoteci mari = vulnerabila.

**Efort implementare:** MIC (API partial disponibil)

---

#### GAP 7: OSIM — Marci Comerciale si Brevete

**Ce lipseste:**
Oficiul de Stat pentru Inventii si Marci (`osim.ro`) — registrul marcilor si brevetelor.

**Ce ar spune:**
- Firma are marci comerciale inregistrate? = investit in brand, planuri pe termen lung
- Are brevete de inventie? = firma inovativa, activ intangibil de valoare
- Marca e in litigiu? = risc brand

**Efort implementare:** MIC (API public OSIM)

**Concluzie:** [RELEVANT pentru firme din sector bunuri de larg consum, tehnologie]

---

### 6.4 DATE RESURSE UMANE SI CONFORMITATE

#### GAP 8: REVISAL / ITM — Istoricul Angajatilor Reali

**Ce lipseste:**
Inspectia Muncii (ITM) mentine REVISAL — registrul electronic al salariatilor.
Date partiale sunt publice via `inspectmuncii.ro`.

**Ce ar spune:**
- Firma a avut conflicte de munca? (greve, sesizari ITM)
- A avut accidente de munca raportate?
- A primit sanctiuni ITM?

**Impact:**
Diferenta intre „angajatii declarati la ANAF" si „angajatii reali din REVISAL" = posibila munca la negru.

**Efort implementare:** MEDIU (date partial structurate)

---

#### GAP 9: ANPC — Sanctiuni Protectia Consumatorilor

**Ce lipseste:**
Autoritatea Nationala pentru Protectia Consumatorilor (`anpc.ro`) publica
sanctiunile aplicate firmelor pentru incalcari ale drepturilor consumatorilor.

**Ce ar spune:**
- Firma a primit amenzi ANPC? = probleme cu calitatea produselor/serviciilor
- E in baza de date „firme periculoase"?

**Efort implementare:** MIC (lista publica pe site)

**Concluzie:** [RELEVANT pentru firme din retail, servicii catre populatie]

---

### 6.5 DATE SECTOARE REGLEMENTATE

#### GAP 10: ANRE — Autorizatii Energie

**Ce lipseste:**
Autoritatea Nationala de Reglementare in Energie (`anre.ro`) — licente si autorizatii.

**Relevant pentru firme din:**
- Productie si distributie energie electrica
- Furnizori gaze naturale
- Panouri solare, eoliene
- Carburanti

**Ce ar spune:**
- Firma are licenta valida de furnizare energie? = activitate legala
- Licenta a expirat sau e suspendata? = risc operational

**Efort implementare:** MIC (registru public)

---

#### GAP 11: ASF — Firme Financiare si Asigurari

**Ce lipseste:**
Autoritatea de Supraveghere Financiara (`asf.ro`) — registrul firmelor autorizate:
brokeri, fonduri de investitii, societati de asigurare.

**Relevant pentru:** Orice firma din sector financiar.

**Ce ar spune:**
- Firma are autorizatie ASF valida? = functineaza legal in sectorul financiar
- A primit sanctiuni sau avertismente?

---

#### GAP 12: Consiliul Concurentei — Investigatii si Amenzi

**Ce lipseste:**
Consiliul Concurentei (`consiliulconcurentei.ro`) — investigatii in curs si amenzi aplicate.

**Ce ar spune:**
- Firma e investigata pentru intelegeri de pret? = risc reputational si financiar major
- A primit amenda pentru pozitie dominanta abuziva?

**Efort implementare:** MIC (date publice pe site)

**Concluzie:** [IMPORTANT pentru firme mari din sectoare concentrate: telecom, energie, constructii]

---

### 6.6 DATE WEB SI SOCIAL MEDIA (GRATUITE)

#### GAP 13: Google Maps / Places — Recenzii si Rating

**Ce lipseste:**
Google Maps are recenzii publice pentru milioane de firme din Romania.
Google Places API are un nivel gratuit generos (28.500 cereri/luna).

**Ce ar aduce:**
- Rating general (1-5 stele)
- Numar recenzii (volum = popularitate)
- Cuvinte cheie din recenzii („escrocherie", „recomand", „termen depasit")
- Ore de program (firma functioneaza efectiv?)

**Impact:**
Dimensiunea „Reputational" din scor e bazata pe prezenta web generica.
Cu Google Maps ar deveni concreta si verificabila.

**Efort implementare:** MIC (API gratuit cu cont Google Cloud)

---

#### GAP 14: LinkedIn — Cresterea Echipei si Calitatea Managementului

**Ce lipseste:**
LinkedIn are profiluri publice pentru:
- Numarul angajatilor declarati pe LinkedIn (adesea mai realist decat ANAF)
- Senioritatea echipei de management
- Rotatia angajatilor (fluctuatie mare = problema interna)
- Activitate recenta a firmei pe platforme

**Cum se acceseaza gratuit:** Cautare web via Tavily/Brave + scraping profil public.

**Efort implementare:** MIC (via Tavily care deja e integrat)

---

#### GAP 15: Stiri Economice Romanesti Structurate

**Ce lipseste:**
Sistemul cauta stiri via Tavily dar nu are integrare directa cu:
- `zf.ro` (Ziarul Financiar) — sursa primara business Romania
- `profit.ro` — stiri corporative
- `economica.net`
- `wall-street.ro`
- `biz.ro`

**Impact:**
Tavily cauta broad. O integrare directa cu surse economice verificate ar oferi stiri
mai relevante si mai recente pentru firme (fuziuni, contracte mari, scandaluri).

**Efort implementare:** MIC-MEDIU (RSS feeds + parsare)

---

#### GAP 16: Harta Retelelor de Firme (Relatii prin Asociati Comuni)

**Ce lipseste:**
Sistemul stie asociatii si administratorii unei firme (din openapi.ro).
Dar **nu construieste reteaua** — nu vede ca „Ionescu Ion" e administrator la alte 5 firme,
dintre care 2 sunt in insolventa.

**Ce ar arata:**
- „Administratorul firmei X a mai fost admin la 3 firme in insolventa"
- „Asociatul Y detine 8 firme active, 2 radiate, 1 in insolventa"
- Legaturi intre firme prin persoane comune

**Impact:**
Acesta e unul din cele mai puternice semnale de risc existente. Sisteme ca Termene.ro
ofera aceasta functie ca feature premium. Ar putea fi implementat **gratuit** cu datele
deja disponibile din openapi.ro.

**Efort implementare:** MEDIU (graph DB sau query recursiv SQLite)

**Concluzie:** [CRITIC — functie de maxim impact, date deja disponibile in sistem]

---

#### GAP 17: Date Import/Export — Directia Vamilor

**Ce lipseste:**
Datele de comert exterior (importuri/exporturi) sunt partial publice via:
- `customs.ro` (Directia Vamilor)
- `eurostat.ec.europa.eu` (comert EU)
- `trademap.org` (gratuit cu cont)

**Ce ar spune:**
- Firma importa mult din China? = dependenta de un singur furnizor
- Firma exporta? = expunere valutara, diversificare piata
- Valoarea importurilor vs CA = marja estimata

**Efort implementare:** MARE (date agregate, nu per firma)

---

#### GAP 18: Licitatii Europene TED (Tenders Electronic Daily)

**Ce lipseste:**
TED (`ted.europa.eu`) — baza de date oficala EU cu toate licitatiile publice
din toate tarile membre, inclusiv Romania.

**Ce ar aduce:**
- Firma a castigat contracte in afara Romaniei?
- E prezenta pe piete internationale?
- Parteneriate cu firme straine?

**Efort implementare:** MIC (API REST gratuit TED)

---

### 6.7 FUNCTIONALITATI ANALITICE LIPSA

#### GAP 19: Analiza Cash Flow Reala

**Ce lipseste:**
Bilantul ANAF da CA si profit. Dar **cash flow-ul** (cati bani intra/ies efectiv) e diferit.
O firma poate fi profitabila pe hartie dar in insolventa cash.

**Ce lipseste:**
- Calcularea ratei de conversie profit → cash
- Detectarea „profit pe hartie + cash negativ"
- Indicatorul DSO (Days Sales Outstanding) — cat timp ii ia sa incaseze facturile

**Impact:** Cazul clasic al firmelor care par bune dar nu pot plati = cel mai frecvent risc practic.

---

#### GAP 20: Scoring Predictiv (nu doar descriptiv)

**Ce lipseste:**
Scorul actual e **descriptiv** — spune „acum firma are risc X".
Un sistem complet ar fi si **predictiv** — „probabilitatea de insolventa in 12 luni e Y%".

**Modele existente publice:**
- **Altman Z-Score** (formula publica din 1968, inca folosita)
  - Foloseste: CA, Active totale, Capitaluri proprii, Profit, Datorii
  - Rezultat: Z > 2.99 = safe, 1.81-2.99 = grey zone, < 1.81 = risc insolventa
- **Beneish M-Score** (detectie manipulare financiara)
  - 8 indicatori din bilant → probabilitate de „ajustare creativa" a conturilor

**Efort implementare:** MIC (formule matematice aplicate pe datele deja existente)

**Concluzie:** [IMPORTANT — transforma RIS dintr-un sistem descriptiv intr-unul predictiv]

---

#### GAP 21: Istoric Complet Scor per Firma (Trend Lung)

**Ce exista:** Scorul e stocat in baza de date la fiecare analiza.

**Ce lipseste:**
O vizualizare grafica pe mai multi ani (nu doar ultimele 5 analize) si
corelarea cu evenimente (a scazut scorul cand a aparut o stire negativa?).

---

#### GAP 22: Exportul Retelei de Firme in Format Grafic

**Ce lipseste:**
Vizualizare grafica a relatiilor dintre firme (graph visualization).
Ex: un „spider diagram" care arata: Firma A → Ionescu Ion → Firma B, C, D.

**Tool gratuit:** `vis.js` sau `D3.js` (librarii JavaScript gratuite)

---

## 7. COMPARATIE CU SISTEME SIMILARE DE PE PIATA

### 7.1 Termene.ro (gratuit partial)

| Functie | Termene.ro (free) | RIS |
|---|---|---|
| Date ANAF | ✅ | ✅ |
| Bilanturi | ✅ | ✅ |
| Insolventa BPI | ✅ | ✅ |
| Monitorul Oficial | ✅ | ❌ **LIPSA** |
| Dosare judecatoresti | ✅ | ⚠️ partial (via Tavily) |
| Retea firme (asociati) | ✅ (premium) | ❌ **LIPSA** |
| Scor risc numeric | ✅ (premium) | ✅ 0-100 |
| Rapoarte PDF/Word | ❌ | ✅ |
| Analiza AI narativa | ❌ | ✅ |
| Monitorizare cu alerte | ✅ (premium) | ✅ gratuit |
| Analiza batch CSV | ❌ | ✅ |
| Comparatie firme | ❌ | ✅ |
| Benchmark sector | ❌ | ✅ |
| SEAP contracte | ✅ | ✅ |
| Fonduri EU | ❌ | ❌ **lipsa ambii** |
| Google Maps recenzii | ❌ | ❌ **lipsa ambii** |

**Concluzie:** RIS este mai avansat in analiza si rapoarte. Termene.ro acopera mai bine
datele juridice si structurale (Monitorul Oficial, retea firme).

---

### 7.2 Listafirme.ro (gratuit)

| Functie | Listafirme.ro | RIS |
|---|---|---|
| Date ONRC | ✅ | ✅ |
| Bilanturi simple | ✅ | ✅ |
| Grafice CA/profit | ✅ | ✅ |
| Analiza risc | ❌ | ✅ |
| Rapoarte descarcabile | ❌ | ✅ |
| AI narativ | ❌ | ✅ |
| Monitoring | ❌ | ✅ |

---

### 7.3 OpenCorporates (gratuit, international)

| Functie | OpenCorporates | RIS |
|---|---|---|
| Date firme Romania | ✅ (limitat) | ✅ complet |
| Date internationale | ✅ 140+ tari | ❌ |
| API gratuit | ✅ 500 req/zi | ✅ |
| Analiza financiara | ❌ | ✅ |
| Scoring risc | ❌ | ✅ |

**Potential:** Integrarea cu OpenCorporates ar adauga date despre firme straine
care au relatii cu firme romanesti (asociati internationali, grupuri multinationale).

---

### 7.4 Ce au sistemele profesionale platite (Bloomberg, Coface, D&B) pe care RIS NU le are

> Mentionam acestea nu pentru a le implementa (sunt platite), ci pentru a intelege
> distanta dintre RIS si cele mai avansate sisteme din lume.

| Functie | Sisteme premium | RIS | Posibil free? |
|---|---|---|---|
| Credit scoring bancar | ✅ | ❌ | Partial (Altman Z-Score) |
| Date financiare real-time | ✅ | ❌ | ❌ (ANAF e cu 1-2 ani intarziere) |
| Verificare identitate director | ✅ | ❌ | Partial (ONRC public) |
| Conexiuni internationale (grupuri) | ✅ | ❌ | Partial (OpenCorporates) |
| Detectie frauda avansat | ✅ | Partial | Imbunatatibil |
| Scoring predictiv ML | ✅ | ❌ | Implementabil (Altman, Beneish) |

---

## 8. ROADMAP DE COMPLETARE P0–P3 (100% GRATUIT)

Toate solutiile propuse mai jos utilizeaza exclusiv surse si instrumente gratuite.

---

### P0 — CRITIC (implementare imediata, impact maxim)

#### P0.0 — CAEN Rev.3 — Deadline OBLIGATORIU 25 Septembrie 2026
**Gap:** NOU — identificat din research extern
**Context:** Din 1 ianuarie 2025, CAEN Rev.3 e obligatoriu pentru firme noi. Din **25 septembrie 2026**, ANAF opereaza EXCLUSIV cu Rev.3 — toate firmele existente trec automat.
**Ce se face:** Actualizeaza `backend/agents/tools/caen_context.py` (122 coduri, Rev.2) cu nomenclatorul Rev.3. Mapare Rev.2 → Rev.3 disponibila oficial la ONRC.
**Risc daca nu se face:** Dupa sept 2026, sistemul va raporta coduri CAEN deprecate — toate analizele vor fi eronate pe dimensiunea CAEN.
**Efort:** Mediu (1-2 zile, dar poate fi facut incremental)

#### P0.1 — Retea firme prin asociati comuni
**Gap:** #16
**Date necesare:** Deja in sistem (openapi.ro)
**Ce se face:** Query SQL recursiv: „gaseste toti asociatii firmei X, apoi gaseste toate firmele in care ei mai apar"
**Output:** Sectiune noua in raport: „Reteaua de firme a asociatilor"
**Risc detectat:** Daca un asociat a mai condus firme in insolventa — SEMNAL ROSU

#### P0.2 — Portal Just — Dosare Judecatoresti
**Gap:** #1
**Sursa:** `portal.just.ro` (public, gratuit)
**Ce se face:** Scraper care cauta CUI-ul in baza de dosare
**Output:** Numar dosare, calitate (reclamant/parat), stadiu, valoare
**Impact:** Dimensiunea „Juridic" din scor devine mult mai precisa

#### P0.3 — Portal Just SOAP API — Dosare Judecatoresti Oficiale (revizuit)
**Gap:** #1 — EFORT REDUS SEMNIFICATIV fata de estimarea initiala
**Sursa:** `http://portalquery.just.ro/query.asmx` — SOAP API oficial public, fara autentificare
**Ce se face:** `pip install zeep` + nou fisier `backend/agents/tools/just_client.py` (~80 linii)
**Output:** Numar dosare, instante, stadiu, calitate (reclamant/parat)
**Impact:** Dimensiunea Juridic din scor devine bazata pe date oficiale, nu Tavily
**Efort:** MIC (1 zi) — NU necesita scraping, API SOAP documentat oficial

#### P0.4 — Modele Predictive: Altman Z''_EMS + Piotroski F-Score + Beneish M-Score
**Gap:** #20 — EXTINS cu 3 modele, nu doar Altman
**Date necesare:** Bilantul ANAF (deja in sistem)
**Ce se face:** Formulele matematice pe datele existente — 3 modele complementare:
- **Altman Z''_EMS** (Emerging Markets): `3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4` → insolventa 2 ani
- **Piotroski F-Score**: 9 criterii binare (0/1) pe bilant → sanatate financiara trending
- **Beneish M-Score** (5 var): `−6.065 + 0.823*DSRI + 0.906*GMI + 0.593*AQI + 0.717*SGI + 7.770*TATA` → detectie manipulare
- **Zmijewski X-Score** (optional): model logistic pentru confirmare distress
**Biblioteca:** `pip install credpy` — implementeaza Altman, Springate, Zmijewski din 31 campuri bilant
**Output:** „Probabilitate insolventa 12 luni: 23% (zona gri) | F-Score: 7/9 (solid) | M-Score: −2.5 (non-manipulator)"
**Impact:** RIS devine predictiv, nu doar descriptiv. Formule detaliate in Sectiunea 13.

#### P0.5 — data.gov.ro ONRC Dataset Local
**Gap:** NOU — identificat din research extern
**Sursa:** `https://data.gov.ro/dataset/firme-06-10-2025` — Licenta CC BY 4.0
**Fisiere:** `OD_FIRME.CSV` (660 MB), `OD_CAEN_AUTORIZAT.CSV` (392 MB), `OD_STARE_FIRMA.CSV` (89 MB)
**Ce se face:** Importa local in SQLite pentru comparatii de sector la scara mare
**Avantaj vs openapi.ro:** Nu mai esti limitat la 100 req/luna. Toate firmele din Romania disponibile local.
**Impact:** Benchmark sector CAEN devine precis (nu estimat), cautare firme similare e instantanee
**Efort:** Mediu (2-3 zile pentru import + indexare)

---

### P1 — IMPORTANT (urmatoarea iteratie)

#### P1.1 — Monitorul Oficial
**Gap:** #2
**Sursa:** `monitoruloficial.ro` (public)
**Ce adauga:** Modificari statut, fuziuni, dizolvari voluntare, sanctiuni

#### P1.2 — AEGRM — Garantii Reale
**Gap:** #3
**Sursa:** `aegrm.ro` API REST (public, gratuit)
**Ce adauga:** Ipoteci, gajuri, executari silite pe active

#### P1.3 — Google Maps Reviews
**Gap:** #13
**Sursa:** Google Places API (gratuit pana la 28.500 req/luna)
**Ce adauga:** Rating 1-5 stele, numar recenzii, sentiment

#### P1.4 — Fonduri Europene (AFIR, PNRR, FEDR)
**Gap:** #5
**Sursa:** `fonduri-ue.ro`, `pnrr.gov.ro` (publice, gratuite)
**Ce adauga:** Dimensiune noua: „Capacitate de accesare fonduri EU"

#### P1.5 — UBO (Beneficiari Reali) via Termene.ro sau AlertaCUI.ro
**Gap:** NOU — identificat din research extern
**Ce lipseste:** Beneficial Ownership (cine detine in realitate firma) — informatii din Registrul Beneficiarilor Reali (obligatoriu ONRC din 2019, conform Directivei AML 4/5)
**Surse disponibile:**
- `termene.ro` API REST — include UBO + dosare judecatoresti + monitorizare (plan gratuit disponibil)
- `alertacui.ro` API — 4 endpoints: Monitorul Oficial, Date Generale, Just.ro, BPI
**Impact:** Due Diligence AML (Anti-Money Laundering) complet — acum RIS nu stie cine detine real firma
**Efort:** Mic (API REST, documentatie existenta)

#### P1.6 — Consiliul Concurentei — Investigatii si Amenzi
**Gap:** #12
**Sursa:** `consiliulconcurentei.ro` (public)
**Ce adauga:** Semnal de alarma pentru carteluri, abuz pozitie dominanta

---

### P2 — RELEVANT (imbunatatiri semnificative)

#### P2.1 — OSIM — Marci si Brevete
**Gap:** #7
**Sursa:** `osim.ro` API public
**Ce adauga:** Valoarea intangibila a brand-ului, inovatie

#### P2.2 — ANPC — Sanctiuni Consumatori
**Gap:** #9
**Sursa:** `anpc.ro` (public)
**Ce adauga:** Risc reputational concret (nu doar estimat din web)

#### P2.3 — Licitatii Europene TED
**Gap:** #18
**Sursa:** `ted.europa.eu` API REST (gratuit)
**Ce adauga:** Prezenta internationala a firmei

#### P2.4 — Stiri Economice Structurate (ZF, Profit.ro)
**Gap:** #15
**Sursa:** RSS feeds publice (gratuite)
**Ce adauga:** Stiri mai relevante si mai recente, surse verificate

#### P2.5 — Ministerul Finantelor Bilant Detaliat
**Gap:** #4
**Sursa:** `mfinante.gov.ro` XML/XBRL
**Ce adauga:** Structura bilantului: cash, creante, stocuri, datorii detaliate

---

### P3 — NICE TO HAVE (completare avansata)

#### P3.1 — Vizualizare Grafic Retea Firme
**Gap:** #22
**Tool:** D3.js sau vis.js (gratuite)
**Ce adauga:** Spider diagram interactiv al retelei de asociati

#### P3.2 — LinkedIn Integrare via Tavily
**Gap:** #14
**Sursa:** Tavily (deja integrat, cauta pe LinkedIn)
**Ce adauga:** Numar angajati LinkedIn, senioritati, crestere echipa

#### P3.3 — ANCPI Proprietati
**Gap:** #6
**Sursa:** `ancpi.ro` (partial public)
**Ce adauga:** Active imobiliare detinute

#### P3.4 — ITM Conflicte Munca
**Gap:** #8
**Sursa:** `inspectmuncii.ro` (public)
**Ce adauga:** Sanctiuni ITM, conflicte de munca

---

### Rezumat Roadmap

| Prioritate | Nr. Items | Impact | Efort | Date deja disponibile in sistem? |
|---|---|---|---|---|
| **P0 (Critic)** | 3 | Maxim | Mic-Mediu | Partial (P0.1 da, P0.3 da) |
| **P1 (Important)** | 5 | Mare | Mic-Mediu | Nu |
| **P2 (Relevant)** | 5 | Mediu | Mediu | Nu |
| **P3 (Nice-to-have)** | 4 | Mic-Mediu | Variabil | Partial |

**Toate sunt 100% gratuite** — nu necesita abonamente sau costuri recurente.

---

## 9. CONCLUZII SI POTENTIAL DE DEZVOLTARE

### 9.1 Ce a realizat RIS pana acum

Intr-un interval de timp remarcabil, RIS a atins un nivel de maturitate care
**depaseste majoritatea instrumentelor gratuite disponibile pe piata romaneasca**:

- **Unic pe piata free:** Combinatia AI narativ + scoring 0-100 + 7 formate raport
  nu exista nicaieri gratuit in Romania
- **Surse oficiale multiple:** 8 surse integrate, cu rezolvare automata a contradictiilor
- **Anti-halucinare:** Sistemul nu inventeaza date — marcheaza explicit ce lipseste
- **Rezilienta:** 5 niveluri de fallback AI, circuit breaker, retry logic
- **Productie-ready:** 184 teste automate, 0 erori TypeScript, securitate hardened

### 9.2 Potentialul de dezvoltare

**Pe termen scurt (P0 — 2-4 saptamani):**
Cu adaugarea Retelei de Firme (date deja in sistem!) si a scoringului predictiv
(formule matematice pe date existente!), RIS ar deveni **mai capabil decat Termene.ro free**
in detectia riscului real.

**Pe termen mediu (P1 — 1-2 luni):**
Cu Portal Just, Monitorul Oficial, AEGRM si Google Maps, RIS ar acoperi
**90% din datele publice relevante** disponibile in Romania.

**Pe termen lung (P2+P3 — 3-6 luni):**
Un sistem complet cu vizualizare retele, scoring predictiv ML si surse EU
ar fi comparabil cu instrumente care costa **sute de euro/luna** pe piata.

### 9.3 Cel mai important lucru de implementat acum

Daca ar fi sa alegem O SINGURA imbunatatire cu impact maxim:

> **Reteaua de firme prin asociati comuni (GAP #16)**

**De ce?**
- Datele sunt deja in sistem (openapi.ro deja integrat)
- Nu necesita API nou, nu necesita chei noi
- Impact direct pe scoring juridic si reputational
- Cel mai frecvent pattern de frauda din Romania = retele de firme „paravan"
- Implementare: 2-3 zile

### 9.4 Valoarea reala a sistemului

Un raport profesional de due diligence de la o firma de consultanta costa **500-2000 EUR**.
RIS produce un raport echivalent (cu limitarile surselor publice) in **2-3 minute, gratuit**.

Valoarea nu e in inlocuirea consultantilor pentru decizii de investitii majore —
ci in **democratizarea accesului la informatii de business** pentru antreprenori,
IMM-uri si profesionisti care nu isi permit servicii premium.

---

## ANEXA — Surse Publice Gratuite Utilizabile (Inventar Complet)

| Sursa | URL | Date disponibile | Tip acces |
|---|---|---|---|
| ANAF TVA/Stare | `webservicesp.anaf.ro` | CUI, TVA, stare, inactivi | API REST |
| ANAF Bilant | `webservicesp.anaf.ro/bilant` | CA, profit, angajati (2014-2024) | API REST |
| ONRC (via openapi.ro) | `api.openapi.ro` | Asociati, CAEN, administratori | API REST |
| BNR Cursuri | `bnr.ro/nbrfxrates.xml` | Cursuri valutare zilnice | XML |
| BPI Insolventa | `buletinul.ro` | Proceduri insolventa | Web scrape |
| SEAP Licitatii | `sicap.anap.gov.ro/api` | Contracte, licitatii publice | API REST |
| Portal Just | `portal.just.ro` | Dosare judecatoresti | Web scrape |
| Monitorul Oficial | `monitoruloficial.ro` | Acte constitutive, modificari | Web scrape/API |
| AEGRM | `aegrm.ro` | Garantii reale mobiliare | API REST |
| MFinante Bilant | `static.anaf.ro/static/10/Anaf/` | Bilanturi XBRL detaliate | XML/XBRL |
| INS TEMPO | `statistici.insse.ro/api` | Statistici nationale per CAEN | API REST |
| Consiliul Concurentei | `consiliulconcurentei.ro` | Investigatii, amenzi | Web scrape |
| ANPC | `anpc.ro` | Sanctiuni consumatori | Web scrape |
| OSIM Marci | `osim.ro` | Marci, brevete | API/Web |
| Fonduri EU | `fonduri-ue.ro` | Beneficiari fonduri structurale | API |
| PNRR | `mfe.gov.ro/pnrr` | Contracte PNRR | Web |
| AFIR | `afir.ro` | Beneficiari AFIR | Web |
| TED EU | `ted.europa.eu/api/` | Licitatii europene | API REST |
| OpenCorporates | `api.opencorporates.com` | Firme internationale (500 req/zi) | API REST |
| Google Places | `maps.googleapis.com` | Recenzii, rating, ore program | API REST |
| Tavily | `api.tavily.com` | Web search (1000 req/luna) | API REST |
| Brave Search | `api.search.brave.com` | Web search (2000 req/luna) | API REST |
| Jina Reader | `r.jina.ai` | Extragere continut pagini | API REST |

---

---

## 10. INFRASTRUCTURA MCP TOOLS — Status si Utilizare

> **Ce sunt MCP Tools?** Model Context Protocol (MCP) sunt „extensii" care ofera lui Claude
> capabilitati suplimentare: sa deschida un browser, sa faca cereri HTTP direct, sa gandeasca
> in pasi structurati. Sunt instalate o data si disponibile in orice sesiune.

### 10.1 Status instalare (verificat 7 Aprilie 2026)

| Tool | Versiune | Instalat | Configurat | Status sesiune |
|---|---|---|---|---|
| **Firecrawl MCP** | latest | ✅ | ✅ settings.json | ✅ Activ |
| **Playwright MCP** | v0.0.70 | ✅ | ✅ settings.json | ⚠️ Necesita restart |
| **Sequential Thinking** | latest | ✅ | ✅ settings.json | ⚠️ Necesita restart |
| **Context7 MCP** | v2.1.7 | ✅ | ✅ settings.json | ⚠️ Necesita restart |
| **Fetch Server** | latest | ✅ | ✅ adaugat v1.1 | ⚠️ Necesita restart |
| **Zapier MCP** | — | — | ✅ settings.json (HTTP) | ⚠️ Necesita auth |
| **GitHub MCP** | — | ✅ | ✅ settings.json | ⚠️ Necesita verificare |
| **Brave Search MCP** | — | ✅ | ✅ settings.json | ⚠️ Necesita verificare |
| **Google Docs MCP** | — | ✅ | ✅ settings.json | ⚠️ Necesita verificare |

**Fix aplicat in v1.1:** Toate tool-urile foloseau `npx -y` (lent, descarca la fiecare pornire).
Inlocuit cu cai directe `node /path/to/module` — pornire instantanee.

**Actiune necesara:** Restart Claude Code pentru a incarca noua configuratie.

### 10.2 Ce adauga fiecare tool sistemului RIS

| Tool | Capabilitate | Utilizare in RIS |
|---|---|---|
| **Playwright MCP** | Screenshot si interactiune browser real | Verifica UI RIS localhost:5173, testeaza fluxuri, captureaza rapoarte |
| **Fetch Server** | Cereri HTTP directe cu raspuns JSON/HTML | Valideaza API-uri ANAF/ONRC live, testeaza endpoint-urile RIS |
| **Sequential Thinking** | Gandire structurata pas-cu-pas | Planificare implementari complexe, debugging logic errors |
| **Context7 MCP** | Documentatie up-to-date pentru librarii | Verifica API-uri Python/React/FastAPI in timp real |
| **Firecrawl MCP** | Scraping web avansat + browser automation | Extrage date din Portal Just, Monitorul Oficial, AEGRM |

### 10.3 Cum se folosesc pentru dezvoltarea RIS

**Playwright** → poate face screenshot din UI-ul RIS si vedea exact ce vede browserul:
```
→ Deschide localhost:5173
→ Navigheaza la pagina Analiza Noua
→ Captureaza screenshot
→ Verifica daca elementele se afiseaza corect
```

**Fetch Server** → valideaza endpoint-urile ANAF live fara a porni backend-ul:
```
→ POST https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva
→ Body: [{"cui": 12345678, "data": "2026-04-07"}]
→ Returneaza raspunsul real ANAF
→ Verifica daca API-ul functioneaza
```

**Context7** → cauta documentatie actualizata:
```
→ "Cum se face paginare in FastAPI?"
→ Returneaza documentatia exacta din FastAPI docs, nu din memoria Claude
```

---

---

## 11. INFRASTRUCTURA API KEYS — Inventar Complet si Plan Integrare

> **Actualizat:** 7 Aprilie 2026 — extras din API_KEYS.md si corelat cu starea curenta a sistemului.
> Valorile cheilor NU sunt incluse in acest document — se gasesc exclusiv in `.env` si `API_KEYS.md`.

---

### 11.1 Fix-uri URGENTE identificate (din analiza logs + keys)

Aceste doua probleme cauzau esecuri silentioase in fiecare analiza:

| # | Problema | Cauza | Fix necesar | Fisier |
|---|---|---|---|---|
| **CRIT-1** | Gemini 404 la fiecare analiza | Model ID `gemini-2.5-flash-preview-05-20` e deprecat | Schimba in `gemini-2.5-flash` sau `gemini-2.0-flash` | `backend/agents/agent_synthesis.py` |
| **CRIT-2** | Mistral 401 Unauthorized | `.env` contine cheia VECHE `UYpBNSr...` | Actualizeaza cu cheia NOUA `kLyGcvN...` din API_KEYS.md | `.env` → `MISTRAL_API_KEY` |

**Impact:** Cu Gemini si Mistral cazute simultan, sinteza AI ruleaza doar pe Groq (care intra in 429) si Claude CLI. Fallback-ul de 5 niveluri devine de fapt 2 niveluri functionale.

---

### 11.2 Provideri AI — Status curent in RIS

| Provider | Env Var | Status in RIS | Limita | Note |
|---|---|---|---|---|
| **Anthropic Claude** | `ANTHROPIC_API_KEY` | ✅ Activ — principal | Subscription platit | Claude Opus 4.6 synthesis via CLI subprocess |
| **Google Gemini** | `GOOGLE_API_KEY` | ⚠️ 404 — model deprecat | 1000 req/zi Flash | Fix: schimba model ID |
| **Groq** | `GROQ_API_KEY` | ✅ Activ — fallback rapid | 14.400 req/zi | 500-2000 tok/s; intra in 429 la mai multe analize simultane |
| **Mistral** | `MISTRAL_API_KEY` | ❌ 401 — cheie gresita | 1 MILIARD tok/luna | Fix: actualizeaza cheia in .env. Mistral OCR = cel mai bun pentru PDF scanate |
| **Cerebras** | `CEREBRAS_API_KEY` | ✅ Activ — fallback final | 1M tok/zi | ~2000 tok/s, Qwen 3 235B |
| **openapi.ro** | `OPENAPI_RO_KEY` | ⚠️ Marcat COMPLETEAZA_MANUAL | 100 req/luna | **VERIFICA `.env`** — daca lipseste, P0.1 (Retea firme) nu functioneaza |

---

### 11.3 Provideri AI noi — Disponibili imediat, neintegrati in RIS

Acesti provideri au chei active in API_KEYS.md si pot fi adaugati la lantul de fallback sau pentru sectiuni specifice:

#### A. xAI Grok — [RECOMANDAT] pentru context extins
- **Env Var:** `XAI_API_KEY`
- **Modele:** Grok 4 (256K context), Grok 4.1 Fast (2M context!)
- **Limita:** $25 credit signup + $150/luna cu data sharing optional
- **Compatibil:** 100% OpenAI SDK — integrare triviala
- **Utilizare RIS:** Sectiuni lungi (raport full, analiza comparativa) — 2M context e unic
- **Prioritate:** P0 — adaugare imediata ca fallback dupa Claude

#### B. OpenRouter — [RECOMANDAT] ca safety net universal
- **Env Var:** `OPENROUTER_API_KEY`
- **Modele:** 348+ modele printr-un singur endpoint
- **Limita:** 50 req/zi fara sold / 1000 req/zi cu $10 deposit (permanent)
- **Utilizare RIS:** Ultimul nivel de fallback — daca TOTI ceilalti provideri cad, OpenRouter are intotdeauna ceva disponibil
- **Prioritate:** P0 — adaugare ca nivel 6 in lantul de fallback

#### C. GitHub Models — [RELEVANT] pentru modele multiple gratuite
- **Env Var:** `GITHUB_TOKEN`
- **Modele disponibile:** GPT-4.1, o3, Grok-3, DeepSeek-R1, Llama 4 Scout
- **Limita:** 50-150 req/zi, fara card
- **Note:** Acces prin Azure inference endpoint
- **Utilizare RIS:** Diversificare fallback; DeepSeek-R1 pentru reasoning financiar
- **Prioritate:** P1

#### D. Fireworks AI — [RELEVANT] pentru modele open-source rapide
- **Env Var:** `FIREWORKS_API_KEY`
- **Modele:** Llama 4 Scout/Maverick, DeepSeek R1/V3, Qwen3 235B
- **Limita:** 10 RPM fara card (600 req/ora)
- **Utilizare RIS:** Alternativa la Groq pentru modele Llama 4
- **Prioritate:** P1

#### E. DeepSeek — [RELEVANT] pentru reasoning financiar, cu rezerve
- **Env Var:** `DEEPSEEK_API_KEY`
- **Modele:** R1 (reasoning), V3.2 (general)
- **Limita:** 5M tokens la signup (30 zile)
- **⚠️ ATENTIE:** Servere in China — **nu trimite date cu CUI-uri ale clientilor reali**
- **Utilizare RIS:** Doar analiza interna/test, nu productie cu date sensibile
- **Prioritate:** P2 (cu restrictie date)

#### F. OpenAI (GPT-4.1, o3) — [RELEVANT] dar pay-per-use
- **Env Var:** `OPENAI_API_KEY`
- **Modele:** GPT-4.1, o3, o4-mini
- **Limita:** Pay-per-use
- **Utilizare RIS:** Rezerva premium — doar daca Claude CLI nu e disponibil
- **Prioritate:** P2

---

### 11.4 Tools noi pentru roadmap P0–P3

#### Jina AI Reader — [RECOMANDAT] pentru Portal Just si scraping
- **Env Var:** `JINA_API_KEY`
- **Functie:** `r.jina.ai/{url}` → returneaza orice pagina web ca Markdown curat pentru LLM
- **Limita:** 1M tokens total (permanent)
- **Utilizare RIS:** Extragere structurata din `portal.just.ro` (P0.4), `monitoruloficial.ro` (P1.1), `consiliulconcurentei.ro` (P2.5)
- **Avantaj vs Firecrawl:** Gratuit permanent, mai simplu, suficient pentru pagini text

#### Adobe Acrobat Services — [RELEVANT] pentru OCR documente
- **Env Var:** `ADOBE_API_KEY` + `ADOBE_CLIENT_SECRET`
- **Functie:** Extract text, tabele si imagini din PDF (inclusiv scanate)
- **Limita:** 500 tranzactii/luna (gratuit)
- **Utilizare RIS:** Extragere date din contracte PDF, bilanturi scanate uploadate manual
- **SDK:** `pip install pdfservices-sdk`
- **Prioritate:** P2 (feature „upload document pentru analiza")

#### Azure Document Intelligence — [RELEVANT] pentru facturi si formulare
- **Env Var:** `AZURE_DOC_INTEL_KEY`
- **Functie:** OCR + structurare formulare, facturi, contracte
- **Limita:** 500 pagini/luna (gratuit)
- **Utilizare RIS:** Alternativa la Adobe, mai bun pentru formulare standardizate
- **Prioritate:** P2

#### Google Cloud (Maps) — [RECOMANDAT] pentru recenzii firme
- **Env Var:** `GOOGLE_CLOUD_API_KEY`
- **Functie:** Google Places API — rating 1-5, numar recenzii, ore program
- **Limita:** 28.500 req/luna gratuit
- **Utilizare RIS:** Dimensiunea Reputational din scoring devine bazata pe date reale (P1.3 din Roadmap)
- **Prioritate:** P1

#### Cohere Embed + Rerank — [RELEVANT] pentru RAG avansat
- **Env Var:** `COHERE_API_KEY`
- **Functie:** Embed v4 (embeddings text) + Rerank v4 (ordonare documente dupa relevanta)
- **Limita:** 100 RPM embed/rerank (practic nelimitat pe free tier)
- **Utilizare RIS:** RAG (Retrieval Augmented Generation) peste toate rapoartele salvate — „cauta in istoricul analizelor mele"
- **Prioritate:** P3

#### Mistral OCR — [RECOMANDAT] pentru documente scanate
- **Env Var:** `MISTRAL_API_KEY` (aceeasi cheie, model diferit)
- **Functie:** Cel mai bun OCR disponibil pentru PDF scanate, inclusiv romana
- **Limita:** 1 MILIARD tokens/luna
- **Utilizare RIS:** Procesare bilanturi ANAF scanate, contracte uploadate
- **Prioritate:** P1 (dupa fix-ul cheii Mistral de la 11.1)

---

### 11.5 Servicii de cautare web — Status

| Provider | Env Var | Limita | Status RIS | Utilizare |
|---|---|---|---|---|
| **Tavily** | `TAVILY_API_KEY` | 1000 req/luna | ✅ Activ | Search inteligent AI, litigii, reputatie |
| **Brave Search** | `BRAVE_SEARCH_API_KEY` | 2000 req/luna | ✅ Activ (Agent 2) | Stiri suplimentare, prezenta brand |
| **Jina Reader** | `JINA_API_KEY` | 1M tokens total | ❌ Neintegrat | Extragere continut pagini → Markdown |
| **OpenRouter (search)** | `OPENROUTER_API_KEY` | 50-1000 req/zi | ❌ Neintegrat | Fallback universal AI |

---

### 11.6 Traducere — Disponibil pentru rapoarte multilingve

| Provider | Env Var | Limita | Utilizare RIS |
|---|---|---|---|
| **DeepL** | `DEEPL_API_KEY` | 500K caractere/luna (2 chei = 1M) | Traducere rapoarte RO→EN pentru clienti externi |
| **Azure Translator** | `AZURE_TRANSLATOR_KEY` | 2M caractere/luna | Alternativa, 100+ limbi |

**Nota:** Rapoartele RIS sunt acum doar in romana. Adaugarea unui buton „Exporta in engleza" ar extinde utilitatea pentru consultanti internationali.

---

### 11.7 Nu relevant pentru RIS (alte proiecte)

| Provider | Proiect | Motiv excludere |
|---|---|---|
| Plant.ID, PlantNet | Livada | Identificare plante — complet diferit |
| Replicate, FLUX, MusicGen | Media | Generare imagini/audio |
| Facebook Graph API | Social Media | Marketing pagina FB |
| Cloudflare Workers AI | Infra | Edge computing, nu analiza business |
| NVIDIA NIM | ML Research | Credite limitate, nu se reincarsa |
| SambaNova (Llama 405B) | Optional | Utile daca OpenRouter/Fireworks cad |

---

### 11.8 Plan de actiune — Ordinea integrarii

```
IMEDIAT (fix-uri, fara cod nou):
  1. Fix Gemini model ID in agent_synthesis.py → 5 minute
  2. Fix Mistral key in .env → 2 minute
  3. Verifica openapi.ro key in .env → 1 minut

P0 (sesiunea curenta):
  4. Adauga xAI Grok ca fallback nivel 2 (dupa Claude, inainte de Groq)
  5. Adauga OpenRouter ca nivel 6 (safety net)
  6. Integreaza Jina Reader pentru Portal Just scraping

P1 (sesiunea urmatoare):
  7. Google Maps (Places API) → scoring reputational real
  8. Mistral OCR → procesare documente scanate

P2 (viitor):
  9. Adobe PDF Services → upload documente
 10. Cohere RAG → search in istoricul analizelor
 11. Traducere DeepL → rapoarte multilingve
```

---

### 11.9 Rezumat — Ce avem vs ce folosim

| Categorie | Disponibile | Integrate in RIS | Neutilizate (oportunitate) |
|---|---|---|---|
| AI Provideri | 12 | 5 (Claude, Gemini*, Groq, Mistral*, Cerebras) | 7 (xAI, OpenRouter, DeepSeek, GitHub, Fireworks, OpenAI, HuggingFace) |
| Web Search | 3 | 2 (Tavily, Brave) | 1 (Jina Reader) |
| OCR/PDF | 3 | 0 | 3 (Adobe, Azure Doc Intel, Mistral OCR) |
| Traducere | 2 | 0 | 2 (DeepL, Azure Translator) |
| Harti/Recenzii | 1 | 0 | 1 (Google Maps/Places) |
| APIs Romania | 5 | 5 (ANAF, ONRC, BNR, BPI, SEAP) | 0 |

*Gemini si Mistral sunt integrate dar nefunctionale din cauza fix-urilor pendinte (sectiunea 11.1)*

---

*Sectiunea 11 adaugata: 7 Aprilie 2026 — sursa: API_KEYS.md audit complet*

---

## 12. AUDIT TEHNIC PROFUND BACKEND — Probleme Concrete cu Numere de Linie

> Aceasta sectiune contine probleme identificate prin citirea directa a codului sursa.
> Fiecare problema e localizata precis — linie, fisier, valoare hardcodata.

---

### 12.1 agent_verification.py — Trust Scoring Naiv

**Problema:** Linia ~732 — formula de calcul confidence:
```
confidence = min(1.0, 0.4 + 0.3 * (sources_count - 1))
```
- Formula LINEAR — nu diferentiaza CALITATEA surselor
- 2 surse ANAF (nivel 1) = acelasi confidence ca 1 ANAF + 1 forum (nivel 4)
- **Fix:** Pondereaza confidence dupa SOURCE_LEVEL (`1/nivel`) — ANAF conteaza mai mult decat Tavily

**Problema:** Linia ~650 — anomalie hardcodata:
```
"0 angajati + CA > 1M" = SUSPECT
```
- Pragul 1M e fix, fara ajustare per sector
- Un startup IT fara angajati cu 1M CA = NORMAL; un retail = SUSPECT
- **Fix:** Ajustare prag per CAEN/sector (ex: IT tolereaza mai mult)

**Problema:** Liniile 445-507 — `_detect_relations()` detecteaza doar:
- Admin unic = asociat unic (firma one-man)
- Virtual office
- NU detecteaza: acelasi administrator la multiple firme, lanturile corporative A→B→C
- NU exista tabel SQL `company_relationships` — datele openapi.ro sunt salvate doar ca JSON blob in `reports.full_data`
- **Fix:** P0.1 — query SQL recursiv + tabel nou `company_administrators`

---

### 12.2 agent_synthesis.py — Probleme de Calitate si Stabilitate

**Problema:** Linia ~74 — routing naiv:
```
if word_target <= 200: route = "fast"  # (Groq)
```
- Prag FIX — nu considera: complexitatea datelor, confidence score, tipul sectiunii
- Executiv Summary cu date putine → Groq; cu date bogate → Claude CLI
- **Fix:** Routing pe baza composite score: word_target + data_confidence + section_type

**Problema:** Linia ~193-198 — estimare tokeni incorecta:
```
tokens_estimate = 500 + data_chars/4 + word_target*2
```
- Formula empirica — nu considera markdown, formatare, repetitii in prompt
- **Risc:** Token overflow pe date mari → trunchierea silentioasa a contextului
- **Fix:** `pip install tiktoken` → numarare exacta inainte de API call

**Problema CRITICA:** `_sanitize_data_for_prompt()` e NOMINALIZAT in cod dar NU e definit in fisier (se asuma ca exista in BaseAgent). Daca BaseAgent nu il implementeaza corect → prompt injection risc.

**Problema:** Linia ~139 — "Cross-section coherence check" DECLARAT dar NEIMPLEMENTAT:
```
# TODO: verify coherence between sections
return sections  # simply returns without checking
```
- O firma cu CA diferit in sectiunea financiara vs. executive summary → nu e detectat
- **Fix:** Semantic similarity check simplu (extrageaza numerele din fiecare sectiune, compara)

**Problema:** NU exista regenerare per sectiune — daca una e slaba, trebuie regenerata TOATA sinteza. Cost: 3-5 minute. **Fix:** Cache per (section_key + data_hash) + endpoint `POST /jobs/{id}/section/{key}/regenerate`

---

### 12.3 scoring.py — Hardcodari si Limitari

**Hardcodari critice:**

| Linia | Valoare | Problema |
|---|---|---|
| ~37-54 | SCORING_THRESHOLDS (ca_excellent=10M, growth_good=20%) | FIX per industrie. 10M pt IT ≠ 10M pt retail |
| ~147-158 | CA > 10M: +15 score | Trepte fixe, NU sector-ajustate |
| ~411 | Insolventa: -60 score | FIX, indiferent de gravitate/data |
| ~451 | Inactiv ANAF: -50 | FIX, nu considera durata inactivitatii |
| ~28-35 | DIMENSION_WEIGHTS | FIX — nu customizabile per tip analiza |

**Date calculate dar neutilizate:**
- `_calculate_financial_ratios()` → 6 ratios (ROE, ROA, Debt-to-Equity, etc.) CALCULATE dar NU integrate in risk_factors
- `solvency_matrix` 3x3 → calculat dar salvat doar ca text, nu ca JSON structurat
- `sector_position` (percentile) → calculat dar nu returnat separat

**Altman Z-Score: COMPLET ABSENT** — nici o referinta in 832 linii. Implementarea lui va fi in scoring.py ca dimensiunea 7 (sau o sub-dimensiune a Financiar). Formulele complete in Sectiunea 13.

---

### 12.4 monitoring_service.py — Escalare si Robustete

**Problema:** Liniile 49-86 — 3 CRITICAL_COMBINATIONS hardcodate:
- (RADIAT, Inactiv), (RADIAT, TVA Lost), (Inactiv, TVA Lost)
- Daca apar 2 RED flags DIFERITE (ex: Inactiv + Insolventa), NU escaladeaza la CRITICAL
- **Fix:** Agregare automata — orice 2+ RED flags → CRITICAL

**Problema:** Linia ~177 — Daca firma devine RADIATA, NU se actualizeaza `companies.is_active` flag → inconsistenta intre starea din DB si rapoartele generate

**Problema:** `monitoring_audit` tabel populat dar NU expus prin REST → utilizatorul nu poate vedea istoricul alertelor. **Fix:** `GET /api/monitoring/{alert_id}/audit-log`

**Problema:** NU exista mecanisme de suprimare false positives → alert SPAM pentru firme cu date inconsistente. **Fix:** `POST /api/monitoring/{alert_id}/suppress` cu motiv + durata

---

### 12.5 openapi_client.py — Quota si Retea

**Problema:** Linia ~40 — 429 (quota depasita 100 req/luna) returnata dar NU se logheaza WARNING specific:
- Utilizatorul vede "openapi.ro: not found" in raport — nu "quota epuizata"
- **Fix:** Log explicit WARNING + alerta Telegram + flag in DB `openapi_quota_exceeded = True`

**Problema:** `asociati` si `administratori` sunt raw pass-through din openapi.ro — NU validate structural, NU indexate in SQL. Orice query pentru reteaua corporativa necesita parsing JSON blob.

**Endpoint-uri REST ABSENTE dar NECESARE:**
```
GET /api/companies/{cui}/network          → retea asociati/administratori
GET /api/companies/{cui}/related-parties  → firme conexe prin persoane comune
GET /api/scoring/{cui}/breakdown          → 6 dimensiuni + confidence + reasons
POST /api/jobs/{id}/section/{key}/regenerate → regenerare sectiune sinteza
GET /api/monitoring/{id}/audit-log        → istoric alerte
POST /api/monitoring/{id}/suppress        → suprima false positive
GET /api/jobs/{id}/agent-status           → stare per-agent in timp real
```

---

### 12.6 config.py — Configurari Problematice

| Config | Problema |
|---|---|
| `app_secret_key = ""` → random la fiecare restart | Session tokens invalide dupa restart |
| `tavily_monthly_quota: 1000` hardcodat | Nu e citit din .env, nu e actualizabil |
| `max_concurrent_jobs: 2` fix | Nu scalabil la 5+ utilizatori |
| `database_path: "./data/ris.db"` relativ | Probleme in Docker/deploy |
| Log level nu e citit din .env explicit | Nu poti schimba verbositatea fara restart |

---

## 13. MODELE PREDICTIVE AVANSATE — Formule Complete si Implementare

> Aceasta sectiune contine formulele matematice complete pentru transformarea RIS
> din sistem descriptiv in sistem predictiv. Toate datele necesare sunt DEJA in sistem (ANAF Bilant).

---

### 13.1 Altman Z'' Emerging Markets — Modelul CORECT pentru Romania

**De ce Z'' si nu Z original:**
- Z original (1968) necesita cotatie bursiera (pret actiune) → imposibil pentru firme nelistate
- Z' (1983) e pentru firme manufacturiere private — poate fi folosit
- **Z''_EMS (1995, Emerging Markets)** — recomandat pentru Romania si piete in curs de dezvoltare

**Formula Z''_EMS:**
```
Z''_EMS = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4

X1 = Capital Circulant / Total Active
     = (Active Curente - Datorii Curente) / Total Active

X2 = Rezultat Reportat / Total Active
     = (Capitaluri Proprii - Capital Social - Rezerve) / Total Active
     (sau: Profit Reinvestit Cumulat / Total Active)

X3 = EBIT / Total Active
     = (Profit inainte de taxe + Cheltuieli financiare) / Total Active

X4 = Valoare Contabila Capitaluri Proprii / Total Datorii
     = Capital Propriu / (Datorii TL + Datorii Curente)
```

**Praguri interpretare:**
- Z''_EMS > 2.60 → **Safe Zone** (solvabil)
- 1.10 < Z''_EMS < 2.60 → **Grey Zone** (monitorizare)
- Z''_EMS < 1.10 → **Distress Zone** (risc insolventa)

**Mapare din ANAF Bilant (indicatori disponibili):**
```python
# Indicatorii ANAF Bilant relevanti (val_den_indicator):
# "Active imobilizate nete" + "Active circulante" = Total Active
# "Capitaluri proprii" = Capital Propriu
# "Datorii" (curente + termen lung) = Total Datorii
# "Profit net / Pierdere neta" = baza calcul EBIT
# "Rezultatul reportat" = X2 (daca disponibil)
```

**Nota importanta:** Calibrat pe firme americane. Adauga disclaimer: "Praguri calibrate pe piata americana; pentru Romania zona gri e mai larga (1.00-2.90)."

**Biblioteca:** `pip install credpy` — suporta toate variantele Altman din 31 pozitii bilant.

---

### 13.2 Piotroski F-Score — 9 Criterii Binare

**De ce e util pentru RIS:** Masoara TRENDUL, nu starea absoluta. 2 ani de bilant → scor 0-9.

**Formula:** F-Score = suma a 9 criterii (0 sau 1 fiecare)

**A. Profitabilitate (4 criterii):**
```
F1 = ROA > 0                        (profit net / total active > 0)
F2 = ROA_t > ROA_t-1                (ROA in crestere fata de anul anterior)
F3 = CFO > 0                        (cash flow operational > 0; proxy: profit + amortizare)
F4 = CFO/Active > ROA               (calitate earnings: cash > profitul contabil)
```

**B. Leverage si Lichiditate (3 criterii):**
```
F5 = Datorii_TL/Active_t < Datorii_TL/Active_t-1   (leverage in scadere)
F6 = Active_Cur/Dat_Cur_t > Active_Cur/Dat_Cur_t-1  (lichiditate in crestere)
F7 = Nu s-a majorat capitalul (nu dilutie actionari)
```

**C. Eficienta Operationala (2 criterii):**
```
F8 = Marja_bruta_t > Marja_bruta_t-1    (eficienta productie in crestere)
F9 = CA/Active_t > CA/Active_t-1         (utilizare active in crestere)
```

**Interpretare:**
- F = 8-9 → **STRONG** (firma solida, trend pozitiv)
- F = 5-7 → **AVERAGE** (mediu, monitorizare)
- F = 0-2 → **WEAK** (deteriorare progresiva, semnal vanzare/evitare)

---

### 13.3 Beneish M-Score — Detectie Manipulare Financiara

**Utilitate pentru RIS:** Detecteaza "contabilitate creativa" — firma care isi infrumuseteaza bilantul.

**Formula completa (8 indicatori, necesita 2 ani consecutivi):**
```
M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
    + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
```

**Cei 8 indicatori:**
```
DSRI = (Creante_t/CA_t) / (Creante_t-1/CA_t-1)
       Creante in crestere mai repede decat CA = semnal manipulare venituri

GMI  = Marja_Bruta_t-1 / Marja_Bruta_t
       Marja in scadere = presiune sa "ajusteze" situatiile

AQI  = [1-(AC_t+IMO_t)/TA_t] / [1-(AC_t-1+IMO_t-1)/TA_t-1]
       Active de calitate slaba in crestere = capitalizare cheltuieli

SGI  = CA_t / CA_t-1
       Crestere CA mare = stimulent sa manipuleze

DEPI = Amortizare_t-1/(Amort_t-1+IMO_t-1) / Amort_t/(Amort_t+IMO_t)
       Amortizare redusa = reduce cheltuielile artificial

SGAI = (Chelt_Vanzare_t/CA_t) / (Chelt_Vanzare_t-1/CA_t-1)
       Cheltuieli G&A in crestere vs CA = semnal probleme

TATA = (Profit_net_t - CFO_t) / Total_Active_t
       Accruals mari = earnings "construite", nu cash real

LVGI = (DLT_t+DC_t)/TA_t / (DLT_t-1+DC_t-1)/TA_t-1
       Leverage in crestere = presiune financiara crescuta
```

**Praguri:**
- M > -1.78 → **Manipulator probabil** (RISC — mai sensibil, mai multi false positives)
- M > -2.22 → **Zona de investigat** (prag recomandat pentru Romania IMM)
- M < -2.22 → **Non-manipulator probabil** (OK)

**Varianta simplificata 5 indicatori (recomandata pentru Romania unde SGAI/DEPI/LVGI nu sunt intotdeauna disponibili):**
```
M5 = -6.065 + 0.823*DSRI + 0.906*GMI + 0.593*AQI + 0.717*SGI + 7.770*TATA
```

---

### 13.4 Zmijewski X-Score — Confirmare Distress (model logistic)

**Formula:**
```
X = -4.336 - 4.513*(Profit_net/Total_active) + 5.679*(Total_datorii/Total_active)
    + 0.004*(Active_curente/Datorii_curente)
```

**Interpretare:**
- X > 0 → **Potential bankruptcy risk**
- X ≤ 0 → **Financial health OK**

**Avantaj:** Model logistic, mai precis statistic decat Altman. Nu necesita date de piata.

---

### 13.5 Mapare Data ANAF → Indicatori Financiari

```
Din ANAF Bilant API (val_den_indicator):
┌─────────────────────────────────────────────┬──────────────────────────┐
│ Text val_den_indicator                      │ Indicator financiar      │
├─────────────────────────────────────────────┼──────────────────────────┤
│ "Cifra de afaceri neta"                     │ CA (Sales)               │
│ "Profit net"                                │ Net Income               │
│ "Pierdere neta"                             │ Net Loss (negativ)        │
│ "Active imobilizate" + "Active circulante"  │ Total Active (TA)        │
│ "Capitaluri proprii"                        │ Book Value Equity (BVE)  │
│ "Datorii"                                   │ Total Liabilities (TL)   │
│ "Active circulante"                         │ Current Assets (CA_cur)  │
│ "Datorii curente"                           │ Current Liabilities (CL) │
│ "Rezultatul reportat"                       │ Retained Earnings (RE)   │
│ "Numar mediu salariati"                     │ Employees                │
│ "Profit brut" / "Pierdere bruta"            │ EBIT (aproximatie)       │
└─────────────────────────────────────────────┴──────────────────────────┘

Working Capital = Active Circulante - Datorii Curente
EBIT = Profit brut (inainte de impozit + cheltuieli financiare)
ROA = Profit net / Total Active
ROE = Profit net / Capitaluri Proprii
```

---

### 13.6 Integrare in RIS — Fisiere de modificat

```
backend/agents/verification/scoring.py
  → add: calculate_altman_z_ems(bilant_data) → {"z_score": float, "zone": str}
  → add: calculate_piotroski_f(bilant_data, bilant_prev) → {"f_score": int, "criteria": list}
  → add: calculate_beneish_m5(bilant_data, bilant_prev) → {"m_score": float, "risk": str}
  → add: calculate_zmijewski_x(bilant_data) → {"x_score": float, "distress": bool}
  → update: _calculate_financial_dimension() → include Z''_EMS in score financiar (30%)

backend/models.py
  → add: PredictiveScores model cu toate 4 scoruri + interpretari

frontend/src/pages/ReportView.tsx
  → add: tab "Scoruri Predictive" cu vizualizare Z-Score, F-Score, M-Score, X-Score
```

---

## 14. AUDIT UI/FRONTEND — Gaps si Imbunatatiri Identificate

> Aceasta sectiune contine probleme identificate prin citirea directa a codului frontend.
> Organizate per pagina, cu localizare precisa.

---

### 14.1 Dashboard — Gaps si Redundante

**Redundanta critica:** Scorul in scadere apare de 2 ori:
- "Scoruri in scadere" (top 3, hardcodat in component)
- "Risk Movers Widget" (top 5, fetch separat din `/companies/stats/risk-movers`)
- **Fix:** Pastreaza doar Risk Movers Widget, sterge componenta duplicata

**Date disponibile in backend dar neafisate:**
- Breakdown analize per tip (nu doar count total)
- Alerte active de monitorizare (ar trebui badge pe dashboard)
- API latency metrics (disponibil din `/health/deep`)
- Batch operations in progres

**Stari loading/error lipsa:**
- Health Status Card nu are loading state individual — apare gol la refresh
- Nu exista retry button pe elemente care esueaza

**Vizualizari lipsa:**
- Line chart pentru evolutia scorurilor in timp (nu solo bars)
- Donut chart pentru breakdown per tip analiza
- Indicator "analize luna curenta vs luna anterioara" comparativ

---

### 14.2 ReportView — Navigatie si Interactivitate

**Navigare intra-raport lipsa:**
- Nu exista anchor links / table of contents
- Tab-urile sunt singura navigatie — la rapoarte lungi, utilizatorul se pierde

**Score apare de 3 ori** (redundant): Risk card top + Dimensions section + Raw JSON tab → unifica vizualizarea

**Actiuni de business lipsa:**
- NU pot share raportul cu altcineva (link public cu token temporar)
- NU pot adauga raportul la o colectie/folder
- NU pot marca raportul ca "Revizuit" sau "Aprobat"
- NU pot export per tab (ex: export doar Risk tab ca PDF)
- NU exista link-uri externe catre sursele datelor (ex: "Verifica pe ANAF portal")

**Date lipsa din UI:**
- Sector percentile ranking (e calculat in backend dar NU afisat in frontend)
- Recomandari de actiuni concrete per risc identificat
- Dimensiuni de scoring cu click pentru a vedea factorii detaliati

**Stari lipsa:**
- Warning vizibil daca surse OK < 50% (exista in backend completeness gate dar NU in UI)
- Error handling pe download (just throw)
- Retry pe email send esuat

---

### 14.3 Companies — Filtrare si Actiuni Bulk

**Risk score badge LIPSESTE pe card** — exista filter dupa risc (Verde/Galben/Rosu) DAR cardul nu afiseaza culoarea riscului vizual → utilizatorul filtreaza dupa ceva ce nu vede pe card. **Fix:** Badge colored pe fiecare company card.

**Actiuni bulk lipsa:**
- Nu exista multi-select + bulk actions (delete, export subset, re-analyze selected)
- Nu exista grupuri/colectii de companii
- Nu exista bulk tag assignment

**Date lipsa pe card:**
- Trend indicator (score up/down fata de analiza anterioara)
- Indicator "alerte active" (firma monitorizata + alerta recenta)
- Preview financiar pe hover (CA, angajati) — date disponibile in backend

---

### 14.4 Probleme de UX General

**Draft pierdut la refresh:** NewAnalysis wizard foloseste `sessionStorage` — pierdut la refresh browser. **Fix:** `localStorage` cu TTL 24h.

**GlobalSearch inaccesibil pe mobile:** Ctrl+K nu functioneaza pe mobile, fara alternative. **Fix:** Buton search vizibil in mobile header.

**Dark/light theme hardcodat:** Intregul sistem e fortat pe dark mode. **Fix:** Toggle theme in Settings + `localStorage` persistenta.

**Breadcrumbs lipsa pe mobile:** Layout mobile nu afiseaza breadcrumbs. **Fix:** Breadcrumb minimal in mobile header.

**Dimensiuni din scoring neinteractive:** CompanyDetail afiseaza dimensiunile cu hover tooltip DAR nu e clar ca e interactiv (nu exista hint vizual). **Fix:** Cursor pointer + underline dashed pe label.

**Accessibility:**
- `role` attributes lipsesc pe unele butoane
- `aria-label` lipsa pe iconite fara text
- Indicatori color-only (Verde/Galben/Rosu) fara text/icon alternativ pentru daltonism
- Keyboard navigation incompleta pe unele componente

---

### 14.5 Oportunitati de Vizualizare Avansate

Urmatoarele vizualizari ar adauga valoare semnificativa si sunt justificate de datele disponibile:

| Vizualizare | Pagina | Date disponibile | Prioritate |
|---|---|---|---|
| **Radar chart** pentru 6 dimensiuni scoring | ReportView / CompanyDetail | scoring.py → 6 dimensiuni | P1 |
| **Line chart** scor evolutie in timp | CompanyDetail | score_history table | P1 |
| **Heatmap** activitate per zi/ora | Dashboard | jobs table cu timestamps | P2 |
| **Network graph** retea asociati | CompanyDetail (dupa P0.1) | openapi.ro asociati/admin | P0.1 |
| **Sector benchmark bar** | ReportView | sector_position calculat | P1 |
| **Timeline interactiva** | CompanyDetail | timeline endpoint existent | P1 |
| **Scatter plot** firma vs. sector (2 metrici) | CompareCompanies | compare endpoint | P2 |
| **Scoruri predictive** (Z, F, M, X) | ReportView nou tab | sectiunea 13 | P0.4 |

---

### 14.6 Rezumat Prioritati Frontend

| Prioritate | Item | Efort | Impact |
|---|---|---|---|
| **P0** | Risk score badge pe company cards | Mic | Mediu |
| **P0** | Tab "Scoruri Predictive" in ReportView (dupa P0.4 backend) | Mic | Maxim |
| **P1** | Radar chart 6 dimensiuni scoring | Mic | Mare |
| **P1** | Draft wizard in localStorage (nu sessionStorage) | Mic | Mediu |
| **P1** | Sector benchmark bar in ReportView | Mic | Mare |
| **P1** | Warning vizibil daca completeness < 50% | Mic | Mediu |
| **P2** | Dark/light theme toggle | Mediu | Mediu |
| **P2** | Bulk actions companiii (multi-select) | Mediu | Mediu |
| **P2** | Share report link (token public) | Medie | Mediu |
| **P3** | GlobalSearch pe mobile | Mic | Mediu |
| **P3** | Network graph retea asociati | Mare | Maxim |
| **P3** | Heatmap activitate Dashboard | Mic | Mic |

---

*Sectiunile 12-14 adaugate: 7 Aprilie 2026 — sursa: analiza cod sursa + research extern*

---

*Document generat: 7 Aprilie 2026*
*Ultima actualizare: 7 Aprilie 2026 (v1.3 — adaugate sectiunile 12, 13, 14: audit tehnic, modele predictive, audit frontend)*
*Sistem: Roland Intelligence System (RIS) v18+*
*Autori: Roland Petrila + Claude Code (claude-sonnet-4-6)*
*Clasificare: INTERN — uz personal si prezentari*
