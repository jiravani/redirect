import requests
import json


def lambda_handler(event, context):
    url = 'https://t94q1vf1g3.execute-api.us-west-2.amazonaws.com/Prod/redirect'
    payload = {'destination_url': 'https://twit.tv'}
    headers = {'Accept': 'application/json'}

    # post to the endpoint
    request = requests.post(url, data=json.dumps(payload), headers=headers)

    # prints the response
    print(json.loads(request.text)['shortened_url'])
    print(request.status_code)
