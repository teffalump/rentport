
from .extensions import db, mail
from .forms import (OpenIssueForm, PostCommentForm, CloseIssueForm,
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
import stripe
#### Blueprint ####
rp = Blueprint('fee', __name__, template_folder = 'templates/fee', static_folder='static')
#### /Blueprint ####


#### FEES ####
@rp.route('/fees', methods=['GET'])
@rp.route('/fees/<int(min=1):page>', methods=['GET'])
@rp.route('/fees/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def fees(page=1, per_page=current_app.config['PAYMENTS_PER_PAGE']):
    '''main fees page
        params:     GET: <page> what page to show
                    GET: <per_page> how many items per page
        returns:    GET: template'''
    fees=g.user.fees.paginate(page, per_page, False)
    return render_template('fees.html', fees=fees)

@rp.route('/fees/<int:pay_id>/show', methods=['GET'])
@login_required
def show_fee(pay_id):
    '''show extended fee info
        params:     GET: <pay_id> payment id
        returns:    GET: json-ed payment info'''
    fee=g.user.fees.filter(Fee.id==pay_id).first()
    if not fee:
        flash('No fee with that id')
        return jsonify({'error': 'No fee with that id'})
    f = stripe.Charge.retrieve(fee.pay_id,
                    api_key=current_app.config['STRIPE_CONSUMER_SECRET'])\
                    .to_dict()
    return jsonify({k:v for (k,v) in f.items() if k in \
            ['amount', 'currency', 'paid', 'refunded','description']})
#### /FEES ####
