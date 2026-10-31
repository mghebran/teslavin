"""Turn raw Fleet API payloads into a VIN report, including the FSD classification."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

# Tesla option codes that denote *purchased* Full Self-Driving across model years.
#   APF2  FSD (Supervised) / FSD Capability (Model 3/Y/S/X 2019+)
#   APF1  Enhanced Autopilot + FSD era (2016-2019 S/X)
#   APFB  FSD bundle on some 2019-2020 builds
#   AF02  "Full Self-Driving Computer" hardware retrofit flag -- hardware, NOT the software; excluded
FSD_PURCHASE_CODES = {"$APF2", "$APF1", "$APFB"}
EAP_CODES = {"$APH3", "$APH4", "$APPA", "$APPB", "$APBS"}  # APBS = basic Autopilot
ACCEL_BOOST = {"$SPT31", "$SPT32", "$SPTY1", "$SPTY2", "$PBAB"}   # "Acceleration Boost" variants

FSD_WORDS = re.compile(r"full\s*self[- ]?driving", re.I)


@dataclass
class FsdVerdict:
    status: str            # purchased | subscription | trial_or_subscription | none | unknown
    confidence: str        # high | medium | low
    evidence: list[str] = field(default_factory=list)


def classify_fsd(options: list[dict], upgrades: Any = None, subscriptions: Any = None) -> FsdVerdict:
    """Purchased ("lifetime") FSD vs. subscription vs. none.

    Logic, strongest signal first:
      1. A purchase code (APF2/APF1/APFB) present and isActive  -> purchased (high)
         ... unless the upgrades endpoint says FSD is still *purchasable* for this VIN,
         which means the car does not own it (an active subscription/trial can set isActive).
      2. No purchase code, but subscription eligibility reports an ACTIVE FSD line -> subscription.
      3. Purchase code absent, nothing active, FSD purchasable/subscribable -> none.
      4. Anything else -> unknown, with the evidence listed so a human can judge.
    """
    ev: list[str] = []
    active_codes = {o["code"] for o in options if o.get("isActive", True)}
    all_codes = {o["code"] for o in options}
    fsd_active = FSD_PURCHASE_CODES & active_codes
    fsd_inactive = (FSD_PURCHASE_CODES & all_codes) - fsd_active
    for c in fsd_active:
        ev.append(f"{c} present and active")
    for c in fsd_inactive:
        ev.append(f"{c} present but isActive=false")

    purchasable = _mentions_fsd(upgrades)
    sub_active = _subscription_state(subscriptions)
    if purchasable:
        ev.append("upgrades/eligibility lists FSD as purchasable")
    if sub_active:
        ev.append(f"subscriptions/eligibility: FSD {sub_active}")

    if fsd_active and not purchasable and sub_active != "ACTIVE":
        return FsdVerdict("purchased", "high" if upgrades is not None else "medium", ev)
    if fsd_active and (purchasable or sub_active == "ACTIVE"):
        return FsdVerdict("trial_or_subscription", "medium", ev)
    if sub_active == "ACTIVE":
        return FsdVerdict("subscription", "high", ev)
    if not fsd_active and (purchasable or sub_active or upgrades is not None):
        return FsdVerdict("none", "high" if purchasable else "medium", ev)
    if not fsd_active and fsd_inactive:
        return FsdVerdict("none", "medium", ev + ["FSD code inactive: removed on transfer?"])
    if not fsd_active:
        return FsdVerdict("none", "medium", ev or ["no FSD purchase code in option list"])
    return FsdVerdict("unknown", "low", ev)


def _mentions_fsd(payload: Any) -> bool:
    return bool(payload) and bool(FSD_WORDS.search(_flat(payload)) or "APF2" in _flat(payload))


def _subscription_state(payload: Any) -> str | None:
    if not payload:
        return None
    items = payload.get("eligible", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return None
    for it in items:
        s = _flat(it)
        if FSD_WORDS.search(s) or "APF2" in s:
            st = (it.get("status") or it.get("state") or "AVAILABLE") if isinstance(it, dict) else "AVAILABLE"
            return str(st).upper()
    return None


def _flat(x: Any) -> str:
    import json
    return json.dumps(x, default=str)


@dataclass
class VinReport:
    vin: str
    fetched_at: str
    year: int | None = None
    model: str | None = None
    trim: str | None = None
    drive_type: str | None = None
    body_type: str | None = None
    country_of_origin: str | None = None
    production_date: str | None = None
    paint: str | None = None
    interior: str | None = None
    wheels: str | None = None
    battery_capacity_kwh: float | None = None
    battery_soh_pct: float | None = None
    battery_soh_timestamp: str | None = None
    fsd: FsdVerdict | None = None
    enhanced_autopilot: bool = False
    acceleration_boost: bool = False
    options: list[dict] = field(default_factory=list)
    priced_options: list[dict] = field(default_factory=list)
    as_built_price: int | None = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def build_report(vin: str, options: list[dict], specs: dict, pricing: Any = None,
                 upgrades: Any = None, subscriptions: Any = None) -> VinReport:
    vin = vin.upper()
    r = VinReport(vin=vin, fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    r.options = options
    r.raw = {"options": options, "specs": specs, "pricing": pricing,
             "upgrades": upgrades, "subscriptions": subscriptions}

    # specs: field names beyond the documented battery trio are best-effort; we read loosely.
    g = lambda *names: next((specs[n] for n in names if specs.get(n) is not None), None)  # noqa: E731
    r.year = g("year", "modelYear")
    r.model = g("model", "modelName")
    r.trim = g("trim", "trimName", "trimDescription")
    r.drive_type = g("driveType", "drive", "drivetrain")
    r.body_type = g("bodyType", "bodyStyle")
    r.country_of_origin = g("countryOfOrigin", "country")
    r.production_date = g("productionDate", "factoryGatedDate", "buildDate")
    r.battery_capacity_kwh = g("batteryCapacityKwh")
    r.battery_soh_pct = g("batterySoH")
    r.battery_soh_timestamp = g("batterySoHTimestamp")

    by_prefix = lambda p: next((o["displayName"] for o in options if o["code"].startswith(p)), None)  # noqa: E731
    r.paint = g("paint", "exteriorColor") or next((o["displayName"] for o in options if o.get("colorCode")), None) or by_prefix("$P")
    r.interior = g("interior", "interiorColor") or by_prefix("$I")
    r.wheels = g("wheels") or by_prefix("$W")
    if not r.trim:
        r.trim = by_prefix("$MT")

    codes = {o["code"] for o in options if o.get("isActive", True)}
    r.fsd = classify_fsd(options, upgrades, subscriptions)
    r.enhanced_autopilot = bool(codes & {"$APH3", "$APH4", "$APPA", "$APPB"})
    r.acceleration_boost = bool(codes & ACCEL_BOOST)

    price_map = _price_map(pricing)
    for o in options:
        p = price_map.get(o["code"])
        if p:
            r.priced_options.append({"code": o["code"], "name": o["displayName"], "price": p})
    if r.priced_options:
        r.as_built_price = sum(x["price"] for x in r.priced_options)
    return r


def _price_map(pricing: Any) -> dict[str, int]:
    """Accepts the loosely-documented pricing payload in a few plausible shapes."""
    out: dict[str, int] = {}
    if not pricing:
        return out
    items = pricing.get("options") if isinstance(pricing, dict) else pricing
    if isinstance(items, dict):
        items = [{"code": k, "price": v} for k, v in items.items()]
    for it in items or []:
        if not isinstance(it, dict):
            continue
        code = it.get("code") or it.get("optionCode")
        price = it.get("price") or it.get("amount")
        if code and price:
            try:
                out[code] = int(float(str(price).replace(",", "")))
            except ValueError:
                pass
    return out


def render_text(r: VinReport) -> str:
    L = []
    L.append(f"VIN {r.vin}   fetched {r.fetched_at}")
    title = r.trim if (r.trim and r.model and r.trim.startswith(r.model)) else f"{r.model or ''} {r.trim or ''}"
    L.append(f"{r.year or ''} {title}".strip())
    L.append(f"  Drive {r.drive_type or '?'} | Body {r.body_type or '?'} | Origin {r.country_of_origin or '?'} | Built {r.production_date or '?'}")
    L.append(f"  Paint {r.paint or '?'} | Interior {r.interior or '?'} | Wheels {r.wheels or '?'}")
    if r.battery_soh_pct is not None:
        L.append(f"  Battery health {r.battery_soh_pct}% ({r.battery_capacity_kwh} kWh usable), Tesla estimate {r.battery_soh_timestamp}")
    else:
        L.append("  Battery health: no Tesla estimate available")
    f = r.fsd
    L.append(f"  FSD: {f.status.upper()}  [{f.confidence} confidence]  " + "; ".join(f.evidence))
    flags = [x for x, on in (("EAP", r.enhanced_autopilot), ("Acceleration Boost", r.acceleration_boost)) if on]
    if flags:
        L.append("  Also: " + ", ".join(flags))
    L.append("  Option codes:")
    for o in r.options:
        p = next((x["price"] for x in r.priced_options if x["code"] == o["code"]), None)
        flag = "" if o.get("isActive", True) else "  (inactive)"
        L.append(f"    {o['code']:8} {o['displayName']:<48} {('$%s' % format(p, ',')) if p else ''}{flag}")
    if r.as_built_price:
        L.append(f"  As-built price (priced items only): ${r.as_built_price:,}")
    return "\n".join(L)
