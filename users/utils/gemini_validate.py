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

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config={"response_mime_type": "application/json"}
    )

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
