import json
import os
import time
import uuid
import urllib.request
import boto3  # built into Lambda, no install needed

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
table = boto3.resource("dynamodb", region_name="ap-south-1").Table("fraud-guard-transactions")

def ask_gemini(prompt):
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(1):
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "x-goog-api-key": os.environ["GEMINI_API_KEY"],
            })
            try:
                with urllib.request.urlopen(req, timeout=8) as r:
                    result = json.loads(r.read())
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                print(f"RETRY: {model} attempt {attempt + 1} failed: {e}")
                time.sleep(1)
    raise Exception("All models failed")

def send_telegram(text, tx_id=None):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": os.environ["TELEGRAM_CHAT_ID"],
        "text": text,
    }
    if tx_id:
        payload["reply_markup"] = {"inline_keyboard": [[
            {"text": "🧊 Freeze", "callback_data": f"freeze:{tx_id}"},
            {"text": "✅ Approve", "callback_data": f"approve:{tx_id}"},
        ]]}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.read()

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    resource = body.get("resource", {})
    amount = float(resource.get("amount", {}).get("value", 0))

    if amount > 50:  # TEMPORARY test value, set to 500 later
        print("FLAGGED: suspicious payment of", amount)
        prompt = (f"A small online shop received a PayPal payment of ${amount}. "
                  "Our rule flagged it as large. In 2 sentences, explain the possible "
                  "fraud risk and recommend freeze or approve.")
        try:
            explanation = ask_gemini(prompt)
            print("AI SAYS:", explanation)
        except Exception as e:
            print("AI ERROR:", e)
            explanation = "AI explanation unavailable. Please review this payment manually."

        tx_id = uuid.uuid4().hex[:12]
        try:
            table.put_item(Item={
                "id": tx_id,
                "amount": str(amount),
                "explanation": explanation,
                "status": "pending",
                "created": int(time.time()),
            })
            print("DB: saved", tx_id)
        except Exception as e:
            print("DB ERROR:", e)
            tx_id = None  # no row to update, so no buttons

        try:
            send_telegram(f"🚨 Flagged payment: ${amount}\n\n{explanation}", tx_id)
            print("TELEGRAM: sent")
        except Exception as e:
            print("TELEGRAM ERROR:", e)
    else:
        print("OK: normal payment of", amount)
    return {"statusCode": 200, "body": "ok"}
