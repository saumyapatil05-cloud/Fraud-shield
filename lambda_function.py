import json

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    event_type = body.get("event_type")
    resource = body.get("resource", {})
    amount = resource.get("amount", {})

    print("EVENT TYPE:", event_type)
    print("AMOUNT:", amount.get("value"), amount.get("currency_code"))
    print("FULL RESOURCE:", json.dumps(resource))

    return {"statusCode": 200, "body": "ok"}
