"""Step 1 — pull the NASS bill-tracker index once and cache it locally.

See ofin-spec.md §2.1 / §6 step 1. The `search[value]` param is ignored by
the server — it always returns all ~2,660 rows, so we pull once and filter
locally.
"""
import json

import requests

from common import DATA_DIR, NASS_INDEX_URL, USER_AGENT

INDEX_CACHE = DATA_DIR / "index.json"


def pull_index(force: bool = False) -> list:
    if INDEX_CACHE.exists() and not force:
        return json.loads(INDEX_CACHE.read_text())

    resp = requests.get(
        NASS_INDEX_URL,
        params={"draw": 1, "start": 0, "length": 3000},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    resp.raise_for_status()
    rows = resp.json()["data"]
    INDEX_CACHE.write_text(json.dumps(rows))
    print(f"Pulled {len(rows)} rows -> {INDEX_CACHE}")
    return rows


if __name__ == "__main__":
    pull_index(force=True)
