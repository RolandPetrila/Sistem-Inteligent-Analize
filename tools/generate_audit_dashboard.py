"""
Genereaza AUDIT_FUNCTII.html (root) — dashboard live de audit al TUTUROR functiilor
testabile din RIS: endpoint-uri REST, WebSocket, tipuri de analiza, provideri AI,
integrari surse externe, canale de notificare, task-uri scheduler, formate raport,
pagini frontend.

DE CE UN GENERATOR, NU UN HTML SCRIS DE MANA:
Lista de endpoint-uri e extrasa AUTOMAT din `backend.main.app.routes` (introspectie
FastAPI reala, nu o lista tinuta manual care ar putea ramane in urma codului). Orice
endpoint nou aparut in cod apare AUTOMAT la urmatoarea rulare a acestui script, marcat
"needs_curation" daca nu are inca metadate (categorie/status test) in CURATED_ENDPOINTS
de mai jos — asta e mecanismul concret prin care fisierul "ramane sincronizat".

RULARE (dupa orice endpoint nou adaugat in backend/routers/*.py sau backend/main.py):
    python tools/generate_audit_dashboard.py
Cauta in output liniile "needs_curation" si adauga o intrare in CURATED_ENDPOINTS.

SECURITATE: acest script NU citeste, NU scrie si NU include NICIO valoare de cheie
API/token/parola. Testarea providerilor in dashboard-ul generat se face DOAR prin
apeluri live catre endpoint-uri existente (`/api/settings/test/{service}`) care
returneaza doar ok/eroare, niciodata valoarea cheii. Editarea cheilor se face DOAR
prin pagina reala Settings (autentificata, valori mascate) — dashboard-ul doar
trimite acolo, nu duplica acel mecanism.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.main import app  # noqa: E402

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "AUDIT_FUNCTII.html"
OUTPUT_JS = ROOT / "AUDIT_FUNCTII.js"

# ─────────────────────────────────────────────────────────────────────────────
# Metadate curate per endpoint, cheie = "METODA path". Completate manual din
# auditul de sesiune 2026-07-12 (E2E sweep + Lead Generation). Orice endpoint
# NEGASIT aici e marcat automat "needs_curation" in output.
#
# Campuri:
#   cat            — categoria/router-ul (pentru grupare in dashboard)
#   tested         — True/False: a fost verificat live cu un apel real macar o data
#   evidence       — nota scurta despre ce s-a verificat si cand
#   live_safe      — True = poate fi apelat automat din dashboard (idempotent, fara
#                    efecte secundare reale sau cost). False = doar comanda curl de
#                    copiat, cu avertisment (creeaza/modifica/sterge date, trimite
#                    mesaje reale, consuma cota API, sau reporneste serviciul).
# ─────────────────────────────────────────────────────────────────────────────
CURATED_ENDPOINTS = {
    # ── analysis.py ──
    "GET /api/analysis/types": {"cat": "Analysis", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200 (cu X-RIS-Key).", "live_safe": True},
    "GET /api/analysis/types/{analysis_type}": {"cat": "Analysis", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200 pt FULL_COMPANY_PROFILE.", "live_safe": True},
    "POST /api/analysis/parse-query": {"cat": "Analysis", "tested": True, "evidence": "E2E 2026-07-12: 95% confidence, extras corect analysis_type+CUI.", "live_safe": False},
    "POST /api/analysis/quick-score": {"cat": "Analysis", "tested": True, "evidence": "E2E 2026-07-12: batch 2 CUI, date reale ANAF+Bilant. Fix aplicat (import gresit).", "live_safe": False},
    "POST /api/analysis/vies": {"cat": "Analysis", "tested": True, "evidence": "E2E 2026-07-12: validare TVA live, date reale UE.", "live_safe": False},

    # ── ask.py ──
    "POST /api/ask": {"cat": "NLQ", "tested": True, "evidence": "E2E 2026-07-12: raspuns structurat inteligent, date reale.", "live_safe": False},

    # ── batch.py ──
    "POST /api/batch/preview": {"cat": "Batch", "tested": True, "evidence": "E2E 2026-07-12: validare CSV fara side-effects.", "live_safe": True},
    "POST /api/batch": {"cat": "Batch", "tested": True, "evidence": "E2E 2026-07-12: create real (2 CUI), progress, DONE 2/2.", "live_safe": False},
    "GET /api/batch/{batch_id}": {"cat": "Batch", "tested": True, "evidence": "E2E 2026-07-12: poll progress.", "live_safe": True},
    "POST /api/batch/{batch_id}/resume": {"cat": "Batch", "tested": True, "evidence": "Verificat live 2026-07-13: raspuns corect 'No failed CUIs to retry' pt job fara esecuri.", "live_safe": False},
    "GET /api/batch/{batch_id}/download": {"cat": "Batch", "tested": True, "evidence": "E2E 2026-07-12: ZIP 14 fisiere (7 formate x 2 firme + CSV).", "live_safe": True},

    # ── companies.py ──
    "GET /api/companies": {"cat": "Companies", "tested": True, "evidence": "Bug #2 fix verification: ?caen=3600 filtreaza corect.", "live_safe": True},
    "GET /api/companies/favorites": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: OK.", "live_safe": True},
    "GET /api/companies/stats/risk-movers": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: OK.", "live_safe": True},
    "GET /api/companies/search/fts": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: FTS5 search OK.", "live_safe": True},
    "POST /api/companies/import": {"cat": "Companies", "tested": True, "evidence": "BUG GASIT+REPARAT 2026-07-13: INSERT referea coloane fantoma created_at/updated_at (reale: first_analyzed_at/last_analyzed_at) — HTTP 500 garantat, niciodata prins. Verificat live 200 OK dupa fix.", "live_safe": False},
    "GET /api/companies/export/csv": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: export CSV CRM-ready OK.", "live_safe": True},
    "GET /api/companies/{company_id}": {"cat": "Companies", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200, date reale MOSSLEIN S.R.L.", "live_safe": True},
    "PUT /api/companies/{company_id}/favorite": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: toggle favorite OK.", "live_safe": False},
    "POST /api/companies/{company_id}/auto-reanalyze": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: OK.", "live_safe": False},
    "GET /api/companies/{company_id}/timeline": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: OK (gol pt Mosslein — plauzibil, nu bug).", "live_safe": True},
    "GET /api/companies/{company_id}/score-trend": {"cat": "Companies", "tested": True, "evidence": "BUG #3 FIX: int->str UUID. Verificat live 200 OK dupa fix.", "live_safe": True},
    "GET /api/companies/{company_id}/tags": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: OK.", "live_safe": True},
    "POST /api/companies/{company_id}/tags": {"cat": "Companies", "tested": True, "evidence": "Verificat live 2026-07-13: creat+sters tag test, pereche completa OK.", "live_safe": False},
    "DELETE /api/companies/{company_id}/tags/{tag}": {"cat": "Companies", "tested": True, "evidence": "Verificat live 2026-07-13: vezi nota POST tags.", "live_safe": False},
    "GET /api/companies/{company_id}/note": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: OK.", "live_safe": True},
    "PUT /api/companies/{company_id}/note": {"cat": "Companies", "tested": True, "evidence": "Verificat live 2026-07-13: setat+revert la gol, 200 OK.", "live_safe": False},
    "POST /api/companies/{company_id}/chat": {"cat": "Companies", "tested": True, "evidence": "BUG GASIT+REPARAT 2026-07-13: contextul 'Date cheie verificate' citea full_data.get('verified_data') — cheie care NU EXISTA NICIODATA (campurile sunt la nivelul de sus). Chat-ul nu raspundea niciodata corect la intrebari despre scor/CA. Reparat + disambiguare firma-analizata-vs-alte-firme-mentionate. Verificat live: raspuns corect '85.5/100, Verde, CA 14.154.303 RON'.", "live_safe": False},
    "GET /api/companies/{company_id}/network": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: OK (gol pt Mosslein).", "live_safe": True},
    "GET /api/companies/{cui}/predictive": {"cat": "Companies", "tested": True, "evidence": "E2E 2026-07-12: Altman/Piotroski/Beneish/Zmijewski OK.", "live_safe": True},
    "GET /api/companies/{cui}/credit-exposure": {"cat": "Companies", "tested": True, "evidence": "P1-4 (2026-07-14): Bonitate & Expunere comerciala (RON), recalculata din ultimul raport. Verificat live CUI 26313362: 432.000 RON, 3 metode, Verde x1.0. Randat si in HTML/PDF/DOCX + card CompanyDetail.", "live_safe": True},
    "GET /api/companies/{cui}/timeline-report": {"cat": "Companies", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200 (varianta JSON, nu doar /pdf).", "live_safe": True},
    "GET /api/companies/{cui}/timeline-report/pdf": {"cat": "Companies", "tested": True, "evidence": "BUG #4 FIX: crash Unicode em-dash. Verificat live 200 OK dupa fix.", "live_safe": True},

    # ── compare.py ──
    "POST /api/compare": {"cat": "Compare", "tested": True, "evidence": "E2E 2026-07-12: 2 firme side-by-side OK.", "live_safe": False},
    "POST /api/compare/report": {"cat": "Compare", "tested": True, "evidence": "E2E 2026-07-12: PDF comparativ OK.", "live_safe": False},
    "GET /api/compare/templates": {"cat": "Compare", "tested": True, "evidence": "E2E 2026-07-12: CRUD templates OK.", "live_safe": True},
    "POST /api/compare/templates": {"cat": "Compare", "tested": True, "evidence": "E2E 2026-07-12: CRUD templates OK.", "live_safe": False},
    "DELETE /api/compare/templates/{template_id}": {"cat": "Compare", "tested": True, "evidence": "E2E 2026-07-12: CRUD templates OK.", "live_safe": False},
    "POST /api/compare/sector": {"cat": "Compare", "tested": True, "evidence": "BUG #2 FIX verification: caen_section=36 returneaza acum date.", "live_safe": False},
    "GET /api/compare/sector/{caen_code}/dashboard": {"cat": "Compare", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200 pt caen_code=3600.", "live_safe": True},

    # ── documents.py ──
    "POST /api/documents/ocr": {"cat": "OCR", "tested": True, "evidence": "E2E 2026-07-12: upload imagine, text extras corect (Mistral).", "live_safe": False},

    # ── jobs.py ──
    "POST /api/jobs": {"cat": "Jobs", "tested": True, "evidence": "Folosit extensiv in TOATE testele — creeaza job real (cost/cota).", "live_safe": False},
    "GET /api/jobs": {"cat": "Jobs", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200, listare reala.", "live_safe": True},
    "GET /api/jobs/diagnostics/latest": {"cat": "Jobs", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200, job real DONE.", "live_safe": True},
    "GET /api/jobs/{job_id}": {"cat": "Jobs", "tested": True, "evidence": "Poll status folosit extensiv in toate testele.", "live_safe": True},
    "POST /api/jobs/{job_id}/start": {"cat": "Jobs", "tested": True, "evidence": "Folosit extensiv in toate testele.", "live_safe": False},
    "GET /api/jobs/{job_id}/diagnostics": {"cat": "Jobs", "tested": True, "evidence": "E2E 2026-07-12: completeness gate real (88/100, gap-uri cu motiv).", "live_safe": True},
    "POST /api/jobs/{job_id}/retry-source/{source}": {"cat": "Jobs", "tested": True, "evidence": "Verificat live 2026-07-13: source=anaf pe job real, date ANAF reale returnate.", "live_safe": False},
    "POST /api/jobs/{job_id}/cancel": {"cat": "Jobs", "tested": True, "evidence": "Verificat live 2026-07-13: job PENDING (necreat inca) creat+anulat, cost zero.", "live_safe": False},
    "POST /api/jobs/{job_id}/section/{section_key}/regenerate": {"cat": "Jobs", "tested": True, "evidence": "TASK1 2026-06-27: smoke live PASS, regen company_profile+executive_summary.", "live_safe": False},

    # ── monitoring.py — toate 9 confirmate "Toate OK" ──
    "GET /api/monitoring": {"cat": "Monitoring", "tested": True, "evidence": "E2E 2026-07-12: create->list->toggle->audit-log->health->history->check-now->suppress->delete, toate OK.", "live_safe": True},
    "POST /api/monitoring": {"cat": "Monitoring", "tested": True, "evidence": "Vezi nota GET /api/monitoring.", "live_safe": False},
    "PUT /api/monitoring/{alert_id}/toggle": {"cat": "Monitoring", "tested": True, "evidence": "Vezi nota GET /api/monitoring.", "live_safe": False},
    "DELETE /api/monitoring/{alert_id}": {"cat": "Monitoring", "tested": True, "evidence": "Vezi nota GET /api/monitoring.", "live_safe": False},
    "POST /api/monitoring/check-now": {"cat": "Monitoring", "tested": True, "evidence": "Vezi nota GET /api/monitoring (0 alerte declansate — real, nu placeholder).", "live_safe": False},
    "GET /api/monitoring/history": {"cat": "Monitoring", "tested": True, "evidence": "Vezi nota GET /api/monitoring.", "live_safe": True},
    "GET /api/monitoring/{alert_id}/audit-log": {"cat": "Monitoring", "tested": True, "evidence": "Vezi nota GET /api/monitoring.", "live_safe": True},
    "POST /api/monitoring/{alert_id}/suppress": {"cat": "Monitoring", "tested": True, "evidence": "Vezi nota GET /api/monitoring.", "live_safe": False},
    "GET /api/monitoring/health": {"cat": "Monitoring", "tested": True, "evidence": "Vezi nota GET /api/monitoring.", "live_safe": True},

    # ── notifications.py ──
    "GET /api/notifications": {"cat": "Notifications", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200.", "live_safe": True},
    "PUT /api/notifications/{notification_id}/read": {"cat": "Notifications", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200 pe notificare reala existenta.", "live_safe": False},
    "PUT /api/notifications/read-all": {"cat": "Notifications", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200.", "live_safe": False},

    # ── reports.py ──
    "GET /api/reports": {"cat": "Reports", "tested": True, "evidence": "E2E 2026-07-12: listare OK.", "live_safe": True},
    "GET /api/reports/{report_id}": {"cat": "Reports", "tested": True, "evidence": "Folosit implicit la fiecare verificare de raport.", "live_safe": True},
    "GET /api/reports/{report_id}/download/one_pager": {"cat": "Reports", "tested": True, "evidence": "Tier 1: 200 OK, dimensiune reala.", "live_safe": True},
    "GET /api/reports/{report_id}/download/{format}": {"cat": "Reports", "tested": True, "evidence": "Tier 1: 5 formate (PDF/DOCX/HTML/Excel/PPTX) 200 OK.", "live_safe": True},
    "GET /api/reports/{report_id}/data": {"cat": "Reports", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200, date reale raport LEAD_GENERATION.", "live_safe": True},
    "GET /api/reports/{report_id}/delta": {"cat": "Reports", "tested": True, "evidence": "E2E 2026-07-12: corect 'prima analiza' pt tip nou.", "live_safe": True},
    "GET /api/reports/{report_id}/export/ics": {"cat": "Reports", "tested": True, "evidence": "BUG #5 FIX: cheie JSON gresita. Verificat live 200 OK, .ics valid 15 evenimente.", "live_safe": True},
    "POST /api/reports/{report_id}/send-email": {"cat": "Reports", "tested": True, "evidence": "E2E 2026-07-12: esuat CORECT (GMAIL_* neconfigurat) — cod OK, gap config.", "live_safe": False},
    "POST /api/reports/{report_id}/share": {"cat": "Reports", "tested": True, "evidence": "Tier 1: share link public HTTP 200 fara auth, 37KB continut real.", "live_safe": False},
    "GET /api/reports/public/{token}": {"cat": "Reports", "tested": True, "evidence": "Vezi share — acces public fara auth confirmat.", "live_safe": True},

    # ── settings.py ──
    "GET /api/settings": {"cat": "Settings", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200, chei mascate corect.", "live_safe": True},
    "PUT /api/settings": {"cat": "Settings", "tested": True, "evidence": "Verificat live 2026-07-13: fields:{} (no-op sigur) -> {\"updated\":[],\"count\":0}, fara a atinge config reala.", "live_safe": False},
    "POST /api/settings/test-telegram": {"cat": "Settings", "tested": True, "evidence": "E2E 2026-07-12: trimis cu succes (mesaj Telegram real).", "live_safe": False},
    "POST /api/settings/test/{service}": {"cat": "Settings", "tested": True, "evidence": "BUG #6 FIX: mistral+cerebras adaugate. Toate 6 servicii (groq/gemini/mistral/cerebras/tavily/telegram) HTTP 200.", "live_safe": False},

    # ── main.py (direct) ──
    "POST /api/frontend-log": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200 cu payload sintetic.", "live_safe": False},
    "GET /api/frontend-log/recent": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200.", "live_safe": True},
    "GET /api/health": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200.", "live_safe": True},
    "GET /api/version": {"cat": "System", "tested": True, "evidence": "Folosit repetat pt confirmare deploy commit dupa fiecare fix.", "live_safe": True},
    "POST /api/update": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13 prin endpoint-ul real (nu doar WinSW/git direct): tree curat -> {\"ok\":true,\"changed\":false,\"note\":\"deja la zi\"}.", "live_safe": False},
    "POST /api/restart": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13 prin endpoint-ul real: serviciul a revenit corect (versiune/commit confirmat dupa restart).", "live_safe": False},
    "GET /metrics": {"cat": "System", "tested": True, "evidence": "GASIT 2026-07-13: HTTP 200 dar body {\"error\":\"prometheus-client not installed\"} — endpoint neconectat real, pachetul lipseste.", "live_safe": True},
    "GET /api/cache/stats": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200, 30 intrari reale in cache.", "live_safe": True},
    "GET /api/health/deep": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200, status healthy, 4/5 provideri AI OK.", "live_safe": True},
    "GET /health/status": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200 (alias legacy functional).", "live_safe": True},
    "GET /api/stats": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200.", "live_safe": True},
    "GET /api/stats/trend": {"cat": "System", "tested": True, "evidence": "Verificat live 2026-07-13: HTTP 200.", "live_safe": True},

    # ── WebSocket ──
    "WS /ws/jobs/{job_id}": {"cat": "System", "tested": True, "evidence": "Tier 1: script real (lib websockets), 10 evenimente complete confirmate.", "live_safe": False},
}

# ─────────────────────────────────────────────────────────────────────────────
# Functii NON-endpoint (nu au un URL apelabil direct, dar sunt "functii" testabile
# ale sistemului in sensul cerut — tipuri de analiza, provideri AI, integrari
# surse externe, notificari, task-uri scheduler, formate raport, pagini frontend).
# ─────────────────────────────────────────────────────────────────────────────

ANALYSIS_TYPES = [
    ("FULL_COMPANY_PROFILE", True, "Testat extensiv in toate sesiunile — flux central."),
    ("PARTNER_RISK_ASSESSMENT", True, "E2E 2026-07-12: 5 sectiuni, testat sub concurenta."),
    ("TENDER_OPPORTUNITIES", True, "E2E 2026-07-12: 15 licitatii reale, bug #7 gasit+reparat aici."),
    ("COMPETITION_ANALYSIS", True, "E2E Partea 2: completeness 88, dar sectiunea 'competition' e feature lipsa (fallback mereu)."),
    ("FUNDING_OPPORTUNITIES", True, "E2E Partea 2: bug #8 gasit+reparat (funding_programs)."),
    ("MARKET_ENTRY_ANALYSIS", True, "E2E Partea 2: bug #9 gasit+reparat (CUI neextras)."),
    ("LEAD_GENERATION", True, "E2E Partea 2 + Partea 3: bug #9 + feature lipsa construit + bug halucinare CUI reparat determinist."),
    ("MONITORING_SETUP", True, "E2E Partea 2: deferred type, bug #10 gasit aici (KeyError anaf)."),
    ("CUSTOM_REPORT", True, "E2E Partea 2: bug #9 gasit+reparat, dar campul 'description' ramane feature lipsa (ignorat)."),
]

AI_PROVIDERS = [
    ("Claude Code CLI", "SYNTHESIS_MODE=claude_code", False, "NEACTIV in productie — .env are SYNTHESIS_MODE=autonomous (serviciul ruleaza ca SYSTEM, fara auth CLI). Vezi plan E2E."),
    ("Groq (Llama 4 Scout)", "GROQ_API_KEY", True, "Testabil live prin /api/settings/test/groq."),
    ("Gemini 2.5 Flash", "GOOGLE_AI_API_KEY", True, "Testabil live prin /api/settings/test/gemini."),
    ("Mistral Small 3", "MISTRAL_API_KEY", True, "Testabil live prin /api/settings/test/mistral (adaugat in acest sweep, bug #6)."),
    ("Cerebras (gpt-oss-120b)", "CEREBRAS_API_KEY", True, "Testabil live prin /api/settings/test/cerebras. Model migrat 2026-07-12 (fostul model retras din catalog)."),
]

EXTERNAL_SOURCES = [
    # (nume, modul, cost/cheie, status test, nota, ping_key pt butonul "Testeaza live" — None = fara buton)
    ("ANAF TVA/Stare", "anaf_client.py", "Gratuit, fara cheie", "TESTABIL live prin POST /api/settings/test/anaf_tva. Verificat 2026-07-12: OK.", "OK — implementat in acest sprint (connectivity.py).", "anaf_tva"),
    ("ANAF Bilant", "anaf_bilant_client.py", "Gratuit, fara cheie", "TESTABIL live. Verificat 2026-07-12: OK.", "OK — implementat.", "anaf_bilant"),
    ("BNR (curs valutar)", "bnr_client.py", "Gratuit, fara cheie", "TESTABIL live. Verificat 2026-07-12: OK.", "OK — implementat.", "bnr"),
    ("openapi.ro (ONRC)", "openapi_client.py", "OPENAPI_RO_KEY (100/luna free)", "TESTABIL live. Verificat 2026-07-12: OK, afiseaza si api_requests_remaining cand disponibil.", "OK — implementat. Consuma 1 request din cota lunara la fiecare test — foloseste cu grija.", "openapi_ro"),
    ("SEAP/SICAP (licitatii+contracte)", "seap_client.py", "Gratuit, fara cheie", "TESTABIL live. Verificat 2026-07-12: OK (10 contracte gasite pt CUI test).", "OK — implementat.", "seap"),
    ("Tavily Search", "tavily_client.py", "TAVILY_API_KEY (1000/luna free)", "TESTABIL live prin /api/settings/test/tavily.", "OK — deja acoperit.", "tavily"),
    ("BPI Insolventa", "bpi_client.py", "Gratuit + Tavily fallback", "TESTABIL live (cale gratuita, use_tavily_fallback=False — nu consuma cota Tavily). Verificat 2026-07-12: FAIL — buletinul.ro DNS-dead (getaddrinfo failed).", "GASIT: sursa gratuita e picata acum — verifica din nou periodic; fallback Tavily tot functioneaza in fluxul normal de analiza.", "bpi"),
    ("Monitorul Oficial (OSINT)", "osint_client.py / monitorul_oficial_client.py", "Gratuit + Tavily fallback", "TESTABIL live (ping reachability pe monitoruloficial.ro, fara Tavily). Verificat 2026-07-12: OK.", "OK — implementat.", "monitorul_oficial"),
    ("VIES (TVA intracomunitar UE)", "vies_client.py", "Gratuit, fara cheie", "TESTABIL indirect prin POST /api/analysis/vies (are efect real, nu doar test).", "OK partial.", None),
    ("Sanctiuni OFAC+UE+ONU", "sanctions_client.py", "Gratuit, fara cheie (cache local 24h)", "TESTABIL live (screen([]) — raporteaza sursele incarcate + varsta cache). Verificat 2026-07-12: OK (OFAC+EU+UN, 53128 intrari, cache 9.4h).", "OK — implementat.", "sanctions"),
    ("Eurostat (benchmark UE)", "eurostat_client.py", "Gratuit, fara cheie", "TESTABIL live (CAEN test 6201). Verificat 2026-07-12: OK.", "OK — implementat.", "eurostat"),
    ("INS TEMPO (statistici CAEN)", "caen_context.py", "Gratuit, fara cheie", "TESTABIL live. Verificat 2026-07-12: FAIL — timeout la statistici.insse.ro:8077 (cunoscut flaky/offline).", "GASIT: momentan indisponibil — sistemul are deja fallback pe dictionar local CAEN, nu blocheaza analize.", "ins_tempo"),
    ("AEGRM (garantii mobiliare)", "aegrm_client.py", "Gratuit, fara cheie", "TESTABIL live (detecteaza explicit DNS-dead). Verificat 2026-07-12: FAIL — [Errno 11001] getaddrinfo failed.", "CONFIRMAT: tot DNS-dead ca la 2026-06-27, acum cu test automat care il semnaleaza clar.", "aegrm"),
    ("Portal Just (dosare instanta)", "just_client.py", "Gratuit, SOAP (necesita 'zeep')", "TESTABIL live (ping verifica doar ca 'zeep' e instalat — un apel SOAP complet e prea lent/nesigur pt un test rapid). `zeep` instalat 2026-07-12 + reparat dupa retest: WSDL cere `institutie` OBLIGATORIU (246 instante, fara 'toate') si campuri complet diferite de cele presupuse initial (`numar`/`parti.DosarParte[]`, nu `numarDosar`/`calitate` — codul nu rulase NICIODATA cu succes pana acum). Cautam Tribunalul judetului firmei + Curtea de Apel regionala. Verificat live cu date reale (cautare 'Popescu' pe Cluj: 242 dosare gasite, parsate corect).", "REPARAT COMPLET: zeep instalat + parametri SOAP corectati + parsare aliniata la shape-ul real + mapare judet->instanta. 15 teste noi/actualizate.", "just"),
    ("Brave Search", "brave_client.py", "BRAVE_API_KEY (2000/luna free)", "TESTABIL live. Verificat 2026-07-12: OK.", "OK — implementat.", "brave"),
    ("Jina Reader", "jina_client.py", "JINA_API_KEY optional (1M tok/zi cu cheie)", "TESTABIL live (fetch example.com). Verificat 2026-07-12: OK.", "OK — implementat.", "jina"),
    ("Google Maps Places", "maps_client.py", "GOOGLE_CLOUD_API_KEY ($200 credit/luna)", "TESTABIL live. Verificat 2026-07-12: OK (raporteaza explicit REQUEST_DENIED / OVER_QUERY_LIMIT daca apar).", "OK — implementat. Alerta credit: Google nu expune cota ramasa prin acest API, doar starea request-ului.", "google_maps"),
    ("Mistral OCR", "documents.py (agent separat de sinteza Mistral)", "MISTRAL_API_KEY", "TESTABIL indirect prin POST /api/documents/ocr (are efect real).", "OK partial.", None),
]

NOTIFICATION_CHANNELS = [
    # (nume, env var, status test, nota, ping_key)
    ("Telegram", "TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID", "TESTABIL live prin POST /api/settings/test-telegram (trimite mesaj real).", "OK.", None),
    ("Email (Gmail SMTP)", "GMAIL_USER + GMAIL_APP_PASSWORD", "TESTABIL live prin POST /api/settings/test/email (mesaj minimal, fara raport real). Verificat 2026-07-12: raspuns corect 'nu e configurat' (GMAIL_* lipsesc).", "OK — implementat.", "email"),
    ("Webhook (job complete)", "WEBHOOK_URL", "TESTABIL live prin POST /api/settings/test/webhook (payload sintetic, refoloseste validarea SSRF/HTTPS reala din job_service). Verificat 2026-07-12: raspuns corect 'nu e configurat' (WEBHOOK_URL lipseste).", "OK — implementat.", "webhook"),
]

SCHEDULER_TASKS = [
    ("Monitoring check", "_run_monitoring_safe", "6h", "Verificat prin tabela scheduler_state (status OK, timestamp recent)."),
    ("Cache cleanup", "_run_cache_cleanup_safe", "12h", "Verificat prin scheduler_state."),
    ("Sanctions refresh", "_run_sanctions_refresh_safe", "24h", "Verificat prin scheduler_state (pre-warm cache local)."),
    ("Auto-update check", "_run_auto_update_safe", "10 min", "Verificat prin scheduler_state — a rulat real dupa commit-uri (confirmat 2026-07-12)."),
    ("Log cleanup", "_run_log_cleanup_safe", "zilnic", "Verificat prin scheduler_state (sterge log-uri rotite >7 zile)."),
    ("Backup DB", "_run_backup_safe", "zilnic", "Verificat prin scheduler_state + fisiere backups/."),
    ("Auto-reanalyze", "(flag per companie, verificat de scheduler)", "periodic", "Nemonitorizat separat in scheduler_state — verifica manual daca ruleaza."),
]

REPORT_FORMATS = [
    ("PDF", True, "Tier 1: HTTP 200, dimensiune reala."),
    ("DOCX", True, "Tier 1: HTTP 200, dimensiune reala."),
    ("HTML", True, "Tier 1: HTTP 200, verificat continut (inclusiv randare lead_candidates in Partea 3)."),
    ("Excel (XLSX)", True, "Tier 1: HTTP 200, dimensiune reala."),
    ("PPTX", True, "Tier 1: HTTP 200, dimensiune reala."),
    ("1-Pager PDF", True, "Tier 1: HTTP 200, dimensiune reala."),
    ("Share link public (HTML)", True, "Tier 1: HTTP 200 fara auth, 37KB continut real."),
    ("ZIP batch", True, "Tier 2: 14 fisiere (7 formate x 2 firme + CSV sumar)."),
]

FRONTEND_PAGES = [
    # (ruta, componenta, verificat_vizual, nota)
    ("/", "Dashboard", True, "Verificat live 2026-07-13: render OK, date reale (54 rapoarte, integrari OK)."),
    ("/new-analysis", "NewAnalysis", True, "Verificat live 2026-07-13: render OK, wizard + template-uri."),
    ("/analysis/:id", "AnalysisProgress", True, "Verificat live 2026-07-13: render OK (job finalizat, progres 100%)."),
    ("/reports", "ReportsList", True, "Verificat live 2026-07-13: render OK, 54 rapoarte listate."),
    ("/report/:id", "ReportView", True, "Verificat live 2026-07-13: render OK, scor+dimensiuni+download-uri."),
    ("/companies", "Companies", True, "GASIT+REPARAT 2026-07-13: badge scor risc arata mereu 'N/A' (citea camp inexistent `last_score` — corect: `last_risk_score_numeric`, lipsea si din SELECT-ul backend COMPANY_COLS). Reparat, verificat live cu scoruri reale (86/100 etc)."),
    ("/company/:id", "CompanyDetail", True, "GASIT+REPARAT 2026-07-13: cardurile 'Analize'/'Prima Analiza'/descriere CAEN goale — COMPANY_COLS nu includea analysis_count/first_analyzed_at/caen_description/city (existau in DB, niciodata expuse). Reparat, verificat live (28 analize, 20.03.2026)."),
    ("/network/:cui", "NetworkGraph", True, "Verificat live 2026-07-13: render OK, empty-state corect (fara date retea)."),
    ("/compare", "CompareCompanies", True, "Verificat live 2026-07-13: render OK."),
    ("/monitoring", "Monitoring", True, "Verificat live 2026-07-13: render OK, empty-state corect."),
    ("/batch", "BatchAnalysis", True, "Verificat live 2026-07-13: render OK."),
    ("/quick-tools", "QuickTools", True, "Verificat live 2026-07-13: render OK."),
    ("/sector", "SectorDashboard", True, "Verificat live 2026-07-13: render OK."),
    ("/ocr", "OcrPage", True, "Verificat live 2026-07-13: render OK."),
    ("/settings", "Settings", True, "Verificat live 2026-07-13: render OK, chei mascate, teste providers vizibile."),
]

# ─────────────────────────────────────────────────────────────────────────────
# JS externa (fisier separat AUDIT_FUNCTII.js, servit same-origin la /audit.js).
# CSP-ul aplicatiei e "script-src 'self'" (fara 'unsafe-inline') — un <script>
# inline sau un onclick="..." ar fi blocat silentios de browser. Fisier extern
# same-origin + addEventListener respecta CSP-ul existent fara sa-l slabeasca.
# ─────────────────────────────────────────────────────────────────────────────
AUDIT_JS = """
const LS_KEY = 'ris_audit_key';

