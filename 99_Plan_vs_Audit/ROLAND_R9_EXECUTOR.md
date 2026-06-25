# R9 — Cerinta Deep Research: Evaluare Post-R8

## Context
R8 implementat si comis (2026-03-24). 121 teste (110 pytest + 11 vitest), 0 failures.
Feedback loop activ (logs/ris_summary.log, ris_runtime.log, ris_frontend.log, ISSUES.md).
Scor R8 pre-implementare: 55/80. Target R9: 70+/80.

## Ce trebuie sa faci

### Pas 1: Ruleaza /deep-research
```
/deep-research
```

Cand iti cere detalii, raspunde:
- **Proiect**: Sistem inteligent de analize business (RIS)
- **Focus**: Calitate rapoarte generate, stabilitate runtime, completitudine date
- **Ce s-a schimbat recent**: R8 = 21 items (HTML tables/bold/lists, split verification, DRY providers, anti-hallucination, 29 teste noi, dead deps cleanup)
- **Ce ne intereseaza**: Bug-uri noi introduse de R8, regresii, probleme ramase

### Pas 2: Salveaza rezultatele
Salveaza raportul si roadmap-ul in:
```
99_Deep_Research/2026-03-24_R9_deep_research/RAPORT.md
99_Deep_Research/2026-03-24_R9_deep_research/ROADMAP_IMBUNATATIRI.md
```

### Pas 3: Dupa generare, ruleaza testele
```bash
cd C:\Proiecte\Sistem_Inteligent_Analize
python -m pytest tests/ -v
cd frontend && npx vitest run
```
NU implementa nimic. Doar genereaza raportul si roadmap-ul.

### Pas 4: Verifica focus areas
Deep research-ul trebuie sa verifice MINIM:
1. **Regresii R8**: Split verification (due_diligence.py, early_warnings.py) — importuri OK?
2. **HTML rendering**: Tabele, bold, numbered lists — `_render_content()` complet?
3. **PDF rendering**: fpdf2 markdown tables — functioneaza cu date reale?
4. **DRY synthesis**: Refactorizarea provider calls — fallback chain intacta?
5. **Anti-hallucination**: Skip financial ratios — nu se sare prea mult?
6. **Compare PDF**: Concluzii narative — calitate text?
7. **BPI client**: Keyword proximity — detecteaza corect insolventa?
8. **Teste noi (29)**: Acopera cazurile critice sau sunt superficiale?
9. **Dead deps removal**: playwright, matplotlib, beautifulsoup4 — nimic nu se strica?
10. **Performance**: Import time, startup time — afectat de modificari?

### Reguli
- NU implementa fix-uri. Doar raport + roadmap.
- NU modifica CLAUDE.md sau alte fisiere de documentatie.
- Roadmap-ul sa aiba format: ID, Fisier:Linie, Descriere, Severitate, Efort estimat.
- Compara cu R8 (scor 55/80) — da scor nou.

## Comanda de trimis in terminalul executor
```
Citeste ROLAND_R9_EXECUTOR.md si executa. Genereaza deep-research R9 fara sa implementezi nimic. Salveaza in 99_Deep_Research/2026-03-24_R9_deep_research/.
```
