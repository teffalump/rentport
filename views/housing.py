from rentport.common.extensions import db, mail
from rentport.common.forms import (OpenIssueForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm,
                        AddProviderForm, ConnectProviderForm, SelectProviderForm)
from rentport.common.model import (Issue, Property, User, LandlordTenant,
                        Comment, WorkOrder, Fee, Payment, StripeUserInfo,
                        Address, SavedProvider, Provider, Image)
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
from rentport.common.utils import (get_address, render_xhr_or_normal,
                                    redirect_xhr_or_normal, yelp)
from os import path as fs
from uuid import uuid4

#### Blueprint ####
housing = Blueprint('property', __name__, template_folder = '../templates/property', static_folder='static')
#### /Blueprint ####

##### PROPERTIES #####
@housing.route('/landlord/property', methods=['GET'])
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
    return render_xhr_or_normal('properties.html', props=props, form=form)

# PAID ENDPOINT
@housing.route('/landlord/property/add', methods=['POST'])
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
        return redirect_xhr_or_normal('.properties')
    form=AddPropertyForm()
    if form.validate_on_submit():
        address=request.form['address']
        city=request.form['city']
        state=request.form['state']
        fs=', '.join([address, city, state])
        loc=get_address(fs)
        if not loc:
            flash("Address not found")
            return redirect_xhr_or_normal('.properties')
        a=Address(lat=loc.get('lat'),
                lon=loc.get('lon'),
                number=loc.get('house_number'),
                street=loc.get('road'),
                neighborhood=loc.get('neighbourhood'),
                city=loc.get('city'),
                county=loc.get('county'),
                state=loc.get('state'),
                postcode=loc.get('postcode'),
                country=loc.get('country'))
        description=request.form['description']

        #Optional unit
        unit=request.form.get('unit')
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
        return redirect_xhr_or_normal('.properties')
    return render_xhr_or_normal('add_property.html', form=form)

@housing.route('/landlord/property/<int(min=1):prop_id>/modify', methods=['GET', 'POST'])
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
        return redirect_xhr_or_normal('.properties')
    form=ModifyPropertyForm()
    if form.validate_on_submit():
        prop.description=request.form['description']
        db.session.add(prop)
        db.session.commit()
        flash("Property modified")
        return redirect_xhr_or_normal('.properties')
    form.description.data=prop.description
    return render_xhr_or_normal('modify_location.html', form=form, location=prop)

# TODO Eventually minimize the redundant code and ajax these sections
#@housing.route('/landlord/provider/connect/<int:prop_id>/<int:prov_id>', methods=['GET', 'POST'])
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

@housing.route('/landlord/provider/add', methods=['POST'])
@login_required
def add_provider():
    '''Add local provider'''
    form=AddProviderForm()
    if form.validate_on_submit():
        p=SavedProvider()
        p.service=request.form['area']
        p.name=request.form['name']
        p.email=request.form['email']
        p.website=request.form['website']
        p.phone=request.form['phone']
        p.by_user_id=g.user.id
        db.session.add(p)
        db.session.commit()
        flash('Provider added')
        return render_xhr_or_normal('show_provider.html', prov=p)
    return render_xhr_or_normal('add_provider.html', form=form)

@housing.route('/landlord/provider/yelp', defaults={'business_id': None},
                        methods=['GET'])
@housing.route('/landlord/provider/yelp/<business_id>', methods=['GET'])
@login_required
def get_yelp_providers(business_id):
    """Return yelp providers"""
    yelp_api=yelp()
    if business_id:
        info=yelp_api.GetBusiness(business_id)
    else:
        info=yelp_api.Search(dict(request.args.items()))
    return jsonify(info)


@housing.route('/landlord/provider', defaults={'prov_id': None}, methods=['GET'])
@housing.route('/landlord/provider/<int:prov_id>', methods=['GET'])
@login_required
def show_providers(prov_id):
    '''Show providers'''
    b=Provider.join(WorkOrder).query.filter(or_(Provider.by_user==g.user, Provider.by_user==g.user.current_landlord(), WorkOrder.issue.location==g.user.current_location()))
    if prov_id:
        x=b.filter(Provider.id==prov_id).first()
        if not x:
            flash('Not a valid provider')
            return redirect_xhr_or_normal('.show_providers')
        return render_xhr_or_normal('show_provider.html', prov=x)
    else:
        form=AddProviderForm()
        return render_xhr_or_normal('show_providers.html', providers=b.all(), form=form,
                action=url_for('.add_provider'))
#### /PROPERTIES ####

__all__=['housing']