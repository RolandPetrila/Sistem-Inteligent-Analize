# R8 — Cerinta Executie: 21 Imbunatatiri Calitate & Robustete

## Context
Deep Research R8 complet (2026-03-23). Scor sanatate: 55/80. Obiectiv: ridicam la 70+/80.

## Fisiere referinta (CITESTE INAINTE DE EXECUTIE)
- `99_Deep_Research/2026-03-23_R8_deep_research/ROADMAP_IMBUNATATIRI.md` — TOATE cele 21 items cu fisier:linie, descriere, efort, dependinte
- `99_Deep_Research/2026-03-23_R8_deep_research/RAPORT.md` — analiza completa, context per item
- `CLAUDE.md` — conventii proiect, stack, decizii tehnice

## Ce trebuie implementat
TOATE cele 21 items din ROADMAP (F1-F21), in ordinea sesiunilor recomandate:

### Sesiune 1: Quick Wins (~2h)
F1 (WS bug list.discard), F3 (bold strip), F4 (version unify), F5 (numbered lists), F6 (PRAGMA optimize), F7+F8+F12 (dead deps remove), F11 (.env.example), F20 (dead method cleanup)

### Sesiune 2: HTML + Quality (~3h)
F2 (table rendering HTML), F9 (except:pass → logger.debug), F10 (anti-hallucination fix), F15 (teste html_generator)

### Sesiune 3: Refactoring + Robustete (~4h)
F13 (split agent_verification 1248 LOC), F14 (DRY provider calls synthesis), F18 (compare PDF concluzii), F19 (BPI client robust)

### Sesiune 4: Teste + PDF (~4h)
F16 (teste orchestrator), F17 (teste pdf_generator), F21 (fpdf2 + mistletoe PDF tables)

## Reguli executie
1. Respecta dependintele din ROADMAP (ex: F15 teste DUPA F2+F3+F5)
2. Ruleaza `python -m pytest tests/ -v` dupa fiecare sesiune
3. Ruleaza `cd frontend && npx vitest run` dupa modificari frontend
4. La F13 (split verification): pastreaza importurile existente compatibile
5. La F2 (tabele): testeaza cu output real din `Testari_Analize_Sistem/Mosslein_4.html`
6. La F21 (PDF tables): foloseste fpdf2 (NU WeasyPrint) — decizie confirmata in CLAUDE.md
7. Actualizeaza CLAUDE.md la final cu status "Faza 15 (R8): COMPLETATA"

## Test final manual
Dupa TOATE sesiunile, ruleaza analiza FULL_COMPANY_PROFILE nivel 3 cu CUI 4239234 (Mosslein):
- Verifica HTML: tabele randate corect, bold fara asteriscuri, numbered lists ca `<ol>`
- Verifica PDF: tabele, caractere romanesti, bookmarks
- Verifica ca WebSocket nu crapa la disconnect
