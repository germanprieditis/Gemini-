import os
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# Ключ берем из переменных окружения (на Render) или используем тот, что в коде
GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    "AQ.Ab8RN6IgEsFWvC0D9d40HMJKBqVOuJAqdcMt1sYFycaF_VDU-A"
)

# Настройка клиента с правильным заголовком для ключа AQ
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        headers={"x-goog-api-key": GEMINI_API_KEY}
    )
)

# Используем самую быструю модель lite, чтобы уложиться в лимит времени
MODEL_NAME = "gemini-3.5-flash-lite"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "empty request"}), 400

    # 1. ЗАЩИТА ОТ СЛУЖЕБНЫХ ЗАПРОСОВ (исправляет ошибку 400)
    req = data.get('request', {})
    if req.get('original_utterance') == 'ping':
        return jsonify({"response": {"text": "ok", "end_session": False}, "version": "1.0"})

    # Безопасно достаем текст (если команды нет, берем original_utterance)
    user_text = req.get('command', req.get('original_utterance', '')).lower()
    version = data.get('version', '1.0')
    session = data.get('session', {})

    # 2. ПРИВЕТСТВИЕ (срабатывает при запуске)
    if not user_text:
        return jsonify({
            "version": version, "session": session,
            "response": {
                "text": "Привет! На связи супер-интеллект Gemini. Я умею управлять часами, музыкой и делиться эмоциями. О чём поговорим?",
                "tts": "<speaker audio=\"alice-sounds-things-gong-1.opus\"> Привет! На связи супер-интеллект Джемини. Я умею управлять часами, музыкой и делиться эмоциями. О чём поговорим?",
                "end_session": False
            }
        })

    # 3. УПРАВЛЕНИЕ ЧАСАМИ (LED-экран)
    if "выключи часы" in user_text or "выключить экран" in user_text:
        return jsonify({
            "version": version, "session": session,
            "response": {
                "text": "Выключаю дисплей часов.",
                "end_session": False,
                "directives": {"led_display": {"command": "off"}}
            }
        })
    
    if "включи часы" in user_text or "включить экран" in user_text:
        return jsonify({
            "version": version, "session": session,
            "response": {
                "text": "Включаю отображение времени.",
                "end_session": False,
                "directives": {"led_display": {"command": "time"}}
            }
        })

    # 4. МУЗЫКА
    if "включи музыку" in user_text or "включи трек" in user_text:
        return jsonify({
            "version": version, "session": session,
            "response": {
                "text": "Включаю расслабляющую музыку для фона.",
                "tts": "Включаю расслабляющую музыку для фона. <speaker audio=\"alice-music-relax-1.opus\">",
                "end_session": False
            }
        })

    # 5. ЗАПРОС К GEMINI
    prompt = (
        "Ты — продвинутый голосовой ассистент с эмоциями. "
        f"Ответь на запрос пользователя на русском языке: '{user_text}'. "
        "Если твой ответ веселый или смешной — начни его строго со слова [РАДОСТЬ]. "
        "Если ты рассказываешь секрет, тайну или что-то таинственное — начни со слова [ШЕПОТ]."
    )

    try:
        gemini_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        raw_reply = gemini_response.text or "Я не смог придумать ответ."
    except Exception as e:
        # Логируем ошибку, чтобы видеть её в Render, если что-то пойдет не так
        app.logger.error(f"Ошибка Gemini: {e}")
        raw_reply = "Извини, произошла ошибка при обращении к моему ИИ-мозгу."

    # Обработка интонаций
    tts_reply = raw_reply
    if "[РАДОСТЬ]" in raw_reply:
        raw_reply = raw_reply.replace("[РАДОСТЬ]", "").strip()
        tts_reply = "<speaker audio=\"alice-sounds-human-laugh-5.opus\">" + raw_reply
    elif "[ШЕПОТ]" in raw_reply:
        raw_reply = raw_reply.replace("[ШЕПОТ]", "").strip()
        tts_reply = "<speaker audio=\"alice-whisper\">" + raw_reply

    # Отправляем ответ на колонку
    return jsonify({
        "version": version, "session": session,
        "response": {
            "text": raw_reply.strip(),
            "tts": tts_reply.strip(),
            "end_session": False,
            "directives": {"led_display": {"command": "animation", "text": "TALK"}}
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
