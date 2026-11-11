import json
import os
import urllib.request
import boto3

table = boto3.resource("dynamodb", region_name="ap-south-1").Table("fraud-guard-transactions")

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

    try:
        action, tx_id = cb.get("data", "").split(":", 1)
    except ValueError:
        print("BAD DATA:", cb.get("data"))
        return {"statusCode": 200, "body": "bad data"}

    if action not in ("freeze", "approve"):
        return {"statusCode": 200, "body": "bad action"}

    new_status = "frozen" if action == "freeze" else "approved"
    label = "🧊 FROZEN" if action == "freeze" else "✅ APPROVED"
    print("BUTTON:", action, tx_id)

    try:
        table.update_item(
            Key={"id": tx_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": new_status},
        )
        print("DB: updated", tx_id, new_status)
    except Exception as e:
        print("DB ERROR:", e)

    try:
        tg("answerCallbackQuery", {"callback_query_id": cb["id"], "text": label})
        tg("editMessageText", {
            "chat_id": msg["chat"]["id"],
            "message_id": msg["message_id"],
            "text": msg["text"] + f"\n\nDecision: {label}",
        })
    except Exception as e:
        print("TELEGRAM ERROR:", e)
    return {"statusCode": 200, "body": "ok"}
