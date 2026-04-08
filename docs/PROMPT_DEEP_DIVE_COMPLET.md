# PROMPT — Deep Dive Complet RIS v2.0

> **Destinat:** Terminal Claude Code (executie)
> **Proiect:** C:\Proiecte\Sistem_Inteligent_Analize
> **Data generare:** 2026-03-20
> **Scop:** Analiza exhaustiva a intregului sistem — performance, imbunatatiri per functie, functii noi, documentare firme extinsa

---

## CONTEXT PROIECT

Roland Intelligence System (RIS) — sistem local de Business Intelligence pe Windows 10.
- **Utilizator unic:** Roland (operator, nu enterprise)
- **Acces:** localhost + Tailscale de pe Android
- **Buget:** $0 (toate serviciile gratuite/free-tier)
- **Volume:** ~10 rapoarte/luna
- **Stack:** Python 3.13 + FastAPI + SQLite | React 18 + Vite + TypeScript + Tailwind
- **AI:** Claude CLI (Opus) + Groq + Gemini Flash + Cerebras — fallback chain 4 nivele
- **Surse date:** ANAF x2, BNR, Tavily, openapi.ro, SEAP, web search (7 clienti)
- **Output:** 5 formate raport (PDF, DOCX, HTML, Excel, PPTX)
- **Status:** Faza 5 COMPLETA — 24 REST endpoints, 1 WebSocket, 9 pagini frontend, 5 agenti AI

---

## INSTRUCTIUNI DE EXECUTIE

### Pas 0 — Pregatire
1. Citeste OBLIGATORIU `CLAUDE.md` si `FUNCTII_SISTEM.md` din radacina proiectului
2. Citeste `SPEC_INTELLIGENCE_SYSTEM_V2.md` (sectiunile relevante, nu integral)
3. Citeste `AUDIT_REPORT.md` pentru context audit anterior
4. Respecta TOATE regulamentele din `.claude/CLAUDE.md` global

### Pas 1 — Profiling Real (OBLIGATORIU — ruleaza INAINTE de analiza)
Masoara date REALE, nu estima. Ruleaza in Bash:
```bash
# Backend
cd C:\Proiecte\Sistem_Inteligent_Analize
python -c "import time; t=time.time(); import backend.main; print(f'Backend import: {time.time()-t:.2f}s')"
python -c "import backend.reports.pdf_generator; print('PDF generator OK')"
python -c "import backend.reports.excel_generator; print('Excel generator OK')"

# Frontend
cd frontend
npm run build 2>&1 | tail -20
# Noteaza: bundle size total, chunk sizes, build time

# Database
python -c "
import sqlite3, os
db = 'data/ris.db'
if os.path.exists(db):
    conn = sqlite3.connect(db)
    for t in ['jobs','companies','reports','data_cache','monitoring_alerts']:
        try:
            c = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
            print(f'{t}: {c} rows')
        except: print(f'{t}: not found')
    print(f'DB size: {os.path.getsize(db)/1024:.0f} KB')
    conn.close()
else: print('DB not found')
"
```
Salveaza TOATE rezultatele — sunt baza raportului.

### Pas 2 — Analiza cod (citeste TOATE fisierele)
- Foloseste Read pe FIECARE fisier .py din backend/ (37+ fisiere)
- Foloseste Read pe FIECARE fisier .tsx/.ts din frontend/src/ (18 fisiere)
- Foloseste Grep pentru pattern-uri specifice (vezi sectiunile de mai jos)
- NU presupune continut — verifica in cod

### Pas 3 — Web Research (OBLIGATORIU pentru sectiuni specifice)
Foloseste WebSearch/WebFetch pentru:
- Verificare API-uri romanesti noi in 2026 (ANAF, ONRC, portal.just.ro, INS)
- Provider scan: AI providers free-tier noi (alternative Groq/Cerebras/Gemini aparute recent)
- FastAPI production best practices 2026
- React 18/19 performance patterns 2026
- Noi surse de date publice romanesti pentru firme

### Pas 4 — Generare raport
- Output in `99_DEEP_DIVE_REPORT.md` in radacina proiectului
- NU modifica NICIUN fisier existent — doar citeste si analizeaza
- Format raport: vezi Sectiunea 9

---

## SECTIUNEA 1 — PROFILING REAL & PERFORMANCE AUDIT

### 1.1 Backend Performance — Masuratori Concrete

**Database:**
- `backend/database.py` — Connection pooling exista sau nu? WAL mode activ? Pragmas setate?
- Cauta TOATE query-urile SQL din `backend/routers/` si `backend/services/` cu Grep
- Identifica: N+1 queries, lipsa LIMIT, full table scans, JOIN-uri neindexate
- Masoara: dimensiune DB, numar rows per tabela, indexuri existente vs necesare

**Async & Concurrency:**
- `backend/agents/base.py` — timeout handling, retry backoff [2, 5, 15]s — optim?
- `backend/agents/orchestrator.py` — Agent 2+3 chiar ruleaza paralel (asyncio.gather) sau secvential?
- `backend/services/job_service.py` — asyncio.create_task leak? Task tracking?
- `backend/main.py` — lifespan cleanup complet? Middleware overhead masurabil?
- Grep `asyncio.sleep` — unde, cat timp, necesar?

