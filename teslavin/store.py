"""SQLite cache of reports so a VIN is only billed once per TTL."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from .report import VinReport, FsdVerdict


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS reports (
            vin TEXT PRIMARY KEY, fetched_at TEXT, year INT, trim TEXT, fsd_status TEXT,
            fsd_confidence TEXT, soh REAL, soh_ts TEXT, production_date TEXT,
            as_built_price INT, json TEXT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS calls (
            ts TEXT, vin TEXT, endpoint TEXT, ok INT, note TEXT)""")

    def get(self, vin: str, max_age_days: int) -> VinReport | None:
        row = self.db.execute("SELECT json, fetched_at FROM reports WHERE vin=?", (vin.upper(),)).fetchone()
        if not row:
            return None
        fetched = datetime.fromisoformat(row[1])
        if datetime.now(timezone.utc) - fetched > timedelta(days=max_age_days):
            return None
        d = json.loads(row[0])
        d["fsd"] = FsdVerdict(**d["fsd"]) if d.get("fsd") else None
        return VinReport(**d)

    def put(self, r: VinReport) -> None:
        self.db.execute("INSERT OR REPLACE INTO reports VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            r.vin, r.fetched_at, r.year, r.trim, r.fsd.status if r.fsd else None,
            r.fsd.confidence if r.fsd else None, r.battery_soh_pct, r.battery_soh_timestamp,
            r.production_date, r.as_built_price, json.dumps(r.to_dict(), default=str)))
        self.db.commit()

    def log_call(self, vin: str, endpoint: str, ok: bool, note: str = "") -> None:
        self.db.execute("INSERT INTO calls VALUES (?,?,?,?,?)",
                        (datetime.now(timezone.utc).isoformat(timespec="seconds"), vin, endpoint, int(ok), note))
        self.db.commit()

    def spend_estimate(self) -> dict:
        """Rough cost so far: specs successes at $0.10, everything else at $0.002."""
        rows = self.db.execute("SELECT endpoint, ok, COUNT(*) FROM calls GROUP BY endpoint, ok").fetchall()
        specs_ok = sum(n for e, ok, n in rows if e == "specs" and ok)
        other = sum(n for e, ok, n in rows if e != "specs")
        return {"specs_successful": specs_ok, "other_calls": other,
                "estimated_usd": round(specs_ok * 0.10 + other * 0.002, 2)}

    def fsd_cars(self) -> list[tuple]:
        return self.db.execute("""SELECT vin, year, trim, fsd_status, fsd_confidence, soh, production_date
                                  FROM reports WHERE fsd_status='purchased' ORDER BY year DESC""").fetchall()
