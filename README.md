# LinguaSmart — школа иностранных языков + ИИ-ассистент (Gemini free tier)

## Стек
- Python + Flask
- HTML/CSS (Jinja2 templates)
- JS (чат)
- Интеграция ИИ: Gemini API через сервер /api/chat (ключ не в браузере)
- Fallback режим без ключа

## Запуск на Replit
1) Create Repl → Python
2) Загрузить проект
3) Secrets → добавить GEMINI_API_KEY
4) Run

## Локально
pip install -r requirements.txt
export GEMINI_API_KEY="..."
python app.py
Открыть: http://localhost:3000
