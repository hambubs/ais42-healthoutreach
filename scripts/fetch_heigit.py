"""Fetch HeiGIT accessibility CSVs.
PowerShell 5.1 (Invoke-WebRequest) fails the TLS handshake against
hot.storage.heigit.org, so we use Python requests (OpenSSL) instead.
"""
import pathlib

import requests

RAW = pathlib.Path(__file__).resolve().parents[1] / "backend" / "data" / "raw"
FILES = {
    "https://hot.storage.heigit.org/heigit-hdx-public/access/ind/IND_primary_healthcare_access_wide.csv":
        "heigit_phc_access_wide.csv",
    "https://hot.storage.heigit.org/heigit-hdx-public/access/ind/IND_hospitals_access_wide.csv":
        "heigit_hospitals_access_wide.csv",
}

for url, name in FILES.items():
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    (RAW / name).write_bytes(r.content)
    print(f"{name}: {len(r.content):,} bytes")
