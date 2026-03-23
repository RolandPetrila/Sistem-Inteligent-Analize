# R7 EXECUTOR INSTRUCTIONS — CALITATE RAPOARTE & SURSE NOI

> Director: C:\Proiecte\Sistem_Inteligent_Analize
> Total: 15 items (9 HIGH + 6 MED) | 3 sesiuni | ~28.5h estimat
> Generat: 2026-03-23

---

## CITESTE OBLIGATORIU INAINTE DE ORICE

- `CLAUDE.md` (conventii proiect, stack, key files)
- `ROLAND_PLANIFICARI_MODULE.md` (sectiunea R7 — 15 items cu descrieri complete, dependente, protocol test)

## REGULI EXECUTIE

1. Implementeaza TOATE cele 15 items din R7 (E1, E5, EP1, EP2, EP3, E2, E6, E3, E13, E4, E9, E12, E11, ER1, ER2)
2. Respecta ORDINEA pe sesiuni din plan (Sesiune 1 -> 2 -> 3) si DEPENDENTELE cross-module
3. Dupa FIECARE item implementat, marcheaza `[x]` in ROLAND_PLANIFICARI_MODULE.md
4. La final, ruleaza teste: `python -m pytest tests/ -v --tb=short` && `cd frontend && npx vitest run`
5. Actualizeaza CLAUDE.md (Faza 14 R7 -> COMPLETATA) si TODO_ROLAND.md

---

## SESIUNEA 1 — CALITATE AI + QUICK WINS (E1, E5, ER2, E13)

### E1: Few-shot examples in TOATE sectiunile

**Fisier:** `backend/prompts/section_prompts.py`

**Problema:** Sectiunile `competition` (linia 63), `opportunities` (linia 75), `swot` (linia 87), `company_profile` (linia 22) NU au exemple concrete (EXEMPLU FRAGMENT). Celelalte 4 sectiuni (executive_summary, financial_analysis, risk_assessment, recommendations) au deja.

**Actiune:** Adauga `"EXEMPLU FRAGMENT (adapteaza la datele reale):\n"` cu text realist in fiecare din cele 4 sectiuni lipsa. Modele de urmat: vezi executive_summary (linia 14-18) si risk_assessment (linia 55-59) — acelasi format.

**Exemple concrete de adaugat:**

**company_profile** (dupa linia 28, inainte de closing `")`):
```
EXEMPLU FRAGMENT (adapteaza la datele reale):
"SC EXEMPLU S.R.L. (CUI 12345678), infiintata la 15.03.2010, cu sediul in Bucuresti, Sector 3.
CAEN principal: 4120 — Lucrari de constructii a cladirilor rezidentiale si nerezidentiale.
Capital social: 10,000 RON. Administrator: Ion Popescu (din 2010).
Asociati: Ion Popescu (60%), Maria Popescu (40%). Puncte de lucru: 2 (Ilfov, Constanta).
[Sursa: openapi.ro | Trust: OFFICIAL]"
```

**competition** (dupa linia 71, inainte de closing `")`):
```
EXEMPLU FRAGMENT (adapteaza la datele reale):
"| Nr | Competitor | CUI | CAEN | Judet | CA estimata |
|---|---|---|---|---|---|
| 1 | ALFA CONSTRUCT S.R.L. | 87654321 | 4120 | Bucuresti | ~3.5M RON |
| 2 | BETA BUILDINGS S.R.L. | 11223344 | 4120 | Ilfov | ~1.8M RON |
Pozitionare: Firma analizata se situeaza pe locul 2 din 3 competitori identificati ca dimensiune CA.
Punct forte relativ: marja profit superioara (+2.3pp vs media). Punct slab: numar angajati inferior."
```

**opportunities** (dupa linia 83, inainte de closing `")`):
```
EXEMPLU FRAGMENT (adapteaza la datele reale):
"1. LICITATIE SEAP: 'Reabilitare scoala nr. 5 Sector 2' — Valoare estimata: 1.2M RON.
Deadline depunere: 15.04.2025. Autoritate: Primaria Sector 2. Eligibilitate: CAEN 4120, experienta similara.
2. FOND EUROPEAN: PNRR Componenta C5 — renovare energetica cladiri publice.
Buget disponibil: 500M EUR national. Eligibilitate: firme constructii cu min 3 ani experienta."
```

