from .extensions import db, mail
from .forms import (OpenIssueForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm,
                        AddProviderForm, ConnectProviderForm, SelectProviderForm,
                        AddTenantForm)
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
from .utils import get_url
import stripe

#### Blueprint ####
rp = Blueprint('relation', __name__, template_folder = 'templates/relation', static_folder='static')
#### /Blueprint ####

#### EMAIL STRINGS ####
def user_email_invite(req):
    '''Email string for current user with token to confirm request:
        token = [<landlord_id>, <request_id>, 'Confirm']
    '''
    loc_str=' '.join([str(req.location.apt_number or ''), 
                                str(req.location.address.number), req.location.address.street])
    st='{0} has indicated you are a tenant @ {1}\n\nFollow this link to confirm: {2}'
    s=URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['INVITE_CONFIRM_SALT'])
    token=s.dumps([req.landlord.id, req.id, 'Confirm'])
    body=st.format(req.landlord.username, loc_str, url_for('relation.confirm_invite', token=token, _external=True))
    return body

def non_user_email_invite(prop):
    pass
#### /EMAIL STRINGS ####

#TODO Switch to landlord invite and streamline

#### LANDLORD ####
@rp.route('/tenant/add', methods=['GET', 'POST'])
@login_required
def add_tenant():
    '''invite tenant endpoint
        params:     POST: <user> username or email
                    POST: <prop_id> absolute property id
        returns:    GET: form
                    POST: redirect
    '''
    if not g.user.fee_paid():
        flash('Cannot add tenant without paying fee')
        return redirect(url_for('fee.pay_fee'))
    if g.user.properties.first() is None:
        flash('Add a property first')
        return redirect(url_for('property.add_property'))
    form=AddTenantForm()
    form.apt.choices=[(x.id, ' '.join([str(x.apt_number or ''), 
                                str(x.address.number), x.address.street])) \
                        for x in g.user.properties.all()]
    if form.validate_on_submit():
        loc_id=int(request.form['apt'])
        ten=request.form['user']
        tenant=User.query.filter(or_(User.username==ten, User.email==ten)).first()
        if tenant:
            if tenant.current_landlord():
                flash('That tenant already has a landlord')
                return redirect(url_for('.add_tenant'))
            lt=LandlordTenant(location_id=loc_id)
            lt.tenant=tenant
            g.user.tenants.append(lt)
            db.session.add(lt)
            db.session.commit()
            msg = Message('Tenant invite', recipients=[tenant.email])
            msg.body=user_email_invite(lt)
            mail.send(msg)
            flash('Invited tenant')
            return redirect(url_for('misc.home'))
        else:
            flash('No user with that info')
            return redirect(url_for('.add_tenant'))
    return render_template('add_tenant.html', form=form)

