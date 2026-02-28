import os
import fitz  # PyMuPDF
import numpy as np
import cv2
from pathlib import Path

# ==========================================================
# BASE PATH (STREAMLIT SAFE)
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent

PDF_FOLDER = BASE_DIR / "pdf_input"
OUT_DIR    = BASE_DIR / "rev_crops"

DPI = 300

OUT_DIR.mkdir(parents=True, exist_ok=True)

# PDF TO IMAGE 

def pdf_to_image(pdf_path, dpi=300):

    doc = fitz.open(pdf_path)
    page = doc.load_page(0)  # first page only

    pix = page.get_pixmap(dpi=dpi)

    img = np.frombuffer(pix.samples, dtype=np.uint8)
    img = img.reshape(pix.height, pix.width, pix.n)

    if pix.n == 4:  # RGBA → RGB
        img = img[:, :, :3]

    doc.close()
    return img


pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf")]

print(f"Found {len(pdf_files)} PDFs")

for pdf_file in pdf_files:

    pdf_path = PDF_FOLDER / pdf_file
    base = Path(pdf_file).stem

    print(f"Converting - {pdf_file}")

    try:
        img = pdf_to_image(str(pdf_path), DPI)

        out_path = OUT_DIR / f"{base}_p001.png"
        cv2.imwrite(str(out_path), img)

        print(f"   Saved - {out_path}")

    except Exception as e:
        print(f"ERROR - {pdf_file} - {e}")

print("\nDONE")