function saveKey() {
  const v = document.getElementById('risKeyInput').value.trim();
  const status = document.getElementById('keyStatus');
  if (v) { sessionStorage.setItem(LS_KEY, v); status.textContent = 'salvata in sesiune'; }
  else { sessionStorage.removeItem(LS_KEY); status.textContent = ''; }
}

function restoreKey() {
  const v = sessionStorage.getItem(LS_KEY);
  if (v) {
    document.getElementById('risKeyInput').value = v;
    document.getElementById('keyStatus').textContent = 'incarcata din sesiune';
  }
}

async function liveTest(btn) {
  const method = btn.dataset.method, path = btn.dataset.path;
  if (path.includes('{')) {
    btn.textContent = 'are parametri — vezi curl';
    btn.className = 'btn-test result-fail';
    setTimeout(() => { btn.textContent = 'Testeaza live'; btn.className = 'btn-test'; }, 3000);
    return;
  }
  const key = sessionStorage.getItem(LS_KEY) || '';
  btn.disabled = true; const orig = btn.textContent; btn.textContent = '...';
  try {
    const res = await fetch(path, { method, headers: key ? {'X-RIS-Key': key} : {} });
    btn.textContent = res.ok ? ('OK ' + res.status) : ('EROARE ' + res.status);
    btn.className = 'btn-test ' + (res.ok ? 'result-ok' : 'result-fail');
  } catch (e) {
    btn.textContent = 'EROARE retea'; btn.className = 'btn-test result-fail';
  }
  setTimeout(() => { btn.disabled = false; btn.textContent = orig; btn.className = 'btn-test'; }, 4000);
}