**swot** (dupa linia 95, inainte de closing `")`):
```
EXEMPLU FRAGMENT (adapteaza la datele reale):
"STRENGTHS: Marja profit 7.8% peste media sector 5.2% (Sursa: ANAF Bilant 2024) | Experienta 14 ani in piata
WEAKNESSES: Dependenta client major 45% din CA (Sursa: analiza portofoliu) | Capital social minim 10K RON
OPPORTUNITIES: 3 licitatii SEAP active in CAEN 4120, val. totala 4.5M RON (Sursa: e-licitatie.ro)
THREATS: Concurenta intensa — 12 firme CAEN 4120 in aceeasi zona (Sursa: listafirme.ro)"
```

---

### E5: Prompt financial_analysis cu ratii financiare

**Fisier:** `backend/prompts/section_prompts.py`

**Problema:** Promptul financial_analysis (linia 34-44) nu mentioneaza cele 6 ratii calculate in `scoring.py` (`_calculate_financial_ratios`): Marja Profit Net, ROE, ROA, Datorii/Capital, Rata Capitalizare, CA per Angajat.

**Actiune:** Adauga in prompt (dupa linia 38, inainte de `"Include cursul BNR"`):
```python
"Daca datele contin ratii financiare calculate (financial_ratios), prezinta-le intr-un tabel:\n"
"| Ratio | Valoare | Interpretare |\n"
"Ratiile standard: Marja Profit Net, ROE, ROA, Datorii/Capital, Rata Capitalizare, CA/Angajat.\n"
"Interpreteaza fiecare valoare in contextul sectorului CAEN al firmei.\n"
```

---

### ER2: Fallback text pentru sectiuni fara date

**Fisier:** `backend/agents/agent_synthesis.py`

**Problema:** In metoda `execute()` (linia 48), inainte de bucla de generare per sectiune, nu se verifica daca sectiunea are date suficiente. AI-ul poate halucinara pe date goale.

**Actiune:** In bucla for (dupa linia 57, inainte de apelurile `_generate_with_*`):

1. Adauga functie noua `_has_sufficient_data(self, section_key, verified_data) -> bool`:
   - `financial_analysis`: verifica `financial.cifra_afaceri`, `financial.profit_net` (min 2 campuri non-null)
   - `competition`: verifica `web_presence.competitors` (min 1 competitor)
   - `opportunities`: verifica `market.seap` sau web_presence cu oportunitati (min 1)
   - `company_profile`: verifica `company` dict (min 3 campuri cu value non-null)
   - Celelalte sectiuni (`executive_summary`, `risk_assessment`, `swot`, `recommendations`): always True — pot genera din orice

2. Daca insuficient, seteaza text = fallback profesional:
```python
f"Sectiunea '{title}' nu a putut fi generata din cauza datelor insuficiente "
f"disponibile in sursele publice consultate. Pentru o analiza completa, "
f"sunt necesare date suplimentare care nu au fost identificate in sursele accesate. "
f"Se recomanda obtinerea acestor informatii direct de la companie."
```
3. Continua la urmatoarea sectiune (skip AI generation complet)

---

### E13: Quick re-analyze din ReportView

**Fisier:** `frontend/src/pages/ReportView.tsx`

**Problema:** Pagina ReportView afiseaza raportul dar nu are buton de regenerare. Utilizatorul trebuie sa navigheze inapoi.

**Actiune:**
- Citeste `ReportView.tsx` complet pentru a intelege structura
- Adauga buton "Regenereaza Raport" langa butonul de download existent
- La click: `POST /api/analysis` cu acelasi CUI + tip + nivel din raportul curent
- Dupa start: redirect la `/analysis/{new_job_id}` (pagina AnalysisProgress)
- Datele necesare (CUI, tip, nivel) sunt in `report.full_data` sau report metadata
- Foloseste `api.startAnalysis()` din `frontend/src/lib/api.ts`
- Import `useNavigate` din react-router-dom pentru redirect

