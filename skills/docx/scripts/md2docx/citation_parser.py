#!/usr/bin/env python3
"""
Citation parsing and conversion module

Core responsibilities:
  1. Detect citation format in MD (tiered fallback T1→T2→T3)
  2. Build original_ID → display_number mapping by first-appearance order
  3. Replace citation markers with Pandoc superscript syntax ^N^
  4. Detect edge cases (non-numeric citations, image placeholders) and return WARNINGs

Format detection strategy:
  T1 [^N^]  Standard format, high confidence, direct conversion
  T2 [^N]   Missing right caret, medium confidence, compat conversion + WARNING
  T3 [N]    Plain brackets, low confidence, requires cross-validation with citation_db (hit rate >50% and >5 to convert)
"""
import re
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


# ─── Regex Definitions ────────────────────────────────────────────

# Single numeric citation detection
_RE_T1 = re.compile(r'\[\^(\d+)\^\]')                                      # [^123^]
_RE_T2 = re.compile(r'\[\^(\d+)\](?!\^)')                                  # [^123]
_RE_T3 = re.compile(r'(?<!^\[)(?<!\n)\[(\d+)\](?!\()', re.MULTILINE)       # [123]

# Consecutive citation clusters (for batch replacement)
_RE_T1_CLUSTER = re.compile(r'(?:\[\^\d+\^\]\s*)+')
_RE_T2_CLUSTER = re.compile(r'(?:\[\^\d+\](?!\^)\s*)+')
_RE_T3_CLUSTER = re.compile(r'(?:(?<!^\[)(?<!\n)\[\d+\](?!\()\s*)+', re.MULTILINE)

# Non-numeric citation IDs: [^Insight6^], [^HC-02^], etc.
_RE_NON_NUMERIC_CARET = re.compile(r'\[\^([^\]^]*[a-zA-Z_-][^\]^]*)\^\]')
_RE_NON_NUMERIC_BRACKET = re.compile(r'\[\^([^\]^]*[a-zA-Z_-][^\]^]*)\]')

# Image placeholders
_RE_IMAGE_PLACEHOLDER = re.compile(r'[*_]*chart generation placeholder[：:][*_]*', re.IGNORECASE)
_RE_ABSOLUTE_IMAGE_PATH = re.compile(r'/(?:mnt|tmp|app)/[^\s)]+\.(?:png|jpg|jpeg|gif|svg)', re.IGNORECASE)

# Format name to regex mapping
_FORMAT_REGEX = {
    'caret':         (_RE_T1, _RE_T1_CLUSTER),
    'bracket_caret': (_RE_T2, _RE_T2_CLUSTER),
    'bracket':       (_RE_T3, _RE_T3_CLUSTER),
}

_CLUSTER_EXTRACT = {
    'caret':         r'\[\^(\d+)\^\]',
    'bracket_caret': r'\[\^(\d+)\]',
    'bracket':       r'\[(\d+)\]',
}


# ─── Format Detection ────────────────────────────────────────────

def detect_citation_format(markdown_content: str, citation_db: Dict[int, dict] = None) -> dict:
    """
    Detect citation format used in MD. Tiered fallback T1→T2→T3, returns on first match.

    Returns:
        {
            'format':        'caret' | 'bracket_caret' | 'bracket' | 'none',
            'confidence':    'high' | 'medium' | 'low' | 'none',
            'total_found':   int,
            'unique_found':  int,
            'db_match_count': int,
            'db_match_rate': float,
            'converted':     bool,   # whether conversion should proceed
            'message':       str,
        }
    """
    if citation_db is None:
        citation_db = {}

    def _check(regex, fmt_name, confidence):
        matches = regex.findall(markdown_content)
        if not matches:
            return None
        ids = [int(m) for m in matches]
        unique_ids = set(ids)
        db_hits = unique_ids & set(citation_db.keys())
        rate = len(db_hits) / len(unique_ids) if unique_ids else 0.0
        return {
            'format': fmt_name,
            'confidence': confidence,
            'total_found': len(matches),
            'unique_found': len(unique_ids),
            'db_match_count': len(db_hits),
            'db_match_rate': rate,
        }

    # T1: [^N^] — Standard format
    r = _check(_RE_T1, 'caret', 'high')
    if r:
        r['converted'] = True
        r['message'] = f"Standard format [^N^], {r['total_found']} markers, {r['db_match_count']} DB matches"
        return r

    # T2: [^N] — Missing right caret
    r = _check(_RE_T2, 'bracket_caret', 'medium')
    if r:
        r['converted'] = True
        r['message'] = (
            f"Non-standard format [^N] (missing right caret), {r['total_found']} markers, "
            f"T2 compat mode, {r['db_match_count']} DB matches"
        )
        return r

    # T3: [N] — Plain brackets, requires cross-validation
    r = _check(_RE_T3, 'bracket', 'low')
    if r:
        if r['db_match_count'] > 5 and r['db_match_rate'] > 0.5:
            r['converted'] = True
            r['message'] = (
                f"Non-standard format [N], {r['total_found']} markers, "
                f"DB hit rate {r['db_match_rate']:.0%} ({r['db_match_count']}/{r['unique_found']}), "
                f"T3 compat mode"
            )
        else:
            r['converted'] = False
            r['message'] = (
                f"Suspected citations [N] {r['total_found']} markers, "
                f"DB hit rate {r['db_match_rate']:.0%} ({r['db_match_count']}/{r['unique_found']}), "
                f"insufficient confidence, skipping conversion"
            )
        return r

    return {
        'format': 'none', 'confidence': 'none',
        'total_found': 0, 'unique_found': 0,
        'db_match_count': 0, 'db_match_rate': 0.0,
        'converted': False, 'message': 'No citation markers detected',
    }


