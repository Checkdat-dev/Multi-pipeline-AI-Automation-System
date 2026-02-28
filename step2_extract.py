# HERE WE EXTRACT TEXT FROM STAMPS USING TRAINED YOLO MODEL AND IMAGE PREPROCESSING

import os
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import easyocr
from ultralytics import YOLO
import cv2
import re

# ==========================================================
# BASE PATH (STREAMLIT SAFE)
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent

model_path = BASE_DIR / "best.pt"
image_dir  = BASE_DIR / "images_stamp"
raw_excel_out  = BASE_DIR / "raw_extraction.xlsx"

SAVE_DEBUG_CROPS = True
DEBUG_DIR = BASE_DIR / "debug_crops"
os.makedirs(DEBUG_DIR, exist_ok=True)

reader = easyocr.Reader(["sv", "en"], gpu=False)
model = YOLO(str(model_path))
names = model.names

LABELS = list(names.values())

# LABEL CONFIGARATION

RAW_OCR_LABELS = {
    "BESKRIVNING_ROW_1",
    "DATUM"
}

RNP_LABEL  = "RITNINGSNUMMER_PROJEKT"
BLAD_LABEL = "BLAD"
LEVERANS_LABEL = "LEVERANS_ANDRINGS_PM"

# RNP PADDING

LEFT_PAD_FRAC  = 0.02
RIGHT_PAD_FRAC = 0.06
TOP_PAD_FRAC   = 0.03
BOT_PAD_FRAC   = 0.05

def apply_padding_rnp(x1, y1, x2, y2, img_w, img_h):

    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)

    x1 = max(0, x1 - int(bw * LEFT_PAD_FRAC))
    x2 = min(img_w, x2 + int(bw * RIGHT_PAD_FRAC))

    y1 = max(0, y1 - int(bh * TOP_PAD_FRAC))
    y2 = min(img_h, y2 + int(bh * BOT_PAD_FRAC))

    return x1, y1, x2, y2

# BLAD PADDING

BLAD_PAD_FRAC = 0.01

def apply_padding_blad(x1, y1, x2, y2, img_w, img_h):

    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)

    x1 = max(0, x1 - int(bw * BLAD_PAD_FRAC))
    x2 = min(img_w, x2 + int(bw * BLAD_PAD_FRAC))

    y1 = max(0, y1 - int(bh * BLAD_PAD_FRAC))
    y2 = min(img_h, y2 + int(bh * BLAD_PAD_FRAC))

    return x1, y1, x2, y2

# STANDARD PADDING

PAD_RULES = {
    "BANDEL": {"right": 0.02},
    "ANLAGGNINGSTYP": {"right": 0.03},
}

def apply_padding_standard(x1, x2, img_w, label):

    if label not in PAD_RULES:
        return x1, x2

    bw = x2 - x1

    if "right" in PAD_RULES[label]:
        x2 = min(img_w, x2 + int(bw * PAD_RULES[label]["right"]))

    return x1, x2

# RNP PREPROCESSING

def pp_rnp_lite(pil_crop):

    g = cv2.cvtColor(np.array(pil_crop), cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, None, fx=2.2, fy=2.2, interpolation=cv2.INTER_CUBIC)

    clahe = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8))
    g = clahe.apply(g)

    g = cv2.GaussianBlur(g, (3, 3), 0)
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)

    return g

# BLAD PREPROCESSING

def pp_blad(pil_crop):

    g = cv2.cvtColor(np.array(pil_crop), cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, None, fx=1.65, fy=1.65, interpolation=cv2.INTER_CUBIC)
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)

    return g

# LEVERANS PREPROCESSING

def pp_leverans(pil_crop):

    g = cv2.cvtColor(np.array(pil_crop), cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)

    g = cv2.GaussianBlur(g, (3, 3), 0)
    _, g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return g

# STANDARD PREPROCESSING

def pp_light(img):

    g = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)

    return g

