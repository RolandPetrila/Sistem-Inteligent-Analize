"""
Agent 4 — Verification
Filtrul de calitate al intregului sistem. Ultimul agent inainte de sinteza.

Reguli:
1. Prioritatea surselor (Nivel 1-4)
2. Rezolvare contradictii (Nivel 1 castiga)
3. Date lipsa -> INDISPONIBIL (nu inventeaza)
4. Etichete trust per camp
5. Deduplicare cu cross-validation
"""

from datetime import datetime, date, UTC

from loguru import logger

from backend.agents.base import BaseAgent
from backend.agents.state import AnalysisState


# Mapare surse la niveluri de trust
SOURCE_LEVELS = {
    # Nivel 1 — AUTORITATE MAXIMA
    "ANAF": 1,
    "ANAF Bilant": 1,
    "ONRC": 1,
    "SEAP": 1,
    "BNR": 1,
    "portal.just.ro": 1,
    "BPI (buletinul.ro)": 2,
    "data.gov.ro": 1,
    # Nivel 2 — VERIFICAT
    "listafirme.ro": 2,
    "topfirme.com": 2,
    "risco.ro": 2,
    "site oficial": 2,
    "Google Maps": 2,
    "LinkedIn": 2,
    # Nivel 3 — ESTIMAT
    "Tavily": 3,
    "presa": 3,
    "ejobs.ro": 3,
    "bestjobs.ro": 3,
    # Nivel 4 — EXCLUS
    "forum": 4,
    "anonymous": 4,
}

TRUST_LABELS = {
    1: "OFICIAL",
    2: "VERIFICAT",
    3: "ESTIMAT",
}


