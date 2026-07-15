"""
build_rich_fields_model(verified_data) -- normalizeaza campurile bogate
(predictive_scores, benchmark, eurostat_sector, achizitii SEAP,
tender_opportunities, actionariat+relations, sanctiuni,
aegrm_guarantees+historical_flags, funding_programs, credit_exposure)
intr-o forma stabila,
consumata identic de html_generator / pdf_generator / docx_generator.

Randarea (culori, markup HTML/PDF/DOCX, trunchiere per format, tabele) ramane
in fiecare renderer -- modelul centralizeaza DOAR:
  (1) localizarea campului (unwrap `.get("value")` pt campuri _make_field-wrapped
      -- risk.aegrm_guarantees, market.seap)
  (2) conditiile de gate (acelasi boolean, calculat o singura data)
  (3) normalizarea preferintelor de nume pt semnalele istorice OSINT
      (label-peste-type, snippet-peste-detail) -- zona care a produs bug-urile
      din 2026-06-27, triplicata independent in 3 fisiere.
  (4) normalizarea listei itemizate de garantii AEGRM (cheia reala e
      "details", nu "guarantees"/"results" cum cautau cele 3 randere).
"""


def build_rich_fields_model(verified_data: dict) -> dict:
    pred = verified_data.get("predictive_scores", {})
    has_pred = bool(isinstance(pred, dict) and pred.get("summary"))

    bench = verified_data.get("benchmark", {})
    has_bench = bool(isinstance(bench, dict) and bench.get("available") and bench.get("comparisons"))

    eust = verified_data.get("eurostat_sector", {})
    has_eust = bool(isinstance(eust, dict) and eust.get("available") and isinstance(eust.get("indicators"), dict))

    market = verified_data.get("market", {})
    seap_field = market.get("seap", {}) if isinstance(market, dict) else {}
    seap = seap_field.get("value", seap_field) if isinstance(seap_field, dict) else {}
    has_seap = bool(isinstance(seap, dict) and (seap.get("total_contracts", 0) or 0) > 0)

    opp = verified_data.get("tender_opportunities", {})
    has_opp = bool(isinstance(opp, dict) and opp.get("available") and opp.get("count"))

    act = verified_data.get("actionariat", {})
    rel = verified_data.get("relations", {})
    act_ok = bool(isinstance(act, dict) and act.get("available"))
    rel_flags = rel.get("flags", []) if isinstance(rel, dict) else []
    has_actionariat = bool(act_ok or rel_flags)

    sanc = verified_data.get("sanctions", {})
    has_sanctions = bool(isinstance(sanc, dict) and sanc.get("status") in ("clean", "hit", "unavailable"))

    risk = verified_data.get("risk", {})
    aegrm_field = risk.get("aegrm_guarantees", {}) if isinstance(risk, dict) else {}
    aegrm = aegrm_field.get("value") if isinstance(aegrm_field, dict) else None
    aegrm_ok = bool(isinstance(aegrm, dict) and aegrm.get("has_data"))
    hist = verified_data.get("historical_flags", [])
    hist_ok = bool(isinstance(hist, list) and hist)
    has_garantii = bool(aegrm_ok or hist_ok)

    # aegrm_client.check_aegrm_guarantees() pune lista itemizata sub cheia
    # "details" -- NICIODATA "guarantees"/"results". Cele 3 randere (HTML/PDF/
    # DOCX) cauta "guarantees"/"results", deci lista detaliata (creditor/data/
    # tip bun/status) era mereu goala. Normalizata O SINGURA DATA aici, ca la
    # historical_flags mai sus.
    aegrm_details = aegrm.get("details") if isinstance(aegrm, dict) else None
    aegrm_guarantees_normalized: list[dict] = []
    if isinstance(aegrm_details, list):
        for g in aegrm_details:
            if isinstance(g, dict):
                aegrm_guarantees_normalized.append({
                    "creditor": str(g.get("creditor") or "N/A"),
                    "data": str(g.get("data") or "N/A"),
                    "tip_bun": str(g.get("tip_bun") or "N/A"),
                    "status": str(g.get("status") or "N/A"),
                })
            else:
                aegrm_guarantees_normalized.append({
                    "creditor": str(g), "data": "N/A", "tip_bun": "N/A", "status": "N/A",
                })

    historical_flags_normalized: list[dict] = []
    if hist_ok:
        for fl in hist:
            if isinstance(fl, dict):
                # osint_client (backend/agents/tools/osint_client.py) emite
                # {type(slug), label(human), severity, snippet}. Preferinta
                # canonica: label peste type, snippet peste detail -- normalizata
                # O SINGURA DATA aici (sursa bug-urilor din 2026-06-27).
                historical_flags_normalized.append({
                    "is_dict": True,
                    "label": str(fl.get("label") or fl.get("type") or fl.get("title") or fl.get("category") or "Semnal"),
                    "detail": str(fl.get("snippet") or fl.get("detail") or fl.get("description") or fl.get("text") or ""),
                    "date": fl.get("date") or fl.get("data") or "",
                    "severity": str(fl.get("severity", "INFO")).upper(),
                })
            else:
                historical_flags_normalized.append({
                    "is_dict": False, "label": "", "detail": str(fl), "date": "", "severity": "INFO",
                })

    funding = verified_data.get("funding_programs", {})
    has_funding = bool(isinstance(funding, dict) and funding.get("eligible"))

    cred = verified_data.get("credit_exposure", {})
    has_cred = bool(isinstance(cred, dict) and "expunere_ron" in cred)

    # verified["web_intelligence"] (backend/agents/agent_verification.py:274-275,
    # propagated verbatim from official["web_intelligence"]) is Brave Search (2
    # queries) + Jina enrichment (3 URLs) run on EVERY analysis -- real quota spent
    # -- but was never rendered anywhere (grep in backend/reports/ = 0 hits before
    # this fix). Shape confirmed in data/ris.db reports.full_data: NOT wrapped in
    # {"value":...}, a plain dict {"categories": {cat: [{"title","url","sentiment"}]}}.
    # Real data observed 2 identical entries (same title+url) in one category --
    # dedup by URL (fallback title) here, once, so all 3 renderers agree.
    wi = verified_data.get("web_intelligence", {})
    wi_categories_raw = wi.get("categories", {}) if isinstance(wi, dict) else {}
    wi_category_labels = {
        "stiri": "Stiri",
        "recenzii": "Recenzii",
        "oficial": "Surse Oficiale",
        "juridic": "Juridic",
        "financiar": "Financiar",
    }
    wi_categories_normalized: list[dict] = []
    if isinstance(wi_categories_raw, dict):
        for cat_key, items in wi_categories_raw.items():
            if not isinstance(items, list) or not items:
                continue
            seen: set[str] = set()
            deduped: list[dict] = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                url = str(it.get("url") or "").strip()
                title = str(it.get("title") or "").strip()
                dedup_key = url or title
                if not dedup_key or dedup_key in seen:
                    continue
                seen.add(dedup_key)
                deduped.append({
                    "title": title or "(fara titlu)",
                    "url": url,
                    "sentiment": str(it.get("sentiment") or "neutral").strip().lower(),
                })
            if deduped:
                wi_categories_normalized.append({
                    "key": str(cat_key),
                    "label": wi_category_labels.get(cat_key, str(cat_key).replace("_", " ").capitalize()),
                    "items": deduped,
                })
    has_wi = bool(wi_categories_normalized)

    return {
        "predictive_scores": {"shown": has_pred, "data": pred},
        "benchmark": {"shown": has_bench, "data": bench},
        "eurostat_sector": {"shown": has_eust, "data": eust},
        "seap": {"shown": has_seap, "data": seap},
        "tender_opportunities": {"shown": has_opp, "data": opp},
        "actionariat": {
            "shown": has_actionariat, "act_ok": act_ok, "act": act, "rel_flags": rel_flags,
        },
        "sanctions": {"shown": has_sanctions, "data": sanc},
        "garantii": {
            "shown": has_garantii, "aegrm_ok": aegrm_ok, "aegrm": aegrm,
            "guarantees": aegrm_guarantees_normalized,
            "hist_ok": hist_ok, "historical_flags": historical_flags_normalized,
        },
        "funding_programs": {"shown": has_funding, "data": funding},
        "credit_exposure": {"shown": has_cred, "data": cred},
        "web_intelligence": {"shown": has_wi, "categories": wi_categories_normalized},
    }
