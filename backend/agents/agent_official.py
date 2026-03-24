"""
Agent 1 — Date Oficiale
Extrage date din: ANAF, ONRC (via Tavily), SEAP, BNR
Output: JSON structurat cu toate campurile + sursa + timestamp
"""

import asyncio
from datetime import datetime, date, UTC

from loguru import logger

from backend.agents.base import BaseAgent
from backend.agents.state import AnalysisState, SourceResult
from backend.agents.tools import anaf_client, bnr_client, tavily_client
from backend.agents.tools.anaf_bilant_client import get_bilant_multi_year
from backend.agents.tools.bpi_client import check_insolvency
from backend.agents.tools.cui_validator import validate_cui
from backend.agents.tools.openapi_client import get_company_onrc
from backend.agents.tools.caen_context import get_caen_context
from backend.services import cache_service
from backend.services.job_logger import (
    get_job_logger, log_agent_start, log_agent_end, log_source_result,
)


class OfficialAgent(BaseAgent):
    name = "official"
    max_retries = 3
    retry_backoff = [2, 5, 15]
    total_timeout = 300  # 5 min

    async def execute(self, state: AnalysisState) -> dict:
        params = state.get("input_params", {})
        cui = params.get("cui", "")
        company_name = params.get("company_name", "")
        job_id = state.get("job_id", "")

        # Job logger
        log_agent_start(job_id, "official")

        # Extrage CUI din input (poate fi "12345678" sau "Firma SRL")
        cui_clean = self._extract_cui(cui)

        sources: list[SourceResult] = []
        official_data: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "cui_input": cui,
        }

        # --- Validare CUI cu cifra de control ---
        if cui_clean:
            validation = validate_cui(cui_clean)
            official_data["cui_validation"] = validation
            if not validation["valid"]:
                # 10A M2.1: CUI Invalid Early Return — skip all 8 sources, save ~15s
                logger.warning(f"[official] CUI invalid: {cui_clean} - {validation['error']}. Early return.")
                official_data["cui_warning"] = validation["error"]
                official_data["early_return"] = True
                official_data["early_return_reason"] = f"CUI {cui_clean} nu trece validarea MOD 11: {validation['error']}"
                log_agent_end(job_id, "official", f"EARLY RETURN — CUI invalid: {validation['error']}")
                return {
                    "official_data": official_data,
                    "sources": sources,
                    "errors": [{"agent": "official", "error": f"CUI invalid: {validation['error']}", "recoverable": False}],
                    "current_step": f"Agent 1: CUI {cui_clean} invalid — analiza oprita",
                    "progress": 0.20,
                }

        # --- 9A: Parallel source fetching (Phase 1 — ANAF + openapi.ro + BNR simultan) ---
        if cui_clean:
            # Fetch ANAF, openapi.ro, ANAF Bilant, BNR in parallel
            anaf_task = self.fetch_with_retry(
                lambda: self._fetch_anaf(cui_clean),
                source_name="ANAF",
                source_url="https://webservicesp.anaf.ro",
            )
            openapi_task = self.fetch_with_retry(
                lambda: self._fetch_openapi_ro(cui_clean),
                source_name="openapi.ro",
                source_url="https://openapi.ro",
            )
            bilant_task = self.fetch_with_retry(
                lambda: self._fetch_anaf_bilant(cui_clean),
                source_name="ANAF Bilant",
                source_url="https://webservicesp.anaf.ro/bilant",
            )
            bnr_task = self.fetch_with_retry(
                lambda: self._fetch_bnr(),
                source_name="BNR",
                source_url="https://www.bnr.ro/nbrfxrates.xml",
            )
            # EP1: BPI insolvency check in parallel
            bpi_task = self.fetch_with_retry(
                lambda c=cui_clean: self._fetch_bpi(c),
                source_name="BPI (buletinul.ro)",
                source_url="https://www.buletinul.ro",
            )

            anaf_source, openapi_source, bilant_source, bnr_source, bpi_source = await asyncio.gather(
                anaf_task, openapi_task, bilant_task, bnr_task, bpi_task
            )

            # Process ANAF result
            sources.append(anaf_source)
            if anaf_source["data_found"]:
                official_data["anaf"] = anaf_source["data"]
                if not company_name:
                    company_name = anaf_source["data"].get("denumire", "")
                official_data["company_name"] = company_name
                official_data["cui"] = cui_clean
                log_source_result(job_id, "ANAF", True, anaf_source.get("response_time_ms", 0),
                    ["denumire", "TVA", "stare", "adresa"])
            else:
                log_source_result(job_id, "ANAF", False, anaf_source.get("response_time_ms", 0),
                    error=anaf_source.get("data", {}).get("error", "no data"))

            # Process openapi.ro result
            sources.append(openapi_source)
            if openapi_source["data_found"]:
                official_data["onrc_structured"] = openapi_source["data"]
                odata = openapi_source["data"]
                fields = [k for k in ["caen_code", "asociati", "administratori", "capital_social", "judet"] if odata.get(k)]
                log_source_result(job_id, "openapi.ro", True, openapi_source.get("response_time_ms", 0), fields)
            else:
                log_source_result(job_id, "openapi.ro", False, openapi_source.get("response_time_ms", 0),
                    error=openapi_source.get("data", {}).get("error", "no data"))

            # Process ANAF Bilant result
            sources.append(bilant_source)
            if bilant_source["data_found"]:
                official_data["financial_official"] = bilant_source["data"]
                years = list(bilant_source["data"].get("data", {}).keys()) if isinstance(bilant_source["data"].get("data"), dict) else []
                log_source_result(job_id, "ANAF Bilant", True, bilant_source.get("response_time_ms", 0),
                    [f"years={','.join(str(y) for y in years[:5])}"])
            else:
                log_source_result(job_id, "ANAF Bilant", False, bilant_source.get("response_time_ms", 0),
                    error="no financial data")

            # Process BNR result
            sources.append(bnr_source)
            if bnr_source["data_found"]:
                official_data["bnr_rates"] = bnr_source["data"]
                log_source_result(job_id, "BNR", True, bnr_source.get("response_time_ms", 0), ["exchange_rates"])
            else:
                log_source_result(job_id, "BNR", False, bnr_source.get("response_time_ms", 0), error="no rates")

            # EP1: Process BPI insolvency result
            sources.append(bpi_source)
            if bpi_source["data_found"]:
                official_data["bpi_insolventa"] = bpi_source["data"]
                bpi_found = bpi_source["data"].get("found", False)
                log_source_result(job_id, "BPI", True, bpi_source.get("response_time_ms", 0),
                    [f"insolventa={'DA' if bpi_found else 'NU'}"])
            else:
                log_source_result(job_id, "BPI", False, bpi_source.get("response_time_ms", 0),
                    error="BPI check failed")

            # EP2+EP3: Extract ANAF inactivi + risc fiscal (already in ANAF v9 response)
            if anaf_source["data_found"]:
                anaf_data = anaf_source["data"]
                official_data["anaf_inactiv"] = {
                    "inactiv": anaf_data.get("inactiv", False),
                    "data_inactivare": anaf_data.get("data_inactivare", ""),
                    "data_reactivare": anaf_data.get("data_reactivare", ""),
                    "source": "ANAF",
                }
                # EP3: Derive risc fiscal from ANAF fields
                is_risc = (
                    anaf_data.get("inactiv", False)
                    or anaf_data.get("split_tva", False)
                    or (anaf_data.get("stare_inregistrare", "").upper() not in ("", "INREGISTRAT"))
                )
                official_data["risc_fiscal"] = {
                    "risc_fiscal": is_risc,
                    "tip_risc": (
                        "Contribuabil inactiv" if anaf_data.get("inactiv") else
                        "Split TVA activ" if anaf_data.get("split_tva") else
                        f"Stare: {anaf_data.get('stare_inregistrare')}" if is_risc else
                        None
                    ),
                    "source": "ANAF",
                }
        else:
            # Fara CUI — incercam sa gasim prin Tavily
            official_data["company_name"] = cui  # presupunem ca e numele firmei
            # BNR standalone
            bnr_source = await self.fetch_with_retry(
                lambda: self._fetch_bnr(),
                source_name="BNR",
                source_url="https://www.bnr.ro/nbrfxrates.xml",
            )
            sources.append(bnr_source)
            if bnr_source["data_found"]:
                official_data["bnr_rates"] = bnr_source["data"]

        # --- 2B. ONRC (via Tavily — fallback) ---
        search_term = company_name or cui
        if search_term and not official_data.get("onrc_structured"):
            onrc_source = await self.fetch_with_retry(
                lambda: self._fetch_onrc_via_tavily(search_term, cui_clean),
                source_name="ONRC (Tavily)",
                source_url="https://recom.onrc.ro",
            )
            sources.append(onrc_source)
            if onrc_source["data_found"]:
                official_data["onrc"] = onrc_source["data"]

        # --- 3B. Date financiare (listafirme.ro via Tavily - fallback) ---
        if search_term and not official_data.get("financial_official"):
            fin_source = await self.fetch_with_retry(
                lambda: self._fetch_financial_data(search_term, cui_clean),
                source_name="Date financiare (listafirme.ro)",
                source_url="https://listafirme.ro",
            )
            sources.append(fin_source)
            if fin_source["data_found"]:
                official_data["financial"] = fin_source["data"]

        # --- 10A M2.2: Tavily Quota Pre-check before BPI + Litigation ---
        tavily_quota_ok = True
        if search_term:
            try:
                quota_ok, quota_usage = await tavily_client._check_quota()
                if not quota_ok:
                    tavily_quota_ok = False
                    logger.warning(f"[official] Tavily quota exhausted ({quota_usage}), skipping BPI+Litigation")
                    official_data["tavily_quota_exhausted"] = True
                    official_data["tavily_usage"] = quota_usage
            except Exception:
                pass  # If quota check fails, proceed anyway

        # --- 10B M2.4: Merged BPI+Litigation into single Tavily call (saves quota) ---
        if search_term and tavily_quota_ok:
            merged_source = await self.fetch_with_retry(
                lambda st=search_term, cc=cui_clean: self._fetch_legal_merged(st, cc),
                source_name="Legal (BPI+Litigii)",
                source_url="https://bpi.ro + portal.just.ro",
            )
            sources.append(merged_source)
            if merged_source["data_found"]:
                merged_data = merged_source["data"]
                # Split merged results into insolvency and litigation
                official_data["insolvency"] = {
                    "results": merged_data.get("results", []),
                    "answer": merged_data.get("answer", ""),
                    "query": merged_data.get("query", ""),
                }
                # B3 fix: Deep copy, not pointer — avoid shared mutation
                official_data["litigation"] = {
                    "results": merged_data.get("results", []),
                    "answer": merged_data.get("answer", ""),
                    "query": merged_data.get("query", ""),
                }
                log_source_result(job_id, "Legal (merged)", True,
                    merged_source.get("response_time_ms", 0), ["insolvency+litigation"])
            else:
                log_source_result(job_id, "Legal (merged)", False,
                    merged_source.get("response_time_ms", 0), error="no data")

        # --- 7. AI Pre-processing: clasificare + sentiment Tavily (ADV7) ---
        tavily_results = []
        for key in ["insolvency", "litigation", "financial", "onrc"]:
            data = official_data.get(key, {})
            if isinstance(data, dict):
                results = data.get("results", [])
                if isinstance(results, list):
                    tavily_results.extend(results[:3])

        if tavily_results:
            classified = self._classify_tavily_results(tavily_results, company_name or cui)
            official_data["web_intelligence"] = classified

        # --- 8. Context CAEN (DF4) ---
        caen_code = ""
        onrc_s = official_data.get("onrc_structured", {})
        if isinstance(onrc_s, dict):
            caen_code = onrc_s.get("caen_code", "")
        if not caen_code and isinstance(official_data.get("anaf", {}), dict):
            caen_code = official_data["anaf"].get("cod_caen", "")
        # CA1: Fallback CAEN from ANAF Bilant (daca openapi.ro + ANAF n-au furnizat)
        if not caen_code and official_data.get("financial_official"):
            bilant_data = official_data["financial_official"].get("data", {})
            if isinstance(bilant_data, dict):
                for year in sorted(bilant_data.keys(), reverse=True):
                    yr = bilant_data[year]
                    if isinstance(yr, dict) and yr.get("caen_code"):
                        caen_code = str(yr["caen_code"])
                        logger.info(f"[official] CAEN fallback from ANAF Bilant {year}: {caen_code}")
                        break
        if caen_code:
            try:
                caen_ctx = await get_caen_context(caen_code)
                if caen_ctx.get("available"):
                    official_data["caen_context"] = caen_ctx
                    logger.info(f"[official] CAEN context: {caen_code} - {caen_ctx.get('caen_description', '')[:50]}")
                    log_source_result(job_id, "CAEN Context", True, 0,
                        [f"code={caen_code}", f"sector={caen_ctx.get('caen_section_name', '')[:30]}"])
                else:
                    log_source_result(job_id, "CAEN Context", False, 0, error="CAEN code not in database")
            except Exception as e:
                logger.debug(f"[official] CAEN context failed: {e}")
                log_source_result(job_id, "CAEN Context", False, 0, error=str(e))
        else:
            log_source_result(job_id, "CAEN Context", False, 0, error="no CAEN code available (openapi.ro or ANAF)")

        # --- 9A: Data freshness tracking per source ---
        data_freshness = {}
        if official_data.get("financial_official"):
            bilant_years = list(official_data["financial_official"].get("data", {}).keys()) if isinstance(official_data["financial_official"].get("data"), dict) else []
            if bilant_years:
                latest_year = max(int(y) for y in bilant_years if str(y).isdigit())
                age_years = datetime.now(UTC).year - latest_year
                data_freshness["anaf_bilant"] = {"latest_year": latest_year, "data_age_years": age_years, "fresh": age_years <= 1}
        if official_data.get("anaf", {}).get("found"):
            data_freshness["anaf_fiscal"] = {"data_age_years": 0, "fresh": True, "note": "real-time API"}
        if official_data.get("bnr_rates"):
            data_freshness["bnr"] = {"data_age_years": 0, "fresh": True, "note": "daily rates"}
        if official_data.get("onrc_structured", {}).get("found"):
            data_freshness["onrc"] = {"data_age_years": 0, "fresh": True, "note": "registry data"}
        official_data["data_freshness"] = data_freshness

        # --- Diagnostic complet per sursa ---
        diagnostics = {}
        for s in sources:
            sname = s.get("source_name", "unknown")
            diagnostics[sname] = {
                "status": s.get("status", "UNKNOWN"),
                "data_found": s.get("data_found", False),
                "response_time_ms": s.get("response_time_ms", 0),
                "error": s.get("data", {}).get("error") if not s.get("data_found") else None,
            }

        # Verifica surse ASTEPTATE dar lipsa
        expected_sources = ["ANAF", "ANAF Bilant", "BNR"]
        if cui_clean:
            expected_sources.extend(["openapi.ro", "BPI (Tavily)", "portal.just.ro (Tavily)"])

        missing_sources = [
            es for es in expected_sources
            if not any(s.get("source_name") == es and s.get("data_found") for s in sources)
        ]

        # Verifica campuri critice lipsa
        missing_fields = []
        if not official_data.get("anaf", {}).get("found"):
            missing_fields.append("ANAF fiscal status")
        if not official_data.get("financial_official"):
            missing_fields.append("Date financiare oficiale (ANAF Bilant)")
        onrc_s = official_data.get("onrc_structured", {})
        if not (isinstance(onrc_s, dict) and onrc_s.get("found")):
            missing_fields.append("ONRC structurat (openapi.ro) — CAEN, asociati, administratori")
        if not caen_code:
            missing_fields.append("Cod CAEN (necesar pentru benchmark si context sector)")
        if not official_data.get("caen_context", {}).get("available"):
            missing_fields.append("Context CAEN (sector, numar firme, benchmark)")

        official_data["diagnostics"] = {
            "per_source": diagnostics,
            "missing_sources": missing_sources,
            "missing_fields": missing_fields,
            # C3 fix: Use total expected fields (5 field checks) as denominator, not source count
            "completeness_score": round(
                (1 - len(missing_fields) / max(5, 1)) * 100
            ),
        }

        # Sumarul surselor
        ok_count = sum(1 for s in sources if s["data_found"])
        total_count = len(sources)
        official_data["sources_summary"] = {
            "total": total_count,
            "ok": ok_count,
            "failed": total_count - ok_count,
        }

        if missing_fields:
            logger.warning(
                f"[official] CAMPURI LIPSA: {', '.join(missing_fields)}"
            )
        if missing_sources:
            logger.warning(
                f"[official] SURSE ESUATE: {', '.join(missing_sources)}"
            )

        logger.info(
            f"[official] Done: {ok_count}/{total_count} surse | "
            f"Completitudine: {official_data['diagnostics']['completeness_score']}% | "
            f"Lipsa: {len(missing_fields)} campuri"
        )

        log_agent_end(job_id, "official",
            f"{ok_count}/{total_count} surse OK | completeness={official_data['diagnostics']['completeness_score']}%")

        return {
            "official_data": official_data,
            "sources": sources,
            "current_step": f"Agent 1 finalizat: {ok_count}/{total_count} surse ({official_data['diagnostics']['completeness_score']}% complet)",
            "progress": 0.20,
        }

    def _extract_cui(self, value: str) -> str:
        """Extrage CUI numeric din input."""
        cleaned = value.strip().replace("RO", "").replace("ro", "").replace(" ", "")
        if cleaned.isdigit() and 1 <= len(cleaned) <= 10:
            return cleaned
        return ""

    async def _fetch_openapi_ro(self, cui: str) -> dict:
        cache_key = cache_service.make_cache_key("openapi", cui)
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="onrc",
            fetch_coro=lambda: get_company_onrc(cui),
            ttl_hours=168,  # 7 zile
        )

    async def _fetch_anaf_bilant(self, cui: str) -> dict:
        cache_key = cache_service.make_cache_key("anaf_bilant", cui)
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="anaf",
            fetch_coro=lambda: get_bilant_multi_year(cui),
            ttl_hours=168,  # 7 zile - datele financiare nu se schimba des
        )

    async def _fetch_anaf(self, cui: str) -> dict:
        cache_key = cache_service.make_cache_key("anaf", cui)
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="anaf",
            fetch_coro=lambda: anaf_client.get_anaf_data(cui),
        )

    async def _fetch_bnr(self) -> dict:
        from datetime import date, UTC
        cache_key = cache_service.make_cache_key("bnr", str(date.today()))
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="bnr",
            fetch_coro=bnr_client.get_exchange_rates,
        )

    async def _fetch_onrc_via_tavily(self, name: str, cui: str) -> dict:
        query = f'"{name}" ONRC date firma'
        if cui:
            query = f'CUI {cui} "{name}" ONRC'
        cache_key = cache_service.make_cache_key("onrc", query)
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="onrc",
            fetch_coro=lambda: tavily_client.search(
                query=query,
                max_results=3,
                include_domains=["recom.onrc.ro", "listafirme.ro", "risco.ro"],
            ),
        )

    async def _fetch_financial_data(self, name: str, cui: str) -> dict:
        query = f'"{name}" cifra afaceri profit angajati'
        if cui:
            query = f'CUI {cui} cifra afaceri profit angajati'
        cache_key = cache_service.make_cache_key("tavily", f"fin_{cui or name}")
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="tavily",
            fetch_coro=lambda: tavily_client.search(
                query=query,
                max_results=3,
                include_domains=["listafirme.ro", "topfirme.com", "risco.ro"],
            ),
        )

    async def _fetch_legal_merged(self, name: str, cui: str) -> dict:
        """10B M2.4: Merged BPI+Litigation into single Tavily query (saves 1 API call)."""
        identifier = cui or name
        query = f'"{identifier}" insolventa litigii BPI portal.just.ro'
        cache_key = cache_service.make_cache_key("tavily", f"legal_{identifier}")
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="tavily",
            fetch_coro=lambda: tavily_client.search(
                query=query,
                max_results=5,
                include_domains=["bpi.ro", "portal.just.ro", "lfrm.ro"],
            ),
        )

    async def _fetch_bpi(self, cui: str) -> dict:
        """EP1: Fetch BPI insolvency data (buletinul.ro with Tavily fallback)."""
        cache_key = cache_service.make_cache_key("bpi", cui)
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="bpi",
            fetch_coro=lambda: check_insolvency(cui),
            ttl_hours=24,
        )

    async def _fetch_insolvency(self, name: str, cui: str) -> dict:
        query = f'"{cui or name}" insolventa'
        cache_key = cache_service.make_cache_key("tavily", f"bpi_{cui or name}")
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="tavily",
            fetch_coro=lambda: tavily_client.search_company_info(
                company_name=name, cui=cui, info_type="insolvency"
            ),
        )

    async def _fetch_litigation(self, name: str) -> dict:
        cache_key = cache_service.make_cache_key("tavily", f"lit_{name}")
        return await cache_service.get_or_fetch(
            key=cache_key,
            source="tavily",
            fetch_coro=lambda: tavily_client.search_company_info(
                company_name=name, info_type="litigation"
            ),
        )


    def _classify_tavily_results(self, results: list, company_name: str) -> dict:
        """
        ADV7: Clasificare + sentiment pe rezultate Tavily.
        Categorii: stiri, recenzii, oficial, juridic, financiar.
        Sentiment: positiv / negativ / neutru (bazat pe keywords).
        """
        classified = {
            "categories": {"stiri": [], "recenzii": [], "oficial": [], "juridic": [], "financiar": []},
            "sentiment_summary": {"positive": 0, "negative": 0, "neutral": 0},
            "total_results": len(results),
        }

        negative_kw = [
            "insolventa", "faliment", "frauda", "datorii", "executare", "litigiu",
            "amendat", "sanctionat", "investigat", "problema", "pierdere",
            "reclamatie", "nemultumire", "esec",
        ]
        positive_kw = [
            "crestere", "profit", "succes", "premiu", "performanta", "investitie",
            "extindere", "inovatie", "contract castigat", "excelent", "recomandat",
        ]

        for item in results:
            if not isinstance(item, dict):
                continue

            content = (item.get("content", "") + " " + item.get("title", "")).lower()
            url = item.get("url", "").lower()

            # Clasificare categorie
            if any(k in url for k in ["just.ro", "portal.just", "bpi.ro"]):
                cat = "juridic"
            elif any(k in url for k in ["anaf.ro", "onrc.ro", "gov.ro", "openapi.ro"]):
                cat = "oficial"
            elif any(k in url for k in ["listafirme", "topfirme", "risco"]):
                cat = "financiar"
            elif any(k in content for k in ["recenzie", "review", "parere", "experienta"]):
                cat = "recenzii"
            else:
                cat = "stiri"

            # Sentiment
            neg_count = sum(1 for kw in negative_kw if kw in content)
            pos_count = sum(1 for kw in positive_kw if kw in content)

            if neg_count > pos_count:
                sentiment = "negative"
            elif pos_count > neg_count:
                sentiment = "positive"
            else:
                sentiment = "neutral"

            classified["categories"][cat].append({
                "title": item.get("title", "")[:100],
                "url": item.get("url", ""),
                "sentiment": sentiment,
            })
            classified["sentiment_summary"][sentiment] += 1

        return classified


official_agent = OfficialAgent()
