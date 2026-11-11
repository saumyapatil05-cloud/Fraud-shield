import json
import boto3

table = boto3.resource("dynamodb", region_name="ap-south-1").Table("fraud-guard-transactions")

def num(o):
    # DynamoDB returns numbers as Decimal, which json can't handle
    return int(o) if o == int(o) else float(o)

def lambda_handler(event, context):
    items = table.scan().get("Items", [])
    items.sort(key=lambda x: x.get("created", 0), reverse=True)
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(items, default=num),
    }
