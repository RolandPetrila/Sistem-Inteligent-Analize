# R8 — Roadmap Imbunatatiri RIS
Data: 2026-03-23 | Total: 21 items (3 CRIT + 9 HIGH + 8 MED + 1 LOW)

## Rezumat

| Categorie | Count | Efort estimat |
|-----------|-------|---------------|
| CRITICAL (bug fix) | 3 | ~2.5h |
| HIGH (imbunatatiri importante) | 9 | ~4h |
| MEDIUM (refactoring + teste) | 8 | ~17h |
| LOW (nice to have) | 1 | ~4h |
| **TOTAL** | **21** | **~27.5h** |

## Item List

### CRITICAL

| # | Item | Fisier | Descriere | Efort |
|---|------|--------|-----------|-------|
| F1 | BUG: list.discard() | main.py:51 | WebSocket dead connections not cleaned — list has no discard() | 5 min |
| F2 | HTML table rendering | html_generator.py:21-50 | Markdown tables `\| col \|` rendered as `<p>` not `<table>` | 2h |
| F3 | Inline bold stripping | html_generator.py:40 | `**bold**` in list items shown as raw asterisks | 30 min |

### HIGH

| # | Item | Fisier | Descriere | Efort |
|---|------|--------|-----------|-------|
| F4 | Version mismatch | main.py:278+292 | health=3.0.0, deep=1.1.0 → unify | 5 min |
| F5 | Numbered lists | html_generator.py | `1. Item` not converted to `<ol>` | 30 min |
| F6 | PRAGMA optimize | database.py | Add temp_store=MEMORY + optimize at close | 15 min |
| F7 | Dead dep: playwright | requirements.txt:17 | 0 imports found — remove | 5 min |
| F8 | Dead dep: matplotlib | requirements.txt:26 | Verify usage, remove if unused | 15 min |
| F9 | Silent except:pass | 9 locatii | Add logger.debug instead of pass | 1h |
| F10 | Anti-hallucination | agent_synthesis.py:555 | Skip financial ratios in number check | 30 min |
| F11 | .env.example | (nou) | Create template from config.py Settings | 15 min |
| F12 | Dead dep: beautifulsoup4 | requirements.txt:18 | Verify usage | 10 min |

### MEDIUM

| # | Item | Fisier | Descriere | Efort |
|---|------|--------|-----------|-------|
| F13 | Split verification | agent_verification.py | 1248 LOC → extract due_diligence, early_warnings | 3h |
| F14 | DRY provider calls | agent_synthesis.py:394-551 | 5 identical methods → 1 generic + config | 2h |
| F15 | Test: html_generator | tests/test_html_generator.py | Tests for _render_content (headers, lists, tables, bold) | 2h |
| F16 | Test: orchestrator | tests/test_orchestrator.py | Mock agent tests for pipeline flow | 3h |
| F17 | Test: pdf_generator | tests/test_pdf_generator.py | Tests for _sanitize latin-1 encoding | 1h |
| F18 | Compare PDF concluzii | compare_generator.py:194 | Add percentage diff + narrative | 2h |
| F19 | BPI client robust | bpi_client.py:43 | Check keyword near CUI, not full page | 2h |
| F20 | Dead method cleanup | agent_synthesis.py:785 | _extract_raw_for_section duplicat | 15 min |

### LOW

| # | Item | Fisier | Descriere | Efort |
|---|------|--------|-----------|-------|
| F21 | fpdf2 + mistletoe | reports/ | Markdown tables in PDF via HTML conversion | 4h |

## Dependinte

```
F15 (teste html) → F2 (table rendering) → F21 (PDF tables via mistletoe)
F3 (bold strip) + F5 (numbered lists) → F15 (teste dupa features)
F7 + F8 + F12 (dead deps) → independent, do first
F1 (WS bug) → independent, do FIRST
F13 (split verification) → F16 (teste orchestrator)
F14 (DRY synthesis) → independent
```

## Sesiuni Recomandate

### Sesiune 1: Quick Wins (~2h)
F1, F4, F7, F8, F12, F6, F11, F3, F5, F20

### Sesiune 2: HTML + Quality (~3h)
F15, F2, F10, F9

### Sesiune 3: Refactoring + Robustete (~4h)
F14, F19, F18, F13

### Sesiune 4 (optional): Teste + PDF (~4h)
F16, F17, F21

## Protocol Testare

```bash
# Backend
cd C:\Proiecte\Sistem_Inteligent_Analize
python -m pytest tests/ -v

# Frontend
cd frontend
npx vitest run

# Manual: testare cu CUI real
# 1. Start backend + frontend
# 2. Analiza FULL_COMPANY_PROFILE nivel 3 cu CUI 4239234 (Mosslein)
# 3. Verifica HTML: tabele, bold, numbered lists
# 4. Verifica PDF: tabele, caractere romanesti
# 5. Verifica Excel: Trend sheet, grafice
```
