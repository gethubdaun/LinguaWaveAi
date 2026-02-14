from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)

SYSTEM_INSTRUCTION = (
    "Ты — ИИ-ассистент школы иностранных языков LinguaSmart. "
    "Отвечай кратко и по делу на русском. "
    "Помогай выбрать курс и объясняй обучение."
)

SCHOOL_INFO = {
    "name": "LinguaWave",
    "formats": ["онлайн", "офлайн"],
    "languages": [
        {"name": "Английский", "price_kzt": 35000},
        {"name": "Немецкий", "price_kzt": 38000},
        {"name": "Испанский", "price_kzt": 36000},
        {"name": "Китайский", "price_kzt": 45000},
    ],
    "schedule": [
        "Пн–Ср–Пт 19:00",
        "Вт–Чт 19:00",
        "Сб 11:00"
    ]
}

def _local_fallback_answer(message: str) -> str:
    m = message.lower()

    if "цена" in m:
        return "\n".join(
            [f"{x['name']} — {x['price_kzt']} ₸"
             for x in SCHOOL_INFO["languages"]]
        )

    if "распис" in m:
        return "\n".join(SCHOOL_INFO["schedule"])

    return "Напиши язык и уровень — помогу выбрать курс."


def call_ai(message: str, history: list) -> str:

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv(
        "OPENROUTER_MODEL",
        "deepseek/deepseek-chat:free"
    )

    if not OPENROUTER_API_KEY:
        raise RuntimeError("NO OPENROUTER API KEY")

    messages = [{
        "role": "system",
        "content": SYSTEM_INSTRUCTION
    }]

    for turn in history[-10:]:
        role = "assistant" if turn.get("role") == "model" else "user"
        text = turn.get("text", "")
        if text:
            messages.append({
                "role": role,
                "content": text
            })

    messages.append({
        "role": "user",
        "content": message
    })

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://linguawaveai.onrender.com",
            "X-Title": "LinguaWaveAI"
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 400
        },
        timeout=30
    )

  if resp.status_code != 200:
    print("OPENROUTER RAW:", resp.text)
    raise RuntimeError(resp.text)


    data = resp.json()

    return (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
        or "Нет ответа."
    )


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
        return jsonify({"error": "message required"}), 400

    try:
        text = call_ai(message, history)
        return jsonify({"text": text, "mode": "ai"})
    except Exception as e:
        print("AI ERROR:", e)
        return jsonify({
            "text": _local_fallback_answer(message),
            "mode": "fallback"
        })


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
