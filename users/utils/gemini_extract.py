import google.generativeai as genai
import base64
import json
import os
import re
from django.conf import settings

# ✅ Use environment variable (IMPORTANT)
genai.configure(api_key=settings.GEMINI_API_KEY)


def extract_cheque_details(image_path):

    # 📸 Read image
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    img_b64 = base64.b64encode(img_bytes).decode()

    # 🧠 Prompt
    prompt = """
    Extract cheque details from the image.

    Return ONLY valid JSON. No explanation.

    Fields:
    account_number, ifsc_code, cheque_number,
    payee_name, amount_words, amount_number,
    signature_remarks

    JSON format:
    {
        "account_number": "",
        "ifsc_code": "",
        "cheque_number": "",
        "payee_name": "",
        "amount_words": "",
        "amount_number": "",
        "signature_remarks": ""
    }
    """

    # 🤖 Gemini model
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    # 🚀 API call
    response = model.generate_content(
        contents=[{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                {"text": prompt}
            ]
        }]
    )

    # 🔍 DEBUG
    print("RAW GEMINI RESPONSE:", response)

    try:
        # ✅ SAFE TEXT HANDLING
        if hasattr(response, "text") and response.text:
            text = response.text.strip()
        else:
            print("Empty response from Gemini")
            return {
                "account_number": "",
                "ifsc_code": "",
                "cheque_number": "",
                "payee_name": "",
                "amount_words": "",
                "amount_number": "",
                "signature_remarks": "No response from AI"
            }

        # ✅ CLEAN JSON (remove ``` if exists)
        text = re.sub(r"```json|```", "", text).strip()

        # ✅ CONVERT TO DICT
        data = json.loads(text)

        # ✅ SAFE FINAL OUTPUT
        final_data = {
            "account_number": data.get("account_number", ""),
            "ifsc_code": data.get("ifsc_code", ""),
            "cheque_number": data.get("cheque_number", ""),
            "payee_name": data.get("payee_name", ""),
            "amount_words": data.get("amount_words", ""),
            "amount_number": data.get("amount_number", ""),
            "signature_remarks": data.get("signature_remarks", "")
        }

        return final_data

    except Exception as e:
        print("Gemini JSON Error:", e)

        return {
            "account_number": "",
            "ifsc_code": "",
            "cheque_number": "",
            "payee_name": "",
            "amount_words": "",
            "amount_number": "",
            "signature_remarks": "Error reading data"
        }