import re
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz


_STOPWORDS = {
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "co",
    "company",
    "the",
    "and",
    "of",
}


def _norm_space(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    # Keep only plausible US 10-digit numbers; otherwise still store digits.
    return digits


def normalize_company_name(name: str) -> str:
    s = _norm_space(name or "")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = [t for t in s.split() if t and t not in _STOPWORDS]
    return " ".join(tokens)


def normalize_address(addr: str) -> str:
    s = _norm_space(addr or "")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\b(street)\b", "st", s)
    s = re.sub(r"\b(avenue)\b", "ave", s)
    s = re.sub(r"\b(road)\b", "rd", s)
    s = re.sub(r"\b(boulevard)\b", "blvd", s)
    s = re.sub(r"\b(suite)\b", "ste", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def compute_keys(company_name_norm: str, address_norm: str) -> Tuple[Optional[str], Optional[str]]:
    name_key = None
    addr_key = None

    if company_name_norm:
        # First 6 alnum chars after removing spaces.
        name_key = re.sub(r"\s+", "", company_name_norm)[:6] or None

    if address_norm:
        addr_key = re.sub(r"\s+", "", address_norm)[:6] or None

    return name_key, addr_key


def _score(company_name: str, address: str, phone: str, cand: Dict[str, Any]) -> int:
    name_sim = fuzz.token_sort_ratio(company_name or "", cand.get("company_name_norm") or "")
    addr_sim = fuzz.token_sort_ratio(address or "", cand.get("address_norm") or "")

    phone_sim = 0
    if phone and cand.get("phone_norm"):
        phone_sim = 100 if phone == cand.get("phone_norm") else 0

    # Weighted blend; phone acts as a strong boost when exact.
    return int(round(0.55 * name_sim + 0.35 * addr_sim + 0.10 * phone_sim))


def pick_best_match(
    *,
    company_name: str,
    address: str,
    phone: str,
    candidates: List[Dict[str, Any]],
    min_score: int = 82,
) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None

    best = None
    best_score = -1

    for c in candidates:
        sc = _score(company_name, address, phone, c)
        if sc > best_score:
            best_score = sc
            best = c

    if best is None:
        return None

    # Additional guardrails:
    # - If phone matches exactly, allow a slightly lower fuzzy score.
    if phone and best.get("phone_norm") == phone:
        if best_score >= 75:
            return {**best, "score": best_score}
        return None

    return {**best, "score": best_score} if best_score >= min_score else None
