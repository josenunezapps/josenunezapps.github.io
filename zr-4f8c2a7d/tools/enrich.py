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
DISCOVERY = ROOT / "comercios-osm.json"
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



# Snapshot de comercios para el navegador: no depende de consultar Overpass en vivo.
# No confirma apertura, necesidad comercial ni ausencia de servicios digitales.
COMMERCIAL_AMENITIES = {
    "restaurant", "cafe", "fast_food", "bar", "pub", "food_court",
    "pharmacy", "doctors", "dentist", "clinic", "car_wash", "fuel", "bank",
}
TOURISM_TYPES = {"hotel", "hostel", "guest_house", "motel", "apartment", "chalet"}
COMMERCIAL_LEISURE = {"fitness_centre", "sports_centre", "spa"}
VALID_TYPES = {"node", "way", "relation"}


def is_commercial(tags):
    return bool(
        tags.get("shop") not in (None, "", "no", "vacant")
        or tags.get("amenity") in COMMERCIAL_AMENITIES
        or tags.get("tourism") in TOURISM_TYPES
        or tags.get("office") not in (None, "", "no")
        or tags.get("craft") not in (None, "", "no")
        or tags.get("healthcare") not in (None, "", "no")
        or tags.get("leisure") in COMMERCIAL_LEISURE
    )


def category(tags):
    amenity = tags.get("amenity", "")
    shop = tags.get("shop", "")
    tourism = tags.get("tourism", "")
    if amenity in {"restaurant", "fast_food", "bar", "pub", "food_court"}:
        return "Gastronomía"
    if amenity == "cafe" or shop in {"bakery", "pastry", "coffee"}:
        return "Cafetería y panadería"
    if tourism in TOURISM_TYPES:
        return "Alojamiento"
    if shop in {"clothes", "shoes", "fashion", "boutique"}:
        return "Indumentaria y calzado"
    if shop in {"beauty", "hairdresser", "cosmetics"} or tags.get("leisure") == "spa":
        return "Belleza y estética"
    if amenity in {"doctors", "dentist", "pharmacy", "clinic"} or tags.get("healthcare"):
        return "Salud y bienestar"
    if shop in {"car", "car_repair", "car_parts", "tyres", "motorcycle"} or amenity == "car_wash":
        return "Automotor"
    if shop in {"hardware", "doityourself", "furniture", "interior_decoration", "paint"} or tags.get("craft"):
        return "Construcción y hogar"
    if tags.get("office") or amenity == "bank":
        return "Servicios profesionales"
    if tags.get("tourism"):
        return "Turismo y excursiones"
    return "Comercio minorista"


def short_text(value, max_length):
    return str(value or "").strip()[:max_length]


def commercial_record(element, observed):
    if not isinstance(element, dict):
        return None
    tags = element.get("tags") or {}
    if not isinstance(tags, dict) or not is_commercial(tags):
        return None
    name = short_text(tags.get("name"), 120)
    osm_type, osm_id = element.get("type"), element.get("id")
    if not name or osm_type not in VALID_TYPES or not isinstance(osm_id, int) or osm_id <= 0:
        return None
    if name.startswith("[DEMO") or name.startswith("[TEST"):
        return None
    coord = element.get("center") or element
    lat, lon = coord.get("lat"), coord.get("lon")
    if not isinstance(lat, (float, int)) or not isinstance(lon, (float, int)):
        return None
    # Include only the Ushuaia bounding box, not an entire surrounding region.
    if not (-54.89 <= lat <= -54.72 and -68.47 <= lon <= -68.14):
        return None
    street = short_text(tags.get("addr:street"), 140)
    number = short_text(tags.get("addr:housenumber"), 20)
    address = " ".join(part for part in (street, number) if part)
    if not address:
        address = short_text(tags.get("addr:full") or tags.get("addr:place"), 180)
    if not address:
        address = "Ushuaia, Tierra del Fuego"
    instagram = str(tags.get("contact:instagram") or tags.get("instagram") or "").strip()
    instagram = re.sub(r"^https?://(?:www\.)?instagram\.com/", "", instagram, flags=re.I)
    instagram = instagram.lstrip("@").split("?")[0].split("/")[0]
    if not re.fullmatch(r"[A-Za-z0-9_.]{1,30}", instagram):
        instagram = ""
    return {
        "id": f"{osm_type}/{osm_id}",
        "name": name,
        "category": category(tags),
        "address": short_text(address, 200),
        "website": safe_url(tags.get("website") or tags.get("contact:website") or ""),
        "instagram": instagram,
        "phone": safe_phone(tags.get("phone") or tags.get("contact:phone") or ""),
        "email": safe_email(tags.get("email") or tags.get("contact:email") or ""),
        "lastObserved": observed,
    }


def prepare_snapshot(elements, previous, successful_groups, total_groups, observed):
    old_records = previous.get("records", []) if isinstance(previous, dict) else []
    existing = {
        rec["id"]: rec for rec in old_records
        if isinstance(rec, dict) and re.fullmatch(r"(node|way|relation)/\d+", str(rec.get("id", "")))
    }
    if successful_groups:
        for e in elements:
            item = commercial_record(e, observed)
            if item:
                existing[item["id"]] = item
    # Retain older rows when some groups were not reachable.
    # Mark their last observation date instead of silently claiming current verification.
    ordered = sorted(existing.values(), key=lambda x: (normalize(x.get("name")), x["id"]))
    if len(ordered) > 4000:
        raise RuntimeError("OSM snapshot unexpectedly large; refusing to publish")
    return {
        "version": 1,
        "source": "OpenStreetMap contributors",
        "licenseUrl": "https://www.openstreetmap.org/copyright",
        "generatedAt": observed if successful_groups else previous.get("generatedAt"),
        "status": "complete" if successful_groups == total_groups else ("partial" if successful_groups else "unavailable"),
        "successfulGroups": successful_groups,
        "totalGroups": total_groups,
        "records": ordered,
    }


def write_if_changed(path, obj):
    payload = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != payload:
        path.write_text(payload, encoding="utf-8")
        return True
    return False


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
    old_snapshot = read_json(DISCOVERY, {"version": 1, "records": [], "generatedAt": None})
    snapshot = prepare_snapshot(all_osm, old_snapshot, succeeded, len(FILTER_GROUPS), date)
    changed_snapshot = write_if_changed(DISCOVERY, snapshot)
    print(f"OSM snapshot: {len(snapshot['records'])} places, {succeeded}/{len(FILTER_GROUPS)} groups, file changed: {changed_snapshot}", flush=True)
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
