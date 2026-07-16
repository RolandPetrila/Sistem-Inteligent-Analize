"""
build_rich_fields_model(verified_data) -- normalizeaza campurile bogate
(predictive_scores, benchmark, eurostat_sector, achizitii SEAP,
tender_opportunities, actionariat+relations, sanctiuni,
aegrm_guarantees+historical_flags, funding_programs, credit_exposure,
tavily_quota_exhausted, predictive_scores.divergences)
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
  (5) A6 (2026-07-16): mesajul onest cand verificarea Tavily (litigii + OSINT
      istoric) NU a rulat din lipsa de cota -- "verificare nefacuta", nu
      "nimic gasit".
  (6) A4 (2026-07-16): FAPTUL dezacordului dintre scorul 6D (verified["risk_score"])
      si modelele predictive de faliment DISPONIBILE -- NICIODATA un verdict nou,
      scoring.py ramane sursa unica a culorii/scorului. Un model INDISPONIBIL nu
      poate diverge (exclus din comparatie, nu tratat ca "de acord").
  (7) 2026-07-16 (RIS colecteaza > afiseaza, etajul 3): 3 campuri calculate CORECT
      dar randate in 0 din 8 formate (grep in backend/reports/ = 0 potriviri pt
      fiecare, inainte de acest fix):
      - maps_rating: verified["maps_rating"] (Google Maps, gasit=True/False).
        found:False / error e absenta LEGITIMA (firma mica, nu e pe Maps) --
        gate-ul ascunde sectiunea intreg, nu afiseaza "0 stele".
      - key_takeaways: verified["key_takeaways"] -- un STRING cu bullet-uri
        "\\n"-separate, fiecare deja prefixat "• " (verificat in
        data/ris.db: 67/78 populat, 11 None, niciodata lista) -- normalizat
        aici intr-o lista curata, o singura data.
      - sector_position: verified["risk_score"]["sector_position"] -- dict
        per-metrica {ratio_vs_avg, estimated_percentile}, unde percentile e un
        BUCKET categorial ("P90+"/"P75-P90"/"P50-P75"/"P25-P50"/"sub P25"),
        NU un procentil numeric exact -- randat ca eticheta, nu ca bara/procent.
"""



from backend.config import settings

TAVILY_QUOTA_MESSAGE_TEMPLATE = (
    "Verificarea litigiilor si a semnalelor istorice OSINT NU a fost efectuata pentru "
    "aceasta analiza -- cota Tavily lunara era epuizata la momentul rularii ({usage}). "
    "Absenta semnalelor in acest raport NU inseamna ca firma e curata -- inseamna ca "
    "aceasta verificare nu a rulat. Reanalizeaza firma dupa reinnoirea cotei (lunar) "
    "pentru o verificare completa."
)


def _build_tavily_quota_message(usage) -> str:
    if isinstance(usage, int):
        quota = settings.tavily_monthly_quota
        usage_str = f"{usage}/{quota} interogari" if quota else f"{usage} interogari"
    else:
        usage_str = "uzaj necunoscut"
    return TAVILY_QUOTA_MESSAGE_TEMPLATE.format(usage=usage_str)


def _predictive_bucket_signal(color) -> str | None:
    """Semnalul scorului 6D, redus la 2 stari comparabile cu modelele predictive.
    Galben (zona ambigua) nu se compara -- nu e nici clar sanatos, nici clar in
    distres, deci orice comparatie ar fi zgomot, nu fapt."""
    if color == "Verde":
        return "healthy"
    if color == "Rosu":
        return "distress"
    return None


def _altman_signal(d: dict) -> str | None:
    zone = d.get("zone")
    if zone == "SAFE":
        return "healthy"
    if zone == "DISTRESS":
        return "distress"
    return None  # GREY sau INDISPONIBIL -- nu diverge, nu concorda


def _piotroski_signal(d: dict) -> str | None:
    grade = d.get("grade")
    if grade == "STRONG":
        return "healthy"
    if grade == "WEAK":
        return "distress"
    return None  # AVERAGE sau INSUFICIENT


def _zmijewski_signal(d: dict) -> str | None:
    if not d.get("available"):
        return None
    return "distress" if d.get("distress") else "healthy"


def _beneish_signal(d: dict) -> str | None:
    if not d.get("available"):
        return None
    risk = d.get("risk")
    if risk == "OK":
        return "healthy"
    if risk in ("INVESTIGAT", "MANIPULATOR_PROBABIL"):
        return "distress"
    return None