---

## SESIUNEA 2 — SURSE NOI + SCORING (EP1, EP2, EP3, E12, E11)

### EP1: BPI Insolventa (buletinul.ro)

**Fisier NOU:** `backend/agents/tools/bpi_client.py`
**Fisier modificat:** `backend/agents/agent_official.py`

**Ce:** Verifica daca o firma apare in Buletinul Procedurilor de Insolventa.

**Actiune bpi_client.py:**
- Creeaza functie `async check_insolvency(cui: str) -> dict`
- Sursa: https://www.buletinul.ro/ — cauta dupa CUI
- Foloseste `httpx` (`get_client` din `backend.http_client`) — NU instala dependinte noi
- Cauta pe pagina: "insolventa", "faliment", "dizolvare", "lichidare", "reorganizare"
- Return: `{"found": bool, "status": str|None, "details": str|None, "source": "buletinul.ro", "checked_at": iso_timestamp}`
- Try/except cu return `{"found": False, "error": str(e)}` la orice eroare
- **IMPORTANT:** Daca buletinul.ro nu permite scraping direct (403/captcha), implementeaza fallback: cauta via Tavily: `"insolventa {cui} buletinul.ro site:buletinul.ro"`
- Cache rezultatul 24h (via `cache_service`)

**Actiune agent_official.py:**
- Import `bpi_client`
- Adauga apel in parallel fetch (`asyncio.gather`) dupa linia 92 — alaturi de ANAF/openapi/BNR
- Proceseaza rezultatul: `official_data["bpi_insolventa"] = bpi_source["data"]`
- Log source result cu `log_source_result()`

---

### EP2: ANAF Contribuabili Inactivi

**Fisier NOU (optional):** `backend/agents/tools/anaf_inactivi_client.py`
**Fisier modificat:** `backend/agents/agent_official.py`

**Ce:** Verifica daca un CUI e pe lista contribuabililor inactivi ANAF.

**Actiune:**
- **CITESTE INTAI** `backend/agents/tools/anaf_client.py` complet
- Raspunsul ANAF v9 contine DEJA campuri precum `statusInactivi`, `statusSplitTVA`, etc.
- Daca `statusInactivi` vine deja in raspunsul ANAF: extrage-l si pune-l in `official_data["anaf_inactiv"]`
- Daca NU vine: implementeaza check via Tavily ca fallback
- NU downloada ZIP-ul intreg de pe ANAF (prea mare, inutil)
- Return: `{"inactiv": bool, "data_inactivare": str|None, "source": "ANAF", "checked_at": iso_timestamp}`

---

### EP3: ANAF Risc Fiscal

**Fisier NOU (optional):** `backend/agents/tools/anaf_risc_client.py`
**Fisier modificat:** `backend/agents/agent_official.py`

**Ce:** Verifica daca firma are risc fiscal ridicat.

**Actiune:**
- Similar cu EP2 — citeste raspunsul ANAF v9 din `anaf_client.py`
- Verifica daca contine campuri de risc fiscal
- Daca da: extrage si pune in `official_data["risc_fiscal"]`
- Daca nu: Tavily search `"risc fiscal {cui} anaf.ro"`
- Return: `{"risc_fiscal": bool, "tip_risc": str|None, "source": "ANAF", "checked_at": iso_timestamp}`

**NOTA EP2+EP3:** Citeste INTAI `backend/agents/tools/anaf_client.py` complet. Raspunsul ANAF v9 contine DEJA campuri precum `statusInactivi`, `statusSplitTVA`, `statusRO_e_Factura`. Posibil sa gasesti si risc fiscal acolo. Daca da, e mult mai simplu — doar extragi campul existent fara client nou.

---

### E12: Scoring integrare surse noi

**Fisier:** `backend/agents/verification/scoring.py`

**Problema:** Scoring-ul nu penalizeaza firme insolvente/inactive/cu risc fiscal.

**Actiune:** In `calculate_risk_score()` (linia 67):