**HTTP Clients (6 clienti):**
- Grep `httpx.AsyncClient` — se creeaza per-request sau singleton cu connection pool?
- Fisiere: `anaf_client.py`, `anaf_bilant_client.py`, `tavily_client.py`, `seap_client.py`, `openapi_client.py`, `bnr_client.py`
- Propune httpx.AsyncClient singleton daca nu exista

**Cache:**
- `backend/services/cache_service.py` — cleanup periodic sau doar la job start?
- Masoara: cate entries in cache, dimensiune totala, hit/miss ratio (daca e loggat)

**Report Generation:**
- `backend/reports/generator.py` — secventiala sau paralela?
- Masoara (sau estimeaza din cod): timp per format
- Propune asyncio.gather() daca e secventiala

**Synthesis Agent:**
- `backend/agents/agent_synthesis.py` — subprocess timeout, fallback chain latency
- Ce se intampla cand Claude CLI nu e disponibil (Roland nu e la PC)?

### 1.2 Frontend Performance — Masuratori Concrete

**Bundle (din build real):**
- Chunk sizes din `npm run build` output
- Code splitting: exista React.lazy()? Toate 9 paginile importate eager?
- Tree-shaking: Tailwind purge configurat in `tailwind.config.js`?

**React Patterns (Grep obligatoriu):**
```
Grep: React.memo → cate instante?
Grep: useMemo → cate instante?
Grep: useCallback → cate instante?
Grep: React.lazy → exista?
Grep: console.log|console.error → ramase in production?
```

**Pagini specifice:**
- `Dashboard.tsx` — re-render-uri la fiecare interval? Promise.all fara cleanup?
- `CompareCompanies.tsx` — calcule inline in render fara memoizare?
- `ReportView.tsx` — tab switch re-render complet?
- `ReportsList.tsx` — lista fara virtualizare (problematic la 100+ rapoarte)?

**API Client:**
- `frontend/src/lib/api.ts` — retry logic? abort controllers? request deduplication?
- Error handling: erori afisate user-ului sau doar console.error?

### 1.3 Cross-Platform Audit (Windows + Android via Tailscale)
- CORS: permite acces de pe IP Tailscale, nu doar localhost?
- WebSocket URL: construction dinamica functioneaza peste Tailscale?
- Responsive: paginile se vad ok pe ecran mobil? Dark theme readability pe AMOLED?
- Touch targets: butoanele sunt suficient de mari pe mobile?
- Font loading: Google Fonts se incarca pe Android fara probleme?

### 1.4 Format Output Profiling

Raporteaza TOATE masuratorile intr-un tabel:
```
| Metrica | Valoare Masurata | Target Recomandat | Status |
|---------|-----------------|-------------------|--------|
| Backend import time | X.XXs | < 2s | OK/SLOW |
| Frontend build time | X.XXs | < 30s | OK/SLOW |
| Bundle size total | X KB | < 500KB gzip | OK/BIG |
| Cel mai mare chunk | X KB | < 200KB | OK/BIG |
| DB size | X KB | info | info |
| Cache entries | X | info | info |
```

---

## SECTIUNEA 2 — IMBUNATATIRI PER FUNCTIE EXISTENTA

### FORMAT OBLIGATORIU — Cost-Benefit per Imbunatatire:
```
| Functie | Ce e acum | Imbunatatire | Impact Business | Efort (S/M/L/XL) | ROI | Prioritate |
```
Unde:
- **Impact:** LOW (cosmetic) / MEDIUM (UX mai bun) / HIGH (functionalitate noua sau fix critic)
- **Efort:** S (<30min) / M (1-3h) / L (3-8h) / XL (8h+)
- **ROI:** Impact/Efort — HIGH impact + S efort = BEST ROI
- **Prioritate:** P1 (quick win, faci imediat) / P2 (planifici in urmatoarea sesiune) / P3 (backlog)

### 2.1 API Endpoints (24 + 1 WS)

**Jobs (6 endpoints):**
- POST /api/jobs — Validare stricta input_data per tip analiza? Duplicate detection (aceeasi firma, acelasi tip, ultimele 24h)?
- GET /api/jobs — Paginare: offset-based sau cursor-based? La 1000+ joburi conteaza
- GET /api/jobs/{id} — Field selection (?fields=status,progress) pentru reducere payload?
- POST /api/jobs/{id}/start — Race condition la start simultan? Mutex/lock?
- POST /api/jobs/{id}/cancel — Cleanup complet: opreste agenti, sterge outputs partiale, elibereaza resurse?
- WS /ws/jobs/{id} — Heartbeat interval (30s actual) optim? Message buffer daca client offline temporar?

**Rapoarte (3 endpoints):**
- GET /api/reports — Sortare multi-criteriu? Filtrare: data, scor risc, tip analiza, companie?
- GET /api/reports/{id} — JSON payload mare: compresie gzip? Lazy loading sectiuni?
- GET /api/reports/{id}/download/{format} — Streaming (StreamingResponse) vs load-in-memory? Important la PDF/PPTX mari

