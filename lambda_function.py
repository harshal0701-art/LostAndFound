import json
import boto3
import base64

# AWS Clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# DynamoDB Table
table = dynamodb.Table("LostFoundItems")

# S3 Bucket
BUCKET = "lost-found-images-0701"


# Common Response Function
def response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }


def lambda_handler(event, context):

    print(event)

    # HTTP API
    method = event["requestContext"]["http"]["method"]
    path = event["rawPath"]

    ########################################################
    # POST /report
    ########################################################

    if method == "POST" and path == "/report":

        body = json.loads(event["body"])

        itemId = body["itemId"]
        item = body["item"]
        location = body["location"]
        concernPerson = body["concernPerson"]
        image = body["image"]

        imageBytes = base64.b64decode(image)

        filename = item + ".jpg"

        s3.put_object(
            Bucket=BUCKET,
            Key=filename,
            Body=imageBytes,
            ContentType="image/jpeg"
        )

        imageUrl = f"https://{BUCKET}.s3.amazonaws.com/{filename}"

        table.put_item(
            Item={
                "name": item,                     # Partition Key
                "itemId": itemId,
                "location": location,
                "concernPerson": concernPerson,
                "imageUrl": imageUrl
            }
        )

        return response(200, {
            "message": "Item Reported Successfully",
            "itemId": itemId,
            "imageUrl": imageUrl
        })

    ########################################################
    # GET /items
    ########################################################

    elif method == "GET" and path == "/items":

        result = table.scan()

        return response(200, result["Items"])

    ########################################################
    # GET /item?name=
    ########################################################

    elif method == "GET" and path == "/item":

        params = event.get("queryStringParameters")

        if not params:
            return response(400, {
                "message": "Missing Query Parameter"
            })

        name = params["name"]

        result = table.get_item(
            Key={
                "name": name
            }
        )

        if "Item" not in result:
            return response(404, {
                "message": "Item Not Found"
            })

        return response(200, result["Item"])

    ########################################################
    # DELETE /item?name=
    ########################################################

    elif method == "DELETE" and path == "/item":

        params = event.get("queryStringParameters")

        if not params:
            return response(400, {
                "message": "Missing Query Parameter"
            })

        name = params["name"]

        result = table.get_item(
            Key={
                "name": name
            }
        )

        if "Item" not in result:
            return response(404, {
                "message": "Item Not Found"
            })

        # Delete Image
        s3.delete_object(
            Bucket=BUCKET,
            Key=name + ".jpg"
        )

        # Delete DynamoDB Record
        table.delete_item(
            Key={
                "name": name
            }
        )

        return response(200, {
            "message": "Item Deleted Successfully"
        })

    ########################################################
    # INVALID API
    ########################################################

    return response(404, {
        "message": "Invalid API"
    })