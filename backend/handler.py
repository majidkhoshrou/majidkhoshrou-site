def lambda_handler(event, context):
    # Not used for HTTP; the Lambda Web Adapter starts Gunicorn and proxies requests.
    return {"statusCode": 200, "body": "ok"}
