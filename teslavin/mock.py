"""Offline stand-in for FleetClient, built from the documented response shapes.

The options schema is copied from a real Fleet API response (teslamotors/vehicle-command
issue #391): {"codes": [{"code": "$SC04", "displayName": "...", "isActive": true, "colorCode"?}]}.
The specs battery fields are the three Tesla documents (batteryCapacityKwh, batterySoH,
batterySoHTimestamp); the other spec fields are our best guess at the as-sold record and
WILL need adjusting against the first real response.

Fixture VINs:
  5YJ3E1ET3RF865230  2024 M3 Performance, purchased FSD (known-good from FSD Hunter)
  5YJ3E1ET4SF084271  2025 M3 Performance, purchased FSD (known-good from FSD Hunter)
  5YJ3E1EA6SF980036  2025 M3 RWD, no FSD, modelled as an active FSD *subscription*
  5YJ3E1EA9SF990639  2025 M3 Premium RWD, basic Autopilot only (from Tesla inventory record)
"""
from __future__ import annotations

from .client import FleetAPIError

_OPT = lambda code, name, active=True, **kw: {"code": code, "displayName": name, "isActive": active, **kw}  # noqa: E731

FIXTURES: dict[str, dict] = {
    "5YJ3E1ET3RF865230": {
        "options": [
            _OPT("$APBS", "Autopilot"), _OPT("$APF2", "Full Self-Driving (Supervised)"),
            _OPT("$CPF1", "Premium Connectivity"), _OPT("$CW03", "Cold Weather Feature"),
            _OPT("$IPB4", "Black Premium Interior"), _OPT("$MDL3", "Model 3"),
            _OPT("$MT353", "Model 3 Performance Dual Motor All-Wheel Drive"),
            _OPT("$PR01", "Ultra Red Paint", colorCode="PR01"),
            _OPT("$SC04", "Supercharger Network Access + Pay-as-you-go"),
            _OPT("$T30S", "Summer Tires"), _OPT("$W30P", "20’’ Warp Wheels"),
        ],
        "specs": {"vin": "5YJ3E1ET3RF865230", "year": 2024, "model": "Model 3",
                  "trim": "Model 3 Performance Dual Motor All-Wheel Drive", "driveType": "AWD",
                  "bodyType": "Sedan, Fastback", "countryOfOrigin": "US",
                  "productionDate": "2024-09-18", "paint": "Ultra Red Paint",
                  "interior": "Black Premium Interior", "wheels": "20’’ Warp Wheels",
                  "batteryCapacityKwh": 73.2, "batterySoH": 92,
                  "batterySoHTimestamp": "2026-10-29T17:31:00Z"},
        "upgrades": {"eligible": []},          # FSD not purchasable => already owned
        "subscriptions": {"eligible": []},
    },
    "5YJ3E1ET4SF084271": {
        "options": [
            _OPT("$APBS", "Autopilot"), _OPT("$APF2", "Full Self-Driving (Supervised)"),
            _OPT("$CPF1", "Premium Connectivity"), _OPT("$IPB4", "Black Premium Interior"),
            _OPT("$MDL3", "Model 3"), _OPT("$MT360", "Model 3 Performance All-Wheel Drive"),
            _OPT("$PN00", "Quicksilver Paint", colorCode="PN00"),
            _OPT("$SC04", "Supercharger Network Access + Pay-as-you-go"),
            _OPT("$T30S", "Summer Tires"), _OPT("$W30P", "20’’ Warp Wheels"),
        ],
        "specs": {"vin": "5YJ3E1ET4SF084271", "year": 2025, "model": "Model 3",
                  "trim": "Model 3 Performance All-Wheel Drive", "driveType": "AWD",
                  "bodyType": "Sedan, Fastback", "countryOfOrigin": "US",
                  "productionDate": "2025-10-01", "paint": "Quicksilver Paint",
                  "interior": "Black Premium Interior", "wheels": "20’’ Warp Wheels",
                  "batteryCapacityKwh": 76.1, "batterySoH": 96,
                  "batterySoHTimestamp": "2026-10-29T12:33:00Z"},
        "upgrades": {"eligible": []},
        "subscriptions": {"eligible": []},
    },
    "5YJ3E1EA6SF980036": {   # modelled: FSD via subscription, not purchased
        "options": [
            _OPT("$APBS", "Autopilot"), _OPT("$CPF1", "Premium Connectivity"),
            _OPT("$IPB2", "Black Premium Interior"), _OPT("$MDL3", "Model 3"),
            _OPT("$MT355", "Model 3 Premium Rear-Wheel Drive"),
            _OPT("$PPSW", "Pearl White Multi-Coat", colorCode="PPSW"),
            _OPT("$SC04", "Supercharger Network Access + Pay-as-you-go"),
            _OPT("$W38A", "18’’ Photon Wheels"),
        ],
        "specs": {"vin": "5YJ3E1EA6SF980036", "year": 2025, "model": "Model 3",
                  "trim": "Model 3 Premium Rear-Wheel Drive", "driveType": "RWD",
                  "bodyType": "Sedan, Fastback", "countryOfOrigin": "US",
                  "productionDate": "2025-03-28", "batteryCapacityKwh": 78.4,
                  "batterySoH": 99, "batterySoHTimestamp": "2026-10-28T03:10:00Z"},
        "upgrades": {"eligible": [{"optionCode": "$APF2", "name": "Full Self-Driving (Supervised)"}]},
        "subscriptions": {"eligible": [{"optionCode": "$APF2", "name": "Full Self-Driving (Supervised)",
                                        "status": "ACTIVE"}]},
    },
    "5YJ3E1EA9SF990639": {   # basic AP only, from the live Tesla inventory record
        "options": [
            _OPT("$APFS", "Traffic-Aware Cruise Control and Autosteer"),
            _OPT("$IPB2", "Black Premium Interior"), _OPT("$PR01", "Ultra Red", colorCode="PR01"),
            _OPT("$SC04", "Supercharger Network Access + Pay-as-you-go"), _OPT("$MDL3", "Model 3"),
            _OPT("$W38A", "18’’ Photon Wheels"), _OPT("$MT355", "Model 3 Premium Rear-Wheel Drive"),
            _OPT("$CPF0", "Standard Connectivity"),
        ],
        "specs": {"vin": "5YJ3E1EA9SF990639", "year": 2025, "model": "Model 3",
                  "trim": "Model 3 Premium Rear-Wheel Drive", "driveType": "RWD",
                  "bodyType": "Sedan, Fastback", "countryOfOrigin": "US",
                  "productionDate": "2025-04-01", "batteryCapacityKwh": None,
                  "batterySoH": None, "batterySoHTimestamp": None},
        "upgrades": {"eligible": [{"optionCode": "$APF2", "name": "Full Self-Driving (Supervised)"}]},
        "subscriptions": {"eligible": [{"optionCode": "$APF2", "name": "Full Self-Driving (Supervised)",
                                        "status": "AVAILABLE"}]},
    },
}

