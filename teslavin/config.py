"""Configuration. Everything comes from environment variables (or a .env file)."""
import os
from dataclasses import dataclass, field
from pathlib import Path

REGIONS = {
    # audience / base URL per Fleet API region
    "na": "https://fleet-api.prd.na.vn.cloud.tesla.com",
    "eu": "https://fleet-api.prd.eu.vn.cloud.tesla.com",
    "cn": "https://fleet-api.prd.cn.vn.cloud.tesla.cn",
}
TOKEN_URL = "https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3/token"

# Minimal read-only scopes for a VIN report. No command scopes on purpose.
DEFAULT_SCOPES = "openid vehicle_device_data vehicle_specs vehicle_pricing_info"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@dataclass
class Settings:
    client_id: str = ""
    client_secret: str = ""
    region: str = "na"
    domain: str = ""              # the domain you registered with Tesla
    scopes: str = DEFAULT_SCOPES
    db_path: str = "teslavin.sqlite"
    mock: bool = False            # run against bundled fixtures, no network
    cache_ttl_days: int = 30      # re-fetch a VIN after this many days
    extra: dict = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return REGIONS[self.region]

    @classmethod
    def from_env(cls, dotenv: str = ".env") -> "Settings":
        _load_dotenv(Path(dotenv))
        return cls(
            client_id=os.getenv("TESLA_CLIENT_ID", ""),
            client_secret=os.getenv("TESLA_CLIENT_SECRET", ""),
            region=os.getenv("TESLA_REGION", "na"),
            domain=os.getenv("TESLA_APP_DOMAIN", ""),
            scopes=os.getenv("TESLA_SCOPES", DEFAULT_SCOPES),
            db_path=os.getenv("TESLAVIN_DB", "teslavin.sqlite"),
            mock=os.getenv("TESLAVIN_MOCK", "").lower() in ("1", "true", "yes"),
            cache_ttl_days=int(os.getenv("TESLAVIN_CACHE_DAYS", "30")),
        )

    def validate(self) -> None:
        if self.mock:
            return
        missing = [n for n, v in (("TESLA_CLIENT_ID", self.client_id),
                                  ("TESLA_CLIENT_SECRET", self.client_secret)) if not v]
        if missing:
            raise SystemExit(
                "Missing " + ", ".join(missing) +
                ". Put them in .env once Tesla approves the app, or set TESLAVIN_MOCK=1 to use fixtures."
            )
        if self.region not in REGIONS:
            raise SystemExit(f"TESLA_REGION must be one of {list(REGIONS)}")
