"""Orchestrates one VIN lookup: cache -> options -> specs -> eligibility -> pricing -> report."""
from __future__ import annotations

from .client import FleetAPIError, FleetClient
from .config import Settings
from .mock import MockClient
from .report import VinReport, build_report
from .store import Store

MODEL_FROM_VIN = {"3": "m3", "Y": "my", "S": "ms", "X": "mx", "C": "ct", "R": "mr"}


def model_code(vin: str) -> str:
    return MODEL_FROM_VIN.get(vin[3].upper(), "m3")


class VinService:
    def __init__(self, settings: Settings, client=None, store: Store | None = None):
        self.s = settings
        self.client = client or (MockClient(settings) if settings.mock else FleetClient(settings))
        self.store = store or Store(settings.db_path)
        self._pricing_cache: dict[str, object] = {}

    def lookup(self, vin: str, *, force: bool = False, with_specs: bool = True,
               with_eligibility: bool = True, with_pricing: bool = True) -> VinReport:
        vin = vin.strip().upper()
        if len(vin) != 17:
            raise ValueError(f"{vin!r} is not a 17-character VIN")
        if not force:
            cached = self.store.get(vin, self.s.cache_ttl_days)
            if cached:
                return cached

        options = self._call("options", vin, lambda: self.client.options(vin)) or []
        specs = (self._call("specs", vin, lambda: self.client.specs(vin)) or {}) if with_specs else {}
        upgrades = subs = None
        if with_eligibility:
            upgrades = self._call("upgrades", vin, lambda: self.client.upgrade_eligibility(vin), optional=True)
            subs = self._call("subscriptions", vin, lambda: self.client.subscription_eligibility(vin), optional=True)
        pricing = self._pricing(model_code(vin)) if with_pricing else None

        report = build_report(vin, options, specs, pricing, upgrades, subs)
        self.store.put(report)
        return report

    # Pricing is per model/market, not per VIN: fetch once per run.
    def _pricing(self, model: str):
        if model not in self._pricing_cache:
            self._pricing_cache[model] = self._call("pricing", model, lambda: self.client.pricing(model, "US"), optional=True)
        return self._pricing_cache[model]

    def _call(self, endpoint: str, key: str, fn, *, optional: bool = False):
        try:
            out = fn()
            self.store.log_call(key, endpoint, True)
            return out
        except FleetAPIError as e:
            self.store.log_call(key, endpoint, False, f"{e.status}")
            if optional or e.status == 404:
                return None
            raise
