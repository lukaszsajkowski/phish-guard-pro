"""HTTP client for a Basal decision server."""

import time
from dataclasses import dataclass

import httpx

_QUESTION = "q"


class BasalUnavailableError(Exception):
    """Basal could not provide a usable answer."""

    def __init__(self, message: str, *, is_timeout: bool = False) -> None:
        super().__init__(message)
        self.is_timeout = is_timeout


@dataclass(frozen=True)
class BasalAnswer:
    """A single-choice answer from Basal."""

    answer: str
    probabilities: dict[str, float]
    confidence: float
    latency_ms: int


class BasalClient:
    """Asks Basal single-choice questions over HTTP."""

    def __init__(
        self,
        url: str,
        timeout_s: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = url
        self._timeout_s = timeout_s
        self._transport = transport

    async def ask_choice(
        self, state: str, instructions: str, criteria: dict[str, str]
    ) -> BasalAnswer:
        """Ask Basal to pick one key of `criteria` for `state`.

        Raises:
            BasalUnavailableError: on any transport/HTTP/parsing failure or when
                the returned choice is not one of the criteria keys.
        """
        body = {
            "state": state,
            "questions": {
                _QUESTION: {
                    "type": "choice",
                    "option_keys": "hide",
                    "instructions": instructions,
                    "criteria": criteria,
                }
            },
        }
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_s, transport=self._transport
            ) as http:
                response = await http.post(self._url, json=body)
            response.raise_for_status()
            result = response.json()["answers"][_QUESTION]
            choice = result["choice"]
            probabilities = {k: float(v) for k, v in result["probabilities"].items()}
            confidence = float(result["confidence"])
        except httpx.HTTPError as e:
            raise BasalUnavailableError(
                f"Basal request failed: {e!r}",
                is_timeout=isinstance(e, httpx.TimeoutException),
            ) from e
        except (KeyError, ValueError, TypeError, AttributeError) as e:
            raise BasalUnavailableError(f"Invalid Basal response: {e!r}") from e

        if choice not in criteria:
            raise BasalUnavailableError(f"Basal choice not in options: {choice!r}")

        latency_ms = int((time.perf_counter() - start) * 1000)
        return BasalAnswer(choice, probabilities, confidence, latency_ms)
