"""
SynthesisProvidersMixin — Provider methods pentru SynthesisAgent.
Extrase din agent_synthesis.py pentru a reduce dimensiunea fisierului principal.

Contine:
- _PROVIDERS config dict (OpenAI-compatible providers)
- _generate_with_claude / _generate_with_openai_compat
- _generate_with_groq/mistral/cerebras/deepseek/openrouter/github/fireworks/sambanova
- _generate_with_gemini
- _concurrent_fallback
"""

import asyncio
import re
import subprocess

from loguru import logger

from backend.agents.circuit_breaker import (
    is_provider_circuit_open,
    record_provider_failure,
    reset_provider_circuit,
)
from backend.config import settings
from backend.http_client import get_client


class SynthesisProvidersMixin:
    """Mixin cu toti providerii AI pentru SynthesisAgent."""

    async def _generate_with_claude(self, prompt: str) -> str | None:
        """Genereaza text via Claude Code CLI subprocess."""
        if settings.synthesis_mode != "claude_code":
            return None

        try:
            logger.debug("[synthesis] Trying Claude Code CLI...")
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
        if is_provider_circuit_open("gemini"):
            logger.info("[synthesis] Gemini circuit OPEN, skipping")
            return None
        if not settings.google_ai_api_key:
            logger.warning("[synthesis] No GOOGLE_AI_API_KEY — cannot use Gemini fallback")
            return None

        try:
            logger.debug("[synthesis] Trying Gemini Flash API...")
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
            }
            client = get_client()
            response = await client.post(
                url,
                json=payload,
                headers={"x-goog-api-key": settings.google_ai_api_key},
                timeout=60,
            )
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
            "deepseek": self._generate_with_deepseek,
            "openrouter": self._generate_with_openrouter,
            "github": self._generate_with_github,
            "fireworks": self._generate_with_fireworks,
            "sambanova": self._generate_with_sambanova,
        }

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
