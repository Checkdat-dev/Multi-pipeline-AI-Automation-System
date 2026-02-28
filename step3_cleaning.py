# ALL RAW DATA FROM EXTRACTION IS CLEANED IN THIS STEP

import pandas as pd
import re
from pathlib import Path

# ==========================================================
# BASE PATH (STREAMLIT / DEPLOYMENT SAFE)
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent

INPUT_EXCEL = BASE_DIR / "raw_extraction.xlsx"
OUTPUT_EXCEL = BASE_DIR / "cleaning_file.xlsx"
# NORMALIZATION

def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def clean_default(text):
    return normalize_text(text)


COMPANY_ALIASES = {
    "TYRÉNS": ["TYRÉNS", "TYRENS", "YRENS", "T.YRÉNS", "T YRÉNS"],
    "ÅF INFRASTRUCTURE AB": [
        "ÅF INFRASTRUCTURE AB",
        "AF INFRASTRUCTURE AB",
        "ÄF INFRASTRUCTURE AB",
    ],
    "SWECO": ["SWECO", "SWECO CIVIL AB"],
    "NCC": ["NCC", "NCO"],
    "BERGAB": ["BERGAB"],
    "NORCONSULT": ["NORCONSULT"],
    "TRAFIKVERKET": ["TRAFIKVERKET"],
    "AMBERG": ["AMBERG"],
}

def normalize_company(text):
    if not isinstance(text, str):
        return ""
    t = normalize_text(text).upper()
    t_compact = t.replace(" ", "")
    for canon, aliases in COMPANY_ALIASES.items():
        for a in aliases:
            if a.replace(" ", "") in t_compact:
                return canon
    return t

# LOGIC FOR PERSON NAME
def dot_person(name: str) -> str:
    name = name.strip()
    if "." in name:
        return name
    letters = re.findall(r"[A-ZÅÄÖ]", name)
    if len(letters) <= 3:
        return name
    if re.fullmatch(r"[A-ZÅÄÖ]{4,}", name):
        return name[0] + "." + name[1:]
    if re.fullmatch(r"[A-ZÅÄÖ]\s+[A-ZÅÄÖ]{3,}", name):
        return name[0] + "." + name.split()[1]
    return name

def clean_PERSON_LABEL(text):

    if not isinstance(text, str):
        return ""

    t = normalize_text(text).upper()

    t = re.sub(r"^I(?=[A-ZÅÄÖ])", "", t)
    t = re.sub(r"^[^A-ZÅÄÖ]+", "", t)
    t = re.sub(r"\b([A-Z])\s+([A-ZÅÄÖ]{3,})", r"\1.\2", t)

    t = t.replace(",", " / ")

    t = re.sub(r"([A-ZÅÄÖ])\s*[/|]\s*([A-ZÅÄÖ])", r"\1 / \2", t)
    t = re.sub(r"(TYRÉNS)\s+(JEB|JEK|FBE|PHN|MBM|THO)", r"\1 / \2", t)
    t = re.sub(r"(TYRÉNS)[I]", r"\1 / ", t)

    parts = [p.strip() for p in t.split("/") if p.strip()]

    cleaned = []

    for p in parts:

        c = normalize_company(p)

        if c in COMPANY_ALIASES:
            cleaned.append(c)
        else:
            cleaned.append(dot_person(p))

    return " / ".join(cleaned)

# SYMBOL REMOVER

def remove_symbols(text: str, keep_slash=False) -> str:

    if not isinstance(text, str):
        return ""

    t = normalize_text(text).upper()

    if keep_slash:
        t = re.sub(r"[^A-ZÅÄÖ0-9\s/]", " ", t)
    else:
        t = re.sub(r"[^A-ZÅÄÖ0-9\s]", " ", t)

    t = re.sub(r"\s+", " ", t)

    return t.strip()

# COLUMN CLEANERS

def clean_LEVERANTOR_1(text):

    if not isinstance(text, str):
        return ""

    t = normalize_text(text).upper()

    # --------------------------------------------------
    #  FIX OCR DAMAGE
    # --------------------------------------------------
    t = re.sub(r"^LEVERANTÖR\s*", "", t)
    t = re.sub(r"^LEVERANTOR\s*", "", t)
    t = re.sub(r"^VERANTOR\s*", "", t)
    t = re.sub(r"^EVERANTOR\s*", "", t)

    return normalize_company(t)


