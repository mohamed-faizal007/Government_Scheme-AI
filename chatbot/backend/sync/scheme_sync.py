"""Sync MongoDB + ChromaDB with MyScheme.gov.in. Adds and updates only — never deletes.

Run (from repo root):
    python -m chatbot.backend.sync.scheme_sync             # real run
    python -m chatbot.backend.sync.scheme_sync --dry-run   # report only, no writes

Every failure mode degrades to "log it, record it in the report, return" so the
chatbot API that hosts the scheduler is never affected.
"""
import argparse
import importlib.util
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from chatbot.backend.config import settings
from chatbot.backend.sync import sync_status

logger = logging.getLogger("scheme_sync")

SEARCH_PATH = "/search/v4/schemes"
DETAIL_PATH = "/schemes/v6/public/schemes"
SITE_SEARCH_PATH = "/search"
SITE_SCHEME_PATH = "/schemes/{slug}"

PAGE_SIZE = 50
MAX_PAGES = 200  # hard stop against a runaway pagination loop
REQUEST_TIMEOUT = 30
DATA_SOURCE = "myscheme_live_sync"
MAX_LIST_ITEM_CHARS = 600

# Filter params sent blank, exactly as the site's own search does.
_BLANK_FILTERS = (
    "keyword schemeType state central age gender category minority disable bpl occupation".split()
)
_UPDATED_KEYS = ("lastUpdated", "last_updated", "updatedAt", "updated_at", "modifiedAt", "lastModified")

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "backend" / "extraction" / "schema.py"