async function liveTestProvider(btn) {
  const provider = btn.dataset.provider;
  const key = sessionStorage.getItem(LS_KEY) || '';
  btn.disabled = true; const orig = btn.textContent; btn.textContent = '...';
  try {
    const res = await fetch('/api/settings/test/' + provider, { method: 'POST', headers: key ? {'X-RIS-Key': key} : {} });
    const data = await res.json().catch(() => ({}));
    const ok = res.ok && data.ok !== false;
    btn.textContent = ok ? 'OK' : ('EROARE: ' + (data.message || res.status));
    btn.className = 'btn-test ' + (ok ? 'result-ok' : 'result-fail');
  } catch (e) {
    btn.textContent = 'EROARE retea'; btn.className = 'btn-test result-fail';
  }
  setTimeout(() => { btn.disabled = false; btn.textContent = orig; btn.className = 'btn-test'; }, 5000);
}

function filterEp(mode, activeBtn) {
  document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
  activeBtn.classList.add('active');
  document.querySelectorAll('.ep-table tbody tr').forEach(tr => {
    let show = true;
    if (mode === 'tested') show = tr.dataset.tested === 'true';
    else if (mode === 'untested') show = tr.dataset.tested === 'false';
    else if (mode === 'safe') show = !!tr.querySelector('.btn-test');
    tr.style.display = show ? '' : 'none';
  });
  document.querySelectorAll('.cat-block').forEach(block => {
    const visible = [...block.querySelectorAll('tbody tr')].some(tr => tr.style.display !== 'none');
    block.style.display = visible ? '' : 'none';
  });
}

