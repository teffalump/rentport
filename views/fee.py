from rentport.common.extensions import db, mail
from rentport.common.forms import (OpenIssueForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm,
                        AddProviderForm, ConnectProviderForm, SelectProviderForm)
from rentport.common.model import (Issue, Property, User, LandlordTenant,
                        Comment, WorkOrder, Fee, Payment, StripeUserInfo,
                        Address, Provider, Image)
from flask.ext.mail import Message
from flask.ext.security import login_required
from requests_oauthlib import OAuth2Session
from flask import (Blueprint, request, g, redirect, url_for,
                    abort, flash, session, json, jsonify, current_app,
                    make_response)
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import or_
from werkzeug.security import gen_salt
from werkzeug import secure_filename
from sys import exc_info as er
from datetime import datetime as dt
from datetime import date
from geopy.geocoders import Nominatim
from os import path as fs
from uuid import uuid4
from rentport.common.utils import render_xhr_or_normal, redirect_xhr_or_normal
import stripe
import logging

logger = logging.getLogger(__name__)

#### Blueprint ####
fee = Blueprint('fee', __name__, template_folder = 'templates/fee', static_folder='static')
#### /Blueprint ####

#### FEES ####
@fee.route('/fee/<int:pay_id>/show', methods=['GET'])
@login_required
def show_fee(pay_id):
    '''show extended fee info
        params:     GET: <pay_id> payment id
        returns:    GET: json-ed payment info'''
    fee=g.user.fees.filter(Fee.id==pay_id).first()
    if not fee:
        flash('No fee with that id')
        return redirect_xhr_or_normal('.fees')
    f = stripe.Charge.retrieve(fee.pay_id,
                    api_key=current_app.config['STRIPE_CONSUMER_SECRET'])
    info=[]
    for k in ['amount', 'currency', 'paid', 'refunded', 'description']:
        info.append((k, getattr(f,k, None)))
    d = getattr(f,'created', None)
    if d:
        info.append(('created', date.fromtimestamp(d).strftime('%Y/%m/%d')))

    return render_xhr_or_normal('show_fee.html', info=info)

# RISK
@fee.route('/fee/pay', methods=['POST', 'GET'])
@login_required
def pay_fee():
    if request.method == 'POST':
        token = request.form['stripeToken']
        try:
            charge = stripe.Charge.create(
                  api_key=current_app.config['STRIPE_CONSUMER_SECRET'],
                  amount=current_app.config['FEE_AMOUNT'],
                  currency="usd",
                  card=token,
                  description=':'.join([str(g.user.id), g.user.username])
                  )
            c = Fee(pay_id=charge.id)
            g.user.fees.append(c)
            db.session.add(c)
            db.session.commit()
            g.user.paid_through=max(g.user.paid_through,dt.utcnow())+c.length
            db.session.add(g.user)
            db.session.commit()
            logger.info(charge)
            flash('Payment processed')
        except stripe.error.CardError:
            flash('Card error')
        except stripe.error.AuthenticationError:
            flash('Authentication error')
        except Exception:
            flash('Other payment error')
        finally:
            return redirect_xhr_or_normal('.fees')

    else:
        return render_xhr_or_normal('pay_service_fee.html',
                                amount=current_app.config['FEE_AMOUNT'],
                                key=current_app.config['STRIPE_CONSUMER_KEY'])

@fee.route('/fee/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@fee.route('/fee/<int(min=1):page>', defaults={'per_page': current_app.config['PAYMENTS_PER_PAGE']}, methods=['GET'])
@fee.route('/fee', defaults={'page':1, 'per_page': current_app.config['PAYMENTS_PER_PAGE']}, methods=['GET'])
@login_required
def fees(page, per_page):
    '''main fees page
        params:     GET: <page> what page to show
                    GET: <per_page> how many items per page
        returns:    GET: template'''
    fees=g.user.fees.paginate(page, per_page, False)
    return render_xhr_or_normal('fees.html', fees=fees)
#### /FEES ####

__all__=['fee']
