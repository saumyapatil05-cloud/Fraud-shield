import json

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    resource = body.get("resource", {})
    amount = float(resource.get("amount", {}).get("value", 0))

    if amount > 500:
        print("FLAGGED: suspicious payment of", amount)
    else:
        print("OK: normal payment of", amount)

    return {"statusCode": 200, "body": "ok"}
