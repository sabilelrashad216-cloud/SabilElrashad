import base64
import json
import os
from openai import OpenAI

MODEL = "gpt-5-nano"
client = OpenAI()

SYSTEM = """أنت محلل محتوى عربي دقيق. استخرج النص كما هو دون إعادة صياغة أو تصحيح أو حذف. ميّز بين قرآن وحديث وسؤال وجواب وأخرى. في سؤال وجواب اجعل main_text هو السؤال وexplanation هو الإجابة. إذا وُجد تفسير أو شرح استخرجه كاملًا. لا تخمن المصدر ولا درجة الحديث. أعد JSON فقط بالمفاتيح: kind (quran/hadith/qa/other), main_text, explanation, source, confidence. إذا لم يوجد شرح أو إجابة اجعل explanation فارغًا. لا تضع نقاط حذف ولا تختصر النص."""

def extract(text=None, image_bytes=None, expected_kind=None):
    user_content = []
    if expected_kind in {"quran", "hadith", "qa"}:
        label = {"quran": "قرآن وآية وتفسير", "hadith": "حديث وشرحه", "qa": "سؤال وجواب"}[expected_kind]
        user_content.append({"type": "text", "text": f"القسم المختار هو: {label}. صنّف المحتوى داخل هذا القسم ولا تغيّر النص."})
    if text:
        user_content.append({"type": "text", "text": "حلل هذا النص:\n" + text})
    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode()
        mime = "image/png" if image_bytes[:8].startswith(b"\x89PNG") else "image/jpeg"
        user_content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_content}]
    last_error = None
    for _ in range(2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                max_completion_tokens=4000,
            )
            content = resp.choices[0].message.content or ""
            if content.strip():
                return json.loads(content)
            last_error = "empty model response"
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"content extraction failed: {last_error}")
