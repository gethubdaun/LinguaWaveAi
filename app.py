from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)

# ===== CONFIG =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = (
    "Ты — ИИ-ассистент школы иностранных языков LinguaSmart. "
    "Отвечай кратко и по делу на русском. "
    "Помогай выбрать курс и объясняй обучение."
)

SCHOOL_INFO = {
    "name": "LinguaWave",
    "formats": ["онлайн", "офлайн"],
    "languages": [
        {"name": "Английский","price_kzt":35000},
        {"name": "Немецкий","price_kzt":38000},
        {"name": "Испанский","price_kzt":36000},
        {"name": "Китайский","price_kzt":45000},
    ],
    "schedule":[
        "Пн–Ср–Пт 19:00",
        "Вт–Чт 19:00",
        "Сб 11:00"
    ]
}

# ===== FALLBACK =====
def _local_fallback_answer(message:str)->str:
    m = message.lower()

    if "цена" in m:
        return "\n".join([f"{x['name']} — {x['price_kzt']} ₸" for x in SCHOOL_INFO["languages"]])

    if "распис" in m:
        return "\n".join(SCHOOL_INFO["schedule"])

    return "Напиши язык и уровень — помогу выбрать курс."

# ===== GEMINI CALL =====
def call_gemini(message:str,history:list)->str:

    if not GEMINI_API_KEY:
        raise RuntimeError("NO API KEY")

    contents=[]

    for turn in history[-10:]:
        role="model" if turn.get("role")=="model" else "user"
        text=turn.get("text","")
        if text:
            contents.append({
                "role":role,
                "parts":[{"text":text}]
            })

    contents.append({
        "role":"user",
        "parts":[{"text":message}]
    })

    url=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    resp=requests.post(
        url,
        json={
            "contents":contents,
            "generationConfig":{
                "temperature":0.4,
                "maxOutputTokens":400
            }
        },
        timeout=20
    )

    if resp.status_code!=200:
        raise RuntimeError(resp.text)

    data=resp.json()

    parts=data.get("candidates",[{}])[0].get("content",{}).get("parts",[])
    text="".join([p.get("text","") for p in parts if isinstance(p,dict)])

    return text or "Нет ответа."

# ===== ROUTES =====
@app.route("/")
def index():
    return render_template("index.html",info=SCHOOL_INFO)

@app.route("/courses")
def courses():
    return render_template("courses.html",info=SCHOOL_INFO)

@app.route("/contact")
def contact():
    return render_template("contact.html",info=SCHOOL_INFO)

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html",info=SCHOOL_INFO)

@app.route("/api/chat",methods=["POST"])
def api_chat():

    payload=request.get_json(silent=True) or {}
    message=(payload.get("message") or "").strip()
    history=payload.get("history") or []

    if not message:
        return jsonify({"error":"message required"}),400

    try:
        text=call_gemini(message,history)
        return jsonify({"text":text,"mode":"gemini"})
    except Exception as e:
        print("AI ERROR:",e)
        return jsonify({
            "text":_local_fallback_answer(message),
            "mode":"fallback"
        })

# ===== HEALTH CHECK (Render любит это) =====
@app.route("/health")
def health():
    return "OK",200

# ===== RUN =====
if __name__=="__main__":
    port=int(os.getenv("PORT",10000))
    app.run(host="0.0.0.0",port=port)
