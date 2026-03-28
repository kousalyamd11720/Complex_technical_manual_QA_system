import re


DEFAULT_ACRONYMS = {
    "SE": "Systems Engineering",
    "TRL": "Technology Readiness Level",
    "KDP": "Key Decision Point",
    "SRR": "System Requirements Review",
    "PDR": "Preliminary Design Review",
    "CDR": "Critical Design Review",
    "FMEA": "Failure Modes and Effects Analysis",
    "RFP": "Request for Proposal",
    "SFR": "System Functional Requirements",
}


def expand_acronyms(text: str, glossary: dict[str, str] | None = None) -> str:
    """
    Expand each configured acronym once to "Long Form (ABBR)"; later uses stay "ABBR"
    so the answer does not repeat "Long Form (ABBR)" in every sentence.
    """
    glossary = glossary or DEFAULT_ACRONYMS
    out = text
    for short, long_form in sorted(glossary.items(), key=lambda kv: -len(kv[0])):
        token = rf"(?<!\()\b{re.escape(short)}\b(?!\s*\()"
        if not re.search(token, out):
            continue
        if re.search(rf"\b{re.escape(long_form)}\s*\({re.escape(short)}\)", out, flags=re.IGNORECASE):
            continue
        if re.search(rf"\b{re.escape(long_form)}\b", out, flags=re.IGNORECASE):
            out = re.sub(token, short, out, flags=re.IGNORECASE)
            continue

        used = False

        def repl(_m: re.Match[str]) -> str:
            nonlocal used
            if not used:
                used = True
                return f"{long_form} ({short})"
            return short

        out = re.sub(token, repl, out, flags=re.IGNORECASE)
    return out


def normalize_acronyms(text: str, glossary: dict[str, str] | None = None) -> str:
    glossary = glossary or DEFAULT_ACRONYMS
    expanded = text
    for short, long_form in glossary.items():
        if re.search(rf"\b{re.escape(short)}\b", text):
            if re.search(rf"\b{re.escape(long_form)}\b", expanded, flags=re.IGNORECASE):
                continue
            expanded = f"{expanded} {long_form}"
    return expanded
