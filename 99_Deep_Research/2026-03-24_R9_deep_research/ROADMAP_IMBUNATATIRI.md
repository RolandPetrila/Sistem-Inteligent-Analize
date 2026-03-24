# R9 Roadmap Imbunatatiri — Roland Intelligence System (RIS)
Data: 2026-03-24 | Sursa: Deep Research R9 (6 agenti paraleli) | Total: 41 items

---

## Prioritizare: BLOC-uri de implementare

Recomandam implementare in 5 BLOC-uri, fiecare bloc testabil independent.

---

## BLOC 1 — BPI Robustness + Teste BPI (URGENT)
**Efort total: 4-6h | Impact: CRIT | Blocheaza: scoring incorect pe firme cu keywords in nume**

| ID | Fisier:Linie | Descriere | Sev | Efort |
|----|-------------|----------|-----|-------|
| BPI-01 | bpi_client.py:72-73 | Fix false positives: keyword proximity scoring trebuie sa verifice ca keyword-ul e in CONTEXT PROCEDURA (nu in numele firmei). Adauga word boundary matching + exclude company name din context window | CRIT | 2h |
| BPI-02 | bpi_client.py:117 | Tavily fallback: normalizeaza CUI (strip "RO" prefix, lowercase) inainte de match in content | HIGH | 30min |
| BPI-03 | bpi_client.py:105 | Normalizeaza CUI in Tavily query (strip RO prefix) | MED | 15min |
| BPI-04 | bpi_client.py:90 | Inlocuieste `except: return None` cu `except Exception as e: logger.debug(f"BPI error: {e}"); return None` | MED | 10min |
| BPI-05 | bpi_client.py | Adauga retry cu backoff pe HTTP 429 (similar cu pattern din anaf_client.py) | MED | 30min |
| TEST-01 | tests/test_bpi_client.py (NOU) | Creeaza 8+ teste: false positive firma name, case sensitivity, Tavily fallback, timeout, cache hit/miss, empty response, malformed HTML, keyword boundary | CRIT | 2h |

**Criteriu reusita:** `pytest tests/test_bpi_client.py -v` — minim 8 teste, 0 failures. Firma "LICHIDARE DESEURI SRL" NU trebuie detectata ca insolventa.

---

## BLOC 2 — Anti-Hallucination Hardening (URGENT)
**Efort total: 3-5h | Impact: HIGH | Blocheaza: rapoarte cu ratii inventate**

| ID | Fisier:Linie | Descriere | Sev | Efort |
|----|-------------|----------|-----|-------|
| AH-01 | agent_synthesis.py:505-508 | Scoate "financial_analysis" din skip_sections — ratiile generate trebuie validate (suspicious percentages, invented numbers) | HIGH | 30min |
| AH-02 | agent_synthesis.py:556-597 | _has_sufficient_data(): executive_summary si recommendations NU mai returneaza True automat daca completeness < 30%. Adauga check: `if completeness_score < 30: return False` | HIGH | 1h |
| AH-03 | section_prompts.py:38-57 | Adauga in prompt financial_analysis: "NU CALCULA ROE daca nu ai capitaluri proprii. NU CALCULA marja profit daca nu ai profit net. PENTRU FIECARE RATIO: scrie EXPLICIT daca datele sunt incomplete." | HIGH | 30min |
| AH-04 | agent_synthesis.py:268-310 | _validate_output(): adauga detectie competitor names inventate — daca sectiunea competition mentioneaza firme care NU apar in verified_data, strip-uieste sau marcheaza [NEVERIFICAT] | MED | 1h |
| AH-05 | tests/test_anti_hallucination.py (NOU) | Creeaza teste: _has_sufficient_data() cu 0 fields, _validate_output() cu percentages >999%, invented CUI, financial ratios cu date incomplete | MED | 1.5h |

**Criteriu reusita:** Analiza pe firma cu date incomplete (doar CA, fara profit/capital) — raportul NU contine ROE/ROA inventate. Test `pytest tests/test_anti_hallucination.py -v` — minim 6 teste.

---

## BLOC 3 — HTML/PDF Rendering Edge Cases (IMPORTANT)
**Efort total: 4-6h | Impact: HIGH | Blocheaza: tabele corupte in rapoarte**