# ─── Core Conversion ────────────────────────────────────────────

def convert_citations(markdown_content: str, citation_db: Dict[int, dict]) -> tuple:
    """
    One-stop citation conversion: detect format → build mapping → replace text.

    Merges all calls into a single entry point to avoid redundant detect_citation_format calls.

    Returns:
        (converted_content, id_to_display_num, detection_result)
        - converted_content: MD text with citations replaced by ^N^ superscripts
        - id_to_display_num: {original_citation_id: display_number} mapping
        - detection_result: detect_citation_format return value
    """
    detection = detect_citation_format(markdown_content, citation_db)
    logger.info(detection['message'])

    id_to_display_num = {}

    if not detection['converted']:
        return markdown_content, id_to_display_num, detection

    fmt = detection['format']
    item_regex, cluster_regex = _FORMAT_REGEX[fmt]
    extract_pattern = _CLUSTER_EXTRACT[fmt]

    # Build mapping by first-appearance order (skip IDs not in DB)
    display_num = 1
    for match in item_regex.finditer(markdown_content):
        cid = int(match.group(1))
        if cid not in citation_db:
            continue
        if cid not in id_to_display_num:
            id_to_display_num[cid] = display_num
            display_num += 1

    logger.info(f"Built {len(id_to_display_num)} citation mappings")

    # Replace consecutive citation clusters
    missing_ids = set()

    def _replace_cluster(match):
        ids = re.findall(extract_pattern, match.group(0))
        nums = []
        for id_str in ids:
            cid = int(id_str)
            if cid in id_to_display_num:
                nums.append(str(id_to_display_num[cid]))
            else:
                missing_ids.add(cid)
        if not nums:
            return ''
        return ' '.join(f'^{n}^' for n in nums)

    converted = cluster_regex.sub(_replace_cluster, markdown_content)

    if missing_ids:
        logger.warning(f"Citation IDs not in citation_db, removed from body: {sorted(missing_ids)}")

    logger.info(f"Conversion complete, {len(id_to_display_num)} citations replaced with superscripts")
    return converted, id_to_display_num, detection


# ─── Edge Case Detection ──────────────────────────────────────────

def detect_edge_cases(markdown_content: str) -> List[str]:
    """
    Detect edge cases in MD, return WARNING list only (no content modification).

    Detection items:
      1. Non-numeric citation IDs ([^Insight6^], etc.) — cannot match citation_db
      2. Image placeholder text (chart placeholders / absolute image paths)
    """
    warnings = []

    # 1. Non-numeric citations
    t1_hits = _RE_NON_NUMERIC_CARET.findall(markdown_content)
    t2_hits = _RE_NON_NUMERIC_BRACKET.findall(markdown_content)
    unique = sorted(set(t1_hits + t2_hits))
    if unique:
        total = len(t1_hits) + len(t2_hits)
        preview = unique[:20]
        suffix = '...' if len(unique) > 20 else ''
        warnings.append(
            f"Detected {total} non-numeric citation markers ({len(unique)} unique), "
            f"cannot match citation_db, kept as plain text: {preview}{suffix}"
        )

    # 2. Image placeholders
    ph = _RE_IMAGE_PLACEHOLDER.findall(markdown_content)
    ap = _RE_ABSOLUTE_IMAGE_PATH.findall(markdown_content)
    if ph or ap:
        parts = []
        if ph:
            parts.append(f"{len(ph)} chart generation placeholders")
        if ap:
            parts.append(f"{len(ap)} container absolute path images (not available locally, displayed as text)")
        warnings.append(f"Image placeholders: {'; '.join(parts)}")

    return warnings