def clean_LEVERANTOR_2(text):
    if not isinstance(text, str):
        return ""
    t = normalize_text(text).upper()
    t = re.sub(r"^[^A-ZÅÄÖ]+", "", t)
    return normalize_company(t)

def clean_TITLE(text: str) -> str:
    if not isinstance(text, str):
        return ""
    t = normalize_text(text).upper()
    t = re.sub(r"VASTLANKEN", "VÄSTLÄNKEN", t)
    t = re.sub(r"VÄSTLANKEN", "VÄSTLÄNKEN", t)
    t = re.sub(r"^[^A-ZÅÄÖ]+", "", t)
    return t

# ============================================================
# TEKNIKOMRADE (UNCHANGED)
# ============================================================
def clean_TEKNIKOMRADE(text):
    if not isinstance(text, str):
        return ""
    t = normalize_text(text).upper()
    t = re.sub(r"[^A-ZÅÄÖ]", "", t)
    return t

# ============================================================
# GRANSKNINGSSTATUS
# ============================================================
def clean_GRANSKNINGSSTATUS_SYFTE(text):

    if not isinstance(text, str):
        return ""

    t = normalize_text(text).upper()
    t_norm = (
        t.replace("Ä", "A")
         .replace("Å", "A")
         .replace("Ö", "O")
    )

    compact = re.sub(r"\s+", "", t_norm)

    if "GODKAND" in compact:
        return "GODKÄND"

    if "FORGRANSKNING" in compact:
        return "FÖR GRANSKNING"

    if "FORFRAGNING" in compact:
        return "FÖRFRÅGNINGSUNDERLAG"

    return t


# ============================================================
# OTHER LABELS
# ============================================================
def clean_HANDLINGSTYP(text):
    if not isinstance(text, str):
        return ""
    t = normalize_text(text).upper()
    return t

def clean_ANLAGGNINGSTYP(text):
    if not isinstance(text, str):
        return ""
    t = normalize_text(text).upper()
    return t

# ============================================================
# KILOMETER_METER CLEANING 
# ============================================================
KM_PATTERN = re.compile(
    r"(\d{1,4})\s*([+/])?\s*(\d{1,3}(?:[.,]\d+)?)"
)

def trim_km(km):
    km = str(km)
    if len(km) > 3:
        km = km[-3:]
    return km.lstrip("0") or "0"

def normalize_meter(m):
    return str(m).replace(",", ".")
def clean_KILOMETER_METER(text):

    if not isinstance(text, str):
        return ""

    original = normalize_text(text)

    # keep starting symbol if present
    prefix = ""
    m_pref = re.match(r"^\s*([~≈])\s*", text)
    if m_pref:
        prefix = m_pref.group(1)

    t = normalize_text(text)

    # Fix broken "+"
    t = re.sub(r"(\d{3})\s+4\s+(\d{3})", r"\1+\2", t)

    matches = KM_PATTERN.findall(t)

    # if not matched, return raw (with symbol)
    if not matches:
        return (prefix + original).upper() if prefix else original.upper()

    sep_style = "/" if "/" in t else "+"

    values = []
    for km, sep, meter in matches:
        values.append(f"{trim_km(km)}{sep_style}{normalize_meter(meter)}")

    if len(values) == 1:
        return (prefix + values[0]).upper() if prefix else values[0]

    return ((prefix + f"{values[0]} - {values[1]}").upper() if prefix else f"{values[0]} - {values[1]}")


# ============================================================
# SKALA 
# ============================================================
def normalize_single_scale(val: str) -> str:

    val = val.strip()
    val = val.replace("-", ":")
    val = val.replace(".", ":")
    val = re.sub(r":+$", "", val)

    # ---------CRITICAL FIX → 1:1001500-----------------------
    
    m = re.fullmatch(r"1:(\d{2,4})(\d{2,4})", val)
    if m:
        return f"1:{m.group(1)} / 1:{m.group(2)}"

    # --------------------------------------------------
    # FIX → 11001500 / 1001500 STYLE DAMAGE
    # --------------------------------------------------
    m2 = re.fullmatch(r"1:?(\d{5,8})", val)
    if m2:
        digits = m2.group(1)

        if len(digits) >= 6:
            return f"1:{digits[:len(digits)//2]} / 1:{digits[len(digits)//2:]}"
    
    if re.fullmatch(r"1:\d+", val):
        return val

    if re.fullmatch(r"\d{2,5}", val):

        if len(val) == 4 and val.startswith("1"):
            val = val[1:]

        if len(val) == 5:
            val = val[:-1]

        return f"1:{val}"

    return val

