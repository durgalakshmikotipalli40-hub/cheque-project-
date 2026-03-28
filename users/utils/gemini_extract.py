



# import google.generativeai as genai
# import base64
# import json

# genai.configure(api_key="AIzaSyAB1y26V-kGsGD5cvXGiSJSI5hgMnOD9Jw")




# def extract_cheque_details(image_path):
#     with open(image_path, "rb") as f:
#         img_bytes = f.read()

#     img_b64 = base64.b64encode(img_bytes).decode()

#     prompt = """
#     You MUST output VALID JSON ONLY.
#     NO markdown, NO text, NO explanation.

#     Extract these fields exactly:

#     {
#       "account_number": "",
#       "ifsc_code": "",
#       "cheque_number": "",
#       "signature_present": "",
#       "signature_remarks": ""
#     }
#     """

#     model = genai.GenerativeModel("gemini-2.5-flash")

#     response = model.generate_content(
#         contents=[
#             {
#                 "role": "user",
#                 "parts": [
#                     {
#                         "inline_data": {
#                             "mime_type": "image/jpeg",
#                             "data": img_b64
#                         }
#                     },
#                     {"text": prompt}
#                 ]
#             }
#         ]
#     )

#     raw = response.text.strip()

#     try:
#         return json.loads(raw)
#     except:
#         return {
#             "account_number": "",
#             "ifsc_code": "",
#             "cheque_number": "",
#             "signature_present": "",
#             "signature_remarks": "Gemini did not return JSON"
#         }

import google.generativeai as genai
import base64
import json

genai.configure(api_key="AIzaSyBEFr8RZAlFQ4w-fUJ3oHyzqcZzjQy8mzM")



def extract_cheque_details(image_path):

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    img_b64 = base64.b64encode(img_bytes).decode()

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

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
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
        text = response.text.strip()

        # 🔥 REMOVE ```json ``` ISSUE
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)

        # 🔥 ENSURE ALL KEYS EXIST
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




# import google.generativeai as genai
# import base64
# import json

# genai.configure(api_key="AIzaSyAl3ZIxyaG21Ht4iMVq_1obTC9g1PXJL80")


# def extract_cheque_details(image_path):

#     with open(image_path, "rb") as f:
#         img_bytes = f.read()

#     img_b64 = base64.b64encode(img_bytes).decode()

#     prompt = """
#     Extract the following details from the cheque image.
#     Return ONLY VALID JSON. NO explanation, NO markdown.

#     Required fields:
#     - account_number
#     - ifsc_code
#     - cheque_number
#     - payee_name
#     - amount_words
#     - amount_number
#     - signature_present
#     - signature_remarks

#     JSON Format:
#     {
#         "account_number": "",
#         "ifsc_code": "",
#         "cheque_number": "",
#         "payee_name": "",
#         "amount_words": "",
#         "amount_number": "",
#         "signature_present": "",
#         "signature_remarks": ""
#     }
#     """

#     model = genai.GenerativeModel(
#         model_name="gemini-2.5-flash",
#         generation_config={"response_mime_type": "application/json"}
#     )

#     response = model.generate_content(
#         contents=[
#             {
#                 "role": "user",
#                 "parts": [
#                     {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
#                     {"text": prompt}
#                 ]
#             }
#         ]
#     )

#     try:
#         return json.loads(response.text)
#     except:
#         print("❌ Gemini returned non-JSON:", response.text)
#         return {
#             "account_number": "",
#             "ifsc_code": "",
#             "cheque_number": "",
#             "payee_name": "",
#             "amount_words": "",
#             "amount_number": "",
#             "signature_present": "",
#             "signature_remarks": "Gemini did not return JSON"
#         }




# import google.generativeai as genai
# import base64
# import json

# genai.configure(api_key="AIzaSyAl3ZIxyaG21Ht4iMVq_1obTC9g1PXJL80")

# def validate_cheque_image(image_path):
#     with open(image_path, "rb") as f:
#         img_bytes = f.read()

#     img_b64 = base64.b64encode(img_bytes).decode()

#     prompt = """
#     Determine whether the given image is a REAL BANK CHEQUE.

#     A valid cheque must contain:
#     - Bank name
#     - Cheque number
#     - Payee line
#     - Amount (number or words)
#     - Signature area

#     Return ONLY JSON.

#     {
#       "is_cheque": true/false,
#       "reason": ""
#     }
#     """

#     model = genai.GenerativeModel(
#         model_name="gemini-2.5-flash",
#         generation_config={"response_mime_type": "application/json"}
#     )

#     response = model.generate_content(
#         contents=[{
#             "role": "user",
#             "parts": [
#                 {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
#                 {"text": prompt}
#             ]
#         }]
#     )

#     try:
#         result = json.loads(response.text)
#         return result["is_cheque"], result["reason"]
#     except:
#         return False, "Unable to verify cheque image"
