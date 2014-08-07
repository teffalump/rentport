
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
rp = Blueprint('relation', __name__, template_folder = 'templates', static_folder='static')
#### /Blueprint ####

#### LANDLORD ####
# ALERT USER(S)
@rp.route('/landlord/<landlord>/add', methods=['GET', 'POST'])
@login_required
def add_landlord(landlord):
    '''make landlord request
        params:     POST:       <location> location id
                    GET/POST:   <landlord> landlord username
        returns:    POST:       Redirect
                    GET:        Request form
    '''
    if g.user.current_landlord():
        flash('End relationship with current landlord first')
        return redirect(url_for('.end_relation', next=url_for('.add_landlord', landlord=landlord)))
    landlord=User.query.filter(User.username==landlord).first_or_404()
    landlord.properties.first_or_404()
    form=AddLandlordForm()
    form.location.choices=[(x.id, ' '.join([str(x.address.number), x.address.street])) for x in landlord.properties.all()]
    if form.validate_on_submit():
        loc_id=int(request.form['location'])
        landlord.properties.filter(Property.id==loc_id).first_or_404()
        lt=LandlordTenant(location_id=loc_id)
        lt.tenant=g.user
        landlord.tenants.append(lt)
        db.session.add(lt)
        db.session.commit()
        flash('Added landlord')
        return redirect(url_for('misc.home'))
    return render_template('add_landlord.html', form=form, landlord=landlord)

# ALERT USER(S)
@rp.route('/landlord/end', methods=['POST', 'GET'])
@login_required
def end_relation():
    '''end landlord relation
        params:     POST: <end> = True
        returns:    POST: Redirect
                    GET: End relation form
    '''
    form=EndLandlordForm()
    lt=LandlordTenant.query.\
            filter(LandlordTenant.tenant_id==g.user.id,
                    LandlordTenant.current==True).\
            first()
    if not lt:
        flash('No relationship to end')
        return redirect(url_for('misc.home'))
    if form.validate_on_submit():
        lt.current=False
        db.session.add(lt)
        db.session.commit()
        flash('Ended landlord relationship')
        return redirect(get_url('misc.home'))
    return render_template('end_relation.html', form=form, landlord=lt.landlord)

# ALERT USER(S)
@rp.route('/landlord/confirm', defaults={'tenant': None}, methods=['GET'])
@rp.route('/landlord/<tenant>/confirm', methods=['POST'])
@login_required
def confirm_relation(tenant):
    '''confirm tenant request
        params:     GET: tenant
                    POST: confirm
        returns:    GET: list of unconfirmed
                    POST: redirect
    '''
    form=ConfirmTenantForm()
    if form.validate_on_submit():
        lt=LandlordTenant.query.\
                join(User.landlords).filter(LandlordTenant.landlord_id==g.user.id,
                        LandlordTenant.current==True,
                        LandlordTenant.confirmed==False,
                        User.username==tenant).\
                first_or_404()
        if request.form.get('confirm', None):
            lt.confirmed=True
            db.session.add(lt)
            db.session.commit()
            flash('Confirmed tenant request')
        else:
            db.session.delete(lt)
            db.session.commit()
            flash('Disallowed tenant request')
        return redirect(url_for('misc.home'))
    tenants=g.user.unconfirmed_tenants().all()
    if not tenants:
        flash('No unconfirmed tenant requests')
        return redirect(url_for('misc.home'))
    return render_template('unconfirmed_tenants.html', tenants=tenants, form=form)
#### /LANDLORD ####
