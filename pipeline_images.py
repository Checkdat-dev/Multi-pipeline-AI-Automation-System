import os
import cv2
import numpy as np
import fitz
from pathlib import Path


# ==========================================================
# PDF → IMAGE
# ==========================================================
def pdf_to_image(pdf_path, dpi=300):

    doc = fitz.open(pdf_path)
    page = doc.load_page(0)

    pix = page.get_pixmap(dpi=dpi)

    img = np.frombuffer(pix.samples, dtype=np.uint8)
    img = img.reshape(pix.height, pix.width, pix.n)

    if pix.n == 4:
        img = img[:, :, :3]

    doc.close()
    return img


# ==========================================================
# CROP FOR 28-LABEL
# ==========================================================
def crop_stamp_28(img):

    h, w = img.shape[:2]

    x_start = int(w * 0.76)
    y_start = int(h * 0.88)
    x_end   = w
    y_end   = int(h * 0.97)

    return img[y_start:y_end, x_start:x_end]


# ==========================================================
# CROP FOR REVISION
# ==========================================================
def crop_stamp_rev(img):

    h, w = img.shape[:2]

    x_start = int(w * 0.70)
    y_start = int(h * 0.80)
    x_end   = int(w * 0.90)
    y_end   = int(h * 0.93)

    return img[y_start:y_end, x_start:x_end]


# ==========================================================
# MAIN PIPELINE FUNCTION
# ==========================================================
def run_image_pipeline(PDF_FOLDER, OUTPUT_DIR):

    PDF_FOLDER = Path(PDF_FOLDER)
    OUTPUT_DIR = Path(OUTPUT_DIR)

    PDF_FOLDER.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nIMAGE PIPELINE STARTED")

    for pdf_file in sorted(os.listdir(PDF_FOLDER)):

        if not pdf_file.lower().endswith(".pdf"):
            continue

        pdf_path = PDF_FOLDER / pdf_file
        base = Path(pdf_file).stem

        print(f"\nProcessing: {pdf_file}")

        try:

            img = pdf_to_image(pdf_path, dpi=300)

            stamp_28 = crop_stamp_28(img)
            stamp_rev = crop_stamp_rev(img)

            if stamp_28.size == 0 or stamp_rev.size == 0:
                print("WARNING: Empty crop detected →", pdf_file)
                continue

            file_output_dir = OUTPUT_DIR / base
            file_output_dir.mkdir(parents=True, exist_ok=True)

            out_28  = file_output_dir / "stamp28.png"
            out_rev = file_output_dir / "stampREV.png"

            cv2.imwrite(str(out_28), stamp_28)
            cv2.imwrite(str(out_rev), stamp_rev)

            print("Folder created:", file_output_dir)
            print("28-stamp saved")
            print("REV-stamp saved")

        except Exception as e:
            print(f"ERROR processing {pdf_file}: {e}")

    print("\nIMAGE PIPELINE COMPLETE")

    return OUTPUT_DIR