| ID | Fisier:Linie | Descriere | Sev | Efort |
|----|-------------|----------|-----|-------|
| HTML-01 | html_generator.py:64-70 | Fix header detection: verifica daca table_rows e GOL cand se gaseste separator. Daca exista deja rows, separator e misplaced — ignora header flag | CRIT | 1h |
| HTML-02 | html_generator.py:100-119 | Audit flow XSS: confirma ca _escape() e aplicat INAINTE de regex bold/inline. Adauga test explicit cu input `<script>alert(1)</script>` | CRIT | 1h |
| HTML-03 | html_generator.py:67 | Column count normalization: calculeaza max_cols, pad randuri scurte cu celule goale | HIGH | 30min |
| HTML-05 | html_generator.py:47 | Hardened separator regex: `r'^\|(?:\s*:?\s*-+\s*:?\s*\|)+$'` (require cel putin un `-` per coloana) | HIGH | 30min |
| PDF-01 | pdf_generator.py:54,63 | Inlocuieste hardcoded truncation cu `multi_cell()` sau adauga `logger.warning()` la truncare | HIGH | 1h |
| PDF-02 | pdf_generator.py:50-65 | Inlocuieste `cell()` cu `multi_cell()` pt auto-height pe text lung | MED | 1h |
| TEST-03 | tests/test_html_generator.py | Adauga teste: separator la final, column mismatch, XSS input, empty table, nested bold | MED | 1h |

**Criteriu reusita:** Tabel cu separator la final randat corect. Input XSS escaped. `pytest tests/test_html_generator.py -v` — 20+ teste.

---

## BLOC 4 — Compare PDF + Synthesis Quality (IMPORTANT)
**Efort total: 5-7h | Impact: HIGH | Blocheaza: rapoarte comparative incomplete**

| ID | Fisier:Linie | Descriere | Sev | Efort |
|----|-------------|----------|-----|-------|
| CMP-01 | compare_generator.py:81-92 | Adauga pagina 5: "Analiza Ratii Financiare" — foloseste company["ratios"] din API (marja profit, ROE, solvency, current ratio). Tabel side-by-side + interpretare | HIGH | 2h |
| CMP-02 | compare_generator.py:154-155 | Inlocuieste `va or 0` cu check explicit: daca va is None, afiseaza "[Date insuficiente]" in loc de 0 | MED | 30min |
| CMP-03 | compare_generator.py:221-235 | Extinde narrative summary de la 1-2 la 4-6 propozitii: dimensiuni avantaj, riscuri relative, recomandare actionabila | MED | 1.5h |
| CMP-04 | compare.py:271-272 | Adauga UUID la filename PDF comparativ: `f"comparativ_{uuid4().hex[:8]}.pdf"` — previne overwrite | MED | 15min |
| CMP-05 | compare_generator.py | Adauga trust labels si confidence scores in pagina comparativa (surse verificate, data freshness) | MED | 1h |
| SYNTH-02 | agent_synthesis.py:121-122 | Cand toti 5 provideri esueaza: log CARE provideri + error message fiecare. Injecteaza in degraded fallback: "Provideri AI indisponibili: [lista]" | HIGH | 1h |
| SYNTH-04 | agent_synthesis.py:384-495 | Extinde error handling Groq/Mistral/Gemini: catch separat httpx.TimeoutError, httpx.HTTPStatusError (401, 429) | MED | 1h |

**Criteriu reusita:** Compare PDF pe 2 firme — pagina ratii financiare prezenta. Firma fara date arata "[Date insuficiente]".

---

## BLOC 5 — Cleanup + Scoring Tests + Minor (NICE TO HAVE)
**Efort total: 3-4h | Impact: MED-LOW | Calitate cod + test coverage**

