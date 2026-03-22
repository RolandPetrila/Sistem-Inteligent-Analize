# Deep Research: Extindere RIS — Functionalitati, Surse Oficiale, Calitate Profesionala

Data: 2026-03-20 | Autor: Claude Code (Opus) + Web Research

---

## DESCOPERIRE CRITICA: ANAF Bilant API

Cea mai importanta descoperire din acest research: ANAF ofera un API GRATUIT
pentru date financiare complete (bilant) per CUI, pe care NU il folosim inca.

```
GET https://webservicesp.anaf.ro/bilant?an=2024&cui=18189442
```

Returneaza JSON cu: cifra de afaceri, profit brut, profit net, numar angajati,
capitaluri proprii, datorii totale, active imobilizate, active circulante.
Disponibil pentru anii 2014-2024. Gratuit, fara API key, fara limita explicita.

IMPACT: Datele financiare trec de la ESTIMAT (listafirme.ro, Nivel 2)
la OFICIAL (ANAF/MF, Nivel 1). Transforma complet calitatea rapoartelor.

Documentatie: https://static.anaf.ro/static/10/Anaf/Informatii_R/doc_WS_Bilant_V1.txt
Sursa: https://www.anaf.ro/anaf/internet/ANAF/servicii_online/servicii_web_anaf

---

## PRIORITATE 1 — Game Changers (impact maxim, efort mic-mediu)

### 1.1 ANAF Bilant API Client
- Endpoint: GET webservicesp.anaf.ro/bilant?an={year}&cui={cui}
- Implementare: anaf_bilant_client.py (similar cu anaf_client.py existent)
- Interogare multi-an: 2019-2024 = trend financiar pe 5 ani
- Integrare in Agent 1 → output "financial_official" cu trust OFICIAL
- Grafice automate: evolutie CA, profit, angajati (matplotlib → SVG)
- Efort: MIC (e un GET simplu)

### 1.2 Scoring Numeric 0-100 Multi-Dimensional
- Actual: Verde/Galben/Rosu (3 niveluri, calitativ)
- Propus: Scor 0-100 cu breakdown pe 6 dimensiuni:
  - Financiar (30%): lichiditate, solvabilitate, profitabilitate, trend CA
  - Juridic (20%): litigii active, insolventa, faliment
  - Fiscal (15%): datorii ANAF, inactiv, split TVA
  - Operational (15%): vechime firma, angajati, CAEN activ
  - Reputational (10%): presa, recenzii, prezenta online
  - Piata (10%): pozitie competitie, contracte publice
- Efort: MEDIU (logica Python, calibrare weights)

### 1.3 Grafice Financiare Automate
- Cu ANAF Bilant pe 5 ani:
  - Bar chart: evolutie cifra de afaceri
  - Line chart: evolutie profit net
  - Bar chart: evolutie numar angajati
  - Gauge: rate financiare (profitabilitate, solvabilitate)
- Inline in PDF (matplotlib → SVG) si HTML (Chart.js)
- Efort: MEDIU

### 1.4 Cross-Validare Multi-Sursa
- Fiecare camp critic verificat in min. 2 surse independente
- Confidence score per camp: 1.0 (3 surse) / 0.7 (2 surse) / 0.4 (1 sursa)
- Exemplu: denumire firma → ANAF + openapi.ro + listafirme.ro
- Discrepante → NECONCLUDENT cu ambele variante + link surse
- Efort: MIC (logica in Agent 4 Verification)

### 1.5 Validare CUI cu Cifra de Control
- Formula: MOD 11 cu ponderi [7,5,3,2,1,7,5,3,2]
- Validare INAINTE de orice API call
- Previne request-uri inutile + erori "CUI not found"
- Efort: MIC (~20 linii Python)

---

## PRIORITATE 2 — Valoare Adaugata Profesionala (impact mare, efort mediu)

### 2.1 SEAP API Client — Licitatii si Contracte
- POST https://e-licitatie.ro/api-pub/NoticeCommon/GetCANoticeList/
- POST https://e-licitatie.ro/api-pub/DirectAcquisitionCommon/GetDirectAcquisitionList/
- Date: licitatii active, contracte castigate, achizitii directe per CUI
- ATENTIE: Rate limit strict din martie 2025, necesita delay + cache
- Util pentru: TIP 4 (Tender) + profil achizitii publice in orice raport
- Sursa: https://github.com/ciocan/sicap-parser (Postman collection documentata)

### 2.2 Openapi.ro Client — Date ONRC Structurate
- 100 req/luna gratuit (suficient pentru 10 rapoarte cu competitori)
- Date: CAEN, adresa completa, asociati, administratori, capital social, puncte de lucru
- Inlocuieste Tavily search ONRC = date structurate JSON, nu text brut
- Signup: https://openapi.ro/
- Efort: MIC (REST API cu API key)

### 2.3 Excel Generator Complet
- Sheet 1: Rezumat executiv + scor risc vizual
- Sheet 2: Date financiare multi-an cu GRAFICE native Excel
- Sheet 3: Competitori (tabel sortabil)
- Sheet 4: Licitatii/contracte SEAP
- Sheet 5: Audit trail surse complet
- Biblioteca: openpyxl (deja in requirements.txt)

