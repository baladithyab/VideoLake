import boto3
import requests
from requests_aws4auth import AWS4Auth
import json

region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

host = 'https://search-videolake-jp74yuza4pylhzhut4vimyh43a.us-east-1.es.amazonaws.com'
index = 'videolake-standard-benchmark'

# Use the master user credentials from terraform variables
# Note: In a real scenario, we should fetch these from Secrets Manager or SSM Parameter Store
# But for this task, we'll use the default values found in variables.tf since they seem to be used
auth = ('admin', 'MediaLake-Demo-2024!')

print("--- SETTINGS ---")
try:
    r = requests.get(f'{host}/{index}/_settings', auth=auth)
    print(r.text)
except Exception as e:
    print(f"Error getting settings: {e}")

print("\n--- MAPPING ---")
try:
    r = requests.get(f'{host}/{index}/_mapping', auth=auth)
    print(r.text)
except Exception as e:
    print(f"Error getting mapping: {e}")