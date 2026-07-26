"""
SynthesisProvidersMixin — Provider methods pentru SynthesisAgent.
Extrase din agent_synthesis.py pentru a reduce dimensiunea fisierului principal.

Numele de modele + limitele NU mai sunt aici — sunt in `backend/agents/ai_models.py`
(sursa unica, verificata live GET /v1/models). Aici e DOAR logica de apel + garzile de
durabilitate:
- §3 detectie model disparut (404/model_not_found) -> provider INDISPONIBIL pe sesiune
- §4 garda de context -> sare providerul daca promptul > 90% din max_context
- §5 canar pe cota (429) -> logat distinct, NU tratat ca esec de continut (fara circuit)

Contine:
- _PROVIDERS = alias la ai_models.AI_PROVIDERS (settings.py + reflexion citesc de aici)
- _generate_with_claude / _generate_with_openai_compat (+ garzile de mai sus)
- _generate_with_groq/mistral/cerebras/openrouter/sambanova
- _generate_with_gemini
- _sequential_fallback (lant ORDONAT — ordinea e reala, nu concurenta)
"""

import asyncio
import os
import subprocess

from loguru import logger

from backend.agents import ai_models
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

        # settings.claude_cli_path: cale absoluta optionala (vezi config.py pt motiv —
        # PATH-ul serviciului Windows e cachet de SCM la boot). Gol = comportament
        # vechi neschimbat ("claude" cautat in PATH-ul procesului curent).
        claude_cmd = settings.claude_cli_path or "claude"
        # Effort + timeout din .env (config.py), NU hardcodate. Masurat live 2026-07-17:
        # --effort max = 252s/sectiune, high = 143s. Vechiul timeout hardcodat de 180s
        # taia MEREU Claude sub --effort max -> fallback tacut (Claude nu scria nimic).
        effort = settings.synthesis_effort or "max"
        sub_timeout = settings.synthesis_claude_timeout
        # $0 GARANTAT prin abonamentul Max: fortam subprocesul pe login-ul Max
        # (~/.claude/.credentials.json), NICIODATA pe ANTHROPIC_API_KEY (care ar consuma
        # bani reali prin API). Serviciul RIS-Backend ruleaza ca ALIENWARE si MOSTENESTE
        # ANTHROPIC_API_KEY din env var-ul Windows la nivel de User (verificat prezent
        # 2026-07-17) — daca l-am lasa, Claude CLI l-ar prefera si ar factura. Decizia lui
        # Roland: fara API key, doar Max. Nu atingem env var-ul global, doar mediul copilului.
        child_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        try:
            logger.debug(f"[synthesis] Trying Claude Code CLI ({claude_cmd}, --effort {effort}, timeout {sub_timeout}s)...")
            import sys
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            # 2026-07-17: promptul NU se mai paseaza ca argument de linie de comanda
            # ("-p", prompt) — Windows CreateProcess taie linia de comanda la ~32.767
            # caractere (ERROR_FILENAME_EXCED_RANGE / WinError 206), iar Python il ridica
            # drept FileNotFoundError (identic cu executabil lipsa), mascand root cause-ul.
            # Prompturile RIS reale au 20.000-28.000+ caractere si loveau garantat limita.
            # Fix dovedit live: promptul trece prin stdin (input=), nu prin argv.
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        [
                            claude_cmd,
                            "--print",
                            "--model", ai_models.get_model("claude"),
                            "--effort", effort,
                        ],
                        input=prompt,
                        capture_output=True,
                        text=True,
                        timeout=sub_timeout,
                        encoding="utf-8",
                        env=child_env,
                        creationflags=creation_flags,
                    ),
                ),
                timeout=sub_timeout + 20,
            )
            if result.returncode == 0 and result.stdout.strip():
                text = result.stdout.strip()
                logger.debug(f"[synthesis] Claude Code OK: {len(text.split())} words")
                return text
            else:
                stderr = result.stderr[:200] if result.stderr else ""
                logger.warning(f"[synthesis] Claude Code failed: rc={result.returncode} {stderr}")
                return None
        except FileNotFoundError as e:
            # WinError 2 (executabil/cale inexistenta) SI WinError 206 (linie de comanda
            # prea lunga) ajung AMANDOUA aici ca FileNotFoundError pe Windows — fara
            # distinctie explicita, mesajul vechi ("not found") mintea cand cauza reala
            # era lungimea liniei de comanda (asa a fost mascat bug-ul de mai sus ore intregi).
            winerror = getattr(e, "winerror", None)
            if winerror == 206:
                logger.warning(
                    f"[synthesis] Claude Code: linie de comanda prea lunga (WinError 206) — "
                    f"promptul are {len(prompt)} caractere. Windows limiteaza linia de comanda "
                    "la ~32.767 caractere. Daca vezi asta, promptul a ajuns din nou in argv "
                    "in loc de stdin (input=) — verifica ca nimeni nu a reintrodus '-p prompt'."
                )
            else:
                logger.warning(
                    f"[synthesis] Claude CLI not found at '{claude_cmd}' — falling back to Gemini. "
                    "Daca serviciul Windows nu vede PATH-ul actualizat (Service Control Manager "
                    "cacheaza PATH la boot), seteaza CLAUDE_CLI_PATH in .env cu calea absoluta "
                    "catre claude.exe (nu necesita restart de PATH)."
                )
            return None
        except (TimeoutError, subprocess.TimeoutExpired):
            logger.warning("[synthesis] Claude Code timeout — falling back to Gemini")
            return None
        except Exception as e:
            logger.warning(f"[synthesis] Claude Code error: {e}")
            return None

    # Sursa UNICA a configului de provideri: backend/agents/ai_models.py (nume verificate
    # live GET /v1/models). Alias pastrat pt compatibilitate — settings.py::test/{service}
    # citeste `SynthesisProvidersMixin._PROVIDERS["mistral"|"cerebras"]` (url/model/api_key_attr).
    # ZERO nume de model hardcodate aici (regula E1). Providerii morti (github/fireworks/
    # deepseek-native) au fost eliminati — erau in niciun lant, cu modele retrase.
    _PROVIDERS = ai_models.AI_PROVIDERS

    def _log_provider_outcome(self, provider: str, model: str, status: int, body: str, headers) -> str:
        """§3/§4/§5: clasifica un raspuns HTTP de EROARE si logheaza DISTINCT (nu un except
        generic care ascunde totul). Returneaza outcome; efecte laterale per categorie:
          gone     -> marcheaza providerul INDISPONIBIL pe sesiune (§3) — nu se mai reapeleaza
          quota    -> logheaza retry-after/x-ratelimit; NU e esec de continut (§5) — fara circuit
          payment  -> credit PLATIT epuizat (§5b); NU e esec de continut, NU e cota — fara circuit
          overflow -> logheaza; problema de dimensiune, nu de provider (§4 runtime) — fara circuit
          fail     -> caller-ul decide record_provider_failure (esec real, tranzitoriu)
        Doar "fail" duce la record_provider_failure (la call-site) — restul sunt fallback curat.
        """
        outcome = ai_models.classify_http_error(status, body)
        if outcome == "gone":
            ai_models.mark_unavailable(provider, model)
            logger.warning(f"[ai] {provider} model {model} INDISPONIBIL — retras? (HTTP {status})")
        elif outcome == "quota":
            # M1b: statusul REAL, nu "(429)" hardcodat — un marker de cota poate veni si pe
            # alt status decat 429; un log care afirma un status pe care nu l-a vazut minte.
            rate = ai_models.extract_rate_limit_info(headers)
            logger.warning(
                f"[ai] {provider} COTA EPUIZATA (HTTP {status}) — fallback." + (f" {rate}" if rate else "")
            )
        elif outcome == "payment":
            # M1: credit PLATIT epuizat (ex. 402 "Insufficient Balance"). Distinct de cota si de
            # esecul generic; NU declanseaza record_provider_failure (numai "fail" o face la
            # call-site) — fallback curat la urmatorul provider, cu semnal truthful.
            logger.warning(
                f"[ai] {provider} CREDIT/PLATA EPUIZAT (HTTP {status}) — fallback, fara circuit"
            )
        elif outcome == "overflow":
            logger.warning(f"[ai] {provider} context depasit la RUNTIME (HTTP {status}) — sar providerul")
        else:
            logger.warning(f"[ai] {provider} HTTP {status}: {(body or '')[:200]}")
        return outcome

    async def _generate_with_openai_compat(
        self, prompt: str, provider: str, extra_headers: dict | None = None
    ) -> str | None:
        """Apel generic OpenAI-compatible cu garzile de durabilitate §3/§4/§5.
        Returneaza textul sau None (None = sari providerul; motivul e logat distinct)."""
        # §3: provider marcat INDISPONIBIL pe sesiune (model retras) -> sar fara apel.
        # WARNING (nu info): marcajul persista pe proces pana la restart -> daca un model e
        # retras, vrem semnal RECURENT in ris_runtime.log (WARNING+), nu tacere dupa primul.
        if ai_models.is_unavailable(provider):
            logger.warning(f"[ai] {provider} INDISPONIBIL pe sesiune — sar (nu reapelez modelul retras)")
            return None

        if is_provider_circuit_open(provider):
            logger.info(f"[synthesis] {provider} circuit OPEN, skipping")
            return None

        cfg = self._PROVIDERS.get(provider)
        if not cfg:
            return None
        api_key = getattr(settings, cfg["api_key_attr"], "") if cfg.get("api_key_attr") else ""
        if not api_key:
            return None

        # §4: garda de context — sari providerul daca promptul > 90% din max_context
        over, est, limit = ai_models.exceeds_context(provider, prompt)
        if over:
            logger.warning(
                f"[ai] {provider} sarit — prompt {est} tokeni > limita {limit} "
                f"(90% din {ai_models.get_max_context(provider)})"
            )
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
            if extra_headers:
                headers.update(extra_headers)
            client = get_client()
            req_timeout = 90 if provider == "openrouter" else 60
            response = await client.post(cfg["url"], json=payload, headers=headers, timeout=req_timeout)

            if response.status_code >= 400:
                outcome = self._log_provider_outcome(
                    provider, cfg["model"], response.status_code, response.text, response.headers
                )
                if outcome == "fail":
                    record_provider_failure(provider)
                return None

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

    async def _generate_with_openrouter(self, prompt: str) -> str | None:
        """OpenRouter gateway — adauga headerele de routing; garzile §3/§4/§5 vin din compat."""
        return await self._generate_with_openai_compat(
            prompt,
            "openrouter",
            extra_headers={
                "HTTP-Referer": "http://localhost:8001",
                "X-Title": "RIS - Roland Intelligence System",
            },
        )

    async def _generate_with_sambanova(self, prompt: str) -> str | None:
        """SambaNova Cloud — bonus temporar (ai_models: temporary_free=True)."""
        return await self._generate_with_openai_compat(prompt, "sambanova")

    async def _generate_with_gemini(self, prompt: str) -> str | None:
        """Gemini — format API diferit (nu OpenAI-compatible). Garzile §3/§4/§5 la fel;
        modelul + URL-ul vin din ai_models (zero hardcodare)."""
        provider = "gemini"
        if ai_models.is_unavailable(provider):
            logger.warning(f"[ai] {provider} INDISPONIBIL pe sesiune — sar")
            return None
        if is_provider_circuit_open(provider):
            logger.info("[synthesis] Gemini circuit OPEN, skipping")
            return None
        if not settings.google_ai_api_key:
            logger.warning("[synthesis] No GOOGLE_AI_API_KEY — cannot use Gemini fallback")
            return None

        # §4: garda de context
        over, est, limit = ai_models.exceeds_context(provider, prompt)
        if over:
            logger.warning(
                f"[ai] {provider} sarit — prompt {est} tokeni > limita {limit} "
                f"(90% din {ai_models.get_max_context(provider)})"
            )
            return None

        try:
            logger.debug("[synthesis] Trying Gemini Flash API...")
            cfg = self._PROVIDERS[provider]
            url = cfg["url"].format(model=cfg["model"])
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
            if response.status_code >= 400:
                outcome = self._log_provider_outcome(
                    provider, cfg["model"], response.status_code, response.text, response.headers
                )
                if outcome == "fail":
                    record_provider_failure(provider)
                return None

            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
                    if text:
                        logger.debug(f"[synthesis] Gemini OK: {len(text.split())} words")
                        reset_provider_circuit(provider)
                        return text

            logger.warning("[synthesis] Gemini returned empty response")
            record_provider_failure(provider)
            return None
        except Exception as e:
            import re as _re
            err_msg = _re.sub(r"key=[A-Za-z0-9_\-]+", "key=***REDACTED***", str(e))
            logger.warning(f"[synthesis] Gemini error: {err_msg}")
            record_provider_failure(provider)
            return None

    # Dispatch nume-provider -> metoda. Sursa unica pt _sequential_fallback.
    def _provider_method_map(self) -> dict:
        return {
            "claude": self._generate_with_claude,
            "groq": self._generate_with_groq,
            "openrouter": self._generate_with_openrouter,
            "sambanova": self._generate_with_sambanova,
            "cerebras": self._generate_with_cerebras,
            "mistral": self._generate_with_mistral,
            "gemini": self._generate_with_gemini,
        }

    async def _sequential_fallback(
        self, section: dict, verified_data: dict, chain: list[str]
    ) -> tuple[str | None, str | None]:
        """Fallback SECVENTIAL ORDONAT peste un lant de provideri — ordinea e REALA.

        De ce nu concurent (fostul _concurrent_fallback): sub asyncio.wait(FIRST_COMPLETED)
        castiga cine raspunde primul, deci Gemini (rapid) batea mereu DeepSeek/OpenRouter
        (lent, dar mai bun) -> "lantul de calitate" nu ajungea NICIODATA la DeepSeek. Exact
        clasa de bug pe care o repara aceasta cerinta. Prioritatea proprietarului
        (DURABILITATE > viteza) cere ca ordinea sa conteze.

        Garzile §3 (indisponibil)/§4 (context)/§5 (cota) sunt IN metodele de provider:
        return None = "sari providerul", iar motivul e logat distinct acolo. Primul non-None
        castiga. Daca TOT lantul esueaza/e sarit -> esec EXPLICIT (nu tacut)."""
        methods = self._provider_method_map()
        for provider in chain:
            fn = methods.get(provider)
            if fn is None:
                logger.warning(f"[ai] provider necunoscut in lant, sarit: {provider}")
                continue
            prompt = self._build_section_prompt(section, verified_data, provider)
            try:
                text = await fn(prompt)
            except Exception as e:
                logger.warning(f"[ai] {provider} exceptie in lant: {e}")
                text = None
            if text:
                logger.info(f"[synthesis] Lant {chain} — castigator: {provider}")
                return text, provider
        logger.warning(
            f"[ai] TOTI providerii din lantul {chain} au esuat/fost sariti — "
            "esec EXPLICIT (motivele distincte sunt logate mai sus, NU tacut)"
        )
        return None, None