def _build_predictive_divergences(verified_data: dict, pred: dict, has_pred: bool) -> list[dict]:
    """Compara faptic scorul 6D cu semnalul fiecarui model predictiv DISPONIBIL.
    Randeaza DOAR faptul dezacordului ("cele doua metode nu concorda"), niciodata
    un scor combinat sau un verdict nou -- scoring.py ramane neatins si e sursa
    unica a culorii/scorului. Caz real verificat (TAROM, CUI 477647): scor 74.5/
    Verde, Zmijewski -0.85 = fara semnal de distres -- NU diverge (ambele "ok"),
    deci lista de mai jos ramane goala pe acel caz, corect."""
    if not has_pred:
        return []
    risk = verified_data.get("risk_score", {})
    color = risk.get("score") if isinstance(risk, dict) else None
    numeric = risk.get("numeric_score") if isinstance(risk, dict) else None
    bucket_signal = _predictive_bucket_signal(color)
    if bucket_signal is None or numeric is None:
        return []

    checks = [
        (
            "Altman Z''", pred.get("altman_z", {}) or {}, _altman_signal,
            lambda d: f"zona {d.get('zone')} (Z''={d.get('z_score')})",
        ),
        (
            "Piotroski F", pred.get("piotroski_f", {}) or {}, _piotroski_signal,
            lambda d: f"{d.get('grade')} ({d.get('f_score')}/{d.get('max_possible')})",
        ),
        (
            "Beneish M", pred.get("beneish_m", {}) or {}, _beneish_signal,
            lambda d: f"{d.get('risk')} (M={d.get('m_score')})",
        ),
        (
            "Zmijewski X", pred.get("zmijewski_x", {}) or {}, _zmijewski_signal,
            lambda d: ("semnal de distres" if d.get("distress") else "fara semnal de distres") + f" (X={d.get('x_score')})",
        ),
    ]

    divergences: list[dict] = []
    for label, data, signal_fn, describe_fn in checks:
        model_signal = signal_fn(data)
        if model_signal is None or model_signal == bucket_signal:
            continue
        divergences.append({
            "model": label,
            "text": (
                f"Scor 6D: {color} ({numeric}). {label}: {describe_fn(data)}. "
                "Cele doua metode nu concorda."
            ),
        })
    return divergences


def _normalize_key_takeaways(kt) -> list[str]:
    """verified["key_takeaways"] (agent_synthesis) is a single string, bullets
    separated by "\\n", each already prefixed "• " (confirmed in data/ris.db:
    67/78 reports populated as str, 11 as None -- never a list, never an empty
    string). Split into a clean list once here instead of each renderer
    re-splitting/re-stripping the bullet marker independently."""
    if not isinstance(kt, str) or not kt.strip():
        return []
    items = []
    for line in kt.split("\n"):
        line = line.strip().lstrip("•").strip()
        if line:
            items.append(line)
    return items


def build_rich_fields_model(verified_data: dict) -> dict:
    pred = verified_data.get("predictive_scores", {})
    has_pred = bool(isinstance(pred, dict) and pred.get("summary"))
    pred_divergences = _build_predictive_divergences(verified_data, pred, has_pred)

    tq = verified_data.get("tavily_quota_exhausted", {})
    tq_flag = bool(isinstance(tq, dict) and tq.get("value"))
    tq_message = _build_tavily_quota_message(tq.get("usage")) if tq_flag else ""

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

    # ---- 2026-07-16 (etajul 3, "colecteaza > afiseaza"): maps_rating, key_takeaways,
    # sector_position -- calculate corect, randate in 0/8 formate inainte de acest fix.
    maps_rating = verified_data.get("maps_rating", {})
    has_maps_rating = bool(isinstance(maps_rating, dict) and maps_rating.get("found") is True)

    key_takeaways_items = _normalize_key_takeaways(verified_data.get("key_takeaways"))

    risk_score_field = verified_data.get("risk_score", {})
    sector_position = (
        risk_score_field.get("sector_position", {}) if isinstance(risk_score_field, dict) else {}
    )
    has_sector_position = bool(isinstance(sector_position, dict) and sector_position)

    return {
        "predictive_scores": {"shown": has_pred, "data": pred, "divergences": pred_divergences},
        "tavily_quota_exhausted": {"shown": tq_flag, "message": tq_message},
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
        "maps_rating": {"shown": has_maps_rating, "data": maps_rating},
        "key_takeaways": {"shown": bool(key_takeaways_items), "items": key_takeaways_items},
        "sector_position": {"shown": has_sector_position, "data": sector_position},
    }
