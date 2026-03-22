import asyncio
from abc import ABC, abstractmethod
from datetime import datetime

from loguru import logger

from backend.agents.state import AnalysisState, SourceResult, AgentError


class BaseAgent(ABC):
    name: str = "base"
    max_retries: int = 3
    retry_backoff: list[int] = [2, 5, 15]
    total_timeout: int = 300  # seconds

    @abstractmethod
    async def execute(self, state: AnalysisState) -> dict:
        """Run agent logic. Return dict to merge into state."""
        ...

    async def run(self, state: AnalysisState) -> dict:
        """Execute with timeout, error handling, and logging."""
        logger.info(f"[{self.name}] Starting...")
        start = datetime.utcnow()

        try:
            result = await asyncio.wait_for(
                self.execute(state),
                timeout=self.total_timeout,
            )
            elapsed = (datetime.utcnow() - start).total_seconds()
            logger.info(f"[{self.name}] Completed in {elapsed:.1f}s")
            return result

        except asyncio.TimeoutError:
            elapsed = (datetime.utcnow() - start).total_seconds()
            logger.error(f"[{self.name}] Timeout after {elapsed:.1f}s")
            return {
                "errors": [AgentError(
                    agent=self.name,
                    error=f"Timeout dupa {self.total_timeout}s",
                    recoverable=True,
                )],
            }

        except Exception as e:
            elapsed = (datetime.utcnow() - start).total_seconds()
            logger.error(f"[{self.name}] Error after {elapsed:.1f}s: {e}")
            return {
                "errors": [AgentError(
                    agent=self.name,
                    error=str(e),
                    recoverable=True,
                )],
            }

    async def fetch_with_retry(
        self,
        coro_factory,
        source_name: str,
        source_url: str = "",
    ) -> SourceResult:
        """Execute an async callable with retry logic. Returns SourceResult."""
        for attempt in range(self.max_retries):
            start_ms = datetime.utcnow()
            try:
                data = await coro_factory()
                elapsed_ms = int(
                    (datetime.utcnow() - start_ms).total_seconds() * 1000
                )
                # Determina daca datele sunt reale (nu doar un dict cu eroare)
                has_real_data = bool(data)
                if isinstance(data, dict):
                    if data.get("found") is False or (
                        "error" in data and not data.get("found", False)
                    ):
                        has_real_data = False

                return SourceResult(
                    source_name=source_name,
                    source_url=source_url,
                    status="OK" if has_real_data else "NO_DATA",
                    data_found=has_real_data,
                    response_time_ms=elapsed_ms,
                    data=data or {},
                )
            except Exception as e:
                elapsed_ms = int(
                    (datetime.utcnow() - start_ms).total_seconds() * 1000
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_backoff[min(attempt, len(self.retry_backoff) - 1)]
                    logger.warning(
                        f"[{self.name}] {source_name} attempt {attempt + 1} failed: {e}. "
                        f"Retry in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"[{self.name}] {source_name} failed after {self.max_retries} attempts: {e}"
                    )
                    status = "TIMEOUT" if "timeout" in str(e).lower() else "ERROR"
                    return SourceResult(
                        source_name=source_name,
                        source_url=source_url,
                        status=status,
                        data_found=False,
                        response_time_ms=elapsed_ms,
                        data={},
                    )
        # Should never reach here
        return SourceResult(
            source_name=source_name,
            source_url=source_url,
            status="ERROR",
            data_found=False,
            response_time_ms=0,
            data={},
        )