In sectiunea **JURIDIC** (cauta `# --- JURIDIC`):
```python
# R7 E12: Penalizare insolventa
bpi = verified.get("bpi_insolventa", {})
if isinstance(bpi, dict) and bpi.get("found"):
    juridic_score -= 40
    risk_factors.append(("Firma in procedura insolventa (BPI)", "CRITICAL"))
```

In sectiunea **FISCAL** (cauta `# --- FISCAL`):
```python
# R7 E12: Penalizare inactivitate + risc fiscal
if verified.get("anaf_inactiv"):
    fiscal_score -= 30
    risk_factors.append(("Contribuabil inactiv ANAF", "CRITICAL"))
risc_fisc = verified.get("risc_fiscal", {})
if isinstance(risc_fisc, dict) and risc_fisc.get("risc_fiscal"):
    fiscal_score -= 15
    risk_factors.append(("Risc fiscal ridicat ANAF", "HIGH"))
```

Clamp toate scorurile la `max(0, min(100, score))`.

---

### E11: Early Warning insolventa asociati

**Fisier:** `backend/agents/agent_verification.py`

**Problema:** Daca un asociat al firmei apare la o firma insolventa, trebuie flaggat.

**Actiune:**
- In sectiunea early warnings (cauta `early_warning` in fisier)
- Dupa ce ai BPI data, daca firma curenta e insolventa:
  - Adauga early_warning: `{"signal": "Firma in procedura de insolventa", "severity": "CRITICAL", "confidence": 95}`
- Daca exista lista asociati din openapi.ro si BPI data:
  - Flag optional: `{"signal": "Asociat {nume} implicat in firma cu procedura insolventa", "severity": "HIGH", "confidence": 70}`
- **SIMPLIFICARE ACCEPTABILA:** Daca e prea complex sa verifici cross-reference pe toate firmele asociatilor, implementeaza doar flag-ul pe firma curenta (din EP1) si lasa cross-reference pentru viitor

---

## SESIUNEA 3 — RAPOARTE + ANTI-HALUCINATION (E6, E2, E3, E4, ER1, E9)

### E6: PDF tabel ratii financiare

**Fisier:** `backend/reports/pdf_generator.py`

**Problema:** HTML-ul are deja tabel ratii (N2 din R6), dar PDF-ul nu.

**Actiune:** Dupa bucla de sectiuni (~linia 175, INAINTE de `# B15: Due Diligence`):
- Extrage ratii din `verified_data.get("financial_ratios", [])`
- Daca exista ratii (lista non-vida):
  ```python
  pdf.add_page()
  pdf.start_section("Ratii Financiare", level=0)
  # Header
  pdf.set_font("Helvetica", "B", 16)
  pdf.set_text_color(99, 102, 241)
  pdf.cell(0, 12, "Ratii Financiare", new_x="LMARGIN", new_y="NEXT")
  pdf.set_draw_color(99, 102, 241)
  pdf.line(10, pdf.get_y(), 80, pdf.get_y())
  pdf.ln(6)
  # Table header
  pdf.set_font("Helvetica", "B", 10)
  pdf.cell(60, 7, "Indicator", border=1)
  pdf.cell(35, 7, "Valoare", border=1, align="C")
  pdf.cell(25, 7, "Unitate", border=1, align="C")
  pdf.cell(60, 7, "Interpretare", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
  # Rows
  for ratio in ratios:
      interp = ratio.get("interpretation", "")
      # Color-code: verde/galben/rosu
      ...
  ```
- Color-code interpretarea: verde (Excelent/Bun/Solid/Conservator), galben (Moderat/Fragil), rosu (Slab/Negativ/Ridicat/Periculos/Subcapitalizat)
- Foloseste `_sanitize()` pe toate textele
- Model: vezi cum e facut Due Diligence checklist table (liniile 183-204)

---

### E2: Sparkline trend CA in HTML

**Fisier:** `backend/reports/html_generator.py`

**Problema:** In sectiunea Financial Analysis, nu exista vizualizare inline a trendului CA.

**Actiune:**
- Citeste `html_generator.py` complet
- In sectiunea financial analysis (dupa textul narativ):
- Daca exista `trend_financiar` cu values multi-an (min 2 ani):
  - Adauga CSS-only sparkline (div-uri cu height proportional cu valoarea, inline-flex)
  - SAU Chart.js line chart mic (300x100px) — similar cu charturile existente din HTML