**Companii (2 endpoints):**
- GET /api/companies — Foloseste LIKE sau FTS5? SQLite FTS5 ar fi semnificativ mai rapid la search text
- GET /api/companies/{id} — Rapoartele incluse inline sau referinta separata?

**Analiza (3 endpoints):**
- GET /api/analysis/types — Date statice: cached in-memory la startup?
- POST /api/analysis/parse-query — Chatbot accuracy: fuzzy matching? Levenshtein distance? Sinonime CAEN?

**Comparator (1 endpoint):**
- POST /api/compare — Cache rezultate? Limita 2-5: extensibila la 10?

**Monitorizare (5 endpoints):**
- POST /api/monitoring/check-now — Progress per firma (nu doar "all done")? Batch paralel?
- GET /api/monitoring — Include ultimele alerte declansate, nu doar config?

**Configurare (3 endpoints):**
- PUT /api/settings — Validare API keys LIVE (test connectivity) inainte de salvare?
- POST /api/settings/test-telegram — Timeout explicit daca Telegram API e lent?

**Sistem (2 endpoints):**
- GET /api/health — Dependency health: DB writeable? ANAF reachable? Tavily quota OK?
- GET /api/stats — Cache cu TTL 30s (nu query DB la fiecare refresh Dashboard)?

### 2.2 Pagini Frontend (9)

| # | Pagina | Audit UX/Performance/Error Handling |
|---|--------|-------------------------------------|
| 1 | Dashboard | Auto-refresh interval? Grafice trend (joburi/luna, timp mediu)? Error state vizibil (nu doar console)? |
| 2 | NewAnalysis | Draft save? Validare CUI real-time (MOD 11 in browser)? Autocomplete firma din DB local? History cereri anterioare? |
| 3 | AnalysisProgress | ETA calculat (nu doar %)? Log exportabil text? Retry granular per agent (nu doar tot job-ul)? |
| 4 | ReportsList | Sortare multi-coloana? Bulk download ZIP? Filtre persistente in URL (shareable)? Infinite scroll vs pagination? |
| 5 | ReportView | Print-friendly CSS (@media print)? Sectiuni collapsible? Export partial (doar financiar, doar risc)? |
| 6 | Companies | Timeline vizuala per companie? Quick-action "Re-analizeaza"? Badge cu ultimul scor risc? |
| 7 | CompareCompanies | Grafice Chart.js comparative (bar overlay, radar)? Export comparatie PDF? Salvare comparatii favorite? |
| 8 | Monitoring | Mini-dashboard alerte recente? Frecventa per-firma (nu globala)? Status indicator (ultima verificare: acum 2h)? |
| 9 | Settings | Health check vizual per API (verde/rosu la salvare)? Grupare logica: AI / Surse date / Notificari? |

### 2.3 Agenti AI (5)

| # | Agent | Fisier | Audit Specific |
|---|-------|--------|----------------|
| 1 | OfficialAgent | agent_official.py | Parsare ANAF robusta la toate edge-cases? Retry inteligent (adaptive, nu doar exponential)? Noi campuri ANAF parsate? |
| 2 | WebAgent | orchestrator.py (run_web) | Filtrare noise din Tavily? Deduplicare surse? Relevance scoring pe rezultate? |
| 3 | MarketAgent | orchestrator.py (run_market) | SEAP pagination completa? Filtre valoare/data? Trend licitatii (cresc/scad in domeniu)? |
| 4 | VerificationAgent | agent_verification.py | Ponderi scoring optime? Calibrate pe date reale? Noi reguli anomalii? |
| 5 | SynthesisAgent | agent_synthesis.py | Prompt quality per fallback provider? Template-uri per industrie (constructii vs IT vs retail)? |

### 2.4 AI Prompt Optimization (SECTIUNE NOUA — HIGH IMPACT)

Citeste si analizeaza:
- `backend/prompts/system_prompt.py` — System prompt pentru synthesis
- `backend/prompts/section_prompts.py` — Template-uri per sectiune raport (138 linii)

Pentru FIECARE prompt:
1. E suficient de specific? Sau prea generic?
2. Contine instructiuni de format (structura output)?
3. Specifica ce sa NU includa (halucinatii, date inventate)?
4. E optimizat pentru fiecare provider (Claude vs Groq vs Gemini — au stiluri diferite)?
5. Include exemplu de output dorit (few-shot)?
6. Propune varianta imbunatatita cu justificare

### 2.5 Surse de Date (7 clienti)

