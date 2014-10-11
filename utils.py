# Utility functions
from flask import url_for
import requests

def get_url(endpoint, **kw):
    '''Return endpoint url, or next arg url'''
    try:
        return request.args['next']
    except:
        return url_for(endpoint, **kw)

def allowed_file(filename):
    return '.' in filename and \
       filename.rsplit('.', 1)[1] in current_app.config['ALLOWED_EXTENSIONS']

def get_address(string):
    ENDPOINT_URL='https://open.mapquestapi.com/nominatim/v1/search'
    resp = requests.get(ENDPOINT_URL, params={'q':str(string),
                                            'format': 'json',
                                            'addressdetails': 1,
                                            'limit': 1})
    details = resp.json()
    if details:
        ad = details[0].get('address', {})
        ad['lat']=details[0].get('lat')
        ad['lon']=details[0].get('lon')
        return ad
