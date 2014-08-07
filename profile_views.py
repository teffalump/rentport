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
rp = Blueprint('profile', __name__, template_folder = 'templates/profile', static_folder='static')
#### /Blueprint ####

#### PROFILE ####
@rp.route('/profile', methods=['GET'])
@login_required
def profile():
    '''display profile
        params:     NONE
        returns:    GET: profile info
    '''
    resend_form = ResendNotifyForm()
    phone_form = AddPhoneNumber()
    tenants = g.user.current_tenants().all()
    return render_template('profile.html', tenants=tenants, resend_form=resend_form, phone_form=phone_form)

@rp.route('/profile/phone', methods=['POST'])
@login_required
def phone():
    '''add phone number
        params:     POST: <phone> phone number w/o country code
                    POST: <country> country code
        returns:    POST: redirect'''
    #TODO Ajaxify?
    #TODO Test valid #
    form = AddPhoneNumber()
    if form.validate_on_submit():
        p = ''.join(filter(lambda x: x.isdigit(), request.form['phone']))
        if len(p) != 10:
            flash('Invalid number: ' + p, category='error')
            return redirect(url_for('.profile'))
        full_p = ''.join([request.form['country'], p])
        g.user.phone = full_p
        g.user.phone_confirmed=False
        db.session.add(g.user)
        db.session.commit()
        flash('Phone updated; Validation text sent!')
        return redirect(url_for('.profile'))
    for error in form.phone.errors: flash(error, category='error')
    for error in form.country.errors: flash(error, category='error')
    return redirect(url_for('.profile'))

@rp.route('/profile/notify', methods=['GET', 'POST'])
@login_required
def notify():
    '''change notification settings
        params:     POST:   method - notification method
        returns:    GET:    change notify form
                    POST:   redirect
    '''
    form = ChangeNotifyForm()

    # If user has confirmed phone, add that notify choice
    if g.user.phone_confirmed:
        form.method.choices.extend([('Text', 'Text'), ('Both', 'Both')])

    if form.validate_on_submit():
        if request.form['method'] != g.user.notify_method:
            g.user.notify_method = request.form['method']
            g.user.notify_confirmed = False
            db.session.add(g.user)
            db.session.commit()
            flash('Updated unconfirmed settings')
            s=URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['NOTIFY_CONFIRM_SALT'])
            token=s.dumps(g.user.id)
            msg = Message('Confirm settings', recipients=[g.user.email])
            msg.body='Confirm notification changes: {0}'.format(url_for('.confirm_notify', token=token, _external=True))
            mail.send(msg)
            flash('Confirmation email sent')
        else:
            flash('Nothing changed')
        return redirect(url_for('.profile'))

    return render_template('change_notify.html', form=form)

@rp.route('/profile/notify/resend', methods=['POST'])
@login_required
def resend_notify_confirm():
    form = ResendNotifyForm()
    if form.validate_on_submit():
        if request.form.get('resend', True):
            s=URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['NOTIFY_CONFIRM_SALT'])
            token=s.dumps(g.user.id)
            msg = Message('Confirm settings', recipients=[g.user.email])
            msg.body='Confirm notification changes: {0}'.format(url_for('.confirm_notify', token=token, _external=True))
            mail.send(msg)
            flash('Confirmation email sent')
    return redirect(url_for('.profile'))

@rp.route('/profile/notify/<token>', methods=['GET'])
@login_required
def confirm_notify(token):
    '''confirm notify endpoint
        params:     GET: token
        returns:    GET: redirect
    '''
    s=URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['NOTIFY_CONFIRM_SALT'])
    sig_okay, payload = s.loads_unsafe(token, max_age=current_app.config['NOTIFY_CONFIRM_WITHIN'])
    if sig_okay and payload == g.user.id:
        g.user.notify_confirmed=True
        db.session.add(g.user)
        db.session.commit()
        flash('Settings updated')
    else:
        flash('Bad token')
    return redirect(url_for('.profile'))
#### /PROFILE ####