document.addEventListener('DOMContentLoaded', () => {
  restoreKey();
  document.getElementById('saveKeyBtn').addEventListener('click', saveKey);
  document.querySelectorAll('.filters button[data-filter]').forEach(b => {
    b.addEventListener('click', () => filterEp(b.dataset.filter, b));
  });
  document.querySelectorAll('button[data-kind="endpoint"]').forEach(b => {
    b.addEventListener('click', () => liveTest(b));
  });
  document.querySelectorAll('button[data-kind="provider"]').forEach(b => {
    b.addEventListener('click', () => liveTestProvider(b));
  });
});
"""


def _walk_routes_with_prefix(routes, prefix=""):
    """Parcurge recursiv `routes`, urmarind prefixul real acumulat prin routerele
    incluse.

    FASTAPI 0.139 GOTCHA (motivul acestei functii): incepand cu 0.139.0 (upgrade
    2026-07-13, commit 5806cd3), `app.routes` nu mai contine rutele incluse prin
    `app.include_router(...)` direct/aplatizat — apar ca obiecte `_IncludedRouter`
    care NU expun `.routes` (introspectia veche `for r in app.routes` vedea doar
    cele ~19 rute definite direct pe `app`, ratand ~70 din routere).
    `_IncludedRouter` are `original_router` (routerul original, cu `.routes` proprii
    dar CU PATH-URI RELATIVE, fara prefix — verificat empiric) si `include_context`
    (obiect intern cu `.prefix`, prefixul dat la `include_router(..., prefix=...)`).
    Recursam prin `original_router.routes` acumuland prefixul, ca sa reconstruim
    path-ul complet exact cum il vede FastAPI la runtime.

    Verificat empiric (2026-07-16): rezultatul acestei functii, filtrat identic ca
    mai jos, produce 89/89 chei IDENTICE cu `CURATED_ENDPOINTS` (0 lipsa, 0 in plus)
    — inclusiv `/api/reports/public/{token}`, care are `include_in_schema=False` si
    de-aia NU apare deloc in `app.openapi()["paths"]` (sursa alternativa, testata si
    respinsa: da 85/89, rateaza exact acest endpoint).
    """
    for r in routes:
        if type(r).__name__ == "_IncludedRouter":
            original_router = getattr(r, "original_router", None)
            if original_router is None:
                continue
            sub_prefix = prefix + getattr(r.include_context, "prefix", "")
            yield from _walk_routes_with_prefix(original_router.routes, sub_prefix)
        else:
            yield r, prefix


def introspect_routes():
    """Extrage automat toate rutele REST + WebSocket din aplicatia FastAPI reala,
    inclusiv cele incluse prin sub-routere (vezi gotcha in `_walk_routes_with_prefix`)."""
    rows = []
    seen = set()
    for r, prefix in _walk_routes_with_prefix(app.routes):
        raw_path = getattr(r, "path", None)
        if raw_path is None:
            continue
        path = prefix + raw_path
        if type(r).__name__ == "APIWebSocketRoute":
            key = f"WS {path}"
            if key not in seen:
                rows.append({"method": "WS", "path": path, "key": key})
                seen.add(key)
            continue
        methods = getattr(r, "methods", None)
        if not methods:
            continue
        if not (path.startswith("/api") or path == "/metrics" or path == "/health/status"):
            continue
        for m in sorted(mm for mm in methods if mm not in ("HEAD", "OPTIONS")):
            key = f"{m} {path}"
            if key not in seen:
                rows.append({"method": m, "path": path, "key": key})
                seen.add(key)
    rows.sort(key=lambda x: (x["path"], x["method"]))
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# GARDA ANTI-REGRESIE (2026-07-16): introspectia de mai sus a fost rupta tacut
# 3 zile de un upgrade fastapi (0.115.5 -> 0.139.0, 2026-07-13) — vechea versiune
# nu arunca nicio eroare, doar scria un dashboard "13/13" plauzibil-dar-fals peste
# cel bun "88/88". `CURATED_ENDPOINTS` (metadate curate, acumulate manual, in git)
# e folosit ca linie de baza REALA — nu fisierul HTML generat anterior, care poate
# fi el insusi deja stricat de o rulare anterioara cu bug. Orice scadere mare fata
# de acest numar cunoscut opreste scrierea, zgomotos, cu explicatie + pasi de verificat.
# ─────────────────────────────────────────────────────────────────────────────
MIN_ENDPOINTS_FLOOR = 50  # sub asta e implauzibil pentru RIS, indiferent de CURATED_ENDPOINTS
REGRESSION_FRACTION = 0.7  # sub 70% din CURATED_ENDPOINTS cunoscute = regresie de introspectie


class IntrospectionRegressionError(RuntimeError):
    """Ridicata cand introspectia gaseste implauzibil de putine endpoint-uri —
    semn ca introspect_routes() s-a rupt (vezi gotcha fastapi 0.139 de mai sus),
    NU ca proiectul chiar are atat de putine rute."""


def _validate_endpoint_count(rows):
    total = len(rows)
    curated_total = len(CURATED_ENDPOINTS)
    threshold = max(MIN_ENDPOINTS_FLOOR, int(curated_total * REGRESSION_FRACTION))
    if total < threshold:
        raise IntrospectionRegressionError(
            f"\n"
            f"REFUZ sa scriu {OUTPUT.name} — introspectia a gasit doar {total} endpoint-uri\n"
            f"REST+WS, dar CURATED_ENDPOINTS (metadate curate, acumulate manual in\n"
            f"tools/generate_audit_dashboard.py, in git) contine {curated_total} chei\n"
            f"cunoscute. Pragul minim acceptat acum e {threshold}.\n"
            f"\n"
            f"Asta e aproape sigur o REGRESIE DE INTROSPECTIE, nu o scadere reala a\n"
            f"numarului de endpoint-uri din RIS (s-a intamplat deja o data: upgrade\n"
            f"fastapi 0.115.5 -> 0.139.0 pe 2026-07-13 a schimbat cum `app.routes`\n"
            f"expune rutele incluse prin `include_router()`, iar introspectia veche\n"
            f"a scris tacut un dashboard '13/13' peste unul bun '88/88').\n"
            f"\n"
            f"Verifica manual inainte de a rula din nou acest script:\n"
            f"  1. python -c \"import sys; sys.path.insert(0,'.'); from backend.main import app; "
            f"print(len(app.routes))\" — compara cu ce te astepti\n"
            f"  2. Daca s-a facut recent un upgrade fastapi/starlette: verifica daca\n"
            f"     `_IncludedRouter`/`original_router`/`include_context.prefix` (folosite\n"
            f"     de introspect_routes()) inca exista cu acelasi nume/forma in noua versiune\n"
            f"  3. NU edita manual {OUTPUT.name} ca sa 'repari' numarul — repara\n"
            f"     introspect_routes() in acest script si ruleaza-l din nou\n"
            f"\n"
            f"Fisierul {OUTPUT.name} existent NU a fost modificat.\n"
        )


def build_endpoint_data():
    rows = introspect_routes()
    out = []
    uncurated = []
    for r in rows:
        meta = CURATED_ENDPOINTS.get(r["key"])
        if meta is None:
            uncurated.append(r["key"])
            meta = {"cat": "NECURATAT", "tested": False, "evidence": "⚠️ Endpoint nou, fara metadate — adauga in CURATED_ENDPOINTS din generate_audit_dashboard.py.", "live_safe": False}
        out.append({**r, **meta})
    return out, uncurated


# ─────────────────────────────────────────────────────────────────────────────
# HTML generation
# ─────────────────────────────────────────────────────────────────────────────

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def render_html(endpoint_data, uncurated, git_sha):
    total_ep = len(endpoint_data)
    tested_ep = sum(1 for e in endpoint_data if e["tested"])
    cats = {}
    for e in endpoint_data:
        cats.setdefault(e["cat"], []).append(e)

    def status_badge(tested):
        return '<span class="badge badge-pass">TESTAT</span>' if tested else '<span class="badge badge-fail">NETESTAT</span>'

    def endpoint_row(e):
        method_class = f"method-{e['method'].lower()}"
        test_cell = (
            f'<button class="btn-test" data-kind="endpoint" data-method="{esc(e["method"])}" data-path="{esc(e["path"])}">Testeaza live</button>'
            if e.get("live_safe") else
            f'<code class="curl-cmd">{esc(curl_for(e))}</code>'
        )
        return f"""<tr data-cat="{esc(e['cat'])}" data-tested="{str(e['tested']).lower()}">
  <td><span class="method {method_class}">{esc(e['method'])}</span></td>
  <td><code>{esc(e['path'])}</code></td>
  <td>{status_badge(e['tested'])}</td>
  <td class="evidence">{esc(e['evidence'])}</td>
  <td>{test_cell}</td>
