import csv
import io
import re


def inspect_snp_file(file_field, max_preview_lines=80):
    # Return both parsed SNP rows and simple PC/NC control checks for the UI.
    text = read_text(file_field)
    rows = parse_rows(text)
    snp_rows = [row for row in rows if row.get("snp_id")]
    upper_text = text.upper()

    return {
        "raw_preview": "\n".join(text.splitlines()[:max_preview_lines]),
        "snp_rows": snp_rows[:50],
        "snp_count": len(snp_rows),
        "pc_check_passed": has_control_marker(upper_text, ["PC", "POSITIVE_CONTROL", "POSITIVE CONTROL"]),
        "nc_check_passed": has_control_marker(upper_text, ["NC", "NEGATIVE_CONTROL", "NEGATIVE CONTROL"]),
    }


def update_snp_checks(record):
    inspection = inspect_snp_file(record.data_file)
    record.snp_count = inspection["snp_count"]
    record.pc_check_passed = inspection["pc_check_passed"]
    record.nc_check_passed = inspection["nc_check_passed"]
    record.save(update_fields=["snp_count", "pc_check_passed", "nc_check_passed"])
    return inspection


def read_text(file_field):
    # Try common encodings seen in lab exports before falling back safely.
    with file_field.open("rb") as source:
        data = source.read()
    for encoding in ("utf-8-sig", "utf-8", "big5", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_rows(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    sample = "\n".join(lines[:10])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel_tab if "\t" in sample else csv.excel

    reader = csv.reader(io.StringIO("\n".join(lines)), dialect)
    raw_rows = list(reader)
    if not raw_rows:
        return []

    header = [cell.strip().lower() for cell in raw_rows[0]]
    has_header = any(name in header for name in ["rsid", "snp", "snp_id", "genotype", "chromosome"])
    data_rows = raw_rows[1:] if has_header else raw_rows

    parsed = []
    for row in data_rows:
        cells = [cell.strip() for cell in row]
        if not cells:
            continue
        snp_id = find_snp_id(cells)
        if not snp_id:
            continue
        parsed.append(
            {
                "snp_id": snp_id,
                "chromosome": value_at(cells, header, ["chromosome", "chr"], 1),
                "position": value_at(cells, header, ["position", "pos"], 2),
                "genotype": value_at(cells, header, ["genotype", "call"], 3),
                "raw": " | ".join(cells),
            }
        )
    return parsed


def find_snp_id(cells):
    for cell in cells:
        if re.match(r"^rs\d+$", cell, re.IGNORECASE):
            return cell
    if cells and not is_control_row(cells):
        return cells[0]
    return ""


def value_at(cells, header, names, fallback_index):
    for name in names:
        if name in header:
            index = header.index(name)
            return cells[index] if index < len(cells) else ""
    return cells[fallback_index] if fallback_index < len(cells) else ""


def has_control_marker(upper_text, markers):
    for marker in markers:
        if re.search(rf"(^|[^A-Z0-9]){re.escape(marker)}([^A-Z0-9]|$)", upper_text):
            return True
    return False


def is_control_row(cells):
    joined = " ".join(cells).upper()
    return "CONTROL" in joined or joined in {"PC", "NC"}