| ID | Fisier:Linie | Descriere | Sev | Efort |
|----|-------------|----------|-----|-------|
| SPLIT-02 | agent_verification.py:626-794 | Sterge dead code _calculate_risk_score_ORIGINAL_REMOVED (~169 linii) | LOW | 5min |
| SPLIT-01 | verification/__init__.py:2-5 | Adauga build_due_diligence si detect_early_warnings in __all__ | LOW | 5min |
| PERF-01 | orchestrator.py:85 | Inlocuieste datetime.utcnow() cu datetime.now(datetime.UTC) | LOW | 5min |
| TEST-02 | tests/test_scoring.py | Extinde cu: test fiecare dimensiune individual, ponderi corecte (30/20/15/15/10/10), solvency matrix 3x3, confidence weighting. Target: +15 teste | HIGH | 2h |
| TEST-04 | tests/test_orchestrator.py | Extinde cu: checkpoint save pe eroare, cascading failures (Agent 1+4 down), state consistency dupa retry. Target: +5 teste | MED | 1h |
| SYNTH-03 | agent_synthesis.py:76-100 | Token budget check pe FIECARE provider din fallback chain, nu doar initial | MED | 30min |
| SYNTH-05 | agent_synthesis.py:76-79 | Elimina prompt build dublu: construieste prompt O SINGURA DATA, apoi reutilizeaza | MED | 30min |
| SYNTH-06 | agent_synthesis.py:811 | Ajusteaza token estimate de la len/4 la len/3.5 + log warning daca aproape de threshold | LOW | 15min |
| SYNTH-07 | orchestrator+synthesis | Consolideaza completeness gate: alege 1 locus (fie orchestrator, fie agent) | LOW | 30min |
| HTML-04 | html_generator.py:25 | Documenteaza in cod ca nested bold nu e suportat (standard markdown) | LOW | 5min |
| HTML-06 | html_generator.py:46 | Documenteaza ca table detection necesita minim 3 pipes | LOW | 5min |
| HTML-07 | html_generator.py:504-507 | Adauga `table-layout:fixed` in CSS .ris-table | MED | 15min |
| PDF-03 | pdf_generator.py:19-33 | Adauga strip HTML tags in _sanitize() (`re.sub(r'<[^>]+>', '', text)`) | MED | 15min |
| PDF-04 | pdf_generator.py:66 | Creste spacing dupa tabel de la 2pt la 4pt | LOW | 5min |

**Criteriu reusita:** `pytest tests/ -v` — 140+ teste, 0 failures. Dead code eliminat.

---

## Sumar Roadmap

| BLOC | Items | CRIT | HIGH | MED | LOW | Efort | Prioritate |
|------|-------|------|------|-----|-----|-------|-----------|
| 1 — BPI Robustness | 6 | 2 | 1 | 3 | 0 | 4-6h | URGENT |
| 2 — Anti-Hallucination | 5 | 0 | 3 | 2 | 0 | 3-5h | URGENT |
| 3 — Rendering Edge Cases | 7 | 2 | 2 | 2 | 0 | 4-6h | IMPORTANT |
| 4 — Compare + Synthesis | 7 | 0 | 2 | 5 | 0 | 5-7h | IMPORTANT |
| 5 — Cleanup + Tests | 14 | 0 | 1 | 5 | 8 | 3-4h | NICE TO HAVE |
| **TOTAL** | **41** | **4** | **12** | **18** | **7** | **19-28h** | |

---

## Ordine Executie Recomandata

```
BLOC 1 (BPI) ─────────────┐
                           ├─── Teste inainte de BLOC 2
BLOC 2 (Anti-Hallucination)┘
         |
BLOC 3 (Rendering) ───────── Independent de 1+2
         |
BLOC 4 (Compare + Synthesis) ── Depinde partial de BLOC 2 (anti-hallucination)
         |
BLOC 5 (Cleanup) ──────────── La final, dupa toate fix-urile
```

**Nota:** BLOC-urile 1+2 sunt URGENTE si trebuie implementate inainte de orice analiza live pe firme noi. BLOC 3+4 imbunatatesc calitatea rapoartelor. BLOC 5 e housekeeping.

---

## Estimare Scor Post-R9

Daca se implementeaza BLOC 1-4 (items CRIT + HIGH):

| Aspect | R9 actual | R9 post-fix | Delta |
|--------|-----------|-------------|-------|
| Securitate | 8/10 | 9/10 | +1 (XSS audit, BPI fix) |
| Calitate Cod | 7/10 | 8/10 | +1 (dead code, DRY complet) |
| Arhitectura | 8/10 | 8/10 | = |
| Testare | 6/10 | 8/10 | +2 (BPI, scoring, anti-hallucination) |
| Performanta | 8/10 | 8/10 | = |
| Documentatie | 8/10 | 8/10 | = |
| Dependente | 8/10 | 8/10 | = |
| Deploy Ready | 7/10 | 8/10 | +1 (anti-hallucination, compare PDF) |
| **TOTAL** | **60/80** | **65/80** | **+5** |

**Cu BLOC 5 inclus: ~67-68/80. Target 70+/80 necesita si imbunatatiri la arhitectura (e.g., structured logging, CI/CD).**
