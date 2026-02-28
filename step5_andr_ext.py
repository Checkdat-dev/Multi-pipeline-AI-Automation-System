import os
import re
import cv2
import numpy as np
import pandas as pd
from datetime import datetime
import easyocr
from pathlib import Path

# ==========================================================
# BASE PATH (STREAMLIT SAFE ONLY CHANGE)
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent

IMAGE_DIR = BASE_DIR / "rev_crops"
OUT_EXCEL = BASE_DIR / "revision_extraction.xlsx"
DEBUG_DIR = BASE_DIR / "revision_extraction"

os.makedirs(DEBUG_DIR, exist_ok=True)

LEFT_FRACTION_DEFAULT   = 0.72
TOP_FRACTION_DEFAULT    = 0.79
RIGHT_FRACTION_DEFAULT  = 0.86
BOTTOM_FRACTION_DEFAULT = 0.88

TOP_FRACTION_LOGO    = 0.825
BOTTOM_FRACTION_LOGO = 0.885

MAX_DIM = 2200

reader = easyocr.Reader(["en"], gpu=False)

# ==========================================================
# REGEX
# ==========================================================
DATE_RE = re.compile(
    r"\b(\d{4}[-/.]\d{2}[-/.]\d{2})\b|"
    r"\b(\d{2}[-/.]\d{2}[-/.]\d{4})\b"
)

REV_RE = re.compile(r"\b([A-G])(?:\.(\d))?\b")
OCR_REV_MAP = {
    "(": "C",
    ")": "D",
}

def bbox_width(bbox):
    xs = [p[0] for p in bbox]
    return max(xs) - min(xs)

# ==========================================================
# TABLE DETECTOR
# ==========================================================

def has_table_structure(candidates):

    if not candidates:
        return False

    ys = sorted([c[1] for c in candidates])
    ROW_TOL = 18

    row_groups = []
    current = [ys[0]]

    for y in ys[1:]:
        if abs(y - current[-1]) <= ROW_TOL:
            current.append(y)
        else:
            row_groups.append(current)
            current = [y]

    row_groups.append(current)

    largest_row = max(row_groups, key=len)
    return len(largest_row) >= 2

# ==========================================================
# REV WORD LOGIC
# ==========================================================

def extract_revision_from_word(txt):

    t = txt.upper()
    m = re.search(r"\bREV[:\-\s]*([A-G])\b", t)

    if m:
        return m.group(1)

    return None

# ==========================================================
# PREPROCESSING
# ==========================================================

def preprocess_letter_recovery(gray):
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
    closed = cv2.morphologyEx(blur, cv2.MORPH_CLOSE, kernel)
    clahe = cv2.createCLAHE(3.5, (8, 8)).apply(closed)
    return clahe

def preprocess_medium(gray):
    g = cv2.createCLAHE(3.0, (8, 8)).apply(gray)
    blur = cv2.GaussianBlur(g, (0, 0), 1.0)
    return cv2.addWeighted(g, 1.5, blur, -0.5, 0)

def preprocess_light_text(gray):
    inv = cv2.bitwise_not(gray)
    clahe = cv2.createCLAHE(4.0, (8, 8)).apply(inv)
    thr = cv2.adaptiveThreshold(
        clahe, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 5
    )
    return thr

PREPROCESSORS = [
    ("LETTER", preprocess_letter_recovery),
    ("MEDIUM", preprocess_medium),
    ("LIGHT", preprocess_light_text),
]

# ==========================================================
# HELPERS
# ==========================================================

def safe_resize(gray):

    if gray is None or gray.size == 0:
        return gray

    h, w = gray.shape
    scale = min(MAX_DIM / h, MAX_DIM / w, 1.0)

    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale)

    return gray

def clamp(v, low, high):
    return max(low, min(v, high))

def parse_date(text):

    m = DATE_RE.search(text)
    if not m:
        return None

    raw = m.group(0).replace(".", "-").replace("/", "-")

    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass

    return None

def normalize_revision(letter, digit=None):
    return f"{letter}.{digit}" if digit else letter

def repair_ocr_token(t):
    t = t.strip().upper()
    if t in OCR_REV_MAP:
        return OCR_REV_MAP[t]
    return t

def is_rev_row(text):
    return "REV" in text.upper()

# ==========================================================
# SAFE REV EXTRACTION
# ==========================================================

def extract_rev_from_text_safely(txt: str):

    if not isinstance(txt, str):
        return None

    raw = txt.upper().strip()
    if not raw:
        return None

    t = raw.replace(",", ".")
    t = t.replace("/", ".").replace("\\", ".").replace("-", ".").replace(":", ".")

    m = re.search(r"\b([A-G])\.(\d)", t)
    if m:
        return f"{m.group(1)}.{m.group(2)}"

    m = re.search(r"\b([A-G])\s+(\d)", raw)
    if m:
        return f"{m.group(1)}.{m.group(2)}"

    m = re.search(r"\b([A-G])\.(I|L|\|)", t)
    if m:
        return f"{m.group(1)}.1"

    m = re.search(r"\b([A-G])\s+(I|L|\|)", raw)
    if m:
        return f"{m.group(1)}.1"

    return None

