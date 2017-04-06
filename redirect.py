import re
import boto3
import string
import os
import random
import json

dynamodb = boto3.client('dynamodb')


def lambda_handler(event, context):

    method = event['httpMethod']
    domain = "https://{domain}/{stage}/redirect".format(domain=event['headers']['Host'], stage=event['requestContext']['stage'])
    print(domain)

    if method == 'GET':
        token = event['pathParameters']['proxy']
        return retrieve_url(token, domain)

    if method == 'POST':
        url = json.loads(event['body'])['destination_url']
        return create_new_url(url, domain)


def create_new_url(url, domain):
    print(url)
    if not validate_url(url):
        return {"content": "Invalid URL"}
    token = generate_token()
    dynamodb.put_item(  TableName=os.environ['dynamodb_table'],
                        Item={
                            'id': {
                                'S': "{}".format(token),
                             },
                             'destination_url': {
                                'S': url
                        }})
    body = "Shorted URL for {url} created. \n".format(url=url) + "The shortened url is {domain}/{token}".format(domain=domain, token=token)
    return {
        "statusCode":200, "headers": {"Content-Type": 'text/html'}, "body": body
    }


def retrieve_url(token, domain):

    response = dynamodb.get_item(  TableName=os.environ['dynamodb_table'], Key={'id': {'S': token}})
    if 'Item' not in response:
        body = "<html><body><h1>Token {} Invalid. URL Not Found</h1></body></html>".format(token)
        return {
            "statusCode": 200, "headers": {'Content-Type': 'text/html'}, "body": body
        }

    destination_url = response['Item']['destination_url']['S']
    body = "<html><body>Moved: <a href={url}>{url}</a></body></html>".format(url=destination_url)
    return {
        "statusCode": 301, "headers": {"Location": destination_url}, "body": body
    }


def generate_token():
    # Generate a random one time token
    allowed_chars = string.digits + string.ascii_letters
    return ''.join(random.SystemRandom().choice(allowed_chars)for _ in range(6))


def validate_url(url):

    regex = re.compile( r'^(?:http|ftp)s?://'  # http:// or https://
                        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
                        r'localhost|'  # localhost...
                        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                        r'(?::\d+)?'  # optional port
                        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    if not re.findall(regex, url):
        return False
    return True