def pp_light_soft(img):

    g = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)

    return g

# VALIDATION

def is_valid_blad(text):
    return bool(re.fullmatch(r"\d{1,4}", text.strip()))

# HELPERS

def list_images(folder: Path):
    exts = {".png",".jpg",".jpeg",".tif",".tiff",".bmp"}
    return [p for p in folder.iterdir() if p.suffix.lower() in exts]

def autosave(rows):

    df = pd.DataFrame(rows)
    df = df.fillna("").astype(str)

    raw_excel_out.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(raw_excel_out, index=False)

    print(f"Autosaved ({len(rows)} rows)")

# ==========================================================
# MAIN
# ==========================================================

def process_folder():

    rows = []
    image_paths = list_images(image_dir)

    for idx, img_path in enumerate(image_paths, start=1):

        pil_img = Image.open(img_path).convert("RGB")
        img_w, img_h = pil_img.size

        row = {label: "" for label in LABELS}
        row["Image"] = img_path.name

        best_blad = ""

        results = model(str(img_path), conf=0.07)[0]

        if results.boxes is not None:

            for i, box in enumerate(results.boxes):

                cls_id = int(box.cls[0])
                label_name = names.get(cls_id, str(cls_id))

                if label_name not in LABELS:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                if label_name == RNP_LABEL:

                    x1, y1, x2, y2 = apply_padding_rnp(x1, y1, x2, y2, img_w, img_h)
                    crop = pil_img.crop((x1, y1, x2, y2))

                    if SAVE_DEBUG_CROPS:
                        crop.save(DEBUG_DIR / f"{img_path.stem}_RNP_{i}.png")

                    processed = pp_rnp_lite(crop)
                    text_list = reader.readtext(processed, detail=0, paragraph=True)
                    text = " ".join(text_list)

                    if not row[label_name]:
                        row[label_name] = text

                elif label_name == BLAD_LABEL:

                    x1, y1, x2, y2 = apply_padding_blad(x1, y1, x2, y2, img_w, img_h)
                    crop = pil_img.crop((x1, y1, x2, y2))

                    if SAVE_DEBUG_CROPS:
                        crop.save(DEBUG_DIR / f"{img_path.stem}_BLAD_{i}.png")

                    processed = pp_blad(crop)
                    text_list = reader.readtext(processed, detail=0, paragraph=True)
                    detected_text = " ".join(text_list).strip()

                    if is_valid_blad(detected_text):

                        if not best_blad:
                            best_blad = detected_text
                        elif len(detected_text) < len(best_blad):
                            best_blad = detected_text

                elif label_name == LEVERANS_LABEL:

                    crop = pil_img.crop((x1, y1, x2, y2))

                    if SAVE_DEBUG_CROPS:
                        crop.save(DEBUG_DIR / f"{img_path.stem}_LEV_{i}.png")

                    processed = pp_leverans(crop)
                    text_list = reader.readtext(
                        processed,
                        detail=0,
                        paragraph=True,
                        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                    )

                    text = " ".join(text_list).strip()

                    if not row[label_name]:
                        row[label_name] = text

                else:

                    x1, x2 = apply_padding_standard(x1, x2, img_w, label_name)
                    crop = pil_img.crop((x1, y1, x2, y2))

                    if SAVE_DEBUG_CROPS:
                        crop.save(DEBUG_DIR / f"{img_path.stem}_{label_name}_{i}.png")

                    processed = pp_light_soft(crop) if label_name in RAW_OCR_LABELS else pp_light(crop)

                    text_list = reader.readtext(processed, detail=0, paragraph=True)
                    text = " ".join(text_list)

                    if not row[label_name]:
                        row[label_name] = text

        row["BLAD"] = best_blad
        rows.append(row)

        print("Processed:", img_path.name)

        if idx % 10 == 0:
            autosave(rows)

    autosave(rows)
    print("\nRAW extraction saved:", raw_excel_out)

# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    process_folder()