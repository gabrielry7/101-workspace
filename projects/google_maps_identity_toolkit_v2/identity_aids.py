#!/usr/bin/env python3
"""Explainable, non-canonical pair-review aids for place identity.

The functions in this module intentionally produce *evidence features*, not an
identity verdict. They are suitable for operational review. For a blind audit,
compute/store them but hide the derived scores until after the human verdict.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Iterable, Optional
from urllib.parse import urlparse


LEGAL_SUFFIXES = {
    "sas", "s a s", "sa", "s a", "ltda", "limitada", "inc", "llc", "corp",
    "corporation", "company", "co", "cia", "compania", "compañia", "bic",
}
SOFT_NAME_WORDS = {"el", "la", "los", "las", "de", "del", "y", "e", "the", "and"}

STREET_TYPES = {
    "cl": "calle", "calle": "calle",
    "cra": "carrera", "cr": "carrera", "kr": "carrera", "kra": "carrera", "carrera": "carrera",
    "av": "avenida", "ave": "avenida", "avenida": "avenida",
    "ak": "avenida carrera", "ac": "avenida calle",
    "dg": "diagonal", "diag": "diagonal", "diagonal": "diagonal",
    "tv": "transversal", "transv": "transversal", "transversal": "transversal",
}

CATEGORY_FAMILIES = {
    "food_and_drink": {
        "restaurant", "restaurante", "bakery", "panaderia", "panadería", "cafe", "café",
        "coffee", "bar", "cocktail", "pub", "nightclub", "discoteca", "food", "drink",
        "dining", "beverage", "pizzeria", "pizza", "fast food", "breakfast",
    },
    "dental": {"dentist", "dental", "odontologia", "odontología", "odontologo", "odontólogo", "orthodont", "ortodoncia"},
    "healthcare": {"clinic", "clinica", "clínica", "hospital", "medical", "medico", "médico", "health", "salud", "pharmacy", "farmacia"},
    "beauty": {"beauty", "salon", "salón", "spa", "aesthetic", "estetica", "estética", "barber", "peluqueria", "peluquería"},
    "retail": {"store", "shop", "retail", "tienda", "supermarket", "market", "mercado", "mall"},
    "finance": {"bank", "banco", "atm", "financial", "financiero", "insurance", "seguro"},
    "lodging": {"hotel", "hostel", "lodging", "motel", "accommodation"},
    "automotive": {"automotive", "auto", "car", "vehicle", "mechanic", "mecanico", "mecánico", "tire", "llantas"},
    "fitness": {"gym", "gimnasio", "fitness", "crossfit", "yoga", "pilates"},
    "education": {"school", "colegio", "university", "universidad", "academy", "academia", "education"},
    "professional_services": {"lawyer", "abogado", "accountant", "contador", "consulting", "consultoria", "consultoría", "notary", "notaria", "notaría"},
    "entertainment": {"cinema", "theater", "theatre", "teatro", "museum", "museo", "entertainment", "casino"},
}


def fold_text(value: Any) -> str:
    s = "" if value is None else str(value)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def tokens(value: Any) -> list[str]:
    return fold_text(value).split()


def _strip_legal_suffixes(ts: list[str]) -> list[str]:
    out = list(ts)
    # Handle single-token suffixes first.
    while out and out[-1] in {"sas", "sa", "ltda", "limitada", "inc", "llc", "corp", "co", "cia", "bic"}:
        out.pop()
    return out


def normalize_name(value: Any, *, core: bool = False) -> str:
    ts = _strip_legal_suffixes(tokens(value))
    if core:
        ts = [t for t in ts if t not in SOFT_NAME_WORDS]
    return " ".join(ts)


def seq_ratio(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def name_features(a: Any, b: Any) -> dict[str, Any]:
    na = normalize_name(a)
    nb = normalize_name(b)
    ca = normalize_name(a, core=True)
    cb = normalize_name(b, core=True)
    strict = seq_ratio(na, nb)
    core = seq_ratio(ca, cb)
    token_overlap = jaccard(ca.split(), cb.split())

    if na and na == nb:
        relation = "EXACT_NORMALIZED"
    elif ca and ca == cb:
        relation = "EQUIVALENT_AFTER_SOFT_WORDS"
    elif max(core, token_overlap) >= 0.90:
        relation = "VERY_SIMILAR"
    elif max(core, token_overlap) >= 0.72:
        relation = "SIMILAR"
    elif max(core, token_overlap) >= 0.45:
        relation = "WEAKLY_SIMILAR"
    else:
        relation = "DIFFERENT_LOOKING"

    return {
        "a_normalized": na,
        "b_normalized": nb,
        "a_core": ca,
        "b_core": cb,
        "strict_sequence_similarity": round(strict, 4),
        "core_sequence_similarity": round(core, 4),
        "core_token_jaccard": round(token_overlap, 4),
        "relation": relation,
    }


def normalize_address(value: Any) -> str:
    s = fold_text(value)
    ts = s.split()
    out: list[str] = []
    for t in ts:
        out.append(STREET_TYPES.get(t, t))
    return " ".join(out)


def address_components(value: Any) -> dict[str, Any]:
    norm = normalize_address(value)
    ts = norm.split()
    street_type: Optional[str] = None
    if ts:
        first = ts[0]
        # Fold two-token avenida calle/carrera if present.
        if len(ts) >= 2 and f"{first} {ts[1]}" in {"avenida calle", "avenida carrera"}:
            street_type = f"{first} {ts[1]}"
        elif first in set(STREET_TYPES.values()):
            street_type = first
    nums = [int(x) for x in re.findall(r"\d+", norm)]
    return {
        "normalized": norm,
        "street_type": street_type,
        "numbers": nums,
        "main_number": nums[0] if nums else None,
        "cross_number": nums[1] if len(nums) > 1 else None,
        "door_number": nums[2] if len(nums) > 2 else None,
    }


def address_features(a: Any, b: Any) -> dict[str, Any]:
    ca = address_components(a)
    cb = address_components(b)
    na, nb = ca["normalized"], cb["normalized"]
    sim = seq_ratio(na, nb)
    tok = jaccard(na.split(), nb.split())

    nums_a, nums_b = ca["numbers"], cb["numbers"]
    num_overlap = jaccard((str(x) for x in nums_a), (str(x) for x in nums_b)) if (nums_a or nums_b) else 0.0

    swap_exact = bool(
        ca["main_number"] is not None and ca["cross_number"] is not None and
        cb["main_number"] is not None and cb["cross_number"] is not None and
        ca["main_number"] == cb["cross_number"] and ca["cross_number"] == cb["main_number"]
    )
    swap_near = bool(
        ca["main_number"] is not None and ca["cross_number"] is not None and
        cb["main_number"] is not None and cb["cross_number"] is not None and
        abs(ca["main_number"] - cb["cross_number"]) <= 1 and
        abs(ca["cross_number"] - cb["main_number"]) <= 1
    )

    if na and na == nb:
        relation = "EXACT_NORMALIZED"
    elif swap_exact:
        relation = "SAME_CORNER_REVERSED"
    elif swap_near:
        relation = "ADJACENT_CORNER_PATTERN"
    elif max(sim, tok) >= 0.85 and num_overlap >= 0.66:
        relation = "VERY_SIMILAR"
    elif max(sim, tok) >= 0.65 and num_overlap >= 0.33:
        relation = "SIMILAR"
    elif not na or not nb:
        relation = "UNKNOWN"
    else:
        relation = "DIFFERENT_LOOKING"

    return {
        "a": ca,
        "b": cb,
        "sequence_similarity": round(sim, 4),
        "token_jaccard": round(tok, 4),
        "number_overlap": round(num_overlap, 4),
        "street_cross_swap_exact": swap_exact,
        "street_cross_near": swap_near,
        "relation": relation,
    }


def normalize_phone(value: Any) -> Optional[str]:
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    # Colombia country code. Preserve the 10-digit national number.
    if digits.startswith("57") and len(digits) == 12:
        digits = digits[2:]
    return digits


def normalize_domain(value: Any) -> Optional[str]:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip().lower()
    if "://" not in raw:
        raw = "https://" + raw
    try:
        host = (urlparse(raw).hostname or "").lower().rstrip(".")
    except ValueError:
        return None
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _flatten_category(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        if s[:1] in "[{":
            try:
                return _flatten_category(json.loads(s))
            except Exception:
                pass
        return [s]
    if isinstance(value, dict):
        out: list[str] = []
        for v in value.values():
            out.extend(_flatten_category(v))
        return out
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for v in value:
            out.extend(_flatten_category(v))
        return out
    return [str(value)]


def category_terms(value: Any) -> set[str]:
    out: set[str] = set()
    for chunk in _flatten_category(value):
        folded = fold_text(chunk)
        if folded:
            out.add(folded)
            out.update(folded.split())
    return out


def category_families(value: Any) -> set[str]:
    terms = category_terms(value)
    joined = " ".join(sorted(terms))
    fams: set[str] = set()
    for family, keywords in CATEGORY_FAMILIES.items():
        for kw in keywords:
            fkw = fold_text(kw)
            if fkw in terms or (" " in fkw and fkw in joined):
                fams.add(family)
                break
    # Dental is a subtype of healthcare; keep both so compatibility works across
    # a broad source and a specific source while preserving specificity.
    if "dental" in fams:
        fams.add("healthcare")
    return fams


def category_features(a: Any, b: Any) -> dict[str, Any]:
    ta, tb = category_terms(a), category_terms(b)
    fa, fb = category_families(a), category_families(b)
    term_overlap = jaccard(ta, tb) if (ta or tb) else 0.0
    shared = fa & fb

    if not ta or not tb:
        relation = "UNKNOWN"
    elif shared:
        relation = "COMPATIBLE_FAMILY"
    elif term_overlap >= 0.35:
        relation = "TEXTUALLY_RELATED"
    elif fa and fb and not shared:
        relation = "POSSIBLE_CONFLICT"
    else:
        relation = "UNRESOLVED"

    return {
        "a_families": sorted(fa),
        "b_families": sorted(fb),
        "shared_families": sorted(shared),
        "term_jaccard": round(term_overlap, 4),
        "relation": relation,
    }


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def pair_review_aids(
    *,
    name_a: Any,
    name_b: Any,
    address_a: Any = None,
    address_b: Any = None,
    phone_a: Any = None,
    phone_b: Any = None,
    domain_a: Any = None,
    domain_b: Any = None,
    category_a: Any = None,
    category_b: Any = None,
    lat_a: Optional[float] = None,
    lon_a: Optional[float] = None,
    lat_b: Optional[float] = None,
    lon_b: Optional[float] = None,
) -> dict[str, Any]:
    pa, pb = normalize_phone(phone_a), normalize_phone(phone_b)
    da, db = normalize_domain(domain_a), normalize_domain(domain_b)
    distance = None
    if None not in (lat_a, lon_a, lat_b, lon_b):
        try:
            distance = round(haversine_m(float(lat_a), float(lon_a), float(lat_b), float(lon_b)), 2)
        except (TypeError, ValueError):
            distance = None

    return {
        "warning": "review aid only; not canonical identity evidence and not an automatic verdict",
        "name": name_features(name_a, name_b),
        "address": address_features(address_a, address_b),
        "phone": {
            "a_normalized": pa,
            "b_normalized": pb,
            "exact": bool(pa and pb and pa == pb),
        },
        "domain": {
            "a_normalized": da,
            "b_normalized": db,
            "exact": bool(da and db and da == db),
        },
        "category": category_features(category_a, category_b),
        "coordinate_distance_m": distance,
    }
