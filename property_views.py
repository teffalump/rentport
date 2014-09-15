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
#from geopy.geocoders import Nominatim, OpenMapQuest
from geopy.geocoders import OpenMapQuest
from os import path as fs
from uuid import uuid4

#### Blueprint ####
rp = Blueprint('property', __name__, template_folder = 'templates/property', static_folder='static')
#### /Blueprint ####

##### PROPERTIES #####
@rp.route('/landlord/property', methods=['GET'])
@login_required
def properties():
    '''show properties
        params:     NONE
        returns:    GET: List of properties
    '''
    if g.user.fee_paid():
        form=AddPropertyForm()
    else:
        form=None
    props = g.user.properties.all()
    return render_template('properties.html', props=props, form=form)

# PAID ENDPOINT
@rp.route('/landlord/property/add', methods=['GET', 'POST'])
@login_required
def add_property():
    '''add property
        params:     POST: <location> location id
                    POST: <description> property description
        returns:    POST: Redirect
                    GET: Add property form
    '''
    if not g.user.fee_paid():
        flash('You need to pay to access this endpoint')
        return redirect(url_for('.properties'))
    form=AddPropertyForm()
    if form.validate_on_submit():
        address=request.form['address']
        city=request.form['city']
        state=request.form['state']
        fs=', '.join([address, city, state])
        n = OpenMapQuest(timeout=5)
        loc = n.geocode(fs)
        if not loc:
            flash("Address not found")
            return redirect(url_for('.properties'))
        ad = [x.strip() for x in loc[0].split(',')]
        try:
            int(ad[0])
        except:
            #no number
            flash("Ambiguous address")
            return redirect(url_for('.properties'))
        if len(ad) != 8:
            #no neighborhood
            ad.insert(2, None)
        a=Address(lat=loc.latitude, lon=loc.longitude,
                number=ad[0],
                street=ad[1],
                neighborhood=ad[2],
                city=ad[3],
                county=ad[4],
                state=ad[5],
                postcode=ad[6],
                country=ad[7])
        unit=request.form['unit']
        description=request.form['description']
        if unit:
            p=Property(apt_number=int(unit),
                    description=description)
        else:
            p=Property(description=description)
        p.address=a
        g.user.properties.append(p)
        db.session.add(p)
        db.session.commit()
        flash("Property added")
        return redirect(url_for('.properties'))
    return render_template('add_property.html', form=form)

@rp.route('/landlord/property/<int(min=1):prop_id>/modify', methods=['GET', 'POST'])
@login_required
def modify_property(prop_id):
    '''modify existing property
        params:     POST: <description> new property description
                    GET/POST: <prop_id> absolute location id
        returns:    POST: Redirect
                    GET: Modify property form
    '''
    prop=g.user.properties.filter(Property.id==prop_id).first()
    if not prop:
        flash('Not a valid property id')
        return redirect(url_for('.properties'))
    form=ModifyPropertyForm()
    if form.validate_on_submit():
        prop.description=request.form['description']
        db.session.add(prop)
        db.session.commit()
        flash("Property modified")
        return redirect(url_for('.properties'))
    form.description.data=prop.description
    return render_template('modify_location.html', form=form, location=prop)

# TODO Eventually minimize the redundant code and ajax these sections
#@rp.route('/landlord/provider/connect/<int:prop_id>/<int:prov_id>', methods=['GET', 'POST'])
#@login_required
#def connect_provider(prop_id, prov_id):
    #'''(Dis)Connect provider with property'''
    #form=ConnectProviderForm()
    #prop=g.user.properties.filter(Property.id==prop_id).first()
    #if not prop:
        #return jsonify({'error': 'No property'})
    #prov=Provider.query.filter(Provider.id==prov_id).first()
    #if not prov:
        #return jsonify({'error': 'No provider'})
    #if form.validate_on_submit():
        #if request.form.get('action', None):
            #if prov in prop.providers:
                #prop.providers.remove(prov)
                #db.session.add(prop)
                #db.session.commit()
                #return jsonify({'success': 'Provider disconnected'})
            #else:
                #prop.providers.append(prov)
                #db.session.add(prop)
                #db.session.commit()
                #return jsonify({'success': 'Provider connected'})
        #else:
            #return jsonify({'error': 'Bad request'})
    #if prov in prop.providers:
        #form.action.label.text = 'Disconnect'
    #return render_template('connect_provider.html', form=form,
                                                    #prop=prop,
                                                    #prov=prov)

@rp.route('/landlord/provider/add', methods=['POST'])
@login_required
def add_provider():
    '''Add provider'''
    form=AddProviderForm()
    if form.validate_on_submit():
        p=Provider()
        p.service=request.form['area']
        p.name=request.form['name']
        p.email=request.form['email']
        p.website=request.form['website']
        p.phone=request.form['phone']
        p.by_user_id=g.user.id
        db.session.add(p)
        db.session.commit()
        return jsonify({'success': 'Provider added'})
    return render_template('add_provider.html', form=form)

@rp.route('/landlord/provider', defaults={'prov_id': None}, methods=['GET'])
@rp.route('/landlord/provider/<int:prov_id>', methods=['GET'])
@login_required
def show_providers(prov_id):
    '''Show providers'''
    if prov_id:
        b=g.user.providers.filter(Provider.id==prov_id).first()
        if not b:
            return jsonify({'error': 'No provider'})
        return jsonify({'success': 'Provider found',
                        'name': b.name,
                        'email': b.email,
                        'service': b.service,
                        'phone': b.phone,
                        'website': b.website})
    else:
        form=AddProviderForm()
        #a=[]
        #for b in g.user.providers.all():
            #a.append({'name': b.name,
                        #'email': b.email,
                        #'service': b.service,
                        #'phone': b.phone,
                        #'website': b.website})
        #if a:
            #return jsonify({'success': 'Providers found',
                            #'providers': a})
        #return jsonify({'error': 'No provider'})
        return render_template('show_providers.html', providers=g.user.providers.all(), form=form,
                action=url_for('.add_provider'))
#### /PROPERTIES ####
