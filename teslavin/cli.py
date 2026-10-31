"""Command line.

  teslavin lookup VIN [VIN ...]        report one or more VINs (cached)
  teslavin batch vins.txt              one VIN per line; prints a CSV summary
  teslavin fsd                         list archived cars classified as purchased FSD
  teslavin spend                       estimated Tesla billing so far
  teslavin register                    one-time partner registration for your domain
  teslavin token                       prove credentials work (prints token prefix)

Set TESLAVIN_MOCK=1 to run against bundled fixtures before Tesla approval.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys

from .config import Settings
from .report import render_text
from .service import VinService


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="teslavin")
    ap.add_argument("--env", default=".env")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lookup"); p.add_argument("vins", nargs="+"); p.add_argument("--force", action="store_true")
    p.add_argument("--json", action="store_true", help="emit JSON instead of text")
    p.add_argument("--no-specs", action="store_true", help="skip the $0.10 specs call (no battery/as-sold fields)")
    b = sub.add_parser("batch"); b.add_argument("file"); b.add_argument("--no-specs", action="store_true")
    sub.add_parser("fsd"); sub.add_parser("spend"); sub.add_parser("register"); sub.add_parser("token")
    a = ap.parse_args(argv)

    s = Settings.from_env(a.env)
    s.validate()
    svc = VinService(s)

    if a.cmd == "token":
        tok = svc.client.partner_token()
        print("OK, partner token obtained:", tok[:12] + "…")
        return 0
    if a.cmd == "register":
        if not s.domain:
            sys.exit("Set TESLA_APP_DOMAIN first (the domain hosting the .well-known public key).")
        print(json.dumps(svc.client.register_partner(s.domain), indent=2))
        print(json.dumps(svc.client.partner_public_key(s.domain), indent=2))
        return 0
    if a.cmd == "lookup":
        for vin in a.vins:
            r = svc.lookup(vin, force=a.force, with_specs=not a.no_specs)
            print(json.dumps(r.to_dict(), indent=2, default=str) if a.json else render_text(r))
            print()
        return 0
    if a.cmd == "batch":
        vins = [l.strip() for l in open(a.file) if l.strip() and not l.startswith("#")]
        w = csv.writer(sys.stdout)
        w.writerow(["vin", "year", "trim", "fsd", "confidence", "battery_soh", "built", "as_built_price", "error"])
        for vin in vins:
            try:
                r = svc.lookup(vin, with_specs=not a.no_specs)
                w.writerow([r.vin, r.year, r.trim, r.fsd.status, r.fsd.confidence, r.battery_soh_pct,
                            r.production_date, r.as_built_price, ""])
            except Exception as e:  # noqa: BLE001
                w.writerow([vin, "", "", "", "", "", "", "", str(e)[:120]])
        return 0
    if a.cmd == "fsd":
        for row in svc.store.fsd_cars():
            print(*row, sep="\t")
        return 0
    if a.cmd == "spend":
        print(json.dumps(svc.store.spend_estimate(), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