# ==========================================================
# OCR ENGINE
# ==========================================================

def run_ocr_on_crop(gray_crop, name, tag):

    if gray_crop is None or gray_crop.size == 0:
        return None, None

    gray_crop = safe_resize(gray_crop)

    all_candidates = []
    rev_row_candidates = []

    for ptag, fn in PREPROCESSORS:

        proc = fn(gray_crop)
        if proc is None:
            continue

        cv2.imwrite(str(DEBUG_DIR / f"{name}_{tag}_{ptag}.png"), proc)

        ocr = reader.readtext(proc, detail=1)

        print("\n==============================")
        print(f"OCR RAW - {name} [{tag}-{ptag}]")
        print("==============================")

        for bbox, txt, conf in ocr:

            if conf < 0.30:
                continue

            print(f"Detected - '{txt}' | CONF = {conf:.3f}")

            txt_raw = txt
            txt_clean = txt.strip().upper()

            date = parse_date(txt_clean)

            ys = [p[1] for p in bbox]
            y_center = sum(ys) / 4

            rev_from_word = extract_revision_from_word(txt_clean)
            if rev_from_word:
                entry = (conf, y_center, rev_from_word, date)
                all_candidates.append(entry)
                if is_rev_row(txt_raw):
                    rev_row_candidates.append(entry)

            if txt_clean in OCR_REV_MAP:
                rev = OCR_REV_MAP[txt_clean]
                entry = (conf, y_center, rev, None)
                all_candidates.append(entry)
                if is_rev_row(txt_raw):
                    rev_row_candidates.append(entry)

            token = repair_ocr_token(txt_clean)
            width = bbox_width(bbox)

            if width <= 120:
                m = re.match(r"^([A-G])(?:\.([1-9]))?$", token)
                if m:
                    rev = normalize_revision(m.group(1), m.group(2))
                    entry = (conf, y_center, rev, date)
                    all_candidates.append(entry)
                    if is_rev_row(txt_raw):
                        rev_row_candidates.append(entry)

            rev_long = extract_rev_from_text_safely(txt_raw)
            if rev_long:
                entry = (conf, y_center, rev_long, date)
                all_candidates.append(entry)
                if is_rev_row(txt_raw):
                    rev_row_candidates.append(entry)

    candidates = rev_row_candidates if rev_row_candidates else all_candidates

    if not candidates:
        print("No revision candidates found")
        return None, None

    if not has_table_structure(all_candidates):
        print("NO TABLE DETECTED - RETURN EMPTY")
        return None, None

    print("TABLE DETECTED")

    if rev_row_candidates:
        print("USING REV ROW PRIORITY")
        rev_row_candidates.sort(key=lambda x: x[1])
        conf, y, rev, date = rev_row_candidates[0]
    else:
        print("FALLBACK - ORIGINAL LOGIC")
        all_candidates.sort(key=lambda x: x[1])
        conf, y, rev, date = all_candidates[0]

    print("FINAL SELECTION")
    print(f"Selected REV - {rev}")
    print(f"Confidence   - {conf:.3f}")
    print(f"Y Position   - {y:.2f}")

    return rev, date.date().isoformat() if date else ""

# ==========================================================
# IMAGE EXTRACTION
# ==========================================================

def extract_revision_from_image(gray, name):

    h, w = gray.shape

    x1 = clamp(int(w * LEFT_FRACTION_DEFAULT), 0, w)
    x2 = clamp(int(w * RIGHT_FRACTION_DEFAULT), 0, w)

    y1 = clamp(int(h * TOP_FRACTION_DEFAULT), 0, h)
    y2 = clamp(int(h * BOTTOM_FRACTION_DEFAULT), 0, h)

    if y2 > y1:
        print(f"TRY FIXED REGION - {name}")
        rev, d = run_ocr_on_crop(gray[y1:y2, x1:x2], name, "FIXED")
        if rev:
            return rev, d

    y1 = clamp(int(h * TOP_FRACTION_LOGO), 0, h)
    y2 = clamp(int(h * BOTTOM_FRACTION_LOGO), 0, h)

    if y2 > y1:
        print(f"TRY LOGO REGION - {name}")
        rev, d = run_ocr_on_crop(gray[y1:y2, x1:x2], name, "LOGO")
        if rev:
            return rev, d

    return None, None

# ==========================================================
# RUN
# ==========================================================

rows = []
image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(".png")]

SAVE_INTERVAL = 10

for idx, f in enumerate(image_files, start=1):

    print("\n======================================")
    print(f"PROCESSING - {f}")
    print("======================================")

    img = cv2.imread(str(IMAGE_DIR / f))
    if img is None:
        continue

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    rev, date = extract_revision_from_image(gray, Path(f).stem)

    print(f"RESULT - {f} - {rev}")

    rows.append({
        "FILE": f,
        "FINAL_REV": rev if rev else "_",
        "REV_DATE": date if date else ""
    })

    if idx % SAVE_INTERVAL == 0:
        pd.DataFrame(rows).to_excel(OUT_EXCEL, index=False)
        print(f"AUTOSAVED AFTER {idx} IMAGES")

pd.DataFrame(rows).to_excel(OUT_EXCEL, index=False)
print("DONE")