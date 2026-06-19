from google import genai
from google.genai import types

API_KEY = "sk-a5TCnYUmvwX9Hoh24gjUVXFn4vuT1R0KBVScwm1Adh7SXwLT"

prompt = "Hãy trả lời đúng một từ: OK"

try:
    client = genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(
            base_url="https://llm.wokushop.com/v1beta/models/gemini-2.5-flash:generateContent"
        )
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    print("=== SUCCESS ===")
    print(response.text)

except Exception as e:
    print("=== ERROR ===")
    print(type(e).__name__)
    print(str(e))