"""Airtable storage adapter for Sabeel Al-Rashad content."""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "appSHecoasMBDC2dY")
PAT = os.environ.get("AIRTABLE_PAT", "")
API_ROOT = f"https://api.airtable.com/v0/{BASE_ID}/"
CACHE = Path("/home/ubuntu/quran_workflow/airtable_cache.json")

TABLES = {
    "quran": {
        "name": "القرآن الكريم",
        "text": "النص الكامل",
        "explanation": "التفسير أو الشرح",
        "source": "المصدر",
        "date": "تاريخ النشر",
        "time": "وقت النشر",
        "status": "الحالة",
        "image": "رابط الصورة",
        "platforms": "المنصات المستهدفة",
    },
    "hadith": {
        "name": "الأحاديث",
        "text": "النص الكامل",
        "explanation": "التفسير أو الشرح",
        "source": "المصدر",
        "date": "تاريخ النشر",
        "time": "وقت النشر",
        "status": "الحالة",
        "image": "رابط الصورة",
        "platforms": "المنصات المستهدفة",
    },
    "qa": {
        "name": "سؤال وجواب",
        "text": "النص الكامل",
        "explanation": "التفسير أو الشرح",
        "source": "المصدر",
        "date": "تاريخ النشر",
        "time": "وقت النشر",
        "status": "الحالة",
        "image": "رابط الصورة",
        "platforms": "المنصات المستهدفة",
    },
}


def _request(method, path, payload=None, query=None):
    if not PAT:
        raise RuntimeError("AIRTABLE_PAT is not configured")
    url = API_ROOT + urllib.parse.quote(path, safe="/")
    if query:
        url += "?" + urllib.parse.urlencode(query)
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {PAT}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _table(kind):
    return TABLES.get(kind, TABLES["qa"])["name"]


def item_fields(item):
    kind = item.get("kind") or item.get("type", "qa")
    if kind == "quran_tafsir":
        kind = "quran"
    spec = TABLES.get(kind, TABLES["qa"])
    fields = {
        spec["text"]: item.get("main_text") or item.get("ayah_text") or "",
        spec["explanation"]: item.get("explanation") or item.get("tafsir") or "",
        spec["source"]: item.get("source") or "",
        spec["date"]: item.get("scheduled_date") or "",
        spec["status"]: item.get("airtable_status") or "مجدول",
    }
    if item.get("publish_time"):
        fields[spec["time"]] = item["publish_time"]
    if item.get("preview_url"):
        fields[spec["image"]] = item["preview_url"]
    platforms = item.get("platforms")
    if isinstance(platforms, str) and platforms:
        platforms = [p.strip() for p in platforms.split(",") if p.strip()]
    if platforms:
        fields[spec["platforms"]] = platforms
    return kind, fields


def create_item(item):
    kind, fields = item_fields(item)
    if not PAT:
        data = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else []
        item = dict(item)
        item.setdefault("record_id", f"local-{len(data)+1}")
        data.append(item)
        CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return item["record_id"], {"local": True}
    result = _request("POST", _table(kind), {"records": [{"fields": fields}], "typecast": True})
    record = (result.get("records") or [{}])[0]
    return record.get("id"), result


def list_items(kind=None):
    if not PAT:
        data = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else []
        return [x for x in data if not kind or x.get("kind") == kind]
    kinds = [kind] if kind else list(TABLES)
    output = []
    for current in kinds:
        result = _request("GET", _table(current), query={"pageSize": 100})
        for record in result.get("records", []):
            fields = record.get("fields", {})
            spec = TABLES[current]
            output.append({
                "record_id": record.get("id"),
                "kind": current,
                "main_text": fields.get(spec["text"], ""),
                "explanation": fields.get(spec["explanation"], ""),
                "source": fields.get(spec["source"], ""),
                "scheduled_date": fields.get(spec["date"], ""),
                "publish_time": fields.get(spec["time"], ""),
                "airtable_status": fields.get(spec["status"], ""),
            })
    return output


def update_status(item, status):
    if not PAT:
        data = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else []
        for row in data:
            if row.get("record_id") == item.get("record_id"):
                row["airtable_status"] = status
        CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"local": True}
    kind = item.get("kind", "qa")
    record_id = item.get("record_id")
    if not record_id:
        return None
    spec = TABLES.get(kind, TABLES["qa"])
    return _request("PATCH", f"{_table(kind)}/{record_id}", {"fields": {spec["status"]: status}})
