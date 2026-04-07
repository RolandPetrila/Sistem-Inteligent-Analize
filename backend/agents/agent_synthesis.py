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
from backend.agents.circuit_breaker import (
    is_provider_circuit_open,
    record_provider_failure,
    reset_provider_circuit,
)
from backend.agents.state import AnalysisState
from backend.config import settings
from backend.http_client import get_client
from backend.prompts.section_prompts import get_sections_for_analysis
from backend.prompts.system_prompt import SYSTEM_PROMPT


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

            # ER2: Skip AI generation if section has insufficient data
            if not self._has_sufficient_data(key, verified_data):
                logger.warning(f"[synthesis] Section {key}: insufficient data, using fallback")
                report_sections[key] = {
                    "title": title,
                    "content": (
                        f"Sectiunea '{title}' nu a putut fi generata din cauza datelor insuficiente "
                        f"disponibile in sursele publice consultate. Pentru o analiza completa, "
                        f"sunt necesare date suplimentare care nu au fost identificate in sursele accesate. "
                        f"Se recomanda obtinerea acestor informatii direct de la companie."
                    ),
                    "word_count": 0,
                }
                continue

            # 8C: Provider routing per section type (overrides simple word-based routing)
            route = section.get("route_preference", "quality")
            if word_target <= 200:
                route = "fast"
            logger.info(f"[synthesis] Section {i+1}/{total}: {title} ({word_target}w, route={route})")

            if route == "fast":
                # B9 fix: Fast route — speed priority: Groq → concurrent fallback (Cerebras+Mistral+Gemini)
                # 10F M4.5: Token Budget Enforcement — check if prompt fits provider context
                # FIX #30: Build prompt once, reuse for token check + generation
                initial_provider = "groq"
                prompt = self._build_section_prompt(section, verified_data, initial_provider)
                initial_provider = self._check_token_budget(prompt, initial_provider)

                if initial_provider == "groq":
                    text = await self._generate_with_groq(prompt)
                else:
                    text = None

                # FIX #9: After primary failure, launch remaining providers concurrently
                if not text:
                    text = await self._concurrent_fallback(
                        section, verified_data,
                        providers=["cerebras", "mistral", "gemini"],
                    )
            else:
                # B9 fix: Quality route — quality priority: Claude → concurrent fallback (Gemini+Groq+Mistral)
                # 10F M4.5: Token Budget Enforcement
                # FIX #30: Build prompt once, reuse for token check + generation
                initial_provider = "claude"
                prompt = self._build_section_prompt(section, verified_data, initial_provider)
                initial_provider = self._check_token_budget(prompt, initial_provider)

                if initial_provider == "claude":
                    text = await self._generate_with_claude(prompt)
                else:
                    text = None

                # FIX #9: After primary failure, launch remaining providers concurrently
                if not text:
                    text = await self._concurrent_fallback(
                        section, verified_data,
                        providers=["gemini", "groq", "mistral"],
                    )

            if not text:
                text = await self._generate_with_cerebras(
                    self._build_section_prompt(section, verified_data, "cerebras"))
            # 10F M4.2: Structured Degradation 3-Tier
            if not text:
                text = self._degraded_fallback(section, verified_data)

            # 10B M4.1: Output Validation — check for invented data, impossible stats
            text = self._validate_output(text, verified_data, section)

            # ER1: Verify numbers in generated text against verified_data
            is_ok, discrepancies = self._verify_numbers_in_text(text, verified_data, key)
            if not is_ok and len(discrepancies) > 2:
                logger.warning(f"[synthesis] Section {key}: {len(discrepancies)} number discrepancies, adding note")
                text += "\n\n[Nota: Verificati cifrele din aceasta sectiune cu sursele primare.]"

            report_sections[key] = {
                "title": title,
                "content": text,
                "word_count": len(text.split()),
            }

        # 10B M4.3: Cross-Section Coherence — verify consistency between sections
        report_sections = self._check_cross_section_coherence(report_sections, verified_data)

        # F2-15: Generate 3 key takeaways from the full report
        full_report_text = "\n\n".join(
            f"{s['title']}:\n{s['content']}"
            for s in report_sections.values()
            if s.get("content")
        )
        key_takeaways = await self._generate_key_takeaways(full_report_text)

        logger.info(f"[synthesis] Done: {len(report_sections)}/{total} sections generated")

        return {
            "report_sections": report_sections,
            "key_takeaways": key_takeaways,
            "current_step": f"Sinteza completa: {len(report_sections)} sectiuni",
            "progress": 0.75,
        }

    async def _generate_key_takeaways(self, full_report_text: str) -> str:
        """F2-15: Genereaza 3 concluzii cheie pe baza raportului complet. Foloseste Groq (provider rapid)."""
        prompt = f"""Analizeaza raportul urmator si genereaza exact 3 concluzii cheie.

Raport (extras):
{full_report_text[:3000]}

Format OBLIGATORIU (exact 3 bullets, nu mai mult, nu mai putin):
\u2022 [Concluzie 1 \u2014 max 20 cuvinte, specific si actionabil, incepe cu un fapt concret]
\u2022 [Concluzie 2 \u2014 max 20 cuvinte, specific si actionabil]
\u2022 [Concluzie 3 \u2014 max 20 cuvinte, orientat spre decizie]

Reguli:
- Fiecare bullet incepe cu un fapt numeric sau o constatare concreta
- NU repeta informatii evidente sau generale
- Orientat spre decizie: ce ar trebui sa stie un decident
- Limba: Romana
- NU adauga alt text in afara de cele 3 bullets"""

        try:
            result = await self._generate_with_groq(prompt)
            if result:
                return result.strip()
        except Exception as e:
            logger.warning(f"[synthesis] Key takeaways Groq failed: {e}")

        try:
            result = await self._generate_with_gemini(prompt)
            if result:
                return result.strip()
        except Exception as e:
            logger.warning(f"[synthesis] Key takeaways generation failed: {e}")

        return ""

    def _estimate_prompt_tokens(self, data: dict, word_target: int) -> int:
        """Pre-check: estimate token count before building the full prompt.
        Formula: base_tokens(500) + data_chars/4 + word_target*2.
        Useful for early budget checks before expensive prompt construction."""
        data_chars = len(json.dumps(data, ensure_ascii=False, default=str))
        return 500 + data_chars // 4 + word_target * 2

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
                if found_cui != input_cui:
                    logger.warning(f"[synthesis] Stripping invented CUI: {found_cui} (expected {input_cui})")
                    text = text.replace(found_cui, input_cui)

        # AH-04: Detect invented competitor names in competition section
        if section.get("key") == "competition":
            web = verified_data.get("web_presence", {})
            known_names = set()
            if isinstance(web, dict):
                comps = web.get("competitors", {})
                if isinstance(comps, dict):
                    for r in comps.get("results", []):
                        name = r.get("name", "") or r.get("title", "")
                        if name:
                            known_names.add(name.lower().strip())
            if known_names:
                # Find quoted company names in text that aren't known
                quoted = re.findall(r'"([A-Z][A-Za-z\s&.\-]+(?:S\.?R\.?L\.?|S\.?A\.?))"', text)
                for name in quoted:
                    if name.lower().strip() not in known_names and name.lower() != input_name.lower():
                        logger.warning(f"[synthesis] Unverified competitor: '{name}' — marking")
                        text = text.replace(f'"{name}"', f'"{name}" [NEVERIFICAT]')

        # Word count check
        word_count = len(text.split())
        target = section.get("word_count", 300)
        if word_count < target * 0.3 and target > 100:
            logger.warning(f"[synthesis] Section '{section['key']}' too short: {word_count}/{target} words")

        return text

    def _check_numeric_coherence(self, sections: dict) -> list:
        """F3-6: Detecteaza discrepante numerice majore intre sectiuni.
        Extrage valori CA mentionate si verifica daca difera cu mai mult de 2.5x."""
        warnings_out = []
        ca_mentions = []

        # Extrage valori numerice mentionate ca "milioane RON" sau "mil. RON" sau "M RON"
        for section_key, content_dict in sections.items():
            if not isinstance(content_dict, dict):
                continue
            content = content_dict.get("content", "")
            if not isinstance(content, str):
                continue
            mil_matches = re.findall(
                r'(\d+(?:[.,]\d+)?)\s*(?:milioane|mil\.|M)\s*RON',
                content,
                re.IGNORECASE,
            )
            for m in mil_matches:
                try:
                    val = float(m.replace(",", "."))
                    ca_mentions.append((section_key, val))
                except ValueError:
                    pass

        if len(ca_mentions) >= 2:
            values = [v for _, v in ca_mentions]
            max_v = max(values)
            min_v = min(values)
            if min_v > 0 and max_v / min_v > 2.5:
                warnings_out.append(
                    f"Discrepanta CA detectata intre sectiuni: {min_v:.1f}M vs {max_v:.1f}M RON — verificati datele"
                )

        return warnings_out

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

        # F3-6: Numeric coherence check — detect CA discrepancies between sections
        coherence_warnings = self._check_numeric_coherence(sections)
        if coherence_warnings:
            logger.warning(f"[synthesis] Numeric coherence warnings: {coherence_warnings}")
            # Append warnings as a note in executive_summary if it exists
            if "executive_summary" in sections and isinstance(sections["executive_summary"].get("content"), str):
                sections["executive_summary"]["content"] += (
                    "\n\n*[Nota sistem: " + "; ".join(coherence_warnings) + "]*"
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
        except (TimeoutError, subprocess.TimeoutExpired):
            logger.warning("[synthesis] Claude Code timeout — falling back to Gemini")
            return None
        except Exception as e:
            logger.warning(f"[synthesis] Claude Code error: {e}")
            return None

    # F14: DRY provider config — OpenAI-compatible providers
    _PROVIDERS = {
        "groq": {
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "api_key_attr": "groq_api_key",
        },
        "mistral": {
            "url": "https://api.mistral.ai/v1/chat/completions",
            "model": "mistral-small-latest",
            "api_key_attr": "mistral_api_key",
        },
        "cerebras": {
            "url": "https://api.cerebras.ai/v1/chat/completions",
            "model": "qwen-3-235b-a22b-instruct-2507",
            "api_key_attr": "cerebras_api_key",
        },
        # F7.2: DeepSeek R1 — financial reasoning specialist
        "deepseek": {
            "url": "https://api.deepseek.com/chat/completions",
            "model": "deepseek-reasoner",
            "api_key_attr": "deepseek_api_key",
        },
        # F7.6: OpenRouter — unified gateway (free :free models)
        "openrouter": {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "model": "deepseek/deepseek-r1:free",
            "api_key_attr": "openrouter_api_key",
        },
        # R6: GitHub Models — GPT-4.1 + Llama 4 Scout gratuit (50-150 req/zi)
        "github": {
            "url": "https://models.inference.ai.azure.com/chat/completions",
            "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "api_key_attr": "github_token",
        },
        # R6: Fireworks AI — Llama 4 Scout/Maverick (10 RPM permanent free)
        "fireworks": {
            "url": "https://api.fireworks.ai/inference/v1/chat/completions",
            "model": "accounts/fireworks/models/llama4-scout-instruct-basic",
            "api_key_attr": "fireworks_api_key",
        },
        # R6: SambaNova — Llama 3.1 405B GRATUIT (unic in industrie, 10 RPM)
        "sambanova": {
            "url": "https://api.sambanova.ai/v1/chat/completions",
            "model": "Meta-Llama-3.1-405B-Instruct",
            "api_key_attr": "sambanova_api_key",
        },
    }

    async def _generate_with_openai_compat(self, prompt: str, provider: str) -> str | None:
        """F14: Generic OpenAI-compatible API call (Groq, Mistral, Cerebras)."""
        # R2 Fix #2: Circuit breaker — skip provider if repeatedly failing
        if is_provider_circuit_open(provider):
            logger.info(f"[synthesis] {provider} circuit OPEN, skipping")
            return None

        cfg = self._PROVIDERS.get(provider)
        if not cfg:
            return None
        api_key = getattr(settings, cfg["api_key_attr"], "")
        if not api_key:
            return None

        try:
            logger.debug(f"[synthesis] Trying {provider.capitalize()} API...")
            payload = {
                "model": cfg["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            client = get_client()
            response = await client.post(cfg["url"], json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "").strip()
                if text:
                    logger.debug(f"[synthesis] {provider.capitalize()} OK: {len(text.split())} words")
                    reset_provider_circuit(provider)
                    return text

            logger.warning(f"[synthesis] {provider.capitalize()} returned empty response")
            record_provider_failure(provider)
            return None
        except Exception as e:
            logger.warning(f"[synthesis] {provider.capitalize()} error: {e}")
            record_provider_failure(provider)
            return None

    async def _generate_with_groq(self, prompt: str) -> str | None:
        return await self._generate_with_openai_compat(prompt, "groq")

    async def _generate_with_mistral(self, prompt: str) -> str | None:
        return await self._generate_with_openai_compat(prompt, "mistral")

    async def _generate_with_cerebras(self, prompt: str) -> str | None:
        return await self._generate_with_openai_compat(prompt, "cerebras")

    async def _generate_with_deepseek(self, prompt: str) -> str | None:
        """F7.2: DeepSeek R1 — strips <think> reasoning block before returning."""
        result = await self._generate_with_openai_compat(prompt, "deepseek")
        if result:
            # R1 wraps chain-of-thought in <think>...</think> — strip for clean output
            result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()
        return result or None

    async def _generate_with_openrouter(self, prompt: str) -> str | None:
        """F7.6: OpenRouter gateway — adds required headers for routing."""
        if is_provider_circuit_open("openrouter"):
            return None
        cfg = self._PROVIDERS["openrouter"]
        api_key = getattr(settings, cfg["api_key_attr"], "")
        if not api_key:
            return None
        try:
            client = get_client()
            response = await client.post(
                cfg["url"],
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "http://localhost:8001",
                    "X-Title": "RIS - Roland Intelligence System",
                },
                json={
                    "model": cfg["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "").strip()
                if text:
                    logger.debug(f"[synthesis] OpenRouter OK: {len(text.split())} words")
                    reset_provider_circuit("openrouter")
                    return text
            record_provider_failure("openrouter")
            return None
        except Exception as e:
            logger.warning(f"[synthesis] OpenRouter error: {e}")
            record_provider_failure("openrouter")
            return None

    async def _generate_with_github(self, prompt: str) -> str | None:
        """R6: GitHub Models — Llama 4 Scout via Azure inference endpoint."""
        return await self._generate_with_openai_compat(prompt, "github")

    async def _generate_with_fireworks(self, prompt: str) -> str | None:
        """R6: Fireworks AI — Llama 4 Scout (10 RPM permanent free)."""
        return await self._generate_with_openai_compat(prompt, "fireworks")

    async def _generate_with_sambanova(self, prompt: str) -> str | None:
        """R6: SambaNova Cloud — Llama 3.1 405B (only free 405B in industry)."""
        return await self._generate_with_openai_compat(prompt, "sambanova")

    async def _generate_with_gemini(self, prompt: str) -> str | None:
        """Gemini uses a different API format (not OpenAI-compatible)."""
        # R2 Fix #2: Circuit breaker for Gemini
        if is_provider_circuit_open("gemini"):
            logger.info("[synthesis] Gemini circuit OPEN, skipping")
            return None
        if not settings.google_ai_api_key:
            logger.warning("[synthesis] No GOOGLE_AI_API_KEY — cannot use Gemini fallback")
            return None

        try:
            logger.debug("[synthesis] Trying Gemini Flash API...")
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.5-flash:generateContent?key={settings.google_ai_api_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
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
                        reset_provider_circuit("gemini")
                        return text

            logger.warning("[synthesis] Gemini returned empty response")
            record_provider_failure("gemini")
            return None
        except Exception as e:
            import re as _re
            err_msg = _re.sub(r'key=[A-Za-z0-9_\-]+', 'key=***REDACTED***', str(e))
            logger.warning(f"[synthesis] Gemini error: {err_msg}")
            record_provider_failure("gemini")
            return None


    async def _concurrent_fallback(
        self, section: dict, verified_data: dict, providers: list[str]
    ) -> str | None:
        """FIX #9: Launch multiple providers concurrently, return first successful result.
        Uses asyncio.wait(FIRST_COMPLETED) with 30s timeout."""
        _provider_methods = {
            "groq": self._generate_with_groq,
            "gemini": self._generate_with_gemini,
            "mistral": self._generate_with_mistral,
            "cerebras": self._generate_with_cerebras,
            "deepseek": self._generate_with_deepseek,        # F7.2
            "openrouter": self._generate_with_openrouter,    # F7.6
            "github": self._generate_with_github,            # R6: GitHub Models (free)
            "fireworks": self._generate_with_fireworks,      # R6: Fireworks AI (free)
            "sambanova": self._generate_with_sambanova,      # R6: SambaNova 405B (free)
        }

        # Filter out providers with open circuit breakers
        active = [p for p in providers if not is_provider_circuit_open(p)]
        if not active:
            logger.warning("[synthesis] _concurrent_fallback: all provider circuits open")
            return None

        tasks = {
            asyncio.create_task(
                _provider_methods[p](self._build_section_prompt(section, verified_data, p))
            ): p
            for p in active
            if p in _provider_methods
        }
        if not tasks:
            return None

        try:
            done, pending = await asyncio.wait(
                tasks.keys(), return_when=asyncio.FIRST_COMPLETED, timeout=30
            )
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

            for task in done:
                exc = task.exception()
                if exc is None:
                    result = task.result()
                    if result:
                        provider_name = tasks[task]
                        reset_provider_circuit(provider_name)
                        logger.info(f"[synthesis] Concurrent fallback winner: {provider_name}")
                        return result
                else:
                    provider_name = tasks[task]
                    logger.warning(f"[synthesis] Concurrent fallback {provider_name} error: {exc}")
                    record_provider_failure(provider_name)
        except Exception as e:
            logger.warning(f"[synthesis] Concurrent fallback failed: {e}")

        return None

    # ── 10F M4.2: Structured Degradation 3-Tier ──────────────────────────────
    def _verify_numbers_in_text(self, text: str, verified_data: dict, section_key: str) -> tuple[bool, list[str]]:
        """ER1: Verify numbers in AI-generated text against verified_data.
        Returns (is_ok, list_of_discrepancies)."""
        if not text:
            return True, []

        # F10: Skip sections with computed/derived numbers (SWOT, recommendations)
        # AH-01: financial_analysis NO LONGER skipped — ratios must be validated
        skip_sections = {"swot_analysis", "recommendations", "opportunities"}
        if section_key in skip_sections:
            return True, []

        # Extract numbers with units from text
        pattern = r'(\d[\d.,]*)\s*(RON|EUR|lei|mii|mil|M|K|%)'
        matches = re.findall(pattern, text)
        if not matches:
            return True, []

        # Build set of known numbers from verified_data
        known_numbers = set()
        def _collect_numbers(obj, depth=0):
            if depth > 4:
                return
            if isinstance(obj, (int, float)) and obj != 0:
                known_numbers.add(abs(obj))
            elif isinstance(obj, dict):
                for v in obj.values():
                    _collect_numbers(v, depth + 1)
            elif isinstance(obj, list):
                for v in obj[:20]:
                    _collect_numbers(v, depth + 1)
        _collect_numbers(verified_data)

        discrepancies = []
        for num_str, unit in matches:
            try:
                # Parse number: handle both 11,950,149 and 6.06 formats
                clean = num_str.replace(",", "")
                num = float(clean)
            except ValueError:
                continue
            # Skip percentages (derived calculations — not raw data)
            if unit == "%":
                continue
            # Skip small numbers (<1000) and calendar years (2014-2030)
            if num < 1000 or 2014 <= num <= 2030:
                continue
            # Check if number exists in known data (within +-15%)
            found = any(
                abs(num - known) / max(known, 1) < 0.15
                for known in known_numbers if known > 0
            )
            if not found:
                discrepancies.append(f"{num_str} {unit}")

        is_ok = len(discrepancies) <= 3
        return is_ok, discrepancies

    def _has_sufficient_data(self, section_key: str, verified_data: dict) -> bool:
        """ER2: Check if section has enough data to generate meaningful content.
        AH-02: executive_summary/recommendations blocked if completeness < 30%."""
        # AH-02: Check overall completeness score — if very low, block even meta sections
        completeness = verified_data.get("completeness", {})
        completeness_score = completeness.get("score", 100) if isinstance(completeness, dict) else 100

        if section_key in ("executive_summary", "risk_assessment", "swot", "recommendations"):
            if completeness_score < 30:
                logger.warning(f"[synthesis] {section_key}: completeness={completeness_score}% < 30% — blocking generation")
                return False
            return True

        if section_key == "financial_analysis":
            fin = verified_data.get("financial", {})
            non_null = 0
            for k in ("cifra_afaceri", "profit_net", "numar_angajati", "capitaluri_proprii"):
                field = fin.get(k, {})
                if isinstance(field, dict) and field.get("value") is not None:
                    non_null += 1
            return non_null >= 2

        if section_key == "competition":
            web = verified_data.get("web_presence", {})
            if isinstance(web, dict):
                comps = web.get("competitors", {})
                if isinstance(comps, dict) and len(comps.get("results", [])) >= 1:
                    return True
            return False

        if section_key == "opportunities":
            market = verified_data.get("market", {})
            if isinstance(market, dict):
                seap = market.get("seap", {})
                if isinstance(seap, dict) and seap.get("total_contracts", 0) > 0:
                    return True
            web = verified_data.get("web_presence", {})
            if isinstance(web, dict) and web.get("opportunities"):
                return True
            return False

        if section_key == "company_profile":
            company = verified_data.get("company", {})
            non_null = 0
            for field in company.values():
                if isinstance(field, dict) and field.get("value") is not None:
                    non_null += 1
            return non_null >= 3

        return True  # Default: allow generation

    def _degraded_fallback(self, section: dict, verified_data: dict) -> str:
        """Fallback in 3 trepte cand TOTI providerii esueaza:
        Tier 1 = narativ (deja incercat si esuat)
        Tier 2 = bullet-point facts din verified_data
        Tier 3 = raw JSON extract daca nici bullet-points nu sunt posibile."""
        key = section["key"]
        title = section["title"]
        # SYNTH-02: Log which providers were attempted (all 5 must have failed to reach here)
        providers_attempted = ["Claude CLI", "Gemini", "Groq", "Mistral", "Cerebras"]
        logger.warning(
            f"[synthesis] ALL providers failed for '{key}': {', '.join(providers_attempted)}"
        )

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
