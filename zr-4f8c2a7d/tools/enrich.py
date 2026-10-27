#!/usr/bin/env python3
"""Zenix Radar: refresh a sourced enrichment snapshot from OSM. No paid APIs.
Do not claim a business lacks a website just because OpenStreetMap does not list one.
"""
import json
import os
import re
import time
import unicodedata
import urllib.request
import urllib.error
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalogo-turismo-2026-03.json"
SEED = ROOT / "investigaciones-seed.json"
OUT = ROOT / "investigaciones-datos.json"
ENDPOINTS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]
BOUNDS = "(-54.89,-68.47,-54.72,-68.14)"
FILTER_GROUPS = [
    ['nwr["name"]["amenity"~"^(restaurant|cafe|fast_food|bar|pub|food_court)$"]',
     'nwr["name"]["shop"~"^(bakery|pastry|coffee)$"]'],
    ['nwr["name"]["shop"]'],
    ['nwr["name"]["tourism"~"^(hotel|hostel|guest_house|motel|apartment|chalet|information)$"]'],
    ['nwr["name"]["office"]', 'nwr["name"]["craft"]', 'nwr["name"]["healthcare"]',
     'nwr["name"]["amenity"~"^(school|pharmacy|doctors|dentist|bank|clinic|car_wash|fuel)$"]'],
]


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.casefold())).strip()


def read_json(path, fallback=None):
    if not path.exists():
        if fallback is not None:
            return fallback
        raise RuntimeError("Missing input: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def safe_url(raw):
    value = str(raw or "").strip()
    if value and not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    parts = urlparse(value)
    if parts.scheme in ("https", "http") and parts.hostname and "." in parts.hostname and len(value) <= 300:
        return value
    return ""


def safe_phone(value):
    value = str(value or "").strip()
    return value[:20] if len(value) <= 20 else ""


def safe_email(value):
    value = str(value or "").strip()
    return value if len(value) <= 160 and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value) else ""