def clean_LEVERANS_ANDRINGS_PM(text):

    if not isinstance(text, str):
        return ""

    t = normalize_text(text).upper()

    if not t:
        return ""
    if len(t) <= 4:
        return ""
    if not re.search(r"\d", t):
        return ""

    return t

def clean_SKALA(text):

    if not isinstance(text, str):
        return ""

    t = normalize_text(text)

    t = t.replace(",", " / ")
    t = t.replace(";", " / ")
    t = t.replace("\\", " / ")
    t = re.sub(r"\s*/\s*", " / ", t)

    parts = re.split(r"\s+|/", t)

    cleaned = [
        normalize_single_scale(p)
        for p in parts
        if p.strip()
    ]

    cleaned = list(dict.fromkeys(cleaned))

    return " / ".join(cleaned)

# ============================================================
# FORMAT
# ============================================================
def clean_FORMAT(text):
    if not isinstance(text, str):
        return ""

    t = normalize_text(text).upper()
    # AI → A1
    if t == "AI":
        return "A1"

    # A I → A1
    t = re.sub(r"^A[I|L]$", "A1", t)
    t = re.sub(r"^4(?=\d)", "A", t)
    t = re.sub(r"[^A-Z0-9]", "", t)

    return t

# ============================================================
# BESKRIVNING 
# ============================================================
def clean_BESKRIVNING_ROW_1(text):
    return remove_symbols(text)

def clean_BESKRIVNING_ROW_2(text):
    return remove_symbols(text)

def clean_BESKRIVNING_ROW_3(text):
    return remove_symbols(text)

def clean_BESKRIVNING_ROW_4(text):
    return remove_symbols(text, keep_slash=True)

def clean_ANDR(text):

    if not isinstance(text, str):
        return "_"

    t = normalize_text(text).upper()

    if not t:
        return "_"

    if re.fullmatch(r"[A-Z]\.\d+", t):
        return t

    compact = re.sub(r"[^A-Z0-9]", "", t)

    m = re.fullmatch(r"4(\d)", compact)
    if m:
        return f"A.{m.group(1)}"

    if "4" in compact:
        return "A"

    if re.fullmatch(r".*1.*", compact):
        if not re.fullmatch(r"[A-Z].*", compact):
            return "_.1"

    if re.fullmatch(r".*2.*", compact):
        if not re.fullmatch(r"[A-Z].*", compact):
            return "_.2"
    if re.fullmatch(r"[A-Z]", compact):
        return compact

    return "_"
def extract_rnp_from_image(image_name):

    return (
        str(image_name)
        .replace("_stamp.png", "")
        .replace(".png", "")
        .strip()
        .upper()
    )
def single_char_difference(a, b):

    if not a or not b:
        return False

    if len(a) != len(b):
        return False

    diff_count = sum(c1 != c2 for c1, c2 in zip(a, b))

    return diff_count == 1
def correct_rnp_using_image(ocr_val, image_val):

    ocr_val   = str(ocr_val).strip().upper()
    image_val = str(image_val).strip().upper()

    if single_char_difference(ocr_val, image_val):
        return image_val   

    return ocr_val

def clean_ritningsnummer_projekt(text: str) -> str:

    if not isinstance(text, str):
        return ""

    t = text.strip().upper()

    OCR_MAP = str.maketrans({
        "O": "0",
        "Q": "0",
        
    })

    t = t.translate(OCR_MAP)
    t = re.sub(r"BBP[0OQ]S", "BBP05", t)
    t = re.sub(r"(?<=\d)S(?=\d)", "5", t)
    t = re.sub(r"^[IJ1|/\\`']+(?=[A-Z0-9])", "", t)

    t = re.sub(r"RITNINGSNUMMER[_\s-]*PROJEKT", " ", t)
    t = re.sub(r"^[^A-Z0-9]+", "", t)

    t = re.sub(r"BBPO5", "BBP05", t)
    t = re.sub(r"BBPOS", "BBP05", t)
    t = re.sub(r"IBBPO5", "BBP05", t)

    t = re.sub(r"0\s+0", "0_0", t)
    t = re.sub(r"-00-", "-0_0-", t)

    t = re.sub(r"[/'`]+$", "", t)

    t = re.sub(r"\s*-\s*", "-", t)
    t = re.sub(r"\s+", "", t)

    m = re.search(r"\b([A-Z0-9]+-\d{2}-\d{3}-\d{4}-0_0-[A-Z0-9]+)\b", t)

    if not m:
        return t

    full = m.group(1)

    base, tail = full.rsplit("-0_0-", 1)

    tail = tail.replace("M", "1")

    if len(tail) > 4:
        tail = tail[:4]

    if len(tail) < 3:
        return base

    return f"{base}-0_0-{tail}"

