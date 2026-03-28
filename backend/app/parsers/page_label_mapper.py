def build_page_mapping(records: list[dict]) -> dict[str, int]:
    """
    Maps printed page labels (string) to first observed pdf page index.
    """
    mapping: dict[str, int] = {}
    for rec in records:
        label = rec.get("printed_page_label")
        idx = rec.get("pdf_page_index")
        if label is None or idx is None:
            continue
        mapping.setdefault(str(label), int(idx))
    return mapping
