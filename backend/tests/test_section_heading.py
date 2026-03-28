from app.parsers.section_heading import (
    find_first_table_caption_in_paragraph,
    find_table_caption_in_text,
    infer_section_from_table_name,
    merge_page_section_with_inferred,
    normalize_table_label,
    parse_section_heading_line,
    table_caption_labels_from_page_text,
    validate_section_id,
)


def test_parse_bold_subsection_line():
    assert parse_section_heading_line("- **6.7.2** Technical Assessment Guidance") == (
        "6.7.2",
        "Technical Assessment Guidance",
    )


def test_parse_section_plain():
    assert parse_section_heading_line("6.7 Technical Assessment") == ("6.7", "Technical Assessment")


def test_parse_section_number_only():
    assert parse_section_heading_line("6.2.7") == ("6.2.7", None)


def test_infer_section_from_table_label():
    assert infer_section_from_table_name("6.7-1") == "6.7"
    assert infer_section_from_table_name("2.1-1") == "2.1"
    assert infer_section_from_table_name("D-1") is None


def test_merge_page_section_prefers_more_specific():
    assert merge_page_section_with_inferred("6.7.2", "6.7") == "6.7.2"
    assert merge_page_section_with_inferred("6.0", "6.7") == "6.7"
    assert merge_page_section_with_inferred("6", "6.7") == "6.7"
    assert merge_page_section_with_inferred(None, "6.7") == "6.7"


def test_normalize_table_label_dashes():
    assert normalize_table_label("6.7–1") == "6.7-1"


def test_find_table_in_markdown_cell():
    md = "|  | Table 6.7-1 | Purpose and Results |\n| --- | --- | --- |"
    assert find_table_caption_in_text(md) == "6.7-1"


def test_find_first_table_in_paragraph_mid_sentence():
    text = "For more detail, see Table 3.11-1 in the tailoring section.\n"
    assert find_first_table_caption_in_paragraph(text) == "3.11-1"


def test_page_captions_order():
    page = "Some intro\nTABLE 6.7-1 Purpose and Results\n| a | b |\n|---|---|"
    assert table_caption_labels_from_page_text(page) == ["6.7-1"]


def test_validate_section_id_rejects_noise():
    assert validate_section_id("2210.1") is None
    assert validate_section_id("2.1") == "2.1"
    assert validate_section_id("4.0") == "4.0"
    assert validate_section_id("6.7.2") == "6.7.2"


def test_parse_section_heading_rejects_invalid():
    assert parse_section_heading_line("2210.1 Noise") is None