PRICING = {  # Tesla's priced line items as shown in inventory OptionCodeData (USD)
    "$MDL3": 35000, "$MT353": 19990, "$MT360": 19990, "$MT355": 7490, "$APF2": 8000,
    "$PR01": 2000, "$PN00": 0, "$PPSW": 0,
}


class MockClient:
    """Drop-in for FleetClient. Unknown VINs raise 404 like the real API would."""
    def __init__(self, settings=None):
        self.s = settings
        self.calls: list[str] = []

    def _get(self, vin: str, key: str):
        self.calls.append(f"{key}:{vin}")
        try:
            return FIXTURES[vin.upper()][key]
        except KeyError:
            raise FleetAPIError(404, f"mock://{key}/{vin}", '{"error":"vehicle not found"}') from None

    def partner_token(self): return "mock-token"
    def register_partner(self, domain=None): return {"domain": domain, "registered": True}
    def partner_public_key(self, domain=None): return {"domain": domain, "public_key": "-----BEGIN PUBLIC KEY-----..."}
    def options(self, vin): return self._get(vin, "options")
    def specs(self, vin): return self._get(vin, "specs")
    def upgrade_eligibility(self, vin): return self._get(vin, "upgrades")
    def subscription_eligibility(self, vin): return self._get(vin, "subscriptions")
    def pricing(self, model, market="US", **extra):
        self.calls.append(f"pricing:{model}:{market}")
        return {"market": market, "currency": "USD",
                "options": [{"code": c, "price": p} for c, p in PRICING.items()]}
