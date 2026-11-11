import json
import os
import time
import uuid
import urllib.request
import boto3

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
table = boto3.resource("dynamodb", region_name="ap-south-1").Table("fraud-guard-transactions")

def ask_gemini(prompt):
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "x-goog-api-key": os.environ["GEMINI_API_KEY"],
        })
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                result = json.loads(r.read())
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"RETRY: {model} failed: {e}")
            time.sleep(1)
    raise Exception("All models failed")

def get_history(amount):
    """Summarise the shop's earlier flagged payments for the AI."""
    items = table.scan().get("Items", [])
    now = int(time.time())
    amounts = [float(i["amount"]) for i in items]
    last_hour = [i for i in items if now - int(i.get("created", 0)) < 3600]
    if not amounts:
        return "This is the first flagged payment on record for this shop."
    avg = sum(amounts) / len(amounts)
    return (
        f"Earlier flagged payments for this shop: {len(amounts)}. "
        f"Their average amount: ${avg:.2f}. Largest: ${max(amounts):.2f}. "
        f"Flagged payments in the last hour: {len(last_hour)}. "
        f"This payment is {amount / avg:.1f}x the average of earlier flagged payments."
    )

def analyse(amount):
    history = get_history(amount)
    prompt = (
        "You are a fraud analyst for a small online shop with no fraud team. "
        f"The shop just received a PayPal payment of ${amount}. "
        "Our rule flags payments over $500. "
        f"{history} "
        "Use ONLY the facts above and do not invent details. "
        "Reply in exactly this format: the first line is 'RISK: LOW', 'RISK: MEDIUM' "
        "or 'RISK: HIGH'. Then 2 short plain-English sentences explaining the main "
        "reasons, referring to the shop's history where relevant. Then a final line "
        "starting 'Recommendation:' saying freeze or approve."
    )
    text = ask_gemini(prompt).strip()
    lines = text.split("\n")
    risk = "MEDIUM"
    if lines[0].upper().startswith("RISK:"):
        risk = lines[0].split(":", 1)[1].strip().upper()
        text = "\n".join(lines[1:]).strip()
    if risk not in ("LOW", "MEDIUM", "HIGH"):
        risk = "MEDIUM"
    return risk, text

def send_telegram(text, tx_id=None):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text}
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

    if amount > 500:  # flag payments over $500
        print("FLAGGED: suspicious payment of", amount)
        try:
            risk, explanation = analyse(amount)
            print("AI SAYS:", risk, explanation)
        except Exception as e:
            print("AI ERROR:", e)
            risk = "UNKNOWN"
            explanation = "AI explanation unavailable. Please review this payment manually."

        tx_id = uuid.uuid4().hex[:12]
        try:
            table.put_item(Item={
                "id": tx_id,
                "amount": str(amount),
                "risk": risk,
                "explanation": explanation,
                "status": "pending",
                "created": int(time.time()),
            })
            print("DB: saved", tx_id)
        except Exception as e:
            print("DB ERROR:", e)
            tx_id = None  # no row to update, so no buttons

        icon = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟢"}.get(risk, "⚪")
        try:
            send_telegram(f"🚨 Flagged payment: ${amount}\n{icon} Risk: {risk}\n\n{explanation}", tx_id)
            print("TELEGRAM: sent")
        except Exception as e:
            print("TELEGRAM ERROR:", e)
    else:
        print("OK: normal payment of", amount)
    return {"statusCode": 200, "body": "ok"}