| # | Client | Fisier | Audit |
|---|--------|--------|-------|
| 1 | ANAF TVA | anaf_client.py | Circuit breaker pattern? Handling 404-cu-JSON-valid robust? |
| 2 | ANAF Bilant | anaf_bilant_client.py | Toti indicatorii parsati? Edge-case firme micro vs mari? Trend multi-an calculat corect? |
| 3 | BNR | bnr_client.py | Cache TTL 24h e prea scurt (cursul se schimba zilnic la 13:00)? |
| 4 | Tavily | tavily_client.py | Smart query construction? Quota prediction? Query optimization (termeni inutili eliminati)? |
| 5 | openapi.ro | openapi_client.py | Fallback daca e down? Toate campurile ONRC parsate? Rate limit (100/luna) tracking? |
| 6 | SEAP | seap_client.py | Pagination completa? Toate campurile extrase? Filtrare dupa CPV code? |
| 7 | CUI Validator | cui_validator.py | Batch validation? Error messages descriptive? |

### 2.6 Formate Raport (5)

| # | Format | Fisier | Audit |
|---|--------|--------|-------|
| 1 | PDF | pdf_generator.py | Layout profesional? Header/footer branding? TOC? Watermark "CONFIDENTIAL"? Page numbers? |
| 2 | DOCX | docx_generator.py | Template master customizabil? TOC auto? Styles consistente? Cover page profesionala? |
| 3 | HTML | html_generator.py | Chart.js drill-down? @media print CSS? Responsive mobile? Sectiuni collapsible? |
| 4 | Excel | excel_generator.py | Formule dinamice? Conditional formatting? Dashboard sheet cu sparklines? Named ranges? |
| 5 | PPTX | pptx_generator.py | Master slide template? Speaker notes cu talking points? Consistent branding? |

### 2.7 Servicii Backend (5)

| # | Serviciu | Fisier | Audit |
|---|---------|--------|-------|
| 1 | Job Service | job_service.py | Job recovery la crash? Priority queue? Retry automat jobs failed? |
| 2 | Cache | cache_service.py | Background cleanup (nu doar la job start)? Hit/miss stats? Cache warming? |
| 3 | Notification | notification.py | Queue cu retry? Template-uri HTML? History notificari? |
| 4 | Delta | delta_service.py | Delta vizual (diff colorat)? Alerta automata schimbari majore (>20% CA)? |
| 5 | Monitoring | monitoring_service.py | Scheduler intern (cron) vs manual check-now? Frequency per firma? |

### 2.8 Securitate (6 masuri)

| # | Masura | Audit |
|---|--------|-------|
| 1 | Security Headers | CSP (Content-Security-Policy) lipsa? Permite inline scripts (Chart.js)? |
| 2 | SQL | Grep `f"` si `f'` in .py files cu SQL — confirma ZERO string interpolation |
| 3 | .env | Fisierul e in .gitignore? Default secret_key schimbat? |
| 4 | Input | CUI field: injection posibil? Company name: XSS stored? |
| 5 | Pydantic | TOATE campurile au max_length? Regex pe CUI, email, URL? |
| 6 | CORS | Origins whitelist corecta? Credentials handling? Tailscale IP permis? |

### 2.9 Scoring Risc (6 dimensiuni + 6 anomalii)

- Ponderile (30/20/15/15/10/10) — bazate pe ce? Propune alternative cu justificare
- Cele 6 reguli anomalii — acopera toate cazurile? Propune noi reguli (minim 3)
- Scoring history: exista salvare scor vechi pt delta? Daca nu, propune
- Benchmark industrie: scor relativ la media CAEN — fezabil cu datele disponibile?

### 2.10 Dead Code Scan (Rapid — max 10 min)

Grep rapid pentru:
- Functii Python definite dar neapelate nicaieri
- Componente React exportate dar neimportate
- Endpoint-uri API fara corespondent in frontend api.ts
- Importuri nefolosite
- Variabile de configurare din .env.example fara utilizare in cod

---

## SECTIUNEA 3 — PROVIDER SCAN & WEB RESEARCH

### 3.1 API-uri Romanesti — Verificare 2026

Foloseste **WebSearch** pentru a verifica status actual:
- **ANAF API** — exista versiuni mai noi decat v9? Noi endpoint-uri?
- **ONRC / Registrul Comertului** — API public aparut? (in 2025 era doar openapi.ro)
- **portal.just.ro** — date litigii accesibile programatic?
- **BPI (Buletinul Procedurilor de Insolventa)** — API sau scraping legal?
- **INS (TEMPO Online)** — API JSON disponibil? Date per CAEN/judet?
- **Monitorul Oficial** — API pentru publicatii societati comerciale?
- **SEAP** — API-ul de la e-licitatie.ro are versiuni noi?
- **Lista sanctiuni BNR/UE/OFAC** — endpoint-uri publice?

### 3.2 AI Providers Free-Tier — Ce e Nou in 2026

Foloseste **WebSearch** pentru:
- Alternative noi la Groq free tier (au schimbat limitele?)
- Alternative noi la Gemini Flash free tier
- Alternative noi la Cerebras free tier
- Provideri AI noi cu free tier generos (Mistral? DeepSeek? Cohere?)
- Modele noi open-source care merg pe Groq/Cerebras (mai bune decat Llama 3.3?)

### 3.3 Best Practices 2026 — FastAPI + React Production