def _load_scheme_model():
    """Import Scheme from backend/extraction/schema.py by path.

    `backend` also names the chatbot's own package, so a normal import is ambiguous
    depending on sys.path. Loading by file keeps the extraction pipeline untouched.
    """
    spec = importlib.util.spec_from_file_location("extraction_schema", _SCHEMA_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Scheme


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(value) -> datetime | None:
    """Best-effort parse of ISO strings / epoch numbers / datetimes into aware UTC."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value / 1000 if value > 1e11 else value, tz=timezone.utc)
    else:
        text = str(value).strip().replace("Z", "+00:00")
        dt = None
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            for fmt in ("%d %b %Y", "%d %B %Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _headers() -> dict:
    headers = {
        "Accept": "application/json, text/html;q=0.9",
        "User-Agent": "SchemeBot-sync/1.0",
        "Origin": settings.myscheme_site_url,
        "Referer": settings.myscheme_site_url + "/",
    }
    if settings.myscheme_api_key:
        headers["x-api-key"] = settings.myscheme_api_key
    return headers


def _get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    resp = session.get(url, headers=_headers(), timeout=REQUEST_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp


def _clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _md_to_lines(value) -> list[str]:
    """Flatten markdown / HTML / list values into a list of plain-text items."""
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(_md_to_lines(item))
        return out
    if isinstance(value, dict):
        return _md_to_lines(list(value.values()))
    text = str(value)
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text("\n")
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", raw)
        line = re.sub(r"[*_`#>]+", "", line)
        line = _clean(re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line))
        if line:
            lines.append(line[:MAX_LIST_ITEM_CHARS])
    return lines


def _first(mapping: dict, keys) -> object:
    for key in keys:
        if isinstance(mapping, dict) and mapping.get(key) not in (None, "", []):
            return mapping[key]
    return None


# ---------------------------------------------------------------------------
# Step 1 — scheme list
# ---------------------------------------------------------------------------
def _list_from_api(session: requests.Session) -> list[dict]:
    schemes: list[dict] = []
    total = None
    for page in range(MAX_PAGES):
        params = {"lang": "en", "q": "", **{k: "" for k in _BLANK_FILTERS}, "page": page, "size": PAGE_SIZE}
        body = _get(session, settings.myscheme_base_url.rstrip("/") + SEARCH_PATH, params=params).json()
        hits = (body.get("data") or {}).get("hits") or {}
        items = hits.get("items") or []
        if total is None:
            total = (hits.get("page") or {}).get("total")
        for item in items:
            fields = item.get("fields") or item
            name = _clean(fields.get("schemeName") or fields.get("name"))
            slug = fields.get("slug")
            if not name or not slug:
                continue
            schemes.append(
                {
                    "scheme_name": name,
                    "slug": slug,
                    "url": settings.myscheme_site_url.rstrip("/") + SITE_SCHEME_PATH.format(slug=slug),
                    "last_updated": parse_date(_first(fields, _UPDATED_KEYS) or _first(item, _UPDATED_KEYS)),
                }
            )
        if not items or (total is not None and len(schemes) >= total):
            break
    return schemes


def _list_from_site(session: requests.Session) -> list[dict]:
    html = _get(session, settings.myscheme_site_url.rstrip("/") + SITE_SEARCH_PATH).text
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, dict] = {}
    for anchor in soup.find_all("a", href=re.compile(r"/schemes/[^/?#]+")):
        slug = re.search(r"/schemes/([^/?#]+)", anchor["href"]).group(1)
        name = _clean(anchor.get_text(" "))
        if name and slug not in found:
            found[slug] = {
                "scheme_name": name,
                "slug": slug,
                "url": settings.myscheme_site_url.rstrip("/") + SITE_SCHEME_PATH.format(slug=slug),
                "last_updated": None,
            }
    return list(found.values())


def fetch_scheme_list(session: requests.Session, errors: list[str]) -> list[dict]:
    """API first, then the HTML search page. Returns [] (and records why) if both fail."""
    try:
        schemes = _list_from_api(session)
        if schemes:
            return schemes
        errors.append("scheme list API returned no schemes")
    except (requests.RequestException, ValueError) as exc:
        errors.append(f"scheme list API failed: {exc}")
        logger.warning("Scheme list API failed (%s); trying %s", exc, SITE_SEARCH_PATH)

    try:
        schemes = _list_from_site(session)
        if schemes:
            return schemes
        errors.append(
            "search page fallback found no scheme links (the page is rendered client-side, "
            "so a plain HTTP fetch cannot see the list)"
        )
    except requests.RequestException as exc:
        errors.append(f"search page fallback failed: {exc}")
    return []


# ---------------------------------------------------------------------------
# Step 3 — scheme details -> our JSON schema
# ---------------------------------------------------------------------------
def _detail_from_api_json(body: dict, fallback: dict) -> dict:
    """Normalise the public scheme-detail API payload."""
    data = body.get("data") or body
    en = data.get("en") if isinstance(data.get("en"), dict) else data
    basic = en.get("basicDetails") or {}
    content = en.get("schemeContent") or {}
    elig = en.get("eligibilityCriteria") or {}
    process = en.get("applicationProcess") or []
    docs = en.get("documents_required") or en.get("documentsRequired") or []
    categories = [c.get("label", c) if isinstance(c, dict) else c for c in basic.get("schemeCategory") or []]

    return {
        "scheme_name": _clean(basic.get("schemeName") or fallback["scheme_name"]),
        "department": _clean(basic.get("nodalMinistryName") or basic.get("nodalDepartmentName")),
        "state": _clean(basic.get("state") or ""),
        "category": ", ".join(_clean(c) for c in categories if c),
        "scheme_type": _clean(basic.get("level") or ""),
        "description": " ".join(
            _md_to_lines(content.get("briefDescription") or content.get("detailedDescription_md"))
        ),
        "benefits": _md_to_lines(content.get("benefits_md") or content.get("benefits")),
        "eligibility": _md_to_lines(elig.get("eligibilityDescription_md") or elig.get("eligibilityDescription")),
        "documents": _md_to_lines([d.get("documentsRequired_md", d) if isinstance(d, dict) else d for d in docs]),
        "steps": _md_to_lines([p.get("process_md", p) if isinstance(p, dict) else p for p in process]),
        "tags": [_clean(t) for t in basic.get("tags") or []],
        "last_updated": parse_date(_first(en, _UPDATED_KEYS) or _first(basic, _UPDATED_KEYS) or fallback["last_updated"]),
    }


_SECTION_HEADINGS = {
    "description": re.compile(r"^(details|overview|about|description)$", re.I),
    "benefits": re.compile(r"^benefits?$", re.I),
    "eligibility": re.compile(r"^eligibility", re.I),
    "documents": re.compile(r"^documents? required", re.I),
    "steps": re.compile(r"^application process", re.I),
}


def _detail_from_html(html: str, fallback: dict) -> dict:
    """Extract fields from a rendered scheme page with BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    # Next.js pages sometimes ship the full payload as JSON; prefer it when present.
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            scheme_data = json.loads(next_data.string)["props"]["pageProps"].get("schemeData")
        except (ValueError, KeyError, TypeError):
            scheme_data = None
        if scheme_data:
            return _detail_from_api_json(scheme_data, fallback)

    title = soup.find("h1")
    sections: dict[str, list[str]] = {key: [] for key in _SECTION_HEADINGS}
    for heading in soup.find_all(["h2", "h3"]):
        key = next((k for k, rx in _SECTION_HEADINGS.items() if rx.match(_clean(heading.get_text(" ")))), None)
        if not key:
            continue
        for sibling in heading.find_next_siblings():
            if sibling.name in ("h2", "h3"):
                break
            sections[key].extend(_md_to_lines(sibling.get_text("\n")))

    updated = None
    match = re.search(r"(?:last\s+updated|updated\s+on)\s*[:\-]?\s*([0-9A-Za-z ,/\-]{6,20})", soup.get_text(" "), re.I)
    if match:
        updated = parse_date(match.group(1).strip())

    return {
        "scheme_name": _clean(title.get_text(" ")) if title else fallback["scheme_name"],
        "department": "", "state": "", "category": "", "scheme_type": "", "tags": [],
        "description": " ".join(sections["description"]),
        "benefits": sections["benefits"],
        "eligibility": sections["eligibility"],
        "documents": sections["documents"],
        "steps": sections["steps"],
        "last_updated": updated or fallback["last_updated"],
    }


def fetch_scheme_detail(session: requests.Session, listing: dict) -> dict:
    """Detail API first, then the scheme page. Raises on total failure."""
    try:
        resp = _get(
            session,
            settings.myscheme_base_url.rstrip("/") + DETAIL_PATH,
            params={"slug": listing["slug"], "lang": "en"},
        )
        raw = _detail_from_api_json(resp.json(), listing)
        if raw["scheme_name"]:
            return raw
    except (requests.RequestException, ValueError) as exc:
        logger.debug("detail API failed for %s: %s", listing["slug"], exc)
    return _detail_from_html(_get(session, listing["url"]).text, listing)


def build_scheme_doc(raw: dict, Scheme) -> dict:
    """Map extracted fields onto the project schema and validate with Pydantic."""
    scheme = Scheme.model_validate(
        {
            "metadata": {
                "scheme_name": raw["scheme_name"],
                "scheme_type": raw.get("scheme_type", ""),
                "state": raw.get("state", ""),
                "implementing_department": raw.get("department", ""),
                "category": raw.get("category", ""),
            },
            "overview": {"description": raw["description"]},
            "benefits": {"other_benefits": raw["benefits"]},
            "eligibility": {"conditions": raw["eligibility"]},
            "application": {"documents": raw["documents"], "steps": raw["steps"]},
            "search_metadata": {"tags": raw.get("tags", [])},
        }
    )
    if not scheme.metadata.scheme_name:
        raise ValueError("scheme_name missing")
    if not (scheme.overview.description or scheme.benefits.other_benefits or scheme.eligibility.conditions):
        raise ValueError("no description, benefits or eligibility extracted")
    return scheme.model_dump()


def _non_empty_paths(doc: dict, prefix: str = "") -> dict:
    """Flatten to dotted paths, dropping empty values so a partial scrape can't blank good data."""
    out = {}
    for key, value in doc.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(_non_empty_paths(value, path + "."))
        elif value not in ("", [], None):
            out[path] = value
    return out


# ---------------------------------------------------------------------------
# Step 2 — compare
# ---------------------------------------------------------------------------
def classify_schemes(listings: list[dict], existing: dict[str, dict]) -> tuple[list, list, list]:
    new, updated, unchanged = [], [], []
    for listing in listings:
        doc = existing.get(listing["scheme_name"].lower())
        if doc is None:
            new.append(listing)
            continue
        # ingested_at never moves, so after a sync the scheme would look stale forever;
        # use whichever of ingested_at / last_synced is later.
        baseline = max(
            (d for d in (parse_date(doc.get("ingested_at")), parse_date(doc.get("last_synced"))) if d),
            default=None,
        )
        website = listing["last_updated"]
        if website and (baseline is None or website > baseline):
            updated.append({**listing, "doc": doc})
        else:
            unchanged.append(listing)
    return new, updated, unchanged


# ---------------------------------------------------------------------------
# Step 5 — re-embed
# ---------------------------------------------------------------------------
def reembed_pending(collection, dry_run: bool, errors: list[str], failed: list[str]) -> int:
    pending = list(collection.find({"embedding_status": "pending"}))
    if dry_run or not pending:
        return len(pending)

    import chromadb

    from chatbot.backend.database.load_chroma import COLLECTION_NAME, build_chunks
    from chatbot.backend.embeddings.multilingual_e5 import MultilingualE5Embedder

    chroma = chromadb.PersistentClient(path=settings.chroma_persist_path).get_or_create_collection(COLLECTION_NAME)
    embedder = MultilingualE5Embedder()
    done = 0
    for doc in pending:
        name = doc.get("metadata", {}).get("scheme_name", doc.get("source_file", "?"))
        try:
            chunks = build_chunks(doc)  # text already carries the "passage: " prefix
            vectors = embedder.embed([c["text"] for c in chunks])
            chroma.delete(where={"source_file": doc["source_file"]})
            chroma.add(
                ids=[c["chunk_id"] for c in chunks],
                embeddings=vectors,
                documents=[c["text"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks],
            )
            collection.update_one({"_id": doc["_id"]}, {"$set": {"embedding_status": "done"}})
            done += 1
        except Exception as exc:
            logger.exception("Re-embedding failed for %s", name)
            failed.append(name)
            errors.append(f"embedding failed for {name}: {exc}")
    return done


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_sync(dry_run: bool = False) -> dict:
    """Run all six steps. Never raises; returns the report dict."""
    report = {
        "sync_timestamp": _now().isoformat(timespec="seconds"),
        "schemes_checked": 0,
        "new_schemes_added": 0,
        "schemes_updated": 0,
        "schemes_unchanged": 0,
        "schemes_failed": [],
        "errors": [],
        "status": "success",
        "dry_run": dry_run,
    }
    errors, failed = report["errors"], report["schemes_failed"]

    if not dry_run and not sync_status.acquire_lock():
        report["status"] = "failed"
        errors.append("another sync is already running")
        logger.warning("Sync skipped: another run holds the lock")
        return report

    try:
        _run_steps(report, dry_run)
    except Exception as exc:  # last-resort guard: a sync bug must never escape
        logger.exception("Sync aborted unexpectedly")
        errors.append(f"unexpected error: {exc}")
        report["status"] = "failed"
    finally:
        if not dry_run:
            sync_status.release_lock()

    if report["status"] == "success" and failed:
        report["status"] = "partial"
    if not dry_run:
        _write_report(report)
    _print_summary(report)
    return report


def _run_steps(report: dict, dry_run: bool) -> None:
    errors, failed = report["errors"], report["schemes_failed"]
    session = requests.Session()

    # Step 1
    listings = fetch_scheme_list(session, errors)
    if not listings:
        logger.error("Could not fetch the scheme list from MyScheme; nothing to sync")
        report["status"] = "failed"
        return
    report["schemes_checked"] = len(listings)

    # Step 2
    from chatbot.backend.database.mongo_client import get_schemes_collection

    try:
        collection = get_schemes_collection()
        existing: dict[str, dict] = {}
        projection = {"metadata.scheme_name": 1, "ingested_at": 1, "last_synced": 1, "source_file": 1}
        for doc in collection.find({}, projection):
            name = _clean(doc.get("metadata", {}).get("scheme_name")).lower()
            existing.setdefault(name, doc)
    except Exception as exc:
        errors.append(f"MongoDB unavailable: {exc}")
        report["status"] = "failed"
        return

    new, updated, unchanged = classify_schemes(listings, existing)
    report["schemes_unchanged"] = len(unchanged)
    logger.info("Compared: %d new, %d updated, %d unchanged", len(new), len(updated), len(unchanged))

    # Steps 3 + 4
    Scheme = _load_scheme_model()
    existing_files = {d.get("source_file") for d in existing.values()}
    for kind, items in (("new", new), ("updated", updated)):
        for listing in items:
            name = listing["scheme_name"]
            if dry_run:
                logger.info("[dry-run] would %s: %s (%s)", "insert" if kind == "new" else "update", name, listing["url"])
                report["new_schemes_added" if kind == "new" else "schemes_updated"] += 1
                continue
            try:
                raw = fetch_scheme_detail(session, listing)
                doc = build_scheme_doc(raw, Scheme)
                now = _now()
                if kind == "new":
                    source_file = f"{listing['slug']}.json"
                    if source_file in existing_files:
                        raise ValueError(f"source_file {source_file} already used by another scheme")
                    collection.insert_one(
                        {
                            **doc,
                            "source_file": source_file,
                            "ingested_at": now,
                            "last_synced": now,
                            "last_updated": raw["last_updated"],
                            "data_source": DATA_SOURCE,
                            "embedding_status": "pending",
                        }
                    )
                    report["new_schemes_added"] += 1
                else:
                    changes = _non_empty_paths(doc)
                    changes.update(
                        {"last_synced": now, "last_updated": raw["last_updated"], "embedding_status": "pending"}
                    )
                    collection.update_one({"_id": listing["doc"]["_id"]}, {"$set": changes})
                    report["schemes_updated"] += 1
            except Exception as exc:
                logger.warning("Failed to sync %s: %s", name, exc)
                failed.append(name)
                errors.append(f"{name}: {exc}")

    # Step 5
    count = reembed_pending(collection, dry_run, errors, failed)
    logger.info("%s %d scheme(s) in ChromaDB", "[dry-run] would re-embed" if dry_run else "Re-embedded", count)


def _write_report(report: dict) -> None:
    try:
        sync_status.SYNC_LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = sync_status.SYNC_LOG_DIR / f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Sync report written to %s", path)
    except OSError:
        logger.exception("Could not write sync report")


def _print_summary(report: dict) -> None:
    suffix = " (would be)" if report["dry_run"] else ""
    print("\n=== MyScheme sync summary" + (" (DRY RUN)" if report["dry_run"] else "") + " ===")
    print(f"Status:            {report['status']}")
    print(f"Schemes checked:   {report['schemes_checked']}")
    print(f"New schemes added: {report['new_schemes_added']}{suffix}")
    print(f"Schemes updated:   {report['schemes_updated']}{suffix}")
    print(f"Unchanged:         {report['schemes_unchanged']}")
    print(f"Failed:            {len(report['schemes_failed'])}")
    for err in report["errors"][:10]:
        print(f"  ! {err}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync schemes from MyScheme.gov.in")
    parser.add_argument("--dry-run", action="store_true", help="show what would change; write nothing")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_sync(dry_run=args.dry_run)
    return 0  # an unreachable MyScheme is reported, not treated as a crash


if __name__ == "__main__":
    sys.exit(main())
