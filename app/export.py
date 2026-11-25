"""Minimal pure-Python OOXML (.xlsx) spreadsheet builder with zero external dependencies."""
import io
import re
import zipfile
from xml.sax.saxutils import escape

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Hisobot" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""


MISSING = {"helmet": "Kaskasiz", "vest": "Jiletsiz", "entry": "Taqiqlangan hududda"}
STATUS = {"yangi": "Yangi", "ko'rildi": "Ko'rildi", "hal_qilindi": "Hal qilindi"}
_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _cell(ref: str, value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{value}</v></c>'
    text = escape(_ILLEGAL.sub("", str(value if value is not None else "")))
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def build_xlsx(rows: list[dict]) -> bytes:
    """Build an .xlsx file bytes from incident rows."""
    headers = ["ID", "Vaqt", "Qoida buzilishi", "Zona", "Kamera", "Holat"]
    cols = ["A", "B", "C", "D", "E", "F"]

    xml_rows = []
    # Header row
    hdr_cells = "".join(_cell(f"{cols[i]}1", h) for i, h in enumerate(headers))
    xml_rows.append(f'<row r="1">{hdr_cells}</row>')

    for idx, r in enumerate(rows, start=2):
        vals = [
            r.get("id", ""),
            r.get("ts", ""),
            ", ".join(MISSING.get(m, m) for m in str(r.get("missing", "")).split(",") if m),
            r.get("zone_name") or ("Ha" if r.get("zone") else "Yo'q"),
            r.get("camera", ""),
            STATUS.get(r.get("status", "yangi"), r.get("status", "")),
        ]
        cells = "".join(_cell(f"{cols[i]}{idx}", v) for i, v in enumerate(vals))
        xml_rows.append(f'<row r="{idx}">{cells}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        '</worksheet>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("xl/workbook.xml", _WORKBOOK)
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()