Foloseste **WebSearch** pentru:
- FastAPI production checklist 2026 — ce lipseste din RIS?
- React 18/19 performance patterns noi
- SQLite production patterns (WAL2? STRICT tables? JSON support?)
- Vite 6+ optimization features noi
- Tailwind CSS v4 (daca RIS e pe v3, merita upgrade?)

---

## SECTIUNEA 4 — FUNCTII NOI PROPUSE

### FORMAT OBLIGATORIU — Cost-Benefit:
```
| Functie | Descriere | Valoare Business | Efort | Dependinte | ROI | Prioritate |
```

### 4.1 Surse de Date Noi pentru Documentare Firme

Investigheaza si propune integrari FEZABILE (gratuite):

**Surse oficiale romanesti:**
- **Lista Neagra BNR** — sanctiuni, entitati interzise
- **Portal Insolventa / BPI** — proceduri insolventa publice
- **Registrul Beneficiarilor Reali** — structura actionariat (daca e public)
- **INS TEMPO** — statistici macro per industrie/judet (media CA pe CAEN, numar firme pe judet)
- **Monitorul Oficial** — infiintare, modificari act constitutiv, dizolvari
- **Registrul Asociatilor si Fundatiilor** — pentru ONG-uri

**Surse internationale/europene:**
- **EU Sanctions List (Consolidated)** — verificare sanctiuni UE
- **OpenCorporates** — date firme cross-border (API gratuit limitat)
- **European Business Register** — legaturi cu firme UE
- **LEI (Legal Entity Identifier)** — identificator global

**Surse complementare:**
- **Google Maps Places API** — locatie reala, reviews, program, poze sediu (free tier)
- **Trustpilot/Google Reviews** — reputatie online structurata
- **Social media presence** — Facebook page, LinkedIn company, activity level

### 4.2 Functii Noi pentru Documentare Firme Mai Ampla si Mai Precisa

**CRITICA — Aceste functii cresc direct calitatea si profunzimea rapoartelor:**

| # | Functie | Ce rezolva | Cum se integreaza |
|---|---------|-----------|-------------------|
| 1 | **Istoric Financiar Complet (5-10 ani)** | Acum ANAF Bilant da date multi-an dar raportul nu le exploateaza vizual complet | Grafice trend CA/profit/angajati pe 5-10 ani in TOATE formatele, nu doar HTML |
| 2 | **Profil Actionariat & Persoane Cheie** | Clientii vor sa stie CINE e in spatele firmei, nu doar CUI-ul | openapi.ro are asociati + administratori — extrage si include in raport |
| 3 | **Analiza CAEN Detaliata** | Acum CAEN e doar un cod — nu contextualizeaza | Adauga: descriere activitate, numar total firme pe CAEN in Romania, pozitie firma in industrie |
| 4 | **Matricea Relatii Firma** | O firma singura nu spune tot — relatiile (furnizori, clienti, grup) conteaza | Cross-reference CUI-uri din SEAP (cu cine a contractat), firme cu aceeasi adresa/administrator |
| 5 | **Due Diligence Checklist Automat** | Raportul e narativ — clientii vor si o lista de verificare da/nu | Genereaza automat: TVA activ DA, Insolventa NU, Datorii NECUNOSCUT, etc. — checklist binar |
| 6 | **Istoric Modificari Firma** | Nu stii daca firma si-a schimbat numele/adresa/CAEN recent — red flag | Daca Monitorul Oficial e accesibil: timeline modificari. Alternativ: openapi.ro change history |
| 7 | **Analiza Geografica** | Adresa firmei e doar text — nu contextualizeaza | Judet, oras, zona economica, proximitate alte firme din domeniu, densitate competitie locala |
| 8 | **Benchmark Financiar CAEN** | Scorul 0-100 e absolut — clientii vor "comparativ cu piata" | Media CA/profit/angajati pe CAEN din INS TEMPO sau estimare din datele colectate |
| 9 | **Raport Furnizor/Client Scoring** | Diferent de "profil complet" — focus pe "merita sa fac business cu ei?" | Scoring dedicat: capacitate livrare, stabilitate financiara, istoric plati, litigii active |
| 10 | **Alerta Early Warning** | Detecteaza semnale INAINTE de probleme, nu dupa | Reguli: scadere CA >30% yoy, pierdere 2 ani consecutiv, reducere angajati >50%, schimbare administrator frecventa |
| 11 | **Document Generator — Contract Framework** | Dupa analiza, urmatorul pas e contractul | Template contract cadru pre-populat cu datele firmei analizate (CUI, adresa, reprezentant) |
| 12 | **Comparative Report Multi-Period** | Aceeasi firma la 6 luni distanta — ce s-a schimbat? | Delta automat intre 2+ rapoarte ale aceleiasi firme, cu highlight schimbari semnificative |
| 13 | **Sector Report** | Nu doar o firma — tot sectorul | "Toate firmele de constructii din Cluj cu CA > 1M" — agregare, top 10, statistici sector |
| 14 | **Export CRM-Ready** | Datele firmei trebuie sa ajunga in CRM-ul clientului | Export JSON/CSV structurat cu campuri standard (company_name, cui, address, phone, email, website, risk_score) |
| 15 | **Raport Executiv 1-Pager** | Unii clienti nu vor 20 pagini — vor esentialul pe o singura foaie | Format nou: PDF 1 pagina cu: scor, top 3 strengths, top 3 risks, recomandare da/nu |
| 16 | **Analiza Grup Firme** | Un antreprenor are 3-5 firme — analiza consolidata | Input: lista CUI-uri acelasi proprietar → raport grup cu date agregate + relatii intre firme |
| 17 | **Verificare Debite Fiscale** | ANAF are date publice despre datorii bugetare | Daca API-ul exista: datorie ANPS, datorie locale — incluse automat in scoring |
| 18 | **Analiza Web Footprint Extinsa** | Tavily da rezultate brute — nu analizeaza calitativ | Site propriu: exista? SSL? Actualizat? Social media: activa? Followers? Posting frequency? |