class VerificationAgent(BaseAgent):
    name = "verification"
    max_retries = 1
    total_timeout = 120

    async def execute(self, state: AnalysisState) -> dict:
        official = state.get("official_data") or {}
        web = state.get("web_data") or {}
        market = state.get("market_data") or {}

        verified: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "verification_version": "1.0",
        }

        # --- Profil firma ---
        verified["company"] = self._verify_company_profile(official, web)

        # --- Date financiare ---
        verified["financial"] = self._verify_financial(official)

        # --- Litigii si insolventa ---
        verified["risk"] = self._verify_risk(official)

        # --- Web intelligence ---
        if web:
            verified["web_presence"] = self._verify_web(web)

        # --- Market data ---
        if market:
            verified["market"] = self._verify_market(market)

        # --- Cross-validare multi-sursa ---
        verified["cross_validation"] = self._cross_validate(verified, official)

        # --- Detectare anomalii / firme fantoma ---
        verified["anomalies"] = self._detect_anomalies(official, verified)

        # --- Due Diligence Checklist (DF1) ---
        verified["due_diligence"] = self._build_due_diligence(verified, official)

        # --- Early Warning Signals (DF5) ---
        verified["early_warnings"] = self._detect_early_warnings(official)

        # --- Profil Actionariat (DF2) ---
        verified["actionariat"] = self._extract_actionariat(official)

        # --- Context CAEN (DF4) ---
        caen_ctx = official.get("caen_context", {})
        if caen_ctx and caen_ctx.get("available"):
            verified["caen_context"] = caen_ctx

        # --- Benchmark Financiar CAEN (DF6) ---
        verified["benchmark"] = self._build_benchmark(verified, caen_ctx)

        # --- Matricea Relatii (ADV5) ---
        verified["relations"] = self._detect_relations(official)

        # --- Scor risc general ---
        verified["risk_score"] = self._calculate_risk_score(verified)

        # --- Surse utilizate ---
        verified["sources_used"] = self._compile_sources(official, web, market)

        # --- Propaga diagnosticele din agent_official ---
        if official.get("diagnostics"):
            verified["agent_diagnostics"] = official["diagnostics"]

        # --- Diagnostic completitudine raport ---
        verified["completeness"] = self._check_completeness(verified, official, market)

        logger.info(
            f"[verification] Done. Risk score: {verified['risk_score']['score']} | "
            f"Completeness: {verified['completeness']['score']}% | "
            f"Gaps: {len(verified['completeness']['gaps'])}"
        )

        if verified["completeness"]["gaps"]:
            logger.warning(
                f"[verification] DATE LIPSA: {', '.join(g['field'] for g in verified['completeness']['gaps'])}"
            )

        return {
            "verified_data": verified,
            "current_step": f"Verificare completa. Risc: {verified['risk_score']['score']} | Completitudine: {verified['completeness']['score']}%",
            "progress": 0.50,
        }

    def _trust_label(self, source_name: str) -> str:
        """Determina eticheta trust pentru o sursa."""
        level = SOURCE_LEVELS.get(source_name, 3)
        return TRUST_LABELS.get(level, "ESTIMAT")

    def _make_field(self, value, source: str, note: str = "") -> dict:
        """Creeaza un camp verificat cu metadata."""
        field = {
            "value": value,
            "trust": self._trust_label(source),
            "source": source,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if note:
            field["note"] = note
        return field

    def _verify_company_profile(self, official: dict, web: dict) -> dict:
        """Verifica si combina datele de profil firma din TOATE sursele disponibile."""
        anaf = official.get("anaf", {})
        onrc = official.get("onrc", {})
        onrc_structured = official.get("onrc_structured", {})

        profile: dict = {}

        # Date ANAF (Nivel 1 — autoritate maxima)
        if anaf.get("found"):
            profile["cui"] = self._make_field(anaf.get("cui"), "ANAF")
            profile["denumire"] = self._make_field(anaf.get("denumire"), "ANAF")
            profile["adresa"] = self._make_field(anaf.get("adresa"), "ANAF")
            profile["nr_reg_com"] = self._make_field(anaf.get("numar_reg_com"), "ANAF")
            profile["stare_inregistrare"] = self._make_field(
                anaf.get("stare_inregistrare"), "ANAF"
            )
            profile["data_inregistrare"] = self._make_field(
                anaf.get("data_inregistrare"), "ANAF"
            )
            profile["platitor_tva"] = self._make_field(anaf.get("platitor_tva"), "ANAF")
            profile["inactiv"] = self._make_field(anaf.get("inactiv"), "ANAF")
            profile["split_tva"] = self._make_field(anaf.get("split_tva"), "ANAF")

        # Date openapi.ro ONRC structurate (Nivel 1 — CAEN, asociati, administratori)
        if isinstance(onrc_structured, dict) and onrc_structured.get("found"):
            # CAEN
            if onrc_structured.get("caen_code"):
                profile["caen_code"] = self._make_field(
                    onrc_structured["caen_code"], "ONRC"
                )
                profile["caen_description"] = self._make_field(
                    onrc_structured.get("caen_description", ""), "ONRC"
                )
            # Adresa (completam daca ANAF nu are sau e mai detaliata)
            if not profile.get("adresa") and onrc_structured.get("adresa"):
                profile["adresa"] = self._make_field(onrc_structured["adresa"], "ONRC")
            # Judet
            if onrc_structured.get("judet"):
                profile["judet"] = self._make_field(onrc_structured["judet"], "ONRC")
            # Telefon
            if onrc_structured.get("telefon"):
                profile["telefon"] = self._make_field(onrc_structured["telefon"], "ONRC")
            # Stare ONRC
            if onrc_structured.get("stare"):
                profile["stare_onrc"] = self._make_field(onrc_structured["stare"], "ONRC")
            # Nr Reg Com (completam daca ANAF nu are)
            if not profile.get("nr_reg_com") and onrc_structured.get("numar_reg_com"):
                profile["nr_reg_com"] = self._make_field(
                    onrc_structured["numar_reg_com"], "ONRC"
                )
            # Capital social
            if onrc_structured.get("capital_social"):
                profile["capital_social"] = self._make_field(
                    onrc_structured["capital_social"], "ONRC"
                )
            # Asociati
            if onrc_structured.get("asociati"):
                profile["asociati"] = self._make_field(
                    onrc_structured["asociati"], "ONRC"
                )
            # Administratori
            if onrc_structured.get("administratori"):
                profile["administratori"] = self._make_field(
                    onrc_structured["administratori"], "ONRC"
                )

            logger.info(
                f"[verification] ONRC structurat integrat: CAEN={onrc_structured.get('caen_code', 'N/A')}, "
                f"asociati={len(onrc_structured.get('asociati', []))}, "
                f"admin={len(onrc_structured.get('administratori', []))}"
            )

        # Fallback CAEN: din ANAF Bilant (mai specific) sau caen_context
        if not profile.get("caen_code"):
            # Try bilant data first (has per-code description from ANAF)
            bilant = official.get("financial_official", {})
            bilant_data = bilant.get("data", {}) if isinstance(bilant, dict) else {}
            bilant_caen = None
            bilant_caen_desc = ""
            bilant_caen_year = None
            if isinstance(bilant_data, dict):
                for yr in sorted(bilant_data.keys(), reverse=True):
                    yr_data = bilant_data.get(yr, {})
                    if isinstance(yr_data, dict) and yr_data.get("caen_code") and yr_data["caen_code"] != 0 and str(yr_data["caen_code"]).strip() != "0":
                        bilant_caen = str(yr_data["caen_code"])
                        bilant_caen_desc = yr_data.get("caen_description", "")
                        bilant_caen_year = yr
                        break

            caen_ctx = official.get("caen_context", {})
            if bilant_caen:
                profile["caen_code"] = self._make_field(
                    bilant_caen, "ANAF",
                    f"Fallback: cod CAEN din ANAF Bilant an {bilant_caen_year}",
                )
                # Prefer bilant description (per-code specific) over caen_context (section-level)
                desc = bilant_caen_desc or (caen_ctx.get("caen_description", "") if isinstance(caen_ctx, dict) else "")
                profile["caen_description"] = self._make_field(
                    desc, "ANAF",
                    f"Fallback: descriere CAEN din ANAF Bilant an {bilant_caen_year}",
                )
                logger.info(f"[verification] CAEN fallback from bilant {bilant_caen_year}: {bilant_caen} - {desc[:50]}")
            elif isinstance(caen_ctx, dict) and caen_ctx.get("caen_code"):
                profile["caen_code"] = self._make_field(
                    caen_ctx["caen_code"], "ANAF",
                    "Fallback: cod CAEN din context sector",
                )
                profile["caen_description"] = self._make_field(
                    caen_ctx.get("caen_description", ""), "ANAF",
                    "Fallback: descriere CAEN din context sector",
                )
                logger.info(f"[verification] CAEN fallback from caen_context: {caen_ctx['caen_code']}")

        # Date ONRC/Tavily (Nivel 2-3 — fallback daca openapi.ro nu a returnat)
        if onrc and isinstance(onrc, dict) and not (isinstance(onrc_structured, dict) and onrc_structured.get("found")):
            results = onrc.get("results", [])
            if results:
                combined_text = " ".join(r.get("content", "") for r in results)
                if "caen" not in profile and combined_text:
                    profile["onrc_info"] = self._make_field(
                        {"raw_results": results[:3]},
                        "ONRC (Tavily)",
                        "Date ONRC extrase via Tavily search — verificare manuala recomandata",
                    )

        return profile

    def _verify_financial(self, official: dict) -> dict:
        """Verifica datele financiare."""
        financial: dict = {}

        # ANAF — datorii si TVA
        anaf = official.get("anaf", {})
        if anaf.get("found"):
            financial["platitor_tva"] = self._make_field(
                anaf.get("platitor_tva"), "ANAF"
            )
            financial["inactiv"] = self._make_field(anaf.get("inactiv"), "ANAF")
            financial["split_tva"] = self._make_field(anaf.get("split_tva"), "ANAF")

        # ANAF Bilant — date financiare OFICIALE (Nivel 1)
        bilant = official.get("financial_official", {})
        if bilant and isinstance(bilant, dict) and bilant.get("data"):
            bilant_data = bilant.get("data", {})
            years_sorted = sorted(bilant_data.keys(), reverse=True) if bilant_data else []

            # Find latest year with non-None value per field
            # (latest year may have None if ANAF hasn't published yet)
            def _latest_val(field_name):
                for yr in years_sorted:
                    yr_data = bilant_data.get(yr, {})
                    if isinstance(yr_data, dict) and yr_data.get(field_name) is not None:
                        return yr_data[field_name], yr
                return None, None

            ca_v, ca_y = _latest_val("cifra_afaceri_neta")
            financial["cifra_afaceri"] = self._make_field(
                ca_v, "ANAF",
                f"An {ca_y} - sursa ANAF Bilant OFICIAL" if ca_y else "ANAF Bilant",
            )
            pn_v, pn_y = _latest_val("profit_net")
            financial["profit_net"] = self._make_field(
                pn_v, "ANAF",
                f"An {pn_y}" if pn_y else "ANAF Bilant",
            )
            ang_v, ang_y = _latest_val("numar_mediu_salariati")
            financial["numar_angajati"] = self._make_field(
                ang_v, "ANAF",
                f"An {ang_y}" if ang_y else "ANAF Bilant",
            )
            cap_v, cap_y = _latest_val("capitaluri_proprii")
            financial["capitaluri_proprii"] = self._make_field(
                cap_v, "ANAF",
                f"An {cap_y}" if cap_y else "ANAF Bilant",
            )

            # Trend multi-an
            trend = bilant.get("trend", {})
            if trend:
                financial["trend_financiar"] = self._make_field(
                    trend, "ANAF",
                    f"Trend {bilant.get('years_found', [])}",
                )

        # Date financiare detaliate (listafirme.ro — Nivel 2, fallback)
        fin_data = official.get("financial", {})
        if fin_data and isinstance(fin_data, dict) and "cifra_afaceri" not in financial:
            results = fin_data.get("results", [])
            if results:
                financial["financial_data_web"] = self._make_field(
                    {"raw_results": results[:3]},
                    "listafirme.ro",
                    "Date financiare din surse agregate — Nivel 2 VERIFICAT (fallback)",
                )

        # BNR
        bnr = official.get("bnr_rates", {})
        if bnr and bnr.get("rates"):
            eur_rate = bnr["rates"].get("EUR")
            if eur_rate:
                financial["eur_ron_rate"] = self._make_field(
                    eur_rate, "BNR",
                    f"Curs la data {bnr.get('date', 'N/A')}",
                )

        return financial

    def _verify_risk(self, official: dict) -> dict:
        """Verifica datele de risc (insolventa, litigii)."""
        risk: dict = {}

        # Insolventa
        insolvency = official.get("insolvency", {})
        if insolvency and isinstance(insolvency, dict):
            results = insolvency.get("results", [])
            has_insolvency = any(
                "insolventa" in r.get("content", "").lower() or
                "insolventa" in r.get("title", "").lower()
                for r in results
            ) if results else False

            risk["insolvency"] = self._make_field(
                {"found": has_insolvency, "results": results[:2]},
                "BPI (Tavily)",
                "Verificare insolventa via Tavily — rezultat ESTIMAT" if results else "Nicio mentiune gasita",
            )

        # Litigii
        litigation = official.get("litigation", {})
        if litigation and isinstance(litigation, dict):
            results = litigation.get("results", [])
            risk["litigation"] = self._make_field(
                {"found": bool(results), "count": len(results), "results": results[:3]},
                "portal.just.ro (Tavily)",
                "Litigii gasite via Tavily search — verificare manuala pe portal.just.ro recomandata"
                if results else "Niciun litigiu gasit via Tavily",
            )

        # ANAF — firma inactiva = risc
        anaf = official.get("anaf", {})
        if anaf.get("found"):
            risk["anaf_inactive"] = self._make_field(
                anaf.get("inactiv", False), "ANAF"
            )

        # EP1/E11: BPI insolventa
        bpi = official.get("bpi_insolventa", {})
        if isinstance(bpi, dict):
            risk["bpi_insolventa"] = self._make_field(
                bpi, "BPI (buletinul.ro)",
                f"Status: {bpi.get('status', 'N/A')}" if bpi.get("found") else "Nicio procedura gasita",
            )

        # EP3: Risc fiscal derivat
        risc_fiscal = official.get("risc_fiscal", {})
        if isinstance(risc_fiscal, dict):
            risk["risc_fiscal"] = self._make_field(
                risc_fiscal, "ANAF",
                risc_fiscal.get("tip_risc", ""),
            )

        return risk

    def _verify_web(self, web: dict) -> dict:
        """Verifica datele din web intelligence."""
        verified_web: dict = {}
        for key, value in web.items():
            if isinstance(value, dict) and "source" in value:
                verified_web[key] = self._make_field(
                    value, value.get("source", "web")
                )
            elif isinstance(value, dict):
                verified_web[key] = self._make_field(value, "web")
        return verified_web

    def _verify_market(self, market: dict) -> dict:
        """Verifica datele de piata."""
        verified_market: dict = {}
        for key, value in market.items():
            if isinstance(value, dict):
                verified_market[key] = self._make_field(value, "Tavily")
        return verified_market

    def _detect_relations(self, official: dict) -> dict:
        """
        ADV5: Matricea Relatii — detecteaza legaturi intre firme.
        Extrage administratori/asociati din openapi.ro si semnaleaza suprapuneri.
        """
        onrc = official.get("onrc_structured", {})
        if not isinstance(onrc, dict) or not onrc.get("found"):
            return {"available": False}

        result = {
            "available": True,
            "address": onrc.get("adresa", ""),
            "administrators": [],
            "shareholders": [],
            "flags": [],
        }

        # Extrage administratori
        admins = onrc.get("administratori", [])
        if isinstance(admins, list):
            for admin in admins:
                if isinstance(admin, dict):
                    result["administrators"].append({
                        "name": admin.get("nume", admin.get("name", str(admin))),
                    })
                elif isinstance(admin, str):
                    result["administrators"].append({"name": admin})

        # Extrage asociati
        asociati = onrc.get("asociati", [])
        if isinstance(asociati, list):
            for asociat in asociati:
                if isinstance(asociat, dict):
                    result["shareholders"].append({
                        "name": asociat.get("nume", asociat.get("name", str(asociat))),
                    })
                elif isinstance(asociat, str):
                    result["shareholders"].append({"name": asociat})

        # Flags: admin = asociat unic (one-man company)
        admin_names = {a["name"].lower() for a in result["administrators"] if a.get("name")}
        share_names = {s["name"].lower() for s in result["shareholders"] if s.get("name")}

        if admin_names and share_names and admin_names == share_names and len(admin_names) == 1:
            result["flags"].append({
                "type": "ONE_PERSON",
                "detail": "Administratorul unic este si asociatul unic",
                "severity": "INFO",
            })

        # Flag: adresa sediu = adresa virtuala tipica
        addr = result["address"].lower()
        virtual_hints = ["coworking", "regus", "virtual", "sediu virtual"]
        if any(h in addr for h in virtual_hints):
            result["flags"].append({
                "type": "VIRTUAL_OFFICE",
                "detail": "Sediu posibil virtual (coworking/virtual office)",
                "severity": "INFO",
            })

        if result["flags"]:
            logger.info(f"[verification] Relations: {len(result['flags'])} flags")
        return result

    def _build_benchmark(self, verified: dict, caen_ctx: dict) -> dict:
        """
        DF6: Benchmark Financiar CAEN — compara firma cu media sectorului.
        Exemplu: "CA firma = 187K. Media CAEN 7120 = 450K. Sub medie."
        """
        if not caen_ctx or not caen_ctx.get("benchmark"):
            return {"available": False}

        benchmark = caen_ctx["benchmark"]
        ca_medie = benchmark.get("ca_medie")
        ang_medii = benchmark.get("angajati_medii")

        if not ca_medie:
            return {"available": False}

        financial = verified.get("financial", {})

        # CA firma
        ca_field = financial.get("cifra_afaceri", {})
        ca_firma = ca_field.get("value") if isinstance(ca_field, dict) else None

        # Angajati firma
        ang_field = financial.get("numar_angajati", {})
        ang_firma = ang_field.get("value") if isinstance(ang_field, dict) else None

        result = {
            "available": True,
            "caen_code": caen_ctx.get("caen_code", ""),
            "caen_section_name": caen_ctx.get("caen_section_name", ""),
            "nr_firme_sector": caen_ctx.get("nr_firme_caen"),
            "comparisons": [],
        }

        # Compara CA
        if ca_firma is not None and isinstance(ca_firma, (int, float)) and ca_medie:
            ratio = ca_firma / ca_medie if ca_medie > 0 else 0
            if ratio >= 2:
                pozitie = "Semnificativ peste medie"
            elif ratio >= 1:
                pozitie = "Peste medie"
            elif ratio >= 0.5:
                pozitie = "Sub medie"
            else:
                pozitie = "Semnificativ sub medie"

            result["comparisons"].append({
                "metric": "Cifra de afaceri",
                "firma": ca_firma,
                "media_sector": ca_medie,
                "ratio": round(ratio, 2),
                "pozitie": pozitie,
                "text": f"CA firma: {ca_firma:,.0f} RON. Media sector: {ca_medie:,.0f} RON. {pozitie} ({ratio:.1f}x).",
            })

        # Compara angajati
        if ang_firma is not None and isinstance(ang_firma, (int, float)) and ang_medii:
            ratio = ang_firma / ang_medii if ang_medii > 0 else 0
            if ratio >= 2:
                pozitie = "Semnificativ peste medie"
            elif ratio >= 1:
                pozitie = "Peste medie"
            elif ratio >= 0.5:
                pozitie = "Sub medie"
            else:
                pozitie = "Semnificativ sub medie"

            result["comparisons"].append({
                "metric": "Numar angajati",
                "firma": int(ang_firma),
                "media_sector": ang_medii,
                "ratio": round(ratio, 2),
                "pozitie": pozitie,
                "text": f"Angajati firma: {int(ang_firma)}. Media sector: {ang_medii}. {pozitie} ({ratio:.1f}x).",
            })

        if result["comparisons"]:
            logger.info(f"[verification] Benchmark: {len(result['comparisons'])} comparatii")
        return result

    def _build_due_diligence(self, verified: dict, official: dict) -> list[dict]:
        """F13: Delegated to verification/due_diligence.py."""
        from backend.agents.verification.due_diligence import build_due_diligence
        return build_due_diligence(verified, official)

    def _detect_early_warnings(self, official: dict) -> list[dict]:
        """F13: Delegated to verification/early_warnings.py."""
        from backend.agents.verification.early_warnings import detect_early_warnings
        return detect_early_warnings(official)

    def _extract_actionariat(self, official: dict) -> dict:
        """
        DF2: Extrage profil actionariat (asociati + administratori) din openapi.ro.
        """
        onrc = official.get("onrc_structured", {})
        if not isinstance(onrc, dict) or not onrc.get("found"):
            return {"available": False, "source": "openapi.ro"}

        result = {
            "available": True,
            "source": "openapi.ro",
            "asociati": onrc.get("asociati", []),
            "administratori": onrc.get("administratori", []),
            "capital_social": onrc.get("capital_social"),
            "stare": onrc.get("stare", ""),
        }

        logger.info(
            f"[verification] Actionariat: {len(result['asociati'])} asociati, "
            f"{len(result['administratori'])} administratori"
        )
        return result

    def _calculate_risk_score(self, verified: dict) -> dict:
        """Delegheaza la modul separat verification/scoring.py."""
        from backend.agents.verification.scoring import calculate_risk_score
        return calculate_risk_score(verified)

    def _detect_anomalies(self, official: dict, verified: dict) -> list[dict]:
        """
        Detecteaza pattern-uri suspecte / firme fantoma.
        Returneaza lista de alerte cu nivel: INFO / ATENTIE / SUSPECT.
        """
        anomalies = []

        # Extrage date
        bilant = official.get("financial_official", {})
        bilant_data = bilant.get("data", {}) if isinstance(bilant, dict) else {}
        latest_year = max(bilant_data.keys()) if bilant_data else None
        latest = bilant_data.get(latest_year, {}) if latest_year else {}

        ca = latest.get("cifra_afaceri_neta")
        angajati = latest.get("numar_mediu_salariati")
        profit_net = latest.get("profit_net")
        pierdere = latest.get("pierdere_neta")
        capital = latest.get("capital_social") or latest.get("capitaluri_proprii")

        anaf = official.get("anaf", {})
        inactiv = anaf.get("inactiv", False)
        data_inreg = anaf.get("data_inregistrare", "")

        # Regula 1: 0 angajati + CA mare
        if angajati is not None and angajati == 0 and ca is not None and ca > 1_000_000:
            anomalies.append({
                "level": "SUSPECT",
                "rule": "0 angajati + CA > 1M RON",
                "detail": f"Firma declara 0 angajati dar are cifra de afaceri de {ca:,.0f} RON. Posibil firma fantoma sau externalizare totala.",
            })

        # Regula 2: Capital social minim + CA mare
        if capital is not None and capital <= 200 and ca is not None and ca > 500_000:
            anomalies.append({
                "level": "ATENTIE",
                "rule": "Capital social minim + CA mare",
                "detail": f"Capital social {capital:,.0f} RON (minim legal) dar CA de {ca:,.0f} RON. Subcapitalizare semnificativa.",
            })

        # Regula 3: Firma inactiva ANAF
        if inactiv:
            anomalies.append({
                "level": "SUSPECT",
                "rule": "Firma inactiva la ANAF",
                "detail": "Firma este declarata INACTIVA de ANAF. Nu poate emite facturi legal.",
            })

        # Regula 4: Pierdere neta
        if pierdere is not None and pierdere > 0:
            anomalies.append({
                "level": "ATENTIE",
                "rule": "Pierdere neta declarata",
                "detail": f"Firma a inregistrat pierdere neta de {pierdere:,.0f} RON in {latest_year}.",
            })

        # Regula 5: Firma foarte noua + CA mare
        if data_inreg:
            try:
                from datetime import datetime, date, UTC
                inreg_date = datetime.strptime(data_inreg.split(" ")[-1] if " " in data_inreg else data_inreg, "%d.%m.%Y")
                age_years = (datetime.now() - inreg_date).days / 365.25
                if age_years < 1 and ca is not None and ca > 500_000:
                    anomalies.append({
                        "level": "ATENTIE",
                        "rule": "Firma sub 1 an + CA > 500K",
                        "detail": f"Firma infiintata recent ({data_inreg}) dar deja are CA de {ca:,.0f} RON. Crestere neobisnuit de rapida.",
                    })
                elif age_years < 2:
                    anomalies.append({
                        "level": "INFO",
                        "rule": "Firma tanara",
                        "detail": f"Firma infiintata in {data_inreg} (sub 2 ani vechime).",
                    })
            except (ValueError, IndexError) as e:
                logger.debug(f"[verification] Age parse error for {data_inreg}: {e}")

        # Regula 6: CA = 0 dar nu e inactiva
        if ca is not None and ca == 0 and not inactiv:
            anomalies.append({
                "level": "INFO",
                "rule": "CA zero",
                "detail": f"Cifra de afaceri 0 RON in {latest_year}. Firma activa dar fara activitate comerciala.",
            })

        return anomalies

    def _cross_validate(self, verified: dict, official: dict) -> dict:
        """
        Cross-validare multi-sursa. Verifica campuri critice in min 2 surse.
        Confidence: 1.0 (3+ surse) / 0.7 (2 surse) / 0.4 (1 sursa)
        """
        cross_validation = {}

        # Denumire firma: ANAF vs ONRC/Tavily
        sources_for_name = []
        anaf = official.get("anaf", {})
        if anaf.get("found") and anaf.get("denumire"):
            sources_for_name.append(("ANAF", anaf["denumire"]))
        onrc = official.get("onrc", {})
        if isinstance(onrc, dict) and onrc.get("results"):
            for r in onrc["results"][:3]:
                title = r.get("title", "")
                if title:
                    sources_for_name.append(("ONRC/Tavily", title))
                    break

        confidence = min(1.0, 0.4 + 0.3 * (len(sources_for_name) - 1)) if sources_for_name else 0.0
        cross_validation["denumire"] = {
            "sources_count": len(sources_for_name),
            "confidence": round(confidence, 1),
            "sources": [s[0] for s in sources_for_name],
            "status": "CONFIRMAT" if confidence >= 0.7 else "NECONCLUDENT" if sources_for_name else "INDISPONIBIL",
        }

        # CUI: validare cifra de control + ANAF
        cui_sources = []
        cui_validation = official.get("cui_validation", {})
        if cui_validation.get("valid"):
            cui_sources.append("Cifra de control")
        if anaf.get("found"):
            cui_sources.append("ANAF")

        confidence = min(1.0, 0.4 + 0.3 * (len(cui_sources) - 1)) if cui_sources else 0.0
        cross_validation["cui"] = {
            "sources_count": len(cui_sources),
            "confidence": round(confidence, 1),
            "sources": cui_sources,
            "status": "CONFIRMAT" if confidence >= 0.7 else "NECONCLUDENT",
        }

        # Date financiare: ANAF Bilant vs listafirme.ro
        fin_sources = []
        if official.get("financial_official", {}).get("data"):
            fin_sources.append("ANAF Bilant")
        fin_tavily = official.get("financial", {})
        if isinstance(fin_tavily, dict) and fin_tavily.get("results"):
            fin_sources.append("listafirme.ro")

        confidence = min(1.0, 0.4 + 0.3 * (len(fin_sources) - 1)) if fin_sources else 0.0
        cross_validation["financiar"] = {
            "sources_count": len(fin_sources),
            "confidence": round(confidence, 1),
            "sources": fin_sources,
            "status": "CONFIRMAT" if confidence >= 0.7 else "NECONCLUDENT" if fin_sources else "INDISPONIBIL",
        }

        return cross_validation

    def _compile_sources(self, official: dict, web: dict, market: dict) -> list[dict]:
        """Compileaza lista tuturor surselor folosite."""
        sources = []
        if official.get("anaf", {}).get("found"):
            sources.append({"name": "ANAF", "level": 1, "status": "OK"})
        if official.get("financial_official"):
            sources.append({"name": "ANAF Bilant", "level": 1, "status": "OK"})
        onrc_s = official.get("onrc_structured", {})
        if isinstance(onrc_s, dict) and onrc_s.get("found"):
            sources.append({"name": "openapi.ro (ONRC)", "level": 1, "status": "OK"})
        elif official.get("onrc"):
            sources.append({"name": "ONRC (Tavily)", "level": 2, "status": "OK"})
        if official.get("financial"):
            sources.append({"name": "listafirme.ro", "level": 2, "status": "OK"})
        if official.get("bnr_rates"):
            sources.append({"name": "BNR", "level": 1, "status": "OK"})
        if official.get("insolvency"):
            sources.append({"name": "BPI (Tavily)", "level": 3, "status": "OK"})
        if official.get("litigation"):
            sources.append({"name": "portal.just.ro (Tavily)", "level": 3, "status": "OK"})
        if official.get("caen_context", {}).get("available"):
            sources.append({"name": "CAEN Context (INS TEMPO)", "level": 1, "status": "OK"})
        if market.get("seap"):
            seap = market["seap"]
            total = seap.get("total_contracts", 0)
            sources.append({"name": "SEAP (e-licitatie.ro)", "level": 1, "status": "OK", "contracts": total})
        if web.get("online_presence"):
            sources.append({"name": "Tavily (prezenta online)", "level": 3, "status": "OK"})
        if web.get("news"):
            sources.append({"name": "Tavily (stiri)", "level": 3, "status": "OK"})
        return sources

    def _check_completeness(self, verified: dict, official: dict, market: dict) -> dict:
        """Delegheaza la modul separat verification/completeness.py."""
        from backend.agents.verification.completeness import check_completeness
        return check_completeness(verified, official, market)



verification_agent = VerificationAgent()
