import os
import hashlib
import requests
from QueryFormat import query_format

def get_day_matches(day):
    query = query_format.replace("{{{QueryDate}}}", day).encode('utf-8');
    
    m = hashlib.sha256()
    m.update(query)
    hashed = m.hexdigest()
    
    req_url = 'https://geql.globo.com/graphql?variables={}&extensions={"persistedQuery":{"version":1,"sha256Hash":"'+hashed+'"}}'
    
    response = requests.get(req_url)
    return response.json()