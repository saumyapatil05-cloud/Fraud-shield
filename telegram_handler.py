import json
import os
import urllib.request

def tg(method, payload):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/{method}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.read()

def lambda_handler(event, context):
    update = json.loads(event.get("body") or "{}")
    cb = update.get("callback_query")
    if not cb:
        return {"statusCode": 200, "body": "ignored"}

    msg = cb["message"]
    # Only accept taps from your own chat
    if str(msg["chat"]["id"]) != os.environ["TELEGRAM_CHAT_ID"]:
        print("REJECTED: wrong chat")
        return {"statusCode": 200, "body": "rejected"}

    action = cb.get("data")
    status = "🧊 FROZEN" if action == "freeze" else "✅ APPROVED"
    print("BUTTON:", action)

    try:
        tg("answerCallbackQuery", {"callback_query_id": cb["id"], "text": status})
        tg("editMessageText", {
            "chat_id": msg["chat"]["id"],
            "message_id": msg["message_id"],
            "text": msg["text"] + f"\n\nDecision: {status}",
        })
    except Exception as e:
        print("TELEGRAM ERROR:", e)
    return {"statusCode": 200, "body": "ok"}