### 4.3 Functionalitati Noi Backend

| # | Functie | Descriere | Valoare |
|---|---------|-----------|---------|
| 1 | **Scheduler Intern (APScheduler)** | Cron-like pentru monitoring periodic — elimina "check-now" manual | Monitorizare devine cu adevarat automata |
| 2 | **Batch Analysis** | Upload CSV cu 10-50 CUI-uri → analiza in serie/paralel cu progress total | Clienti care vor analiza portofoliu furnizori |
| 3 | **Job Queue Persistent** | Priority queue cu retry automat la failed + rate limiting global | Robustete la volume mai mari |
| 4 | **Report Templates Engine** | Template-uri customizabile per client (branding, sectiuni, limba) | Rapoarte personalizate fara cod |
| 5 | **Audit Log** | Log complet: cine a cerut ce, cand, cu ce rezultat | Compliance + troubleshooting |
| 6 | **PDF Merge** | Combina rapoarte multiple intr-un singur PDF cu TOC | Livrare portofoliu complet |
| 7 | **Webhook Notifications** | POST la URL extern cand job-ul e gata | Integrare cu alte sisteme |
| 8 | **Data Retention Policy** | Auto-cleanup rapoarte/cache vechi (>90 zile) cu backup | DB nu creste nelimitat |
| 9 | **API Versioning** | /api/v1/ prefix pentru backward compatibility | Pregatire evolutie API |
| 10 | **Rate Limiter Global** | slowapi sau custom — protejeaza toate endpoint-urile | Previne abuse accidental |

### 4.4 Functionalitati Noi Frontend

| # | Functie | Descriere | Valoare |
|---|---------|-----------|---------|
| 1 | **Dark/Light Mode Toggle** | Unii utilizatori prefera light — toggle in Settings | Accesibilitate |
| 2 | **Dashboard Grafice Trend** | Chart.js pe Dashboard: joburi/luna, timp mediu, distributie tipuri | Vizibilitate activitate |
| 3 | **Global Search** | Cauta in rapoarte + companii + joburi dintr-un singur input | UX rapid |
| 4 | **Timeline Companie** | Vizualizare cronologica toate analizele unei firme | Istoric vizual |
| 5 | **Export Comparatie** | PDF/Excel din pagina Compare | Livrabil catre clienti |
| 6 | **Toast Notifications** | Erori si succese afisate vizibil, nu doar console | UX profesional |
| 7 | **Keyboard Shortcuts** | Ctrl+N=new, Ctrl+K=search, Esc=close | Power user efficiency |
| 8 | **Offline Indicator** | Banner cand backend-ul nu raspunde | Debugging rapid |
| 9 | **Report Preview** | Preview raport inainte de download (HTML inline) | UX |
| 10 | **Batch Actions** | Select multiple rapoarte → download ZIP / delete / re-run | Eficienta |

### 4.5 AI & Intelligence

| # | Functie | Descriere | Valoare |
|---|---------|-----------|---------|
| 1 | **Predictive Risk Scoring** | Trend scor risc bazat pe date istorice: "firma merge spre rosu" | Anticipare, nu reactie |
| 2 | **Industry Benchmarking** | Compara cu media CAEN din datele colectate | Context pentru scor |
| 3 | **Sentiment Analysis** | Pe stiri si recenzii din Tavily — nu doar text brut | Reputatie cuantificata |
| 4 | **Smart Query** | "firme din Cluj cu scor sub 40 si CA peste 1M" → query SQL automat | Power feature |
| 5 | **Auto-Suggest Analysis** | Bazat pe profil firma: "aceasta firma ar beneficia de analiza competitie" | Upsell natural |
| 6 | **Executive Summary Auto** | La login: "3 firme monitorizate au schimbari, 2 rapoarte noi" | Dashboard inteligent |

### 4.6 DevOps & Operational

| # | Functie | Descriere | Valoare |
|---|---------|-----------|---------|
| 1 | **Structured Logging** | loguru → JSON cu rotatie, nivel per modul | Debugging production |
| 2 | **Health Check Avansat** | /api/health verifica: DB writable, ANAF reachable, Tavily quota, disk space | Monitoring real |
| 3 | **Auto-Backup DB** | SQLite .backup() periodic → timestamped file | Zero data loss |
| 4 | **Performance Metrics** | Endpoint /api/metrics: timp per agent, per sursa, cache hit ratio | Optimizare informata |
| 5 | **Error Aggregation** | Colecteaza si grupeaza erori (nu doar log) — afisare in Dashboard | Prioritizare fix-uri |