def clean_blad(value):

    if not value:
        return ""

    value = str(value).strip()

    # Remove OCR junk
    value = value.replace("O", "0")   # OCR O → 0
    value = value.replace("I", "1")   # OCR I → 1
    value = value.replace("l", "1")   # OCR l → 1
    value = value.replace(".", "")    # Remove dots
    value = value.replace(",", "")    # Remove commas
    value = value.replace(" ", "")    # Remove spaces

    # Keep digits only
    value = "".join(ch for ch in value if ch.isdigit())

    # Length rules (YOUR MASTER LOGIC)
    if 2 <= len(value) <= 4:
        return value

    return value   # return anyway → validation decides error
def extract_blad_from_image(image_name):

    if not image_name:
        return ""

    image_name = str(image_name)

    image_name = (
        image_name
        .replace("_stamp.png", "")
        .replace("_pdf_stamp.png", "")
        .replace(".png", "")
    )

    m = re.search(r"(\\d+)$", image_name)

    if not m:
        return ""

    return m.group(1)


def normalize_blad(value):

    if not value:
        return ""

    value = str(value)

    value = value.replace("O", "0")
    value = value.replace("I", "1")
    value = value.replace("l", "1")

    value = "".join(ch for ch in value if ch.isdigit())

    return value
# ============================================================
# CLEANER MAP
# ============================================================
CLEANERS = {
    "RITNINGSNUMMER_PROJEKT" : clean_ritningsnummer_projekt,
    "LEVERANTOR_1": clean_LEVERANTOR_1,
    "LEVERANTOR_2": clean_LEVERANTOR_2,
    "SKAPAD_AV": clean_PERSON_LABEL,
    "GRANSKAD_AV": clean_PERSON_LABEL,
    "GODKAND_AV": clean_PERSON_LABEL,
    "TITLE": clean_TITLE,
    "ANDR": clean_ANDR,
    "TEKNIKOMRADE": clean_TEKNIKOMRADE,
    "GRANSKNINGSSTATUS_SYFTE": clean_GRANSKNINGSSTATUS_SYFTE,
    "HANDLINGSTYP": clean_HANDLINGSTYP,
    "ANLAGGNINGSTYP": clean_ANLAGGNINGSTYP,
    "LEVERANS_ANDRINGS_PM": clean_LEVERANS_ANDRINGS_PM,
    "KILOMETER_METER": clean_KILOMETER_METER,
    "BLAD": clean_blad,
    "SKALA": clean_SKALA,
    "FORMAT": clean_FORMAT,
    "BESKRIVNING_ROW_1": clean_BESKRIVNING_ROW_1,
    "BESKRIVNING_ROW_2": clean_BESKRIVNING_ROW_2,
    "BESKRIVNING_ROW_3": clean_BESKRIVNING_ROW_3,
    "BESKRIVNING_ROW_4": clean_BESKRIVNING_ROW_4,
}

# ============================================================
# RUN
# ============================================================
def main():

    df = pd.read_excel(INPUT_EXCEL, dtype=str, keep_default_na=False)
    df.columns = df.columns.str.strip()
    if "BLAD_STATUS" not in df.columns:
        df["BLAD_STATUS"] = ""

    for idx, row in df.iterrows():

        for col in df.columns:

            cleaner = CLEANERS.get(col, clean_default)

            cleaned_value = cleaner(row[col])
            if col == "BLAD":

                ocr_blad   = normalize_blad(row["BLAD"])
                image_blad = extract_blad_from_image(row["Image"])

                if not image_blad:
                    cleaned_value = ocr_blad

                else:
                    if ocr_blad == image_blad:
                        cleaned_value = ocr_blad     

                    else:
                        cleaned_value = ocr_blad      
                        df.at[idx, "BLAD_STATUS"] = "ERROR"

            if col == "RITNINGSNUMMER_PROJEKT":

                expected_value = extract_rnp_from_image(row["Image"])

                cleaned_value = correct_rnp_using_image(
                    cleaned_value,
                    expected_value
                )

            df.at[idx, col] = cleaned_value

    df.to_excel(OUTPUT_EXCEL, index=False)

    print(" CLEANING COMPLETE:", OUTPUT_EXCEL)

if __name__ == "__main__":
    main()