### 2.4 Comparator Side-by-Side (2-3 firme)
- Pagina noua: /compare
- Selecteaza firme din DB proprie sau introduce CUI-uri noi
- Tabel comparativ: CA, profit, angajati, risc, CAEN
- Grafic radar overlay pe dimensiuni de risc
- Util pentru: "care furnizor e mai sigur?" "cine e liderul pietei?"

### 2.5 Detectare Automata Firme Fantoma / Anomalii
- Reguli bazate pe date ANAF Bilant:
  - 0 angajati + CA > 1M RON = SUSPECT
  - Inactiv ANAF + contracte SEAP recente = ANOMALIE
  - Capital social 200 RON + contracte publice > 100K RON = ATENTIE
  - Schimbari frecvente administratori (3+ in 2 ani) = INSTABILITATE
  - Firma <1 an vechime + licitatie publica = RISC
- Afiseaza ca "Alerte" in sectiunea de risc

---

## PRIORITATE 3 — Polish Profesional (impact mediu, efort mic)

### 3.1 Numar Raport Unic
- Format: RIS-2026-0001, RIS-2026-0002...
- Auto-increment in DB, afisat pe cover page si header

### 3.2 Watermark PDF
- CONFIDENTIAL / DRAFT / FINAL — selectabil din wizard
- Semi-transparent diagonal pe fiecare pagina

### 3.3 Disclaimer Legal Complet
- Metodologie: ce surse, ce algoritmi, ce limitari
- GDPR: baza legala pentru date personale (registre publice)
- Nu inlocuieste consultanta profesionala
- Data generarii + versiune sistem

### 3.4 Dashboard Analitic Imbunatatit
- Grafic activitate ultimele 30 zile
- Top 5 firme analizate cu mini-sparkline risc
- Status integrari live (ANAF OK, BNR OK, Tavily 234/1000)
- Quick action: "Analiza rapida CUI: ___"

### 3.5 Link Partajabil HTML
- /report/html/{token} — servit static
- Token unic per raport (UUID)
- Expirare configurabila (30 zile default)
- Roland trimite link in loc de atasament

---

## PRIORITATE 4 — De implementat ulterior

- Agent 2 Web Intelligence complet (Playwright scraping)
- Agent 3 Market Research complet (SEAP + fonduri)
- Monitoring TIP 8 (cron + alerte Telegram)
- PPTX generator (PowerPoint)
- Modul prezentare full-screen
- Alertacui.ro integrare (monitoring)
- Data.gov.ro datasets (statistici macro)
- Mfinante.gov.ro scraping (date financiare alternative)

---

## SURSE OFICIALE — HARTA COMPLETA

### Nivel 1 — Surse Guvernamentale Directe (GRATUITE)
| Sursa | URL | Status in RIS | Date | Efort |
|-------|-----|---------------|------|-------|
| ANAF TVA/Datorii | webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva | IMPLEMENTAT | TVA, stare, adresa | - |
| ANAF Bilant | webservicesp.anaf.ro/bilant | DE IMPLEMENTAT | CA, profit, angajati | Mic |
| BNR Cursuri | bnr.ro/nbrfxrates.xml | IMPLEMENTAT | Cursuri valutare | - |
| SEAP Licitatii | e-licitatie.ro/api-pub/ | DE IMPLEMENTAT | Licitatii, contracte | Mediu |
| Data.gov.ro | data.gov.ro/api | NEIMPLEMENTAT | Open datasets | Mic |

### Nivel 1.5 — API-uri Romanesti cu Free Tier
| Sursa | URL | Limita | Date |
|-------|-----|--------|------|
| openapi.ro | openapi.ro | 100 req/luna gratuit | ONRC, CAEN, adresa, asociati |
| alertacui.ro | alertacui.ro/api | Gratuit (limitat) | Monitorizare, agregate ANAF+ONRC |

### Nivel 2 — Via Tavily Search
| Sursa | Query pattern | Date |
|-------|--------------|------|
| listafirme.ro | site:listafirme.ro "{CUI}" | Date financiare agregate |
| portal.just.ro | site:portal.just.ro "{firma}" | Litigii |
| bpi.ro | site:bpi.ro "{CUI}" | Insolventa |

---

## RECOMANDARE FINALA

Implementeaza PRIORITATEA 1 (items 1.1-1.5) in urmatoarea sesiune de lucru.

Aceste 5 imbunatatiri transforma RIS de la "proof of concept functional"
la "instrument profesional de business intelligence" cu:
- Date financiare OFICIALE pe 5 ani (nu estimate)
- Scoring cantitativ 0-100 (nu doar 3 culori)
- Grafice profesionale (nu doar text)
- Validare multi-sursa (nu just "am citit de pe un site")
- Verificare CUI inainte de orice (nu erori inutile)

Efort total estimat: o sesiune de lucru (~2-3 ore).