- Foloseste datele din `verified_data["financial"]["trend_financiar"]["value"]["cifra_afaceri_neta"]["values"]`
- Pastreaza stilul dark theme existent (#1a1a2e)

---

### E3: Excel sheet Trend dedicat

**Fisier:** `backend/reports/excel_generator.py`

**Problema:** Sheet-ul "Financiar" existent e prea dens. Datele multi-an merita sheet separat.

**Actiune:**
- Citeste `excel_generator.py` complet
- Dupa sheet-urile existente: `ws_trend = wb.create_sheet("Trend")`
- Coloane: An | CA (RON) | Profit Net (RON) | Nr Angajati
- Populeaza din `verified_data` trend_financiar values
- Adauga `LineChart` openpyxl: `from openpyxl.chart import LineChart, Reference`
- Chart 1: CA + Profit pe aceeasi axa (2 serii)
- Chart 2: Angajati (axa separata, optional)
- **Daca nu exista date multi-an: skip sheet-ul (nu crea sheet gol)**

---

### E4: Template analiza per tip client

**Fisier:** `frontend/src/pages/NewAnalysis.tsx`

**Problema:** Utilizatorul trebuie sa selecteze manual tip + nivel de fiecare data. Preseturile economisesc timp.

**Actiune:**
- Citeste `NewAnalysis.tsx` complet
- Defineste `ANALYSIS_TEMPLATES`:
  ```typescript
  const ANALYSIS_TEMPLATES = [
    {name: "Due Diligence Partener", type: "PARTNER_RISK_ASSESSMENT", level: 3, description: "Verificare completa partener de afaceri"},
    {name: "Screening Rapid", type: "CUSTOM_REPORT", level: 1, description: "Verificare rapida, date de baza"},
    {name: "Raport Complet Vanzare", type: "FULL_COMPANY_PROFILE", level: 3, description: "Raport complet pentru prezentare client"},
    {name: "Analiza Competitie", type: "COMPETITION_ANALYSIS", level: 2, description: "Focus pe competitori si pozitionare"},
    {name: "Oportunitati Licitatii", type: "TENDER_OPPORTUNITIES", level: 2, description: "Licitatii SEAP relevante"},
  ];
  ```
- UI: Dropdown/select "Template rapid:" deasupra selectiei de tip analiza (pasul 2 din wizard)
- La selectare template: auto-seteaza `analysis_type` + `report_level`
- Optional: buton "Personalizat" care reseteaza la selectia manuala
- Stilul: consistent cu dark theme existent

---

### ER1: Validare output AI anti-halucination

**Fisier:** `backend/agents/agent_synthesis.py`

**Problema:** AI-ul poate genera cifre inexistente in date. Trebuie verificat post-generare.

**Actiune:** Dupa linia 110 (`_validate_output` existent), adauga sau extinde:

1. Functie noua `_verify_numbers_in_text(self, text, verified_data, section_key) -> tuple[bool, list[str]]`:
   - Extrage numere din text cu regex: `r'(\d[\d.,]*)\s*(RON|EUR|lei|mii|mil|M|K|%)'`
   - Pentru fiecare numar gasit, cauta in verified_data daca exista ceva similar (+-10%)
   - Daca gasesti numar in text care NU exista in date si NU e an calendaristic (2020-2030): flag
   - Return: `(is_ok, [lista discrepante])`

2. Dupa _validate_output, apeleaza _verify_numbers_in_text
3. Daca `is_ok == False` si `len(discrepante) > 2`:
   - Log warning
   - Re-genereaza sectiunea O SINGURA DATA cu prompt suplimentar:
     `"ATENTIE: Textul anterior continea cifre care nu corespund datelor. Foloseste EXCLUSIV cifrele din JSON-ul furnizat. NU inventa valori."`
   - Daca a doua generare tot are probleme: pastreaza textul dar adauga nota `"\n\n[Nota: Verificati cifrele din aceasta sectiune cu sursele primare.]"`
4. **IMPORTANT:** Nu fi prea agresiv — unele numere (procente calculate, medii, diferente) sunt derivate valide. Ignora numere sub 100 si ani calendaristici.

---

### E9: Raport comparativ 2 firme PDF

**Fisier NOU:** `backend/reports/compare_generator.py`
**Fisier modificat:** `backend/routers/compare.py`
**Fisier modificat:** `frontend/src/pages/CompareCompanies.tsx`

**Ce:** Genereaza PDF comparativ cu 2 firme side-by-side.

**Actiune compare.py:**
- Citeste `compare.py` complet — exista deja `POST /api/compare` care returneaza JSON comparativ
- Adauga endpoint: `POST /api/compare/report` care:
  1. Primeste `{cui_1: str, cui_2: str}`
  2. Preia datele celor 2 firme din DB (reports table — cele mai recente rapoarte)
  3. Genereaza PDF comparativ cu `compare_generator.py`
  4. Returneaza fisierul PDF (`FileResponse`)

**Actiune compare_generator.py:**
- Foloseste `fpdf2` (ca `pdf_generator.py`)
- Import `_sanitize` din `pdf_generator`
- Structura PDF:
  - Pagina 1: titlu "Raport Comparativ" + numele celor 2 firme + data generare
  - Pagina 2: Tabel comparativ (CA, Profit, Angajati, Scor risc, Sector, Vechime)
  - Pagina 3: Vizualizare comparativa (bare colorate proportionale — fpdf2 rect() cu fill)
  - Pagina 4: Concluzii (text scurt: care firma e mai buna pe fiecare dimensiune)
  - Footer + watermark CONFIDENTIAL (refoloseste din pdf_generator)

**Actiune frontend:**
- In `CompareCompanies.tsx`, adauga buton "Descarca Raport Comparativ PDF"
- La click: `POST /api/compare/report` cu `{cui_1, cui_2}` -> download blob ca PDF

---

## DUPA TOATE IMPLEMENTARILE

1. Ruleaza testele:
   ```bash
   cd C:\Proiecte\Sistem_Inteligent_Analize
   python -m pytest tests/ -v --tb=short
   cd frontend && npx vitest run --reporter=verbose
   ```

2. Marcheaza TOATE items `[x]` in `ROLAND_PLANIFICARI_MODULE.md` sectiunea R7

3. Actualizeaza `CLAUDE.md`:
   - Linia cu Faza 14: `**Faza 14 (R7):** COMPLETATA — 15 items: E1-E13 + EP1-EP3 + ER1-ER2 — calitate rapoarte, surse noi (BPI/ANAF inactivi/risc fiscal), anti-halucination, template-uri, raport comparativ`

4. Actualizeaza `TODO_ROLAND.md`: schimba `PLANIFICAT` in `COMPLET`

5. Test manual:
   ```
   Porneste RIS (START_RIS.vbs)
   Analizeaza CUI 26313362 (MOSSLEIN S.R.L.)
   Tip: FULL_COMPANY_PROFILE | Nivel: 3 (COMPLET)

   Verifica:
   [ ] HTML: toate sectiunile au text profesional cu exemple (E1)
   [ ] HTML: ratii financiare mentionate in analiza (E5)
   [ ] HTML: sparkline trend CA (E2)
   [ ] PDF: tabel ratii financiare (E6)
   [ ] PDF: nu exista cifre inventate (ER1)
   [ ] Excel: sheet "Trend" cu grafic (E3)
   [ ] Scoring: penalizari insolventa/inactivitate (E12)
   [ ] Frontend: buton re-analyze pe ReportView (E13)
   [ ] Frontend: template-uri pe NewAnalysis (E4)
   [ ] Compare: buton raport comparativ PDF (E9)
   ```

---

## DEPENDENTE CROSS-MODULE (RESPECTA ORDINEA!)

```
EP1 + EP2 + EP3 --> E12 (scoring trebuie actualizat DUPA sursele noi)
EP1 --> E11 (early warning associati depinde de BPI)
E5 --> E6 (PDF ratii depinde de prompt care le mentioneaza)
E1 --> ER1 (anti-halucination e mai eficient cu few-shot bune)
```
