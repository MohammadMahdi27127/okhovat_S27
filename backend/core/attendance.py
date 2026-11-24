"""Read the acceptance tab, returning only one member's ring."""
import csv
import io
import json
import logging
import os
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.request import Request, urlopen

SHEET = "1LFe8XI4vdu_-LfMQEPkRxqewg5_BX3BJo-f7NPwmcA4"
TAB = 643360414
LIMIT = 2 * 1024 * 1024
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩يىك٫", "01234567890123456789ییک.")
log = logging.getLogger("okhovat.attendance")


def clean(value):
    return re.sub(r"[\s\u200c\ufeff]+", "", str(value).translate(DIGITS))


def read_rows():
    credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_file:
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_file(credentials_file, scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly"])
        creds.refresh(lambda **kwargs: GoogleRequest()(**{**kwargs, "timeout": 4}))
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values:batchGetByDataFilter"
        query = {"dataFilters":[{"gridRange":{"sheetId":TAB}}],"valueRenderOption":"FORMATTED_VALUE"}
        req = Request(url, data=json.dumps(query).encode(), headers={
            "Authorization":"Bearer "+creds.token, "Content-Type":"application/json"})
    else:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid={TAB}"
        req = Request(url)
    with urlopen(req, timeout=4) as response:
        raw = response.read(LIMIT+1)
    if len(raw)>LIMIT:
        raise ValueError("sheet too large")
    if credentials_file:
        return json.loads(raw)["valueRanges"][0]["valueRange"].get("values",[])
    return csv.reader(io.StringIO(raw.decode("utf-8-sig")), strict=True)


def percent(value):
    raw=clean(value).rstrip("%٪")
    try:
        n=Decimal(raw)
        return float(n) if n.is_finite() and 0<=n<=100 else None
    except InvalidOperation:
        return None


def extract(rows, code):
    rows=iter(rows)
    grouped = False
    for row in rows:
        headers=[clean(v) for v in row]
        if headers[:1] == ["کدگروهی"] and headers[1:2] in (["تعدادحاضرین"], ["تعدادحاضران"]):
            grouped = True
            pct = 3
            break
        pct=next((i for i,h in enumerate(headers) if "درصد" in h and "حضور" in h),None)
        if pct is not None:
            break
    else:
        return {"status":"missing_column"}
    ring=next((i for i,h in enumerate(headers) if "حلقه" in h and "مسئول" not in h and "سرحلقه" not in h),None)
    name=next((i for i,h in enumerate(headers) if h in ("نام","نامکامل","نامونامخانوادگی","نامعضو")),None)
    surname=next((i for i,h in enumerate(headers) if h=="نامخانوادگی"),None)
    records={}
    block = None
    block_name = ""
    for index, row in enumerate(rows):
        def cell(i):
            return str(row[i]).strip() if i is not None and i<len(row) else ""
        key=clean(cell(0))
        if grouped:
            if key.isdecimal() and len(key) < 5 and not cell(2) and not cell(3):
                block, block_name = index, cell(1)
                continue
            if not key.isdecimal() or len(key) != 5:
                continue
        if not key:continue
        if key in records: # Ambiguous codes must not resolve a person's ring.
            records[key]=None
            continue
        label=cell(name)
        if name is not None and headers[name]=="نام" and surname is not None:
            label=(label+" "+cell(surname)).strip()
        ring_name = block_name if grouped else cell(ring)
        group_id = block if grouped else clean(ring_name) or None
        records[key] = (ring_name, (cell(1) if grouped else label) or key, percent(cell(pct)), group_id)
    own=records.get(clean(code))
    if own is None:return {"status":"unknown_code"}
    peers=[]
    if own[3] is not None:
        for key,person in records.items():
            if person and key!=clean(code) and person[3]==own[3]:
                peers.append({"name":person[1],"percent":person[2]})
    return {"status":"ok","percent":own[2],"ring":own[0],"peers":peers,
            "checked":datetime.now(timezone.utc).isoformat()}


def lookup(code):
    try:
        return extract(read_rows(),code)
    except Exception as exc:
        # Do not log the response, names, credentials or attendance values.
        log.warning("attendance_unavailable error_type=%s",type(exc).__name__)
        return {"status":"unavailable"}
