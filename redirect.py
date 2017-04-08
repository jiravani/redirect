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
        return create_new_url(event['body'], domain)


def create_new_url(post_body, domain):

    url = json.loads(post_body)['destination_url']
    token = json.loads(post_body)['custom_token'] if 'custom_token' in json.loads(post_body) else generate_token()
    print(token)
    return_payload = {
                        "statusCode": 200,
                        "headers": {"Content-Type": 'text/html', "Access-Control-Allow-Origin": "*"}
                     }

    if not validate_url(url):
        return_payload['body'] = "The provided URL is invalid.\n"
        return return_payload

    # token = generate_token()
    dynamodb.put_item(  TableName=os.environ['dynamodb_table'],
                        Item={  'id': {'S': "{}".format(token)},
                                'destination_url': {
                                'S': url}})
    return_payload['body'] = "Shorted URL for {url} created. \n".format(url=url) + \
                             "The shortened url is {domain}/{token}".format(domain=domain, token=token)
    return return_payload


def retrieve_url(token, domain):

    return_payload = {
                        "statusCode": 301,
                        "headers": {
                            "Content-Type": 'text/html',
                            "Access-Control-Allow-Origin": "*"
                        }
                     }

    # based on the token, retrieve url from dynamodb table
    response = dynamodb.get_item(   TableName=os.environ['dynamodb_table'],
                                    Key={'id': {'S': token}})

    # if the token key doesn't exist in the dynamodb table, return response
    if 'Item' not in response:
        return_payload['statusCode'] = 200
        return_payload['body'] = "Token {} Invalid. URL Not Found\n".format(token)
        return return_payload

    return_payload['headers']['Location'] = response['Item']['destination_url']['S']
    return_payload['body'] = ""
    return return_payload


def generate_token():
    # Generate a random one time token
    allowed_chars = string.digits + string.ascii_letters
    return ''.join(random.SystemRandom().choice(allowed_chars)for _ in range(6))


def validate_url(url):

    regex = re.compile( r'^(?:http|ftp)s?://'  # http:// or https://
                        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                        r'localhost|'  # localhost...
                        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                        r'(?::\d+)?'  # optional port
                        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    if not re.findall(regex, url):
        return False
    return True
