Vreau o evaluare sincera si detaliata a acestui proiect. Context critic inainte de analiza:

## CINE SUNT SI CUM FOLOSESC SISTEMUL
- Sunt singurul utilizator al acestui sistem. Nu il impart cu nimeni.
- Vand clientilor documentatia cu datele valoroase extrase (rapoartele generate).
- Calitatea rapoartelor = direct proportionala cu veniturile mele.
- NU am nevoie de: user management, branding, multi-tenancy, API publica, i18n.

## CE S-A IMPLEMENTAT DEJA (sa nu propui lucruri existente)
Proiectul are 13 faze complete, 73 bug fixes (R4+R5+R6), 37 REST endpoints,
12 pagini frontend, 7 formate raport, 88 teste (77 pytest + 11 vitest).

R6 (ultima runda, azi 2026-03-23) a implementat 25 items in 5 BLOCs:
- BLOC 1: D16 monitoring CRIT, D7/D8/D9 token budgets AI, D17 Tavily cache, D18 lock eviction, D20 WebSocket cleanup
- BLOC 2: N1 Financial Ratios auto-calc (6 ratii din ANAF Bilant), N2 Ratii in HTML report, N3 Executive Summary 3-line KPI
- BLOC 3: D1 SEAP EUR BNR, D2/D3 JSON parse safety, D6 confidence flag, D11 Early Warnings HTML, D12 Excel scoring, D13 PPTX null guard
- BLOC 4: N4 CompanyDetail page (/company/:id) cu profil+rapoarte+scor history+re-analiza 1-click
- BLOC 5: D4 BNR namespace fallback, D5 INS TEMPO float, D10 Level 1 competition/opportunities, D14 Due Diligence Excel, D15 Batch CSV CAEN desc, D19 secret key auto-gen, D21 auto-retry 429/503

## CE VREAU DE LA TINE

1. Citeste CLAUDE.md, ROLAND_PLANIFICARI_MODULE.md, FUNCTII_SISTEM.md si TODO_ROLAND.md complet.

2. Analizeaza codul real (nu presupune) — citeste fisierele cheie:
   - backend/agents/agent_synthesis.py (sinteza AI — cel mai important pt calitate raport)
   - backend/agents/agent_official.py (colectare date)
   - backend/agents/verification/scoring.py (scoring 0-100)
   - backend/reports/html_generator.py + pdf_generator.py + excel_generator.py
   - backend/prompts/section_prompts.py (prompturi AI per sectiune)
   - frontend/src/pages/CompanyDetail.tsx + ReportView.tsx + Dashboard.tsx

3. Raspunde la aceste intrebari:

   A) POTENTIAL EXPLOATAT — la ce procent estimezi ca e sistemul acum?
      Calculeaza pe axe separate:
      - Calitate rapoarte livrate clientilor (%)
      - Eficienta mea ca utilizator unic (%)
      - Robustete tehnica / reliability (%)
      - Exploatare date disponibile (%)

   B) CE IMBUNATATIRI REALE propui?
      DOAR lucruri care:
      - Fac rapoartele mai valoroase pentru clienti (date noi, analize mai bune, prezentare superioara)
      - Ma fac pe mine mai eficient (mai putin timp per raport, mai putini pasi manuali)
      - Reduc riscul de erori care ajung la client

      NU propune:
      - Functii decorative (dark/light theme, animatii, badges fancy)
      - Refactorizari interne fara impact pe output
      - Features pt multi-user (auth, roles, permissions)
      - Over-engineering (microservicii, Docker, CI/CD — e single machine)

   C) SURSE DE DATE NOI — ce alte surse publice romanesti ar putea fi integrate?
      Gandeste-te la: BPI (insolventa), Lista Neagra ANAF, Registrul Beneficiarilor Reali,
      date europene, alte registre. Fiecare sursa: ce date ofera, API disponibil?,
      efort integrare, impact pe calitate raport.

   D) CALITATE SINTEZA AI — cum pot imbunatati prompturile pentru ca textul generat
      sa fie mai profesional, mai specific, mai util clientului? Citeste section_prompts.py
      si agent_synthesis.py si propune imbunatatiri concrete pe prompturi.

4. FORMAT RASPUNS:
   Grupeaza propunerile in:
   - IMPACT MARE + EFORT MIC (prioritate 1)
   - IMPACT MARE + EFORT MEDIU (prioritate 2)
   - IMPACT MEDIU + EFORT MIC (prioritate 3)

   Per propunere: titlu, ce fisier se modifica, ce face concret, de ce e valoroasa pt client.

5. La final, genereaza un fisier ROLAND_PLANIFICARI_MODULE.md actualizat cu noua runda (R7)
   in acelasi format ca R4/R5/R6 (tabel cu #, Cod, checkbox, descriere, locatie, efort, severitate).
   SINCRONIZEAZA cu itemii existenti — nu duplica ce e deja implementat.

IMPORTANT: Fii brutal de sincer. Daca ceva e bine, spune ca e bine.
Daca ceva e mediocru dar pare complicat, spune-mi. Prefer 5 imbunatatiri reale
decat 30 de "nice to have" care nu schimba nimic in practica.