#FIX I'm breaking the rule of no GET side-effects
@rp.route('/landlord/confirm', defaults={'token': None}, methods=['GET'])
@rp.route('/landlord/confirm/<token>', methods=['GET'])
@login_required
def confirm_invite(token):
    '''confirm invite endpoint
        params:     GET: <token> (optional)
        returns:    GET: redirect or invite list
    '''
    if token is None:
        requests=LandlordTenant.query.filter(LandlordTenant.tenant == g.user,
                                            LandlordTenant.current==True,
                                            LandlordTenant.confirmed==False).all()
        if requests:
            urls=[]
            for req in requests:
                #slow?
                s=URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['INVITE_CONFIRM_SALT'])
                confirm=s.dumps([req.landlord.id, req.id, 'Confirm'])
                s=URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['INVITE_CONFIRM_SALT'])
                decline=s.dumps([req.landlord.id, req.id, 'Decline'])
                urls.append([req.landlord.username,
                            ' '.join([str(req.location.apt_number or ''),
                                            str(req.location.address.number),
                                            req.location.address.street]),
                            url_for('.confirm_invite', token=confirm),
                            url_for('.confirm_invite', token=decline)])
            return render_template('unconfirmed_requests.html', urls=urls)
        else:
            flash('No outstanding requests')
            return redirect(url_for('misc.home'))
    if g.user.current_landlord():
        flash('End relationship with current landlord first')
        return redirect(url_for('.end_relation', next=url_for('.confirm_invite', token=token)))
    s=URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['INVITE_CONFIRM_SALT'])
    sig_okay, payload = s.loads_unsafe(token, max_age=current_app.config['INVITE_CONFIRM_WITHIN'])
    if sig_okay:
        lt=LandlordTenant.query.filter(LandlordTenant.id==payload[1]).first()
        if lt:
            if lt.confirmed:
                flash('Already confirmed')
            else:
                if payload[2] == 'Confirm':
                    lt.confirmed=True
                    db.session.add(lt)
                    db.session.commit()
                    flash('Landlord confirmed')
                else:
                    db.session.delete(lt)
                    db.session.commit()
                    flash('Request declined')
        else:
            if payload[2] == 'Create':
                l=User.query.filter(User.id==payload[0]).first()
                if l is None:
                    flash('That landlord does not exist')
                    return redirect(url_for('misc.home'))
                lt=LandlordTenant(location_id=payload[1])
                lt.tenant=g.user
                l.tenants.append(lt)
                db.session.add(lt)
                db.session.commit()
                flash('Landlord confirmed')
            else:
                flash('Bad token')
        return redirect(url_for('profile.profile'))
    flash('Bad token')
    return redirect(url_for('misc.home'))

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
#@rp.route('/landlord/<landlord>/add', methods=['GET', 'POST'])
#@login_required
#def add_landlord(landlord):
    #'''make landlord request
        #params:     POST:       <location> location id
                    #GET/POST:   <landlord> landlord username
        #returns:    POST:       Redirect
                    #GET:        Request form
    #'''
    #if g.user.current_landlord():
        #flash('End relationship with current landlord first')
        #return redirect(url_for('.end_relation', next=url_for('.add_landlord', landlord=landlord)))
    #landlord=User.query.filter(User.username==landlord).first_or_404()
    #landlord.properties.first_or_404()
    #form=AddLandlordForm()
    #form.location.choices=[(x.id, ' '.join([str(x.address.number), x.address.street])) for x in landlord.properties.all()]
    #if form.validate_on_submit():
        #loc_id=int(request.form['location'])
        #landlord.properties.filter(Property.id==loc_id).first_or_404()
        #lt=LandlordTenant(location_id=loc_id)
        #lt.tenant=g.user
        #landlord.tenants.append(lt)
        #db.session.add(lt)
        #db.session.commit()
        #flash('Added landlord')
        #return redirect(url_for('misc.home'))
    #return render_template('add_landlord.html', form=form, landlord=landlord)


# ALERT USER(S)
#@rp.route('/landlord/confirm', defaults={'tenant': None}, methods=['GET'])
#@rp.route('/landlord/<tenant>/confirm', methods=['POST'])
#@login_required
#def confirm_relation(tenant):
    #'''confirm tenant request
        #params:     GET: tenant
                    #POST: confirm
        #returns:    GET: list of unconfirmed
                    #POST: redirect
    #'''
    #form=ConfirmTenantForm()
    #if form.validate_on_submit():
        #lt=LandlordTenant.query.\
                #join(User.landlords).filter(LandlordTenant.landlord_id==g.user.id,
                        #LandlordTenant.current==True,
                        #LandlordTenant.confirmed==False,
                        #User.username==tenant).\
                #first_or_404()
        #if request.form.get('confirm', None):
            #lt.confirmed=True
            #db.session.add(lt)
            #db.session.commit()
            #flash('Confirmed tenant request')
        #else:
            #db.session.delete(lt)
            #db.session.commit()
            #flash('Disallowed tenant request')
        #return redirect(url_for('misc.home'))
    #tenants=g.user.unconfirmed_tenants().all()
    #if not tenants:
        #flash('No unconfirmed tenant requests')
        #return redirect(url_for('misc.home'))
    #return render_template('unconfirmed_tenants.html', tenants=tenants, form=form)
#### /LANDLORD ####
