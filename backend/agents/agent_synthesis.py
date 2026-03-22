"""
Agent 5 — Synthesis
Primeste verified_data JSON si genereaza text narativ per sectiune de raport.

Modul principal: Claude Code CLI subprocess (`claude --print`)
Fallback autonom: Gemini Flash API (gratuit)
"""

import asyncio
import copy
import json
import re
import subprocess

from loguru import logger

from backend.agents.base import BaseAgent
from backend.agents.state import AnalysisState
from backend.config import settings
from backend.http_client import get_client
from backend.prompts.system_prompt import SYSTEM_PROMPT
from backend.prompts.section_prompts import get_sections_for_analysis


class SynthesisAgent(BaseAgent):
    name = "synthesis"
    max_retries = 2
    retry_backoff = [5, 15]
    total_timeout = 600  # 10 min (sinteza poate fi lenta)

    async def execute(self, state: AnalysisState) -> dict:
        verified_data = state.get("verified_data", {})
        analysis_type = state.get("analysis_type", "CUSTOM_REPORT")
        report_level = state.get("report_level", 2)

        if not verified_data:
            return {
                "report_sections": {},
                "errors": [{"agent": "synthesis", "error": "No verified data", "recoverable": False}],
                "current_step": "Synthesis: nu exista date verificate",
                "progress": 0.75,
            }

        sections_config = get_sections_for_analysis(analysis_type, report_level, verified_data)
        report_sections: dict = {}
        total = len(sections_config)

        for i, section in enumerate(sections_config):
            key = section["key"]
            title = section["title"]
            word_target = section.get("word_count", 300)

            # 8C: Provider routing per section type (overrides simple word-based routing)
            route = section.get("route_preference", "quality")
            if word_target <= 200:
                route = "fast"
            logger.info(f"[synthesis] Section {i+1}/{total}: {title} ({word_target}w, route={route})")

            if route == "fast":
                # B9 fix: Fast route — speed priority: Groq → Cerebras → Mistral → Gemini
                # 10F M4.5: Token Budget Enforcement — check if prompt fits provider context
                initial_provider = "groq"
                test_prompt = self._build_section_prompt(section, verified_data, initial_provider)
                initial_provider = self._check_token_budget(test_prompt, initial_provider)

                if initial_provider == "groq":
                    text = await self._generate_with_groq(
                        self._build_section_prompt(section, verified_data, "groq"))
                else:
                    text = None
                if not text:
                    text = await self._generate_with_cerebras(
                        self._build_section_prompt(section, verified_data, "cerebras"))
                if not text:
                    text = await self._generate_with_mistral(
                        self._build_section_prompt(section, verified_data, "mistral"))
                if not text:
                    text = await self._generate_with_gemini(
                        self._build_section_prompt(section, verified_data, "gemini"))
            else:
                # B9 fix: Quality route — quality priority: Claude → Gemini → Groq → Mistral
                # 10F M4.5: Token Budget Enforcement
                initial_provider = "claude"
                test_prompt = self._build_section_prompt(section, verified_data, initial_provider)
                initial_provider = self._check_token_budget(test_prompt, initial_provider)

                if initial_provider == "claude":
                    text = await self._generate_with_claude(
                        self._build_section_prompt(section, verified_data, "claude"))
                else:
                    text = None
                if not text:
                    text = await self._generate_with_gemini(
                        self._build_section_prompt(section, verified_data, "gemini"))
                if not text:
                    text = await self._generate_with_groq(
                        self._build_section_prompt(section, verified_data, "groq"))
                if not text:
                    text = await self._generate_with_mistral(
                        self._build_section_prompt(section, verified_data, "mistral"))

            if not text:
                text = await self._generate_with_cerebras(
                    self._build_section_prompt(section, verified_data, "cerebras"))
            # 10F M4.2: Structured Degradation 3-Tier
            if not text:
                text = self._degraded_fallback(section, verified_data)

            # 10B M4.1: Output Validation — check for invented data, impossible stats
            text = self._validate_output(text, verified_data, section)

            report_sections[key] = {
                "title": title,
                "content": text,
                "word_count": len(text.split()),
            }

        # 10B M4.3: Cross-Section Coherence — verify consistency between sections
        report_sections = self._check_cross_section_coherence(report_sections, verified_data)

        logger.info(f"[synthesis] Done: {len(report_sections)}/{total} sections generated")

        return {
            "report_sections": report_sections,
            "current_step": f"Sinteza completa: {len(report_sections)} sectiuni",
            "progress": 0.75,
        }

    def _build_section_prompt(self, section: dict, verified_data: dict, provider: str = "claude") -> str:
        """Construieste prompt-ul optimizat per provider AI.
        8C: Context awareness — inject structured summary instead of raw JSON dump."""
        # 10F M4.4: Prompt Injection Hardening — sanitize data before prompt construction
        verified_data = self._sanitize_data_for_prompt(verified_data)

        # Context awareness injection (8C) — structured summary
        context_summary = self._build_context_summary(section["key"], verified_data)

        # B10 fix: Dynamic JSON context limits based on actual provider context windows
        # Reserve ~40% of context for prompt+output; use ~60% for data JSON
        max_json_chars = {
            "claude": 50000,   # 200K context → plenty of room
            "groq": 20000,     # 131K context (Llama 4 Scout)
            "mistral": 20000,  # 128K context (Small 3)
            "gemini": 400000,  # D8 fix: 1M context → use 400K chars for data
            "cerebras": 20000, # 128K context (Qwen 3 235B)
        }
        json_limit = max_json_chars.get(provider, 15000)
        data_json = json.dumps(verified_data, ensure_ascii=False, default=str, indent=2)
        # Only truncate if actually exceeds limit — small data passes through intact
        if len(data_json) > json_limit:
            data_json = data_json[:json_limit] + f"\n... [date trunchiate la {json_limit} chars pt {provider}]"

        # Provider-specific instructions
        style = {
            "claude": (
                "Scrie un text narativ, profesional, in limba romana. "
                "Foloseste paragrafe fluente cu tranzitii naturale. "
                "Integreaza cifrele in context explicativ."
            ),
            "groq": (
                "Genereaza un text STRUCTURAT in limba romana. "
                "Foloseste bullet points si headere clare. "
                "Fii concis si direct la obiect. Format: ## Subtitlu + bullet points."
            ),
            "mistral": (
                "Redacteaza textul in limba romana, stil european profesional. "
                "Foloseste formulari precise si terminologie de business romaneasca. "
                "Structura clara cu paragrafe scurte."
            ),
            "gemini": (
                "Scrie textul in limba romana, stil analitic. "
                "Structureaza cu headere si sub-puncte. "
                "Include concluzii actionabile la final."
            ),
            "cerebras": (
                "Scrie textul in limba romana. "
                "Structura simpla: introducere, analiza, concluzie. "
                "Maxim 3 paragrafe pe punct."
            ),
        }

        # CA4: Inject completeness warnings
        warnings = verified_data.get("_warnings", [])
        warnings_text = ""
        if warnings:
            warnings_text = "\n--- AVERTISMENTE SISTEM ---\n" + "\n".join(warnings) + "\n"

        # 9B: Anomaly feedback loop — force synthesis to address anomalies
        anomaly_alerts = verified_data.get("_anomaly_alerts", [])
        anomaly_text = ""
        if anomaly_alerts:
            anomaly_text = (
                "\n--- ANOMALII DETECTATE (TREBUIE ANALIZATE EXPLICIT!) ---\n"
                + "\n".join(f"- {a}" for a in anomaly_alerts)
                + "\nAceste anomalii TREBUIE mentionate si explicate in text.\n"
            )

        # 10A M4.6: Confidence-Aware Synthesis — low confidence → explicit "Date incomplete"
        cross_val = verified_data.get("cross_validation", {})
        low_confidence_text = ""
        low_dims = []
        for dim, info in cross_val.items():
            conf = info.get("confidence", 1.0) if isinstance(info, dict) else 1.0
            if conf < 0.5:
                low_dims.append(f"{dim} (confidence={conf})")
        if low_dims:
            low_confidence_text = (
                "\n--- DATE INCOMPLETE (CONFIDENCE SCAZUTA) ---\n"
                f"Urmatoarele dimensiuni au date insuficiente sau neconfirmate: {', '.join(low_dims)}.\n"
                f"Pentru aceste dimensiuni: NU trage concluzii ferme. Scrie explicit 'Date incomplete — "
                f"informatiile disponibile sunt limitate si neconfirmate din surse multiple.'\n"
            )

        # Anti-halucinare: semnaleaza campuri lipsa
        completeness = verified_data.get("completeness", {})
        gaps = completeness.get("gaps", [])
        gaps_text = ""
        if gaps:
            gap_names = [g["field"] for g in gaps]
            gaps_text = (
                f"\n--- ATENTIE: DATE LIPSA (NU INVENTA!) ---\n"
                f"Urmatoarele campuri NU au date disponibile: {', '.join(gap_names)}.\n"
                f"Pentru aceste campuri scrie EXPLICIT: '[INDISPONIBIL] — sursa nu a furnizat date.'\n"
                f"NU inventa, NU estima, NU presupune valori. 0% toleranta la informatii neadevarate.\n"
            )

        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"--- SECTIUNE: {section['title']} ---\n"
            f"{section['prompt']}\n\n"
            f"--- STIL ---\n{style.get(provider, style['claude'])}\n\n"
            f"{warnings_text}"
            f"{anomaly_text}"
            f"{low_confidence_text}"
            f"--- CONTEXT STRUCTURAT ---\n{context_summary}\n\n"
            f"--- REGULA ABSOLUTA ---\n"
            f"Scrie DOAR pe baza datelor din JSON-ul de mai jos. "
            f"Daca o informatie nu exista in date, scrie '[INDISPONIBIL]'. "
            f"NU inventa competitori, cifre, proiecte sau contracte.\n"
            f"{gaps_text}\n"
            f"--- DATE VERIFICATE (JSON) ---\n"
            f"{data_json}\n\n"
            f"Scrie DIRECT textul sectiunii, fara introduceri sau explicatii meta. "
            f"Limita: ~{section['word_count']} cuvinte."
        )

    def _validate_output(self, text: str, verified_data: dict, section: dict) -> str:
        """10B M4.1: Validate generated output — check for hallucinations and impossible stats."""
        if not text or text.startswith("[Sectiunea"):
            return text

        # Check: CUI in text must match input CUI
        company = verified_data.get("company", {})
        input_cui = ""
        cui_field = company.get("cui", {})
        if isinstance(cui_field, dict):
            input_cui = str(cui_field.get("value", ""))

        # Check: company name consistency
        input_name = ""
        name_field = company.get("denumire", {})
        if isinstance(name_field, dict):
            input_name = str(name_field.get("value", ""))

        # B11 fix: Active hallucination detection — strip suspicious percentages
        # D9 fix: Exclude calendar years (2020%, 2024%, etc.) from false positives
        suspicious = re.findall(r'[-+]?\d{4,}%', text)
        if suspicious:
            real_suspicious = [s for s in suspicious if not re.match(r'^-?20\d{2}%$', s)]
            if real_suspicious:
                logger.warning(f"[synthesis] Stripping suspicious percentages: {real_suspicious[:5]}")
                for s in real_suspicious:
                    text = text.replace(s, "[procent neverificat]")

        # Strip invented CUI numbers not matching input
        if input_cui:
            invented_cuis = re.findall(r'\bCUI\s*:?\s*(\d{6,10})\b', text)
            for found_cui in invented_cuis:
                if found_cui != input_cui and found_cui not in text[:50]:  # allow header mentions
                    logger.warning(f"[synthesis] Stripping invented CUI: {found_cui} (expected {input_cui})")
                    text = text.replace(found_cui, input_cui)

        # Word count check
        word_count = len(text.split())
        target = section.get("word_count", 300)
        if word_count < target * 0.3 and target > 100:
            logger.warning(f"[synthesis] Section '{section['key']}' too short: {word_count}/{target} words")

        return text

    def _check_cross_section_coherence(self, sections: dict, verified_data: dict) -> dict:
        """10B M4.3: Check consistency between sections — risk color, financial figures."""
        risk_score = verified_data.get("risk_score", {})
        risk_color = risk_score.get("score", "")

        if not risk_color or len(sections) < 2:
            return sections

        # Check: executive_summary and risk_assessment should agree on risk color
        exec_content = sections.get("executive_summary", {}).get("content", "")
        risk_content = sections.get("risk_assessment", {}).get("content", "")

        color_map = {
            "Verde": ["verde", "scazut", "favorabil", "low risk"],
            "Galben": ["galben", "mediu", "moderat", "medium risk"],
            "Rosu": ["rosu", "ridicat", "semnificativ", "high risk"],
        }
        expected_terms = color_map.get(risk_color, [])

        if exec_content and risk_color and expected_terms:
            exec_lower = exec_content.lower()
            has_match = any(term in exec_lower for term in expected_terms)
            # Check for contradictory risk mentions
            other_colors = [t for c, terms in color_map.items() if c != risk_color for t in terms]
            has_contradiction = any(term in exec_lower for term in other_colors[:3])

            if has_contradiction and not has_match:
                logger.warning(f"[synthesis] Cross-section incoherence: exec_summary contradicts risk={risk_color}")
                sections["executive_summary"]["content"] += (
                    f"\n\n*[Nota: Scorul de risc calculat este {risk_color} ({risk_score.get('numeric_score', '?')}/100).]*"
                )

        return sections

    async def _generate_with_claude(self, prompt: str) -> str | None:
        """Genereaza text via Claude Code CLI subprocess."""
        if settings.synthesis_mode != "claude_code":
            return None

        try:
            logger.debug("[synthesis] Trying Claude Code CLI...")
            # CREATE_NO_WINDOW previne aparitia terminalelor in taskbar
            import sys
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        [
                            "claude",
                            "--print",
                            "--model", "claude-opus-4-6",
                            "--effort", "max",
                            "-p", prompt,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=180,
                        encoding="utf-8",
                        creationflags=creation_flags,
                    ),
                ),
                timeout=200,
            )
            if result.returncode == 0 and result.stdout.strip():
                text = result.stdout.strip()
                logger.debug(f"[synthesis] Claude Code OK: {len(text.split())} words")
                return text
            else:
                stderr = result.stderr[:200] if result.stderr else ""
                logger.warning(f"[synthesis] Claude Code failed: rc={result.returncode} {stderr}")
                return None
        except FileNotFoundError:
            logger.warning("[synthesis] Claude CLI not found — falling back to Gemini")
            return None
        except (asyncio.TimeoutError, subprocess.TimeoutExpired):
            logger.warning("[synthesis] Claude Code timeout — falling back to Gemini")
            return None
        except Exception as e:
            logger.warning(f"[synthesis] Claude Code error: {e}")
            return None

    async def _generate_with_groq(self, prompt: str) -> str | None:
        """Genereaza text via Groq API (fallback rapid, gratuit, OpenAI-compatibil)."""
        if not settings.groq_api_key:
            return None

        try:
            logger.debug("[synthesis] Trying Groq API...")

            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            }
            headers = {
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            }

            client = get_client()
            response = await client.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "").strip()
                if text:
                    logger.debug(f"[synthesis] Groq OK: {len(text.split())} words")
                    return text

            logger.warning("[synthesis] Groq returned empty response")
            return None

        except Exception as e:
            logger.warning(f"[synthesis] Groq error: {e}")
            return None

    async def _generate_with_mistral(self, prompt: str) -> str | None:
        """Genereaza text via Mistral API (1B tokeni/luna gratis, excelent pt limbi europene)."""
        if not settings.mistral_api_key:
            return None

        try:
            logger.debug("[synthesis] Trying Mistral API...")

            url = "https://api.mistral.ai/v1/chat/completions"
            payload = {
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            }
            headers = {
                "Authorization": f"Bearer {settings.mistral_api_key}",
                "Content-Type": "application/json",
            }

            client = get_client()
            response = await client.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "").strip()
                if text:
                    logger.debug(f"[synthesis] Mistral OK: {len(text.split())} words")
                    return text

            logger.warning("[synthesis] Mistral returned empty response")
            return None

        except Exception as e:
            logger.warning(f"[synthesis] Mistral error: {e}")
            return None

    async def _generate_with_gemini(self, prompt: str) -> str | None:
        """Genereaza text via Gemini Flash API (fallback gratuit)."""
        if not settings.google_ai_api_key:
            logger.warning("[synthesis] No GOOGLE_AI_API_KEY — cannot use Gemini fallback")
            return None

        try:
            logger.debug("[synthesis] Trying Gemini Flash API...")

            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.5-flash-preview-05-20:generateContent?key={settings.google_ai_api_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 4096,
                },
            }

            client = get_client()
            response = await client.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
                    if text:
                        logger.debug(f"[synthesis] Gemini OK: {len(text.split())} words")
                        return text

            logger.warning("[synthesis] Gemini returned empty response")
            return None

        except Exception as e:
            logger.warning(f"[synthesis] Gemini error: {e}")
            return None

    async def _generate_with_cerebras(self, prompt: str) -> str | None:
        """Genereaza text via Cerebras API (fallback cu Qwen 3 235B)."""
        if not settings.cerebras_api_key:
            return None

        try:
            logger.debug("[synthesis] Trying Cerebras API...")

            url = "https://api.cerebras.ai/v1/chat/completions"
            payload = {
                "model": "qwen-3-235b-a22b-instruct-2507",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            }
            headers = {
                "Authorization": f"Bearer {settings.cerebras_api_key}",
                "Content-Type": "application/json",
            }

            client = get_client()
            response = await client.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "").strip()
                if text:
                    logger.debug(f"[synthesis] Cerebras OK: {len(text.split())} words")
                    return text

            logger.warning("[synthesis] Cerebras returned empty response")
            return None

        except Exception as e:
            logger.warning(f"[synthesis] Cerebras error: {e}")
            return None


    # ── 10F M4.2: Structured Degradation 3-Tier ──────────────────────────────
    def _degraded_fallback(self, section: dict, verified_data: dict) -> str:
        """Fallback in 3 trepte cand TOTI providerii esueaza:
        Tier 1 = narativ (deja incercat si esuat)
        Tier 2 = bullet-point facts din verified_data
        Tier 3 = raw JSON extract daca nici bullet-points nu sunt posibile."""
        key = section["key"]
        title = section["title"]
        logger.warning(f"[synthesis] All providers failed for '{key}' — applying degraded fallback")

        # --- Tier 2: bullet-point facts from verified_data ---
        bullets = self._extract_bullets_for_section(key, verified_data)
        if bullets:
            header = f"**{title}** *(generat automat din date verificate — text narativ indisponibil)*\n"
            body = "\n".join(f"- {b}" for b in bullets)
            logger.info(f"[synthesis] Degraded Tier 2 for '{key}': {len(bullets)} bullet points")
            return header + body

        # --- Tier 3: B12 fix — readable key-value format instead of raw JSON ---
        raw_data = self._extract_raw_dict_for_section(key, verified_data)
        logger.info(f"[synthesis] Degraded Tier 3 for '{key}': readable data extract")
        lines = [f"**{title}** — *Indisponibil (toti providerii AI au esuat)*\n"]
        lines.append("Date disponibile din surse oficiale:\n")
        for category, values in raw_data.items():
            lines.append(f"**{category.replace('_', ' ').title()}:**")
            if isinstance(values, dict):
                for k, v in values.items():
                    val = v.get("value", v) if isinstance(v, dict) else v
                    if val is not None and val != "" and val != {}:
                        label = k.replace("_", " ").title()
                        if isinstance(val, (int, float)) and abs(val) > 1000:
                            lines.append(f"- {label}: {val:,.0f}")
                        else:
                            lines.append(f"- {label}: {val}")
            elif isinstance(values, list):
                for item in values[:5]:
                    if isinstance(item, dict):
                        summary = ", ".join(f"{k}: {v}" for k, v in list(item.items())[:3])
                        lines.append(f"- {summary}")
                    else:
                        lines.append(f"- {item}")
            lines.append("")
        return "\n".join(lines)

    def _extract_bullets_for_section(self, section_key: str, data: dict) -> list[str]:
        """Extrage bullet-point facts relevante din verified_data per section key."""
        bullets: list[str] = []

        def _v(field):
            if isinstance(field, dict):
                return field.get("value")
            return field

        company = data.get("company", {})
        financial = data.get("financial", {})
        risk_score = data.get("risk_score", {})
        market = data.get("market", {})
        legal = data.get("legal", {})
        due_diligence = data.get("due_diligence", {})

        # Common facts available for most sections
        name = _v(company.get("denumire", {}))
        cui = _v(company.get("cui", {}))
        caen = _v(company.get("caen_code", {}))
        caen_desc = _v(company.get("caen_description", {}))

        if section_key in ("executive_summary", "company_overview"):
            if name:
                bullets.append(f"Denumire: {name}")
            if cui:
                bullets.append(f"CUI: {cui}")
            if caen:
                bullets.append(f"CAEN: {caen} — {caen_desc or 'N/A'}")
            stare = _v(company.get("stare_firma", {}))
            if stare:
                bullets.append(f"Stare firma: {stare}")
            adresa = _v(company.get("adresa", {}))
            if adresa:
                bullets.append(f"Adresa: {adresa}")
            score = risk_score.get("numeric_score")
            if score is not None:
                bullets.append(f"Scor risc: {score}/100 ({risk_score.get('score', '?')})")

        if section_key in ("financial_analysis", "executive_summary"):
            ca = _v(financial.get("cifra_afaceri", {}))
            pn = _v(financial.get("profit_net", {}))
            ang = _v(financial.get("numar_angajati", {}))
            cap = _v(financial.get("capitaluri_proprii", {}))
            if ca is not None:
                bullets.append(f"Cifra de afaceri: {ca:,.0f} RON" if isinstance(ca, (int, float)) else f"CA: {ca}")
            if pn is not None:
                bullets.append(f"Profit net: {pn:,.0f} RON" if isinstance(pn, (int, float)) else f"Profit: {pn}")
            if ang is not None:
                bullets.append(f"Numar angajati: {ang}")
            if cap is not None:
                bullets.append(f"Capitaluri proprii: {cap:,.0f} RON" if isinstance(cap, (int, float)) else f"Capital: {cap}")

        if section_key == "risk_assessment":
            factors = risk_score.get("factors", [])
            for name_f, sev in factors[:10]:
                bullets.append(f"[{sev}] {name_f}")
            warnings = data.get("early_warnings", [])
            if isinstance(warnings, list):
                for w in warnings[:5]:
                    if isinstance(w, dict):
                        bullets.append(f"Early warning: {w.get('signal', w)}")
                    else:
                        bullets.append(f"Early warning: {w}")

        if section_key == "competition":
            seap = market.get("seap", {}) if isinstance(market, dict) else {}
            if isinstance(seap, dict) and seap.get("total_contracts"):
                bullets.append(f"Contracte SEAP: {seap['total_contracts']}")
            benchmark = data.get("benchmark", {})
            if isinstance(benchmark, dict):
                for k, v in benchmark.items():
                    if v is not None:
                        bullets.append(f"Benchmark {k}: {v}")

        if section_key == "legal_compliance":
            if isinstance(legal, dict):
                for k, v in legal.items():
                    val = _v(v)
                    if val is not None:
                        bullets.append(f"{k}: {val}")

        if section_key == "due_diligence":
            if isinstance(due_diligence, dict):
                checklist = due_diligence.get("checklist", [])
                if isinstance(checklist, list):
                    for item in checklist[:10]:
                        if isinstance(item, dict):
                            bullets.append(f"{item.get('name', '?')}: {item.get('status', '?')}")

        return bullets

    def _extract_raw_for_section(self, section_key: str, data: dict) -> str:
        """Extrage un subset JSON relevant din verified_data pentru fallback Tier 3."""
        # Map section keys to relevant data subtrees
        section_data_map = {
            "executive_summary": ["company", "financial", "risk_score"],
            "company_overview": ["company"],
            "financial_analysis": ["financial"],
            "risk_assessment": ["risk_score", "early_warnings"],
            "competition": ["market", "benchmark"],
            "legal_compliance": ["legal"],
            "due_diligence": ["due_diligence"],
            "swot_analysis": ["risk_score", "financial", "market"],
            "opportunities": ["market", "benchmark"],
            "recommendations": ["risk_score", "early_warnings"],
        }
        keys = section_data_map.get(section_key, ["company", "financial"])
        subset = {}
        for k in keys:
            if k in data:
                subset[k] = data[k]
        # Truncate to avoid huge output
        raw = json.dumps(subset, ensure_ascii=False, default=str, indent=2)
        if len(raw) > 3000:
            raw = raw[:3000] + "\n... [trunchiat]"
        return raw

    def _extract_raw_dict_for_section(self, section_key: str, data: dict) -> dict:
        """B12: Return raw dict subset for readable Tier 3 rendering."""
        section_data_map = {
            "executive_summary": ["company", "financial", "risk_score"],
            "company_overview": ["company"],
            "company_profile": ["company"],
            "financial_analysis": ["financial"],
            "risk_assessment": ["risk_score", "early_warnings"],
            "competition": ["market", "benchmark"],
            "legal_compliance": ["legal"],
            "due_diligence": ["due_diligence"],
            "swot_analysis": ["risk_score", "financial", "market"],
            "swot": ["risk_score", "financial", "market"],
            "opportunities": ["market", "benchmark"],
            "recommendations": ["risk_score", "early_warnings"],
        }
        keys = section_data_map.get(section_key, ["company", "financial"])
        subset = {}
        for k in keys:
            if k in data:
                subset[k] = data[k]
        return subset

    # ── 10F M4.4: Prompt Injection Hardening ───────────────────────────────
    def _sanitize_data_for_prompt(self, data: dict) -> dict:
        """Sanitizeaza verified_data pentru a preveni prompt injection.
        - Elimina backtick-uri triple (```) din valori string
        - Elimina triple-quotes din text fields
        - Escapeaza caractere de control (\\x00-\\x1f) exceptand \\n si \\t
        Returneaza o copie profunda — NU modifica originalul."""
        sanitized = copy.deepcopy(data)
        self._sanitize_recursive(sanitized)
        return sanitized

    def _sanitize_recursive(self, obj):
        """Parcurge recursiv structura si sanitizeaza toate string-urile."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str):
                    obj[k] = self._sanitize_string(v)
                elif isinstance(v, (dict, list)):
                    self._sanitize_recursive(v)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str):
                    obj[i] = self._sanitize_string(item)
                elif isinstance(item, (dict, list)):
                    self._sanitize_recursive(item)

    def _sanitize_string(self, text: str) -> str:
        """Sanitizeaza un singur string: backticks, triple-quotes, control chars."""
        # Strip triple backticks (prevents breaking out of code blocks in prompts)
        text = text.replace("```", "")
        # Strip triple quotes (prevents breaking out of string literals)
        text = text.replace('"""', "")
        text = text.replace("'''", "")
        # Escape control characters (\x00-\x1f) EXCEPT \n (\x0a) and \t (\x09)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return text

    # ── 10F M4.5: Token Budget Enforcement ─────────────────────────────────
    # Max context windows per provider (in tokens)
    _PROVIDER_MAX_CONTEXT = {
        "claude": 150_000,
        "groq": 131_000,    # D7 fix: Llama 4 Scout has 131K context
        "gemini": 1_000_000, # D8 fix: Gemini 2.5 Flash has 1M context
        "mistral": 128_000,  # Mistral Small 3 has 128K context
        "cerebras": 128_000, # Qwen 3 235B has 128K context
    }
    # Provider preference order: from largest to smallest context
    _PROVIDER_SIZE_ORDER = ["claude", "gemini", "mistral", "cerebras", "groq"]

    def _check_token_budget(self, prompt: str, provider: str) -> str:
        """Verifica daca prompt-ul incape in 70% din contextul provider-ului.
        Daca nu incape, recomanda un provider cu context mai mare.
        Returneaza provider-ul recomandat (poate fi acelasi sau altul)."""
        estimated_tokens = len(prompt) / 4  # rough estimate: 1 token ~ 4 chars
        max_ctx = self._PROVIDER_MAX_CONTEXT.get(provider, 12_000)
        threshold = max_ctx * 0.7

        if estimated_tokens <= threshold:
            return provider  # Fits fine

        logger.warning(
            f"[synthesis] Token budget exceeded for {provider}: "
            f"~{int(estimated_tokens)} tokens > {int(threshold)} (70% of {max_ctx}). "
            f"Searching for larger provider..."
        )

        # Find a provider with enough capacity
        for candidate in self._PROVIDER_SIZE_ORDER:
            candidate_max = self._PROVIDER_MAX_CONTEXT.get(candidate, 12_000)
            if estimated_tokens <= candidate_max * 0.7:
                logger.info(f"[synthesis] Token budget: switching {provider} -> {candidate}")
                return candidate

        # None fit perfectly — use the largest available (claude)
        logger.warning(
            f"[synthesis] Token budget: prompt too large for all providers "
            f"(~{int(estimated_tokens)} tokens). Using claude as largest context."
        )
        return "claude"

    def _build_context_summary(self, section_key: str, data: dict) -> str:
        """8C: Genereaza un rezumat structurat al datelor relevante per sectiune."""
        lines = []
        company = data.get("company", {})
        financial = data.get("financial", {})
        risk_score = data.get("risk_score", {})
        completeness = data.get("completeness", {})

        def _v(field):
            if isinstance(field, dict):
                return field.get("value")
            return field

        # Common context
        name = _v(company.get("denumire", {}))
        cui = _v(company.get("cui", {}))
        caen = _v(company.get("caen_code", {}))
        caen_desc = _v(company.get("caen_description", {}))
        if name:
            lines.append(f"Firma: {name} (CUI: {cui or 'N/A'})")
        if caen:
            lines.append(f"CAEN: {caen} — {caen_desc or 'N/A'}")
        lines.append(f"Scor risc: {risk_score.get('numeric_score', '?')}/100 ({risk_score.get('score', '?')})")
        lines.append(f"Completitudine date: {completeness.get('score', '?')}%")

        if section_key in ("financial_analysis", "executive_summary"):
            ca = _v(financial.get("cifra_afaceri", {}))
            pn = _v(financial.get("profit_net", {}))
            ang = _v(financial.get("numar_angajati", {}))
            cap = _v(financial.get("capitaluri_proprii", {}))
            if ca is not None:
                lines.append(f"CA: {ca:,.0f} RON" if isinstance(ca, (int, float)) else f"CA: {ca}")
            if pn is not None:
                lines.append(f"Profit net: {pn:,.0f} RON" if isinstance(pn, (int, float)) else f"Profit: {pn}")
            if ang is not None:
                lines.append(f"Angajati: {ang}")
            if cap is not None:
                lines.append(f"Capitaluri proprii: {cap:,.0f} RON" if isinstance(cap, (int, float)) else f"Capital: {cap}")

        if section_key == "risk_assessment":
            factors = risk_score.get("factors", [])
            if factors:
                lines.append(f"Risk factors ({len(factors)}):")
                for name_f, sev in factors[:8]:
                    lines.append(f"  [{sev}] {name_f}")

        if section_key == "competition":
            market = data.get("market", {})
            seap = market.get("seap", {}) if isinstance(market, dict) else {}
            if isinstance(seap, dict):
                lines.append(f"Contracte SEAP: {seap.get('total_contracts', 0)}")

        return "\n".join(lines) if lines else "Fara context suplimentar disponibil."


synthesis_agent = SynthesisAgent()
