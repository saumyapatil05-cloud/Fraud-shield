import json

def lambda_handler(event, context):
    print("WEBHOOK RECEIVED:")
    print(json.dumps(event))
    return {"statusCode": 200, "body": "ok"}
