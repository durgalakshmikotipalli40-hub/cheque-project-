import cv2
import numpy as np

# ---------------------------------------------------------
# STEP 1 — LOAD IMAGE + PREPROCESS
# ---------------------------------------------------------

def preprocess(img_path):
    img = cv2.imread(img_path)

    if img is None:
        return None, None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Remove noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection
    edges = cv2.Canny(blur, 80, 180)

    return img, edges


# ---------------------------------------------------------
# STEP 2 — FIND CHEQUE OUTLINE
# ---------------------------------------------------------

def detect_cheque_outline(edges):
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        return None

    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)

    if area < 50000:
        return None

    return cnt


# ---------------------------------------------------------
# STEP 3 — DETECT SIGNATURE
# ---------------------------------------------------------

def detect_signature(img):
    h, w = img.shape[:2]

    sig_region = img[int(h*0.60):int(h*0.90), int(w*0.55):int(w*0.95)]

    gray = cv2.cvtColor(sig_region, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    ink_pixels = np.sum(thresh == 255)
    total_pixels = thresh.size

    if total_pixels == 0:
        return False

    ink_ratio = ink_pixels / total_pixels

    if ink_ratio > 0.02:
        return True
    return False


# ---------------------------------------------------------
# STEP 4 — BLUR CHECK
# ---------------------------------------------------------

def is_blurry(gray):
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var < 50


# ---------------------------------------------------------
# STEP 5 — FINAL DECISION
# ---------------------------------------------------------

def process_cheque(img_path):
    img, edges = preprocess(img_path)

    if img is None:
        return "ERROR: Could not load image"
    
    if edges is None:
        return "ERROR: Image processing failed"

    # 1. Detect cheque boundary
    cheque_outline = detect_cheque_outline(edges)
    if cheque_outline is None:
        return "FORGED (Cheque boundary missing)"

    # 2. Check signature
    signature_ok = detect_signature(img)
    if not signature_ok:
        return "FORGED (Signature missing)"

    # 3. Blur / tampering check
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if is_blurry(gray):
        return "FORGED (Cheque is blurred / tampered)"

    return "VALID"