import google.generativeai as genai
import base64
import json
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def validate_cheque_image(image_path):

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    img_b64 = base64.b64encode(img_bytes).decode()

    prompt = """
    Decide whether the given image is a REAL BANK CHEQUE.

    A valid cheque must have:
    - Bank name
    - Cheque number
    - Payee line
    - Amount field
    - Signature area

    Return ONLY JSON.

    {
      "is_cheque": true/false,
      "reason": ""
    }
    """

    # 🔥 DYNAMICALLY FIND BEST AVAILABLE MODEL
    available = []
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception as e:
        print("Model list error:", e)

    best_model = "gemini-1.5-flash"
    for want in ["models/gemini-1.5-flash", "gemini-1.5-flash", "models/gemini-1.5-flash-latest", "gemini-1.5-flash-latest", "models/gemini-1.5-pro", "gemini-1.5-pro", "models/gemini-pro-vision", "gemini-pro-vision"]:
        if want in available:
            best_model = want
            break
            
    if best_model not in available and available:
        best_model = available[0]

    print("USING MODEL FOR VALIDATION:", best_model)

    try:
        # If it's gemini-pro-vision, it doesn't support response_mime_type=json
        if "pro-vision" in best_model:
            model = genai.GenerativeModel(model_name=best_model)
        else:
            model = genai.GenerativeModel(
                model_name=best_model,
                generation_config={"response_mime_type": "application/json"}
            )
    except Exception:
        model = genai.GenerativeModel(model_name=best_model)

    response = model.generate_content(
        contents=[{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                {"text": prompt}
            ]
        }]
    )

    try:
        result = json.loads(response.text)
        return result["is_cheque"], result["reason"]
    except:
        return False, "Gemini validation failed"