---

## SECTIUNEA 5 — ROADMAP CU DEPENDINTE

Genereaza un roadmap prioritizat care respecta dependintele. Format:

```
FAZA 6A — Quick Wins Performance (1-2 sesiuni)
  ├─ [QW1] httpx.AsyncClient singleton ← nu depinde de nimic
  ├─ [QW2] React.lazy() code splitting ← nu depinde de nimic
  ├─ [QW3] Cache background cleanup ← nu depinde de nimic
  └─ [QW4] ... (listeaza TOATE quick wins gasite)

FAZA 6B — Documentare Firme Extinsa (3-5 sesiuni)
  ├─ [DF1] Profil actionariat din openapi.ro ← depinde de Agent 1
  ├─ [DF2] Istoric financiar complet vizual ← depinde de ANAF Bilant existent
  ├─ [DF3] Due diligence checklist ← depinde de VerificationAgent
  └─ [DF4] ... (ordonate dupa dependinte)

FAZA 6C — Functii Core Noi (5-8 sesiuni)
  ├─ [FC1] Scheduler APScheduler ← prerequisite pentru monitoring automat
  ├─ [FC2] Batch Analysis ← depinde de job queue
  └─ [FC3] ...

FAZA 6D — Polish & Nice-to-Have (backlog)
  └─ [NH1] Dark/Light toggle
  └─ [NH2] ...
```

**IMPORTANT:** Marcheaza explicit dependintele: `[DF2] depinde de [DF1]` — nu propune ordine aleatorie.

---

## SECTIUNEA 6 — BEST PRACTICES COMPARISON

Compara RIS cu un checklist de productie FastAPI + React:

```
| Practica | Status RIS | Recomandare | Prioritate |
|----------|-----------|-------------|-----------|
| Connection pooling | ? | verificare | P1 |
| Structured logging | ? | JSON + rotatie | P2 |
| Health checks deep | PARTIAL | adauga deps | P1 |
| CORS production | ? | audit | P1 |
| Rate limiting | PER-CLIENT | global | P2 |
| Error boundaries React | ? | adauga | P2 |
| Code splitting | ? | React.lazy | P1 |
| CSP headers | LIPSA? | adauga | P2 |
| Input sanitization | DA (Pydantic) | audit complet | P2 |
| API versioning | NU | /api/v1/ | P3 |
| Graceful shutdown | ? | verificare | P2 |
| Request timeout global | ? | verificare | P1 |
```

---

## SECTIUNEA 7 — METRICI ACTUALE vs TARGET

```
| Metrica | Actual (masurat) | Target | Cum Masori |
|---------|-----------------|--------|-----------|
| Backend cold start | ?s | < 3s | time python import |
| Analiza completa (end-to-end) | ?min | < 5min nivel 1 | timestamp job start→done |
| Frontend bundle | ?KB | < 500KB gzip | npm run build |
| Largest chunk | ?KB | < 200KB | npm run build |
| DB query slowest | ?ms | < 100ms | sqlite3 .timer on |
| Cache hit ratio | ?% | > 70% | cache_service stats |
| Report gen time | ?s | < 10s all 5 | timestamp in generator |
| WebSocket reconnect | ?s | < 5s | useWebSocket config |
| ANAF API response | ?s | < 3s avg | agent logging |
| Tavily quota used | ?/1000 | monitor | tavily_client |
```

---

## SECTIUNEA 8 — SNAPSHOT PARSABIL

La FINALUL raportului, genereaza un bloc JSON parsabil pentru comparatie viitoare:

```json
{
  "snapshot_date": "2026-03-20",
  "version": "RIS 1.1",
  "metrics": {
    "backend_import_time_s": null,
    "frontend_bundle_kb": null,
    "db_size_kb": null,
    "total_endpoints": 25,
    "total_pages": 9,
    "total_agents": 5,
    "total_report_formats": 5,
    "total_data_sources": 7,
    "code_lines_backend": 5800,
    "code_lines_frontend": 2500
  },
  "scores": {
    "performance": "?/10",
    "security": "?/10",
    "code_quality": "?/10",
    "documentation": "?/10",
    "ux": "?/10",
    "overall": "?/10"
  },
  "improvements_proposed": {
    "p1_count": 0,
    "p2_count": 0,
    "p3_count": 0,
    "new_functions_proposed": 0
  }
}
```

Completeaza cu valorile reale masurate. La urmatorul deep dive, se compara cu acest snapshot.

---

## SECTIUNEA 9 — FORMAT RAPORT FINAL

Genereaza `99_DEEP_DIVE_REPORT.md` cu EXACT aceasta structura:

