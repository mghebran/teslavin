import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from teslavin.config import Settings
from teslavin.mock import FIXTURES, MockClient
from teslavin.report import classify_fsd, build_report
from teslavin.service import VinService


def _svc():
    s = Settings(mock=True, db_path=os.path.join(tempfile.mkdtemp(), "t.sqlite"))
    return VinService(s)


def test_purchased_fsd_detected():
    r = _svc().lookup("5YJ3E1ET3RF865230")
    assert r.fsd.status == "purchased" and r.fsd.confidence == "high"
    assert r.production_date == "2024-09-18" and r.battery_soh_pct == 92


def test_subscription_not_mistaken_for_purchase():
    r = _svc().lookup("5YJ3E1EA6SF980036")
    assert r.fsd.status == "subscription"


def test_no_fsd():
    r = _svc().lookup("5YJ3E1EA9SF990639")
    assert r.fsd.status == "none"


def test_active_code_but_purchasable_is_flagged_not_purchased():
    opts = FIXTURES["5YJ3E1ET3RF865230"]["options"]
    v = classify_fsd(opts, upgrades={"eligible": [{"name": "Full Self-Driving (Supervised)"}]})
    assert v.status == "trial_or_subscription"


def test_purchase_code_without_eligibility_is_medium_confidence():
    opts = FIXTURES["5YJ3E1ET3RF865230"]["options"]
    v = classify_fsd(opts)
    assert v.status == "purchased" and v.confidence == "medium"


def test_inactive_fsd_code_is_none():
    opts = [dict(o, isActive=False) if o["code"] == "$APF2" else o
            for o in FIXTURES["5YJ3E1ET3RF865230"]["options"]]
    assert classify_fsd(opts).status == "none"


def test_cache_prevents_second_billing():
    svc = _svc()
    svc.lookup("5YJ3E1ET4SF084271")
    n = len(svc.client.calls)
    svc.lookup("5YJ3E1ET4SF084271")
    assert len(svc.client.calls) == n
    assert svc.store.spend_estimate()["specs_successful"] == 1


def test_unknown_vin_yields_empty_report_not_crash():
    r = _svc().lookup("5YJ3E1EA0SF000000")
    assert r.fsd.status == "none" and r.options == []


def test_pricing_sum_matches_tesla_priced_items():
    r = _svc().lookup("5YJ3E1ET4SF084271")
    assert r.as_built_price == 35000 + 19990 + 8000
