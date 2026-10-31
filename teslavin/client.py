"""Fleet API client: partner-token auth + the per-VIN endpoints.

Endpoints used (all with a Partner Token, none need owner authorization per Tesla docs):
  GET  /api/1/dx/vehicles/options?vin=                    option codes          (data rate)
  GET  /api/1/vehicles/{vin}/specs                        as-sold specs+battery ($0.10/success)
  POST /api/1/dx/vehicles/pricing                         price table for model/market
  GET  /api/1/dx/vehicles/upgrades/eligibility?vin=       purchasable upgrades (FSD => not owned)
  GET  /api/1/dx/vehicles/subscriptions/eligibility?vin=  subscribable products
  POST /api/1/partner_accounts                            one-time registration per region
  GET  /api/1/partner_accounts/public_key?domain=         confirm registration
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from .config import Settings, TOKEN_URL


class FleetAPIError(RuntimeError):
    def __init__(self, status: int, url: str, body: str):
        super().__init__(f"HTTP {status} from {url}: {body[:300]}")
        self.status, self.url, self.body = status, url, body


@dataclass
class Token:
    access_token: str
    expires_at: float

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at - 60


class FleetClient:
    def __init__(self, settings: Settings):
        self.s = settings
        self._token: Optional[Token] = None

    # ---- auth -------------------------------------------------------------
    def partner_token(self) -> str:
        if self._token and not self._token.expired:
            return self._token.access_token
        form = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.s.client_id,
            "client_secret": self.s.client_secret,
            "scope": self.s.scopes,
            "audience": self.s.base_url,
        }).encode()
        req = urllib.request.Request(
            TOKEN_URL, data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        data = self._send(req)
        self._token = Token(data["access_token"], time.time() + int(data.get("expires_in", 3600)))
        return self._token.access_token

    # ---- low level ---------------------------------------------------------
    def _send(self, req: urllib.request.Request) -> Any:
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read().decode()
        except urllib.error.HTTPError as e:
            raise FleetAPIError(e.code, req.full_url, e.read().decode(errors="replace")) from None
        return json.loads(raw) if raw else {}

    def _call(self, method: str, path: str, *, params: dict | None = None,
              body: dict | None = None) -> Any:
        url = self.s.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": "Bearer " + self.partner_token(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        out = self._send(req)
        # Fleet API wraps most payloads as {"response": ...}; options returns {"codes": [...]}
        return out.get("response", out) if isinstance(out, dict) else out

    # ---- partner registration (run once per region) ------------------------
    def register_partner(self, domain: str | None = None) -> Any:
        return self._call("POST", "/api/1/partner_accounts", body={"domain": domain or self.s.domain})

    def partner_public_key(self, domain: str | None = None) -> Any:
        return self._call("GET", "/api/1/partner_accounts/public_key",
                          params={"domain": domain or self.s.domain})

    # ---- per-VIN data ------------------------------------------------------
    def options(self, vin: str) -> list[dict]:
        out = self._call("GET", "/api/1/dx/vehicles/options", params={"vin": vin})
        codes = out.get("codes", out) if isinstance(out, dict) else out
        return list(codes or [])

    def specs(self, vin: str) -> dict:
        return self._call("GET", f"/api/1/vehicles/{vin}/specs") or {}

    def pricing(self, model: str, market: str = "US", **extra) -> Any:
        # Body shape is only loosely documented ("pricing details for a vehicle model in a
        # specific market"); model/market are the two fields Tesla names. Extra keys pass through.
        return self._call("POST", "/api/1/dx/vehicles/pricing",
                          body={"model": model, "market": market, **extra})

    def upgrade_eligibility(self, vin: str) -> Any:
        return self._call("GET", "/api/1/dx/vehicles/upgrades/eligibility", params={"vin": vin})

    def subscription_eligibility(self, vin: str) -> Any:
        return self._call("GET", "/api/1/dx/vehicles/subscriptions/eligibility", params={"vin": vin})