</tr>"""

    def curl_for(e):
        base = "curl -X " + e["method"] + " \"$BASE_URL" + e["path"] + "\" -H \"X-RIS-Key: $RIS_API_KEY\""
        if e["method"] in ("POST", "PUT"):
            base += " -H \"Content-Type: application/json\" -d '{}'"
        return base

    cat_sections = []
    for cat, items in sorted(cats.items()):
        rows_html = "\n".join(endpoint_row(e) for e in items)
        n_tested = sum(1 for e in items if e["tested"])
        cat_sections.append(f"""
<div class="cat-block" data-catblock="{esc(cat)}">
  <h3>{esc(cat)} <span class="cat-count">{n_tested}/{len(items)} testate</span></h3>
  <table class="ep-table">
    <thead><tr><th>Metoda</th><th>Path</th><th>Status</th><th>Dovada / notă</th><th>Test</th></tr></thead>
    <tbody>
{rows_html}
    </tbody>
  </table>
</div>""")

    analysis_rows = "\n".join(
        f'<tr><td><strong>{esc(name)}</strong></td><td>{"✅" if ok else "❌"}</td><td>{esc(note)}</td></tr>'
        for name, ok, note in ANALYSIS_TYPES
    )

    provider_rows = "\n".join(
        f'''<tr><td><strong>{esc(name)}</strong></td><td><code>{esc(envvar)}</code></td>
<td>{"<button class=\"btn-test\" data-kind=\"provider\" data-provider=\"" + esc(name.split()[0].lower()) + "\">Testeaza live</button>" if live else "—"}</td>
<td>{esc(note)}</td></tr>'''
        for name, envvar, live, note in AI_PROVIDERS
    )

    def _ping_button(ping_key):
        if not ping_key:
            return "—"
        return f'<button class="btn-test" data-kind="provider" data-provider="{esc(ping_key)}">Testeaza live</button>'

    external_rows = "\n".join(
        f'<tr><td><strong>{esc(name)}</strong></td><td><code>{esc(module)}</code></td><td>{esc(cost)}</td><td>{esc(status)}</td><td>{_ping_button(ping_key)}</td><td class="improve">{esc(improve)}</td></tr>'
        for name, module, cost, status, improve, ping_key in EXTERNAL_SOURCES
    )

    notif_rows = "\n".join(
        f'<tr><td><strong>{esc(name)}</strong></td><td><code>{esc(envvar)}</code></td><td>{esc(status)}</td><td>{_ping_button(ping_key)}</td><td class="improve">{esc(improve)}</td></tr>'
        for name, envvar, status, improve, ping_key in NOTIFICATION_CHANNELS
    )

    sched_rows = "\n".join(
        f'<tr><td><strong>{esc(name)}</strong></td><td><code>{esc(fn)}</code></td><td>{esc(freq)}</td><td>{esc(note)}</td></tr>'
        for name, fn, freq, note in SCHEDULER_TASKS
    )

    fmt_rows = "\n".join(
        f'<tr><td><strong>{esc(name)}</strong></td><td>{"✅" if ok else "❌"}</td><td>{esc(note)}</td></tr>'
        for name, ok, note in REPORT_FORMATS
    )

    page_rows = "\n".join(
        f'<tr><td><code>{esc(path)}</code></td><td>{esc(comp)}</td><td>{"✅" if ok else "❌ neverificat vizual in browser"}</td><td class="evidence">{esc(note)}</td></tr>'
        for path, comp, ok, note in FRONTEND_PAGES
    )
    pages_verified = sum(1 for _, _, ok, _ in FRONTEND_PAGES if ok)

    uncurated_html = ""
    if uncurated:
        items = "".join(f"<li><code>{esc(u)}</code></li>" for u in uncurated)
        uncurated_html = f"""