def request_overpass(filters, endpoint, timeout=44):
    query = "[out:json][timeout:32];(" + "".join(f + BOUNDS + ";" for f in filters) + ");out center;"
    req = urllib.request.Request(
        endpoint,
        data=("data=" + urllib.parse.quote(query, safe="")).encode("utf-8"),
        headers={"User-Agent": "ZenixRadarResearch/1.0 (public OSM data; low-frequency GitHub Actions)",
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as reply:
        if reply.status != 200:
            raise RuntimeError("HTTP " + str(reply.status))
        parsed = json.loads(reply.read(10_000_000).decode("utf-8"))
    if not isinstance(parsed.get("elements"), list):
        raise RuntimeError("No OSM element list")
    return parsed["elements"]


def match_osm(elements, directory):
    # Match exact normalized name only, and only unique candidate per name.
    # This conservatively avoids attributing another business's contact details.
    by_name = defaultdict(list)
    for e in elements:
        tags = e.get("tags") or {}
        key = normalize(tags.get("name"))
        if key:
            by_name[key].append(e)

    by_catalog_name = defaultdict(list)
    for row in directory:
        by_catalog_name[normalize(row.get("name"))].append(row)

    matches = {}
    for norm_name, rows in by_catalog_name.items():
        candidates = by_name.get(norm_name) or []
        if len(rows) != 1 or len(candidates) != 1:
            continue
        item, obj = rows[0], candidates[0]
        tags = obj.get("tags") or {}
        website = safe_url(tags.get("website") or tags.get("contact:website") or "")
        email = safe_email(tags.get("email") or tags.get("contact:email") or "")
        phone = safe_phone(tags.get("phone") or tags.get("contact:phone") or "")
        instagram = str(tags.get("contact:instagram") or tags.get("instagram") or "").strip()
        if instagram.startswith("@"):
            instagram = instagram[1:]
        instagram = instagram[:30] if len(instagram) <= 30 and re.fullmatch(r"[a-zA-Z0-9_.]{1,30}", instagram) else ""
        if not (website or email or phone or instagram):
            continue
        item_id = item["id"]
        osm_type, osm_id = obj.get("type"), obj.get("id")
        if osm_type not in {"node", "way", "relation"} or not isinstance(osm_id, int):
            continue
        matches[item_id] = {
            "catalogId": item_id,
            "name": item["name"],
            "website": website,
            "email": email,
            "phone": phone,
            "instagram": instagram,
            "features": [],
            "observation": "OpenStreetMap publica estos datos de contacto; se debe confirmar su actualidad.",
            "evidenceUrls": [f"https://www.openstreetmap.org/{osm_type}/{osm_id}"],
            "checkedAt": datetime.now(timezone.utc).date().isoformat(),
            "basis": "Coincidencia única del nombre exacto normalizado dentro de Ushuaia, en OpenStreetMap.",
        }
    return matches


def main():
    seed = read_json(SEED)
    previous = read_json(OUT, {})
    catalog = read_json(CATALOG)["entries"]
    indexed = {e["catalogId"]: e for e in seed["records"]}
    old_osm_records = {
        e["catalogId"]: e for e in previous.get("records", [])
        if e.get("catalogId") not in indexed
    }
    all_osm = []
    failures = []
    succeeded = 0
    for number, group in enumerate(FILTER_GROUPS, 1):
        response = None
        errors = []
        for endpoint in ENDPOINTS:
            try:
                response = request_overpass(group, endpoint)
                print(f"Group {number}: {len(response)} OSM elements from {urlparse(endpoint).hostname}", flush=True)
                break
            except (Exception,) as exc:
                errors.append(f"{urlparse(endpoint).hostname}: {exc}")
                time.sleep(1.5)
        if response is not None:
            all_osm.extend(response)
            succeeded += 1
        else:
            failures.append(f"group {number}: " + "; ".join(errors))
    if succeeded:
        matches = match_osm(all_osm, catalog)
        # If the current search is partial, do not forget any previously found
        # match; it can later be rechecked by a complete successful crawl.
        if succeeded < len(FILTER_GROUPS):
            for k, item in old_osm_records.items():
                matches.setdefault(k, item)
        old_osm_records = matches

    for key, found in old_osm_records.items():
        if key in indexed:
            curated = indexed[key]
            # An authoritative business site takes precedence over an OSM tag.
            combined = dict(curated)
            for field in ("website", "email", "phone", "instagram"):
                if not combined.get(field) and found.get(field):
                    combined[field] = found[field]
            combined["evidenceUrls"] = list(dict.fromkeys(curated["evidenceUrls"] + found.get("evidenceUrls", [])))
            indexed[key] = combined
        else:
            indexed[key] = found

    date = datetime.now(timezone.utc).date().isoformat()
    result = {
        "version": 1,
        "updatedAt": date,
        "method": "Sitios públicos dirigidos + coincidencias exactas únicas de OpenStreetMap. No se infiere la ausencia de páginas o necesidades comerciales.",
        "openStreetMap": {
            "status": "complete" if succeeded == len(FILTER_GROUPS) else ("partial" if succeeded else "unavailable"),
            "updatedAt": date if succeeded else previous.get("openStreetMap", {}).get("updatedAt"),
            "successfulGroups": succeeded,
            "totalGroups": len(FILTER_GROUPS),
            "matchedBusinesses": len(old_osm_records),
            "warnings": failures[:4],
        },
        "records": sorted(indexed.values(), key=lambda x: x["catalogId"]),
    }
    body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if OUT.exists() and OUT.read_text(encoding="utf-8") == body:
        print("No changes.")
    else:
        OUT.write_text(body, encoding="utf-8")
        print(f"Wrote {len(result['records'])} sourced records ({succeeded}/{len(FILTER_GROUPS)} OSM groups).", flush=True)


if __name__ == "__main__":
    main()
