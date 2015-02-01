# Utility functions
from flask import url_for, jsonify, request, render_template, redirect, current_app
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
        try:
            ad['lat']=float(details[0].get('lat'))
        except:
            pass
        try:
            ad['lon']=float(details[0].get('lon'))
        except:
            pass
        try:
            ad['house_number']=int(ad['house_number'])
        except:
            pass

        return ad

def redirect_xhr_or_normal(endpoint, **kwargs):
    if request.is_xhr:
        return jsonify({'redirect': get_url(endpoint, **kwargs)})
    else:
        return redirect(get_url(endpoint, **kwargs))

def render_xhr_or_normal(template, **kwargs):
    if request.is_xhr:
        return jsonify({'page': render_template(template, **kwargs)})
    else:
        return render_template(template, **kwargs)

__all__=['get_url', 'allowed_file', 'get_address',
        'redirect_xhr_or_normal', 'render_xhr_or_normal']
