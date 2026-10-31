# Tesla Developer Application Package

Everything needed to file the partner application at https://developer.tesla.com, in the
order Tesla asks for it. Replace the bracketed placeholders.

## Before you start (prerequisites Tesla checks)

| Item | Why | Status |
|---|---|---|
| Tesla account with verified email + MFA | Required to open the developer portal | |
| Legal entity name, address, country | Asked on the application; sole proprietorship is acceptable | |
| A domain you control, `evbuildsheet.com` | Must host the public key and match `allowed_origins` | |
| HTTPS hosting for `site/` (Netlify, Cloudflare Pages, GitHub Pages all work) | The key must be reachable at `https://<domain>/.well-known/appspecific/com.tesla.3p.public-key.pem` and *remain* hosted | |
| Key pair generated with `scripts/make_keys.sh` | Public key goes in the site, private key stays offline | |
| A payment method and a billing limit (start at $25) | Default limit is $0 and usage is suspended at the limit | |

## Application fields

**Application name:** EV Build Sheet

**Description** (paste as-is):

> EV Build Sheet (evbuildsheet.com) is a pre-purchase research tool for people buying a used Tesla from a dealer,
> auction, or private seller. A prospective buyer enters the vehicle's VIN from a listing and
> receives the vehicle's factory configuration as recorded at the time of sale, its factory options and
> software packages and whether they are currently active, and Tesla's battery-health estimate when available. The purpose is to let a
> buyer confirm a seller's description against Tesla's own records before committing to a purchase.
>
> The application is read-only. It issues no vehicle commands, requests no vehicle pairing, and
> does not access location, charging state, or any live telemetry. Results are cached per VIN for
> up to 30 days and shown only to the user who requested that VIN. The service is clearly labeled
> as independent and not affiliated with, endorsed by, or sponsored by Tesla, Inc.

**Purpose of use:** Consumer vehicle research / pre-purchase verification.

**Scopes requested (and only these):**
- `vehicle_device_data` — `GET /api/1/dx/vehicles/options` (option codes; Tesla returns "missing scope: vehicle_device_data" without it)
- `vehicle_specs` — `GET /api/1/vehicles/{vin}/specs` (as-sold specs + battery health)
- `vehicle_pricing_info` — `POST /api/1/dx/vehicles/pricing` (list prices for option codes)
- `openid` — required for token issuance

Do **not** request `vehicle_cmds`, `vehicle_charging_cmds`, `vehicle_location`, or `vehicle_device_data`.
The two data scopes above are the ones Tesla documents as usable with a Partner Token "for any
vehicle without owner authorization"; asking for owner-level scopes you can't justify is the
usual reason an application stalls.

**Allowed origin(s):** `https://evbuildsheet.com`

**Redirect URI:** `https://evbuildsheet.com/auth/callback` (unused by a partner-token-only app, but the form requires one)

**Business / contact email:** a mailbox on the same domain, e.g. `hello@evbuildsheet.com`

## After approval (do these in order)

1. Put `TESLA_CLIENT_ID`, `TESLA_CLIENT_SECRET`, `TESLA_APP_DOMAIN` in `.env` (copy `.env.example`).
2. `python3 -m teslavin token` — proves the credentials and scopes issue a partner token.
3. `python3 -m teslavin register` — one-time `POST /api/1/partner_accounts` for your domain in the
   North America region, then reads back the public key to confirm. If you later need EU VINs,
   set `TESLA_REGION=eu` and register again.
4. `python3 -m teslavin lookup 5YJ3E1ET3RF865230` — first real call. Compare the output to the
   FSD Hunter PDF for the same VIN; the option codes and gate date should match exactly.
5. Open `teslavin/mock.py` and reconcile the fixture field names with the real `/specs`
   response (Tesla only documents the three battery fields; the rest are our guesses and
   `report.py` reads them loosely, but the fixtures should mirror reality).
6. Raise the billing limit once the first 20 lookups look right.

## Cost model

| Call | Billing | Per VIN |
|---|---|---|
| `dx/vehicles/options` | Data rate, 500 requests / $1 | ~$0.002 |
| `vehicles/{vin}/specs` | Special pricing, $0.10 per *successful* result | $0.10 |
| `dx/vehicles/pricing` | Data rate; cached per model per run | ~$0 |
| `upgrades` / `subscriptions` eligibility | Data rate | ~$0.004 |
| **Total** | | **≈ $0.11** |

Tesla applies a ~$10/month developer credit, so roughly the first 90 full reports each month are
free. `python3 -m teslavin lookup --no-specs` skips the $0.10 call when you only need the FSD
answer (option codes alone), bringing a lookup to under a cent.

## Timeline

- Day 0: buy domain, deploy `site/`, run `make_keys.sh`, file application.
- Days 1–21: Tesla review (reports range from a few days to a few weeks). The code is done and
  tested in mock mode; nothing else blocks on Tesla.
- Approval day: steps 1–6 above, about an hour.
