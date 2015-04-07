from rentport.common.extensions import db, mail
from rentport.common.forms import (OpenIssueForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm,
                        AddProviderForm, ConnectProviderForm, SelectProviderForm,
                        AddTenantForm)
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
from sqlalchemy.exc import IntegrityError
from werkzeug.security import gen_salt
from werkzeug import secure_filename
from sys import exc_info as er
from datetime import datetime as dt
from geopy.geocoders import Nominatim
from os import path as fs
from uuid import uuid4
from rentport.common.utils import (get_url, render_xhr_or_normal,
                                    redirect_xhr_or_normal)
import stripe
import logging

logger = logging.getLogger(__name__)

#### Blueprint ####
relation = Blueprint('relation', __name__, template_folder = '../templates/relation', static_folder='static')
#### /Blueprint ####

#### EMAIL STRINGS ####
def user_email_invite(req):
    '''Email string for current user with token to confirm request:
        token = [<landlord_id>, <request_id>, 'Confirm']
    '''
    loc_str=' '.join([str(req.location.apt_number or ''),
                        str(req.location.address.number),
                        req.location.address.street])
    st='{0} has indicated you are a tenant @ {1}\n\n\
            Follow this link to confirm: {2}'
    s=URLSafeTimedSerializer(current_app.config['SECRET_KEY'],
                            salt=current_app.config['INVITE_CONFIRM_SALT'])
    token=s.dumps([req.landlord.id, req.id, 'Confirm'])
    body=st.format(req.landlord.username,
                    loc_str,
                    url_for('relation.confirm_invite',
                            token=token,
                            _external=True))
    return body

def non_user_email_invite(prop):
    pass
#### /EMAIL STRINGS ####

#TODO Switch to landlord invite and streamline

#### LANDLORD ####
@relation.route('/tenant/add', methods=['GET', 'POST'])
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
        return redirect_xhr_or_normal('fee.pay_fee')
    if g.user.properties.first() is None:
        flash('Add a property first')
        return redirect_xhr_or_normal('property.add_property')
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
                return redirect_xhr_or_normal('.add_tenant')
            try:
                lt=LandlordTenant(location_id=loc_id)
                lt.tenant=tenant
                g.user.tenants.append(lt)
                db.session.add(lt)
                db.session.commit()
                msg = Message('Tenant invite', recipients=[tenant.email])
                msg.body=user_email_invite(lt)
                mail.send(msg)
                logger.info('mail sent: {0}'.format(msg))
                flash('Invited tenant')
            except IntegrityError:
                flash('Invite already sent')
            finally:
                return redirect_xhr_or_normal('misc.home')
        else:
            flash('No user with that info')
            return redirect_xhr_or_normal('.add_tenant')
    try:
        i=int(request.args['ident'])
        options=[(x,y) for x, y in form.apt.choices if x == i]
        if options:
            form.apt.choices=options
    except:
        pass
    finally:
        return render_xhr_or_normal('add_tenant.html', form=form)

#FIX I'm breaking the rule of no GET side-effects
@relation.route('/landlord/confirm', defaults={'token': None}, methods=['GET'])
@relation.route('/landlord/confirm/<token>', methods=['GET'])
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
                #ugly? I mean, I could move it to POST but w/e
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
            return render_xhr_or_normal('unconfirmed_requests.html', urls=urls)
        else:
            flash('No outstanding requests')
            return redirect_xhr_or_normal('misc.home')
    s=URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['INVITE_CONFIRM_SALT'])
    sig_okay, payload = s.loads_unsafe(token, max_age=current_app.config['INVITE_CONFIRM_WITHIN'])
    if sig_okay:
        lt=LandlordTenant.query.filter(LandlordTenant.id==payload[1]).first()
        if lt:
            if lt.confirmed:
                flash('Already confirmed')
            else:
                if payload[2] == 'Confirm':
                    if g.user.current_landlord():
                        flash('End relationship with current landlord first')
                        return redirect_xhr_or_normal('profile.show_profile', next=url_for('.confirm_invite', token=token))
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
                    return redirect_xhr_or_normal('misc.home')
                lt=LandlordTenant(location_id=payload[1])
                lt.tenant=g.user
                l.tenants.append(lt)
                db.session.add(lt)
                db.session.commit()
                flash('Landlord confirmed')
            else:
                flash('Bad token')
        return redirect_xhr_or_normal('profile.show_profile')
    flash('Bad token')
    return redirect_xhr_or_normal('misc.home')

# ALERT USER(S)
@relation.route('/landlord/end', methods=['POST', 'GET'])
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
        return redirect_xhr_or_normal('misc.home')
    if form.validate_on_submit():
        lt.current=False
        db.session.add(lt)
        db.session.commit()
        flash('Ended landlord relationship')
        return redirect_xhr_or_normal('profile.show_profile')
    return render_xhr_or_normal('end_relation.html', form=form, landlord=lt.landlord)
#### /LANDLORD ####

__all__=['relation']
