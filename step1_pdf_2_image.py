# -------------------------------------------------------------
# HERE WE CONVERT INPUT PDF TO PNG FILES 
# -------------------------------------------------------------

import os
import cv2
import numpy as np
import fitz
from pathlib import Path

# 🔥 BASE DIRECTORY (DEPLOYMENT SAFE)
BASE_DIR = Path(__file__).resolve().parent

PDF_FOLDER = BASE_DIR / "pdf_input"
OUTPUT_BASE = BASE_DIR
OUTPUT_STAMP = OUTPUT_BASE / "images_stamp"

os.makedirs(OUTPUT_STAMP, exist_ok=True)

# ===================== Function used to convert image to numpy array =====================

def pdf_to_image(pdf_path, dpi=300):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=dpi)

    img = np.frombuffer(pix.samples, dtype=np.uint8)
    img = img.reshape(pix.height, pix.width, pix.n)

    # RGBA → RGB
    if pix.n == 4:
        img = img[:, :, :3]

    doc.close()
    return img

# ===================== Crop stamp dimensions =====================

def crop_stamp(img):
    h, w = img.shape[:2]

    x_start = int(w * 0.76)
    y_start = int(h * 0.88)
    x_end = w
    y_end = int(h * 0.97)

    return img[y_start:y_end, x_start:x_end]

# ===================== Process all images =====================

for pdf_file in os.listdir(PDF_FOLDER):
    if not pdf_file.lower().endswith(".pdf"):
        continue

    pdf_path = PDF_FOLDER / pdf_file
    base = os.path.splitext(pdf_file)[0]

    print(f"Processing: {pdf_file}")

    try:
        img = pdf_to_image(str(pdf_path))
        stamp = crop_stamp(img)

        stamp_out = OUTPUT_STAMP / f"{base}_stamp.png"
        cv2.imwrite(str(stamp_out), stamp)

        print(f"   Stamp crop saved: {stamp_out}")

    except Exception as e:
        print(f"ERROR processing {pdf_file}: {e}")

print("\n ALL PDFs processed — ONLY stamp crops saved")