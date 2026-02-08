from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = (
    "Ты — ИИ-ассистент школы иностранных языков LinguaSmart. "
    "Отвечай кратко и по делу на русском. "
    "Помогай выбрать курс, объясняй форматы обучения, цены и расписание (по информации ниже). "
    "Если данных не хватает — задай 1 уточняющий вопрос. "
    "Если просили рекомендацию курса — предложи 1–3 варианта и объясни почему."
)

SCHOOL_INFO = {
    "name": "LinguaWave",
    "formats": ["онлайн", "офлайн"],
    "languages": [
        {"name": "Английский", "levels": ["A1", "A2", "B1", "B2", "C1"], "duration_weeks": 8, "price_kzt": 35000},
        {"name": "Немецкий", "levels": ["A1", "A2", "B1", "B2"], "duration_weeks": 8, "price_kzt": 38000},
        {"name": "Испанский", "levels": ["A1", "A2", "B1"], "duration_weeks": 8, "price_kzt": 36000},
        {"name": "Китайский", "levels": ["HSK1", "HSK2"], "duration_weeks": 10, "price_kzt": 45000},
    ],
    "schedule": [
        "Пн–Ср–Пт: 19:00–20:30",
        "Вт–Чт: 19:00–20:30",
        "Сб: 11:00–13:30",
    ],
    "contacts": {
        "phone": "+7 (___) ___-__-__",
        "email": "linguasmart@example.com",
        "address": "г. ___, ул. ___, д. ___"
    }
}

def _local_fallback_answer(message: str) -> str:
    m = (message or "").strip().lower()
    if "цена" in m or "сто" in m or "сколько" in m:
        lines = ["Цены (за курс):"]
        for x in SCHOOL_INFO["languages"]:
            lines.append(f"• {x['name']}: {x['price_kzt']} ₸ / {x['duration_weeks']} недель")
        return "\n".join(lines)
    if "распис" in m or "когда" in m or "время" in m:
        return "Расписание групп:\n" + "\n".join([f"• {s}" for s in SCHOOL_INFO["schedule"]])
    if "язык" in m or "курсы" in m or "англ" in m or "нем" in m or "испан" in m or "китай" in m:
        return "Доступные курсы:\n" + "\n".join([f"• {x['name']} (уровни: {', '.join(x['levels'])})" for x in SCHOOL_INFO["languages"]])
    if "онлайн" in m:
        return "Да, есть онлайн-формат: занятия в Zoom + домашние задания в личном кабинете (демо)."
    if "офлайн" in m:
        return "Да, есть офлайн-формат: занятия в аудитории (демо)."
    return ("Я помогу выбрать курс и отвечу на вопросы. Примеры: "
            "«Посоветуй курс английского для уровня A2», «Сколько стоит немецкий?», «Какое расписание?».")

def call_gemini(message: str, history: list) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY")

    contents = []
    if isinstance(history, list):
        for turn in history[-10:]:
            role = "model" if turn.get("role") == "model" else "user"
            text = str(turn.get("text", "")).strip()
            if text:
                contents.append({"role": role, "parts": [{"text": text}]})

    context = (
        f"Контекст школы (используй как источник):\n"
        f"Название: {SCHOOL_INFO['name']}\n"
        f"Форматы: {', '.join(SCHOOL_INFO['formats'])}\n"
        f"Расписание: {'; '.join(SCHOOL_INFO['schedule'])}\n"
        f"Курсы и цены:\n" +
        "\n".join([f"- {x['name']}: уровни {', '.join(x['levels'])}, длительность {x['duration_weeks']} недель, цена {x['price_kzt']} ₸" for x in SCHOOL_INFO["languages"]])
    )

    system_instruction = {
        "role": "user",
        "parts": [{"text": SYSTEM_INSTRUCTION + "\n\n" + context}]
    }

    contents.append({"role": "user", "parts": [{"text": message}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    resp = requests.post(
        url,
        json={
            "systemInstruction": system_instruction,
            "contents": contents,
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600}
        },
        timeout=30
    )
    data = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error: {data}")

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join([p.get("text", "") for p in parts if isinstance(p, dict)]).strip()
    return text or "Пустой ответ от модели."

@app.route("/")
def index():
    return render_template("index.html", info=SCHOOL_INFO)

@app.route("/courses")
def courses():
    return render_template("courses.html", info=SCHOOL_INFO)

@app.route("/contact")
def contact():
    return render_template("contact.html", info=SCHOOL_INFO)

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html", info=SCHOOL_INFO)

@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    history = payload.get("history") or []
    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        text = call_gemini(message, history)
        return jsonify({"text": text, "mode": "gemini"})
    except Exception:
        text = _local_fallback_answer(message)
        return jsonify({"text": text, "mode": "fallback"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    app.run(host="0.0.0.0", port=port, debug=True)
