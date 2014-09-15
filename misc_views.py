from .extensions import db, mail
from .forms import (OpenIssueForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm,
                        AddProviderForm, ConnectProviderForm, SelectProviderForm)
from .model import (Issue, Property, User, LandlordTenant, Comment, WorkOrder,
                        Fee, Payment, StripeUserInfo, Address, Provider, Image)
from flask.ext.mail import Message
from flask.ext.security import login_required
from requests_oauthlib import OAuth2Session
from flask import (Blueprint, render_template, request, g, redirect, url_for,
                    abort, flash, session, json, jsonify, current_app,
                    make_response)
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import or_
from werkzeug.security import gen_salt
from werkzeug import secure_filename
from sys import exc_info as er
from datetime import datetime as dt
from geopy.geocoders import Nominatim
from os import path as fs
from uuid import uuid4
from .utils import get_url, allowed_file
import stripe

#### Blueprint ####
rp = Blueprint('misc', __name__, template_folder = 'templates/misc', static_folder='static')
#### /Blueprint ####

#### DEFAULT ####
@rp.route('/')
@login_required
def home():
    return render_template('home.html')
#### /DEFAULT ####

#### HOOKS ####
@rp.route('/hook/stripe', methods=['POST'])
def stripe_hook():
    try:
        event=json.loads(request.data)
        if event:
            c = stripe.Event.retrieve(event['id'],
                    api_key=current_app.config['STRIPE_CONSUMER_SECRET'])
            if not c: return 'No event'
            #acct=c.get('user_id', None)
            #if not acct: return 'No acct'
            if c['type']['object']=='charge':
                #i=Payment.query.filter(Payment.pay_id==c['data']['object']['id']).first() \
                i=Fee.query.filter(Fee.pay_id==c['data']['object']['id']).first()
                if not i: return 'no fee'
                if c['type']=='charge.succeeded':
                    i.status='Confirmed'
                elif c['type']=='charge.refunded':
                    i.status='Refunded'
                elif c['type']=='charge.failed':
                    i.status='Denied'
                else:
                    return 'Type not supported'
                db.session.add(i)
                db.session.commit()
                return 'Success'
            else:
                return 'Not supported type'
    except:
        return print(er())
        #if c['type']=='account.application.deauthorized':
            #t=StripeUserInfo.query.filter(StripeUserInfo.user_acct==acct).first()
            #if not t: return 'not a user'
            #db.session.delete(t)
            #db.session.commit()
        #elif c['data']['object']=='dispute':
            #pass
        #elif c['data']['object']=='customer':
            #pass
        #elif c['data']['object']=='card':
            #pass
        #elif c['data']['object']=='subscription':
            #pass
        #elif c['data']['object']=='invoice':
            #pass
        #elif c['data']['object']=='plan':
            #pass
        #elif c['data']['object']=='transfer':
            #pass
        #elif c['data']['object']=='discount':
            #pass
        #elif c['data']['object']=='coupon':
            #pass
        #elif c['data']['object']=='balance':
            #pass
        #elif c['data']['object']=='account':
            #pass
        #else:
            #pass
        #return ''
    #except:
        #return str(er())

@rp.route('/hook/twilio')
def twilio_hook():
    '''twilio hook'''
    #TODO
    return ''
#### /HOOKS ####

#### IMAGES ####
@rp.route('/img/<image_uuid>', methods=['GET'])
@login_required
def show_img(image_uuid):
    '''Use X-Accel-Redirect to let nginx handle static files'''
    #TODO What images should be able to be seen by what users
    im=Image.query.filter(Image.uuid==image_uuid).first()
    if im is None:
        abort(404)
    #fs_path='/'.join([current_app.config['UPLOAD_FOLDER'], im.filename])
    ur_redirect='/'.join(['/srv/images', im.filename])
    response=make_response("")
    response.headers['X-Accel-Redirect']=ur_redirect
    return response
#### /IMAGES ####