```markdown
# Deep Dive Report — Roland Intelligence System
Data: [data] | Executor: Claude Code (Opus) | Durata analiza: ~Xmin

## Executive Summary
[5-7 propozitii: stare generala, top 3 probleme de performance, top 3 imbunatatiri quick-win,
 top 3 functii noi cu cel mai mare impact pentru documentare firme]

## 1. Profiling Real — Masuratori
[tabelele din Sectiunea 1.4 si 7 completate cu date REALE]

## 2. Performance Audit
### 2.1 Backend [tabel probleme cu prioritate + cost-benefit]
### 2.2 Frontend [tabel probleme cu prioritate + cost-benefit]
### 2.3 Cross-Platform [Tailscale + Android findings]
### 2.4 Quick Wins (sub 30 min, ROI maxim)

## 3. Imbunatatiri Functii Existente
### Per categorie (A-J din FUNCTII_SISTEM.md)
[tabel cu cost-benefit: functie | imbunatatire | impact | efort | ROI | prioritate]

## 4. AI Prompt Optimization
[analiza detaliata prompts + variante imbunatatite]

## 5. Provider Scan & Web Research
### 5.1 API-uri Romanesti 2026 [ce e nou/schimbat]
### 5.2 AI Providers [alternative gasite]
### 5.3 Best Practices [ce lipseste]

## 6. Functii Noi — Documentare Firme Extinsa
[tabelul din 4.2 completat cu cost-benefit si fezabilitate verificata]

## 7. Functii Noi — Backend/Frontend/AI/DevOps
[tabelele din 4.3-4.6 completate]

## 8. Best Practices Comparison
[tabelul din Sectiunea 6]

## 9. Roadmap cu Dependinte
[diagrama din Sectiunea 5 — Faze 6A/6B/6C/6D cu dependinte]

## 10. Metrici Actuale vs Target
[tabelul din Sectiunea 7 completat]

## 11. Dead Code & Cleanup
[rezultate scan rapid]

## Snapshot JSON
[blocul JSON parsabil din Sectiunea 8]

## Anexa A: Fisiere Analizate
[lista completa fisiere citite]

## Anexa B: Comenzi Rulate
[lista comenzi Bash executate cu output-ul lor]
```

---

## RESTRICTII

1. **NU modifica niciun fisier existent** — doar citeste, masoara si analizeaza
2. **NU inventa functionalitati** care nu exista — verifica in cod cu Grep/Read inainte de a raporta
3. **Respecta regulamentul** din CLAUDE.md (global + proiect)
4. **Prioritizeaza pragmatic** — proiectul e pentru 1 utilizator pe Windows, nu enterprise
5. **Cost $0** — toate propunerile trebuie sa functioneze cu servicii gratuite sau deja platite
6. **Windows 10 compatibil** — fara dependinte Linux-only sau GTK
7. **Limba raport: Romana** (cod si comenzi tehnice in engleza)
8. **Verifica FIECARE propunere** — daca propui o API, verifica cu WebSearch ca exista si e accesibila in 2026
9. **Date reale, nu estimari** — ruleaza comenzile de profiling, nu presupune timpi
10. **Cost-benefit pe FIECARE propunere** — nu exista propunere fara efort si impact estimat

---

## TOOLS & SKILLS DISPONIBILE

Foloseste ORICE combinatie necesara:

| Tool | Cand |
|------|------|
| **Read** | Citeste FIECARE fisier .py si .tsx |
| **Grep** | Pattern-uri: `asyncio.sleep`, `httpx.AsyncClient`, `React.memo`, `useMemo`, `console.log`, `TODO`, `FIXME`, `f"SELECT`, `f'SELECT` |
| **Glob** | Inventar complet fisiere per tip |
| **Bash** | Profiling: `npm run build`, `python -c "..."`, `du -sh`, DB queries |
| **Agent (Explore)** | Deep exploration pe arii complexe |
| **WebSearch** | API-uri romanesti 2026, AI providers, best practices |
| **WebFetch** | Verificare endpoints API specifice |
| **/health** | Health check sistem (daca disponibil ca skill) |

---

## CHECKLIST FINAL

Inainte de a genera raportul 99_DEEP_DIVE_REPORT.md, confirma TOATE:
- [ ] Am rulat comenzile de profiling si am date REALE (Sectiunea 1)
- [ ] Am citit TOATE fisierele .py din backend/ (37+ fisiere)
- [ ] Am citit TOATE fisierele .tsx/.ts din frontend/src/ (18 fisiere)
- [ ] Am facut Grep pe TOATE pattern-urile cerute
- [ ] Am verificat fiecare propunere de imbunatatire in codul actual
- [ ] Am rulat WebSearch pentru API-uri, providers si best practices
- [ ] Am verificat fezabilitatea API-urilor noi propuse
- [ ] Am analizat prompt-urile AI si propus imbunatatiri
- [ ] Am clasificat TOATE propunerile cu cost-benefit (impact + efort + ROI)
- [ ] Am generat roadmap cu dependinte explicite
- [ ] Am completat snapshot-ul JSON parsabil
- [ ] Raportul respecta EXACT formatul din Sectiunea 9
- [ ] Zero propuneri care necesita plata sau dependinte incompatibile Windows
- [ ] Limba: romana (cod in engleza)
