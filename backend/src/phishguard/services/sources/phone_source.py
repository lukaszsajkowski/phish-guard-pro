"""Phone number enrichment source (US-037).

Enriches phone number IOCs with metadata:

Local (always available — no API key required)
----------------------------------------------
Uses ``phonenumbers`` (libphonenumber port) to derive:
- Country name and ISO code
- Carrier / operator name (best-effort; may be empty for number ranges)
- Line type: mobile / voip / landline / unknown

Optional remote (NumVerify API)
--------------------------------
When ``NUMVERIFY_API_KEY`` is set, an additional API call fetches
carrier and line-type data that is more accurate for number ranges
where libphonenumber cannot determine the carrier.

API endpoint: ``http://apilayer.net/api/validate``

Reputation labels
-----------------
- ``suspicious`` — VoIP line (higher anonymity; frequently used by scammers)
- ``clean``      — Mobile or landline
- ``unknown``    — Invalid number or parsing failure
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
import phonenumbers
from phonenumbers import carrier, geocoder, number_type

from phishguard.core import get_settings
from phishguard.services.enrichment_service import RateLimitConfig

logger = logging.getLogger(__name__)

_NUMVERIFY_BASE = "http://apilayer.net/api/validate"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Map phonenumbers.PhoneNumberType to our canonical line type string
_LINE_TYPE_MAP: dict[int, str] = {
    phonenumbers.PhoneNumberType.MOBILE: "mobile",
    phonenumbers.PhoneNumberType.FIXED_LINE: "landline",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "landline",
    phonenumbers.PhoneNumberType.VOIP: "voip",
    phonenumbers.PhoneNumberType.TOLL_FREE: "landline",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "landline",
    phonenumbers.PhoneNumberType.SHARED_COST: "landline",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "mobile",
    phonenumbers.PhoneNumberType.PAGER: "mobile",
    phonenumbers.PhoneNumberType.UAN: "landline",
    phonenumbers.PhoneNumberType.UNKNOWN: "unknown",
    phonenumbers.PhoneNumberType.VOICEMAIL: "unknown",
}


def _derive_reputation(line_type: str) -> str:
    """VoIP lines are flagged as suspicious; all others are clean."""
    if line_type == "voip":
        return "suspicious"
    if line_type == "unknown":
        return "unknown"
    return "clean"


def _unknown_payload(*, reason: str = "error") -> dict[str, Any]:
    return {
        "country": None,
        "country_code": None,
        "carrier": None,
        "line_type": "unknown",
        "reputation": "unknown",
        "local_parse": False,
        "error": reason,
    }


def _parse_locally(value: str) -> dict[str, Any] | None:
    """Parse phone number with libphonenumber. Returns None if invalid."""
    try:
        parsed = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_valid_number(parsed):
        return None

    country = geocoder.description_for_number(parsed, "en") or None
    country_code = phonenumbers.region_code_for_number(parsed) or None
    carrier_name = carrier.name_for_number(parsed, "en") or None
    num_type_int = number_type(parsed)
    line_type = _LINE_TYPE_MAP.get(num_type_int, "unknown")

    return {
        "country": country,
        "country_code": country_code,
        "carrier": carrier_name,
        "line_type": line_type,
        "reputation": _derive_reputation(line_type),
        "local_parse": True,
    }


class PhoneNumberSource:
    """Enrichment source for phone number IOCs.

    Satisfies the ``EnrichmentSource`` protocol defined in
    ``phishguard.services.enrichment_service``.

    Local parsing via ``phonenumbers`` (libphonenumber) requires no API key.
    Optional NumVerify API call provides more accurate carrier/line-type data.
    """

    name: str = "phonenumbers"
    ioc_types: set[str] = {"phone"}
    rate_limit: RateLimitConfig = RateLimitConfig(
        requests_per_minute=60,
        requests_per_day=10_000,
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = (
            api_key if api_key is not None else get_settings().numverify_api_key
        )
        self._external_client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient()

    async def _enrich_via_numverify(
        self, value: str, local_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Supplement local parse with NumVerify API data.

        On any error, falls back to the local result unchanged.
        """
        client = await self._get_client()
        owns_client = self._external_client is None
        try:
            resp = await client.get(
                _NUMVERIFY_BASE,
                params={
                    "access_key": self._api_key,
                    "number": value.strip(),
                    "format": "1",
                },
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            if not data.get("valid", False):
                # NumVerify says invalid — keep local result but flag it
                return {**local_result, "numverify_valid": False}

            remote_line_type = (data.get("line_type") or "").lower()
            canonical_line_type = (
                remote_line_type
                if remote_line_type in {"mobile", "landline", "voip"}
                else local_result["line_type"]
            )

            return {
                "country": data.get("country_name") or local_result["country"],
                "country_code": data.get("country_code")
                or local_result["country_code"],
                "carrier": data.get("carrier") or local_result["carrier"],
                "line_type": canonical_line_type,
                "reputation": _derive_reputation(canonical_line_type),
                "local_parse": True,
                "numverify_valid": True,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "numverify_call_failed",
                extra={"error_class": exc.__class__.__name__},
            )
            return local_result
        finally:
            if owns_client:
                await client.aclose()

    async def enrich(self, ioc_type: str, value: str) -> dict[str, Any]:
        """Enrich a phone number with metadata.

        Always attempts local parsing first. If a NumVerify API key is
        configured, supplements the result with remote data.

        Returns a payload dict on success.
        Raises ``ValueError`` for invalid numbers so the ``EnrichmentService``
        can wrap it into an ``unavailable`` result.
        """
        local_result = _parse_locally(value.strip())
        if local_result is None:
            raise ValueError(f"Invalid phone number: {value!r}")

        if self._api_key:
            return await self._enrich_via_numverify(value, local_result)

        return local_result
