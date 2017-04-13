import re
import boto3
import string
import os
import random
import json

dynamodb = boto3.client('dynamodb')


def lambda_handler(event, context):

    print(event)
    method = event['httpMethod']

    # Get the domain be referenced (either example.com/redirect or ...amazonaws.com)
    # Stage will be omitted if the API is behind a domain (rather than the api gateway dns)
    domain = get_domain(event)

    # The
    if method == 'GET':
        if  event['resource'] == '/redirect':
            print('Serve Website')
            return api_website(event, domain)
        elif event['pathParameters'] != None:
            print('Return Token')
            return retrieve_url(event['pathParameters']['proxy'], domain)

    if method == 'POST':
        print('Post')
        return create_new_url(event['body'], domain)


    return  {
                        "statusCode": 200,
                        "headers": {"Content-Type": 'text/html', "Access-Control-Allow-Origin": "*"},
                        "body":"HTTP method not supported."
            }


def create_new_url(post_body, domain):
    print(post_body)
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
    return_payload['body'] = "Shortened URL for {url} created. \n".format(url=url) + \
                             "The shortened url is {domain}/{token}\n".format(domain=domain, token=token)
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


def api_website(event, domain):

    body = """<html>
            <body bgcolor=\"#E6E6FA\">
            <head>
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
            <script>

            $(document).ready(function(){
                $("button").click(function(){
                  var destinationUrl = document.getElementById("destinationUrl").value;
                  var dict = {};
                  dict["destination_url"] = destinationUrl;
                  if (document.getElementById("customToken").value != "") {
                      dict["custom_token"] = document.getElementById("customToken").value;
                  }

                  $.ajax({
                    type: 'POST',
                    headers: {
                        'Content-Type':'application/json',
                        'Accept':'text/html'
                    },
                    url:'"""

    body += domain
    body +=         """',
                    crossDomain: true,
                    data: JSON.stringify(dict),
                    dataType: 'text',
                    success: function(responseData) {
                        document.getElementById("id").innerHTML = responseData;
                    },
                    error: function (responseData) {
                        alert('POST failed.'+ JSON.stringify(responseData));
                    }
                  });
                });
            });
            </script>
            </head>
            <body>"""
    body += event['resource'][1:]
    body += """<form class="form" action="" method="post">
                    <textarea rows="1" cols="50" name="text" id="destinationUrl" placeholder="Enter URL (http://www.example.com)"></textarea>
              </form>
              <form class="form" action="" method="post">
                    <textarea rows="1" cols="50" name="text" id="customToken" placeholder="Use Custom Token (domain.com/redirect/custom_token)"></textarea>
              </form>
            <button>Shorten URL</button>
            <div id='id'></div>
            </body>
            </html>"""

    return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": 'text/html',
                    "Access-Control-Allow-Origin": "*"
                },
                "body": body
    }


def get_domain(event):
    if 'amazonaws.com' in event['headers']['Host']:
        return "https://{domain}/{stage}/redirect".format(domain=event['headers']['Host'], stage=event['requestContext']['stage'])
    else:
        return "https://{domain}/redirect".format(domain=event['headers']['Host'])