<div class="warning-box">
  <strong>⚠️ {len(uncurated)} endpoint(uri) noi, necuratate</strong> — gasite in cod dar fara metadate in
  <code>tools/generate_audit_dashboard.py</code>. Adauga-le in <code>CURATED_ENDPOINTS</code> si regenereaza.
  <ul>{items}</ul>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8">
<title>RIS — Audit Functii (live)</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#0f1117; color:#e2e8f0; margin:0; padding:24px; line-height:1.5; }}
h1 {{ font-size:1.6em; margin-bottom:4px; }}
h2 {{ font-size:1.25em; margin-top:36px; border-bottom:1px solid #2a2f3a; padding-bottom:8px; }}
h3 {{ font-size:1.05em; margin-top:22px; display:flex; justify-content:space-between; align-items:center; }}
.subtitle {{ color:#94a3b8; font-size:0.9em; margin-bottom:20px; }}
.stats-bar {{ display:flex; gap:14px; flex-wrap:wrap; margin:16px 0 28px; }}
.stat-card {{ background:#1a1d29; border:1px solid #2a2f3a; border-radius:10px; padding:14px 18px; min-width:140px; }}
.stat-card .num {{ font-size:1.7em; font-weight:700; color:#818cf8; }}
.stat-card .label {{ font-size:0.8em; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; }}
.key-bar {{ background:#1a1d29; border:1px solid #2a2f3a; border-radius:10px; padding:14px 18px; margin-bottom:20px; display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
.key-bar input {{ background:#0f1117; border:1px solid #2a2f3a; color:#e2e8f0; padding:8px 10px; border-radius:6px; font-family:monospace; min-width:280px; }}
.key-bar a {{ color:#818cf8; text-decoration:none; }}
.key-bar a:hover {{ text-decoration:underline; }}
.warning-box {{ background:#2d1a1a; border:1px solid #7f1d1d; border-radius:8px; padding:12px 16px; margin:16px 0; font-size:0.9em; }}
.info-box {{ background:#1a2332; border:1px solid #1e3a5f; border-radius:8px; padding:12px 16px; margin:16px 0; font-size:0.88em; color:#cbd5e1; }}
table {{ width:100%; border-collapse:collapse; margin:8px 0 4px; font-size:0.87em; }}
th {{ text-align:left; color:#94a3b8; font-weight:600; padding:8px 10px; border-bottom:1px solid #2a2f3a; font-size:0.8em; text-transform:uppercase; letter-spacing:0.04em; }}
td {{ padding:8px 10px; border-bottom:1px solid #1e2230; vertical-align:top; }}
tr:hover td {{ background:#161925; }}
code {{ background:#1e2230; padding:2px 6px; border-radius:4px; font-size:0.92em; color:#a5b4fc; }}
.method {{ font-weight:700; padding:2px 8px; border-radius:4px; font-size:0.82em; }}
.method-get {{ background:#0f3d2e; color:#4ade80; }}
.method-post {{ background:#1e3a5f; color:#60a5fa; }}
.method-put {{ background:#3d2e0f; color:#facc15; }}
.method-delete {{ background:#3d0f0f; color:#f87171; }}
.method-ws {{ background:#2e0f3d; color:#c084fc; }}
.badge {{ padding:2px 8px; border-radius:10px; font-size:0.78em; font-weight:600; }}
.badge-pass {{ background:#0f3d2e; color:#4ade80; }}
.badge-fail {{ background:#3d2e0f; color:#facc15; }}
.evidence {{ color:#94a3b8; font-size:0.92em; max-width:420px; }}
.improve {{ color:#fbbf24; font-size:0.9em; max-width:320px; }}
.cat-count {{ font-size:0.75em; color:#64748b; font-weight:400; }}
.btn-test {{ background:#312e81; color:#c7d2fe; border:none; padding:5px 11px; border-radius:6px; cursor:pointer; font-size:0.82em; white-space:nowrap; }}
.btn-test:hover {{ background:#4338ca; }}
.btn-test:disabled {{ opacity:0.5; cursor:wait; }}
.curl-cmd {{ font-size:0.76em; word-break:break-all; color:#64748b; }}
.filters {{ display:flex; gap:8px; margin:14px 0; flex-wrap:wrap; }}
.filters button {{ background:#1a1d29; border:1px solid #2a2f3a; color:#cbd5e1; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:0.85em; }}
.filters button.active {{ background:#312e81; border-color:#4338ca; color:#c7d2fe; }}
.result-ok {{ color:#4ade80; }}
.result-fail {{ color:#f87171; }}
footer {{ margin-top:50px; padding-top:16px; border-top:1px solid #2a2f3a; color:#64748b; font-size:0.82em; }}
.toc {{ display:flex; gap:14px; flex-wrap:wrap; margin:14px 0 24px; }}
.toc a {{ color:#a5b4fc; text-decoration:none; font-size:0.88em; background:#1a1d29; padding:5px 10px; border-radius:6px; border:1px solid #2a2f3a; }}
</style>
</head>
<body>

<h1>RIS — Audit Functii (dashboard live)</h1>
<div class="subtitle">Generat din codul real la commit <code>{esc(git_sha)}</code> — regenereaza cu <code>python tools/generate_audit_dashboard.py</code> dupa orice functie noua.</div>

<div class="stats-bar">
  <div class="stat-card"><div class="num">{tested_ep}/{total_ep}</div><div class="label">Endpoint-uri REST+WS testate</div></div>
  <div class="stat-card"><div class="num">9/9</div><div class="label">Tipuri de analiza</div></div>
  <div class="stat-card"><div class="num">5/5</div><div class="label">Provideri AI</div></div>
  <div class="stat-card"><div class="num">{sum(1 for x in EXTERNAL_SOURCES if 'OK' in x[3] or 'TESTABIL' in x[3])}/{len(EXTERNAL_SOURCES)}</div><div class="label">Surse externe cu test live</div></div>
  <div class="stat-card"><div class="num">8/8</div><div class="label">Formate raport</div></div>
  <div class="stat-card"><div class="num">{pages_verified}/{len(FRONTEND_PAGES)}</div><div class="label">Pagini verificate vizual</div></div>
</div>

{uncurated_html}

<div class="key-bar">
  <strong>Cheie API RIS (X-RIS-Key):</strong>
  <input type="password" id="risKeyInput" placeholder="lipeste aici cheia locala, ramane doar in acest browser">
  <button class="btn-test" id="saveKeyBtn">Salveaza in sesiune</button>
  <span id="keyStatus"></span>
  <a href="/settings" target="_blank">→ Editeaza chei/credentiale in Settings (pagina reala, mascata+autentificata)</a>
</div>

<div class="info-box">
  Cheile/token-urile propriu-zise NU sunt afisate niciunde in acest fisier (nici mascate, nici in clar) — per regula
  de securitate a proiectului. Butoanele "Testeaza live" apeleaza endpoint-uri existente care returneaza DOAR
  ok/eroare. Pentru editare foloseste linkul catre pagina Settings reala. Comenzile <code>curl</code> afisate pentru
  actiunile cu efect real (creeaza/modifica/sterge date, trimite mesaje, consuma cota, reporneste serviciul) sunt
  doar de copiat manual — nu ruleaza automat.
</div>

<div class="toc">
  <a href="#endpoints">Endpoint-uri REST+WS</a>
  <a href="#analysistypes">Tipuri de analiza</a>
  <a href="#providers">Provideri AI</a>
  <a href="#external">Surse externe</a>
  <a href="#notif">Notificari</a>
  <a href="#scheduler">Scheduler</a>
  <a href="#formats">Formate raport</a>
  <a href="#pages">Pagini frontend</a>
</div>

<h2 id="endpoints">Endpoint-uri REST + WebSocket ({total_ep} total)</h2>
<div class="filters">
  <button class="active" data-filter="all">Toate ({total_ep})</button>
  <button data-filter="tested">Testate ({tested_ep})</button>
  <button data-filter="untested">Netestate ({total_ep - tested_ep})</button>
  <button data-filter="safe">Testabile live acum</button>
</div>
{"".join(cat_sections)}

<h2 id="analysistypes">Tipuri de analiza (AnalysisType) — 9/9 testate</h2>
<table><thead><tr><th>Tip</th><th>Testat</th><th>Nota</th></tr></thead><tbody>{analysis_rows}</tbody></table>

<h2 id="providers">Provideri AI Sinteza — 5/5</h2>
<table><thead><tr><th>Provider</th><th>Env var</th><th>Test live</th><th>Nota</th></tr></thead><tbody>{provider_rows}</tbody></table>

<h2 id="external">Integrari surse externe de date — {len(EXTERNAL_SOURCES)}</h2>
<table><thead><tr><th>Sursa</th><th>Modul</th><th>Cost/cheie</th><th>Status test</th><th>Test</th><th>Nota</th></tr></thead><tbody>{external_rows}</tbody></table>

<h2 id="notif">Canale de notificare — {len(NOTIFICATION_CHANNELS)}</h2>
<table><thead><tr><th>Canal</th><th>Env var</th><th>Status test</th><th>Test</th><th>Nota</th></tr></thead><tbody>{notif_rows}</tbody></table>

<h2 id="scheduler">Task-uri Scheduler (background) — {len(SCHEDULER_TASKS)}</h2>
<table><thead><tr><th>Task</th><th>Functie</th><th>Frecventa</th><th>Verificare</th></tr></thead><tbody>{sched_rows}</tbody></table>

<h2 id="formats">Formate raport — 8/8</h2>
<table><thead><tr><th>Format</th><th>Testat</th><th>Nota</th></tr></thead><tbody>{fmt_rows}</tbody></table>

<h2 id="pages">Pagini frontend — {pages_verified}/{len(FRONTEND_PAGES)} verificate vizual</h2>
<div class="info-box">Verificare vizuala live 2026-07-13 (Chrome, browser real, nu doar curl/fetch) — toate 15 pagini deschise, screenshot + console errors verificate. 1 bug real gasit + reparat (Companies/CompanyDetail — vezi coloana Nota).</div>
<table><thead><tr><th>Ruta</th><th>Componenta</th><th>Status</th><th>Nota</th></tr></thead><tbody>{page_rows}</tbody></table>

<footer>
  RIS — Audit Functii — regenerat din <code>tools/generate_audit_dashboard.py</code>.
  Regula: acest fisier trebuie regenerat dupa orice endpoint/functie noua (vezi CLAUDE.md, sectiunea Audit Functii).
</footer>

<script src="/audit.js"></script>
</body>
</html>
"""


def main():
    import subprocess
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        git_sha = "unknown"

    endpoint_data, uncurated = build_endpoint_data()
    _validate_endpoint_count(endpoint_data)  # arunca IntrospectionRegressionError daca e implauzibil
    html = render_html(endpoint_data, uncurated, git_sha)
    OUTPUT.write_text(html, encoding="utf-8")
    OUTPUT_JS.write_text(AUDIT_JS.strip() + "\n", encoding="utf-8")
    print(f"Generat: {OUTPUT} + {OUTPUT_JS} ({len(endpoint_data)} endpoint-uri, {len(uncurated)} necuratate)")
    if uncurated:
        print("Endpoint-uri fara metadate (adauga in CURATED_ENDPOINTS):")
        for u in uncurated:
            print(" -", u)


if __name__ == "__main__":
    main()
