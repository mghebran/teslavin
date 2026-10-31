# teslavin

Per-VIN Tesla reports (factory option codes, purchased-vs-subscription FSD, as-sold specs,
Tesla's battery-health estimate) through the official Tesla Fleet API, for any VIN, no owner
authorization needed. This is the same mechanism the FSD Hunter app uses for its "VIN Build Check".

Status: code complete and tested against fixtures. Needs a Tesla developer approval to run live;
see `docs/APPLICATION.md` for the application text and the post-approval checklist.

## Layout

```
teslavin/        the package
  config.py      env/.env settings, regions, default (read-only) scopes
  client.py      Fleet API: partner token, partner registration, options/specs/pricing/eligibility
  mock.py        offline client + fixtures (4 VINs: purchased FSD x2, subscription FSD, none)
  report.py      field mapping + FSD classifier (purchased / subscription / trial / none)
  store.py       SQLite cache (one billing per VIN per 30 days) + spend tracking
  service.py     orchestration
  cli.py         command line
site/            the public page Tesla requires (landing, privacy, .well-known key path)
scripts/make_keys.sh   generates the prime256v1 key pair
tests/           pytest suite
docs/APPLICATION.md    what to paste into developer.tesla.com, costs, timeline
```

## Try it now (no Tesla credentials)

```
TESLAVIN_MOCK=1 python3 -m teslavin lookup 5YJ3E1ET3RF865230 5YJ3E1EA6SF980036
TESLAVIN_MOCK=1 python3 -m teslavin lookup --json 5YJ3E1ET4SF084271
python3 -m pytest -q tests
```

## Run live (after approval)

```
cp .env.example .env            # fill in TESLA_CLIENT_ID / TESLA_CLIENT_SECRET / TESLA_APP_DOMAIN
python3 -m teslavin token       # credentials sanity check
python3 -m teslavin register    # one-time partner registration (per region)
python3 -m teslavin lookup 5YJ3E1ET3RF865230
python3 -m teslavin batch vins.txt > results.csv
python3 -m teslavin fsd         # every archived car classified as purchased FSD
python3 -m teslavin spend       # estimated Tesla billing so far
```

## How the FSD call is made

1. `GET /api/1/dx/vehicles/options?vin=` returns `{"codes":[{code, displayName, isActive}]}`.
   A purchase code (`$APF2`, older `$APF1`/`$APFB`) with `isActive: true` is the primary signal.
2. `GET /api/1/dx/vehicles/upgrades/eligibility?vin=` is the tie-breaker: if FSD is still
   *purchasable* for the VIN, the car doesn't own it, so an active code means a subscription or
   trial, not a lifetime purchase. `subscriptions/eligibility` confirms an active subscription.
3. Confidence is `high` only when both the code and the eligibility endpoints agree.

The eligibility endpoints are not documented as partner-token accessible; the code treats them
as optional, so if Tesla rejects them you still get the code-based verdict at `medium`
confidence. Step 4 in `docs/APPLICATION.md` is where you find out which.

## Known unknowns to settle on the first live call

- Exact non-battery field names in `/specs` (`report.py` reads several candidates).
- Request body shape for `dx/vehicles/pricing` (`client.pricing` sends `{model, market}` and
  passes extra keys through).
- Whether `upgrades`/`subscriptions` eligibility accept a partner token.
- The display name Tesla uses for `$APF2` (fixtures say "Full Self-Driving (Supervised)").

Not affiliated with Tesla, Inc.
