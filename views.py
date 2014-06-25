from rentport.extensions import db, mail
from rentport.forms import (OpenIssueForm, PostCommentForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm)
from flask.ext.mail import Message
from flask.ext.security import login_required
from requests_oauthlib import OAuth2Session
from rentport.model import (Issue, Property, User, LandlordTenant,
                            Comment, Fee, Payment, StripeUserInfo)
from flask import (Blueprint, render_template, request, g, redirect, url_for,
                    abort, flash, session, json, jsonify, current_app)
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import or_
from werkzeug.security import gen_salt
from sys import exc_info as er
from datetime import datetime as dt
import stripe

#### Blueprint ####

rp = Blueprint('rentport', __name__, template_folder = 'templates', static_folder='static')

#### /Blueprint ####

#### UTILS ####
def get_url(endpoint, **kw):
    '''Return endpoint url, or next arg url'''
    try:
        return request.args['next']
    except:
        return url_for(endpoint, **kw)
#### /UTILS ####


#### DEFAULT ####
@rp.route('/')
@login_required
def home():
    return render_template('home.html')
#### /DEFAULT ####

#### ISSUES ####
@rp.route('/issues', methods=['GET'])
@rp.route('/issues/<int(min=1):page>', methods=['GET'])
@rp.route('/issues/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def issues(page=1, per_page=current_app.config['ISSUES_PER_PAGE']):
    '''display main issues page
        params:     GET: <page> page number (optional)
                    GET: <per_page> # of issues per page (optional)
        returns:    GET: list of issues
    '''
    allowed_sort={'id': Issue.id,
            'date': Issue.opened,
            'severity': Issue.severity,
            'status': Issue.status}
    sort_key=request.args.get('sort', 'id')
    sort = allowed_sort.get(sort_key, Issue.id)
    order_key = request.args.get('order')
    if order_key =='asc':
        issues=g.user.all_issues().order_by(sort.asc()).\
                paginate(page, per_page, False)
    else:
        order_key='desc'
        issues=g.user.all_issues().order_by(sort.desc()).\
                paginate(page, per_page, False)
    return render_template('issues.html', issues=issues, sort=sort_key, order=order_key)

@rp.route('/issues/<int(min=1):ident>/show', methods=['GET'])
@login_required
def show_issue(ident):
    '''show issue
        params:     GET: <ident> absolute id
        returns:    GET: detailed issue page
    '''
    issue=g.user.all_issues().filter(Issue.status=='Open',
            Issue.id==ident).first()
    comment = None
    close = None
    if not issue:
        flash('No issue with that id')
        return redirect(url_for('rentport.issues'))
    if issue.landlord_id == g.user.id or g.user.landlords.filter(LandlordTenant.current==True).first().confirmed:
        comment=CommentForm()
    if issue.creator_id == g.user.id or issue.landlord_id == g.user.id:
        close=CloseIssueForm()
    return render_template('show_issue.html', issue=issue, comment=comment, close=close)

# PAID ENDPOINT
# MUST BE CONFIRMED
# ALERT USER(S)
@rp.route('/issues/open', methods=['POST', 'GET'])
@login_required
def open_issue():
    '''open new issue at current location
        params:     POST:   <severity> issue severity
                    POST:   <description> issue description
        returns:    POST:   Redirect for main issues
                    GET:    Open issue form
    '''
    lt = g.user.landlords.filter(LandlordTenant.current==True).first()
    if not lt:
        flash('No current landlord')
        return redirect(url_for('rentport.issues'))
    if not lt.confirmed:
        flash('Need to be confirmed!')
        return redirect(url_for('rentport.profile'))
    if not lt.landlord.fee_paid():
        flash('Landlord needs to pay fee')
        return redirect(url_for('rentport.issues'))
    form=OpenIssueForm()
    if form.validate_on_submit():
        i=g.user.open_issue()
        i.description=request.form['description']
        i.severity=request.form['severity']
        db.session.add(i)
        db.session.commit()
        flash('Issue opened')
        msg = Message('New issue', recipients=[i.landlord.email])
        msg.body = 'New issue @ {0}: {1} ::: {2}'.\
                format(i.location.location, i.severity, i.description)
        mail.send(msg)
        flash('Landlord notified')
        return redirect(url_for('rentport.issues'))
    return render_template('open_issue.html', form=form)

# MUST BE CONFIRMED
@rp.route('/issues/<int(min=1):ident>/comment', methods=['POST'])
@login_required
def comment(ident):
    '''comment on issue
        params:     POST: <comment> comment text
                    POST: <ident> absolute id
        returns:    POST: Redirect to main issues page
    '''
    #TODO Jsonify?
    form = CommentForm()
    issue=g.user.all_issues().\
            filter(Issue.status=='Open',Issue.id==ident).first()
    if not g.user.landlords.filter(LandlordTenant.current==True).first().confirmed:
        flash('Need to be confirmed by landlord!')
    if not issue:
        flash('No issue with that id')
    if form.validate_on_submit():
        d=request.form['comment']
        comment=Comment(text=d, user_id=g.user.id)
        issue.comments.append(comment)
        db.session.add(comment)
        db.session.commit()
        flash('Commented on issue')
        return redirect(url_for('rentport.show_issue', ident=ident))
    return redirect(url_for('rentport.issues'))

@rp.route('/issues/<int(min=1):ident>/close', methods=['POST'])
@login_required
def close_issue(ident):
    '''close issue - only opener or landlord can
        params:     POST: <reason> reason (to close issue)
                    POST: <ident> absolute id
        returns:    POST: Redirect to main issues page
    '''
    #TODO Jsonify?
    issue=Issue.query.filter(or_(Issue.landlord_id==g.user.id,
                Issue.creator_id==g.user.id),
                Issue.status == 'Open',
                Issue.id == ident).first()
    form=CloseIssueForm()
    if not issue:
        flash('No close-able issue with that id')
        return redirect(url_for('rentport.issues'))
    if form.validate_on_submit():
        reason=request.form['reason']
        issue.status='Closed'
        issue.closed_because=reason
        db.session.add(issue)
        db.session.commit()
        flash('Issue closed')
        return redirect(url_for('rentport.issues'))
    return redirect(url_for('rentport.issues', ident=ident))

#### /ISSUES ####

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
        params:     POST: <phone> phone number
        returns:    POST: redirect'''
    #TODO Ajaxify?
    #TODO Test valid #
    form = AddPhoneNumber()
    if form.validate_on_submit():
        p = request.form['phone']
        g.user.phone = p
        g.user.phone_confirmed=False
        db.session.add(g.user)
        db.session.commit()
        flash('Phone updated; Validation text sent!')
    for error in form.phone.errors: flash(error, category='error')
    return redirect(url_for('rentport.profile'))

@rp.route('/profile/notify', methods=['GET', 'POST'])
@login_required
def notify():
    '''change notification settings
        params:     POST:   method - notification method
        returns:    GET:    change notify form
                    POST:   redirect
    '''
    form = ChangeNotifyForm()
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
            msg.body='Confirm notification changes: {0}'.format(url_for('rentport.confirm_notify', token=token, _external=True))
            mail.send(msg)
            flash('Confirmation email sent')
        else:
            flash('Nothing changed')
        return redirect(url_for('rentport.profile'))
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
            msg.body='Confirm notification changes: {0}'.format(url_for('rentport.confirm_notify', token=token, _external=True))
            mail.send(msg)
            flash('Confirmation email sent')
    return redirect(url_for('rentport.profile'))

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
    return redirect(url_for('rentport.profile'))
#### /PROFILE ####

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
        return redirect(url_for('rentport.end_relation', next=url_for('rentport.add_landlord', landlord=landlord)))
    landlord=User.query.filter(User.username==landlord).first_or_404()
    landlord.properties.first_or_404()
    form=AddLandlordForm()
    form.location.choices=[(x.id, x.location) for x in landlord.properties.all()]
    if form.validate_on_submit():
        loc_id=int(request.form['location'])
        landlord.properties.filter(Property.id==loc_id).first_or_404()
        lt=LandlordTenant(location_id=loc_id)
        lt.tenant=g.user
        landlord.tenants.append(lt)
        db.session.add(lt)
        db.session.commit()
        flash('Added landlord')
        return redirect(url_for('rentport.home'))
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
        return redirect(url_for('rentport.home'))
    if form.validate_on_submit():
        lt.current=False
        db.session.add(lt)
        db.session.commit()
        flash('Ended landlord relationship')
        return redirect(get_url('rentport.home'))
    return render_template('end_relation.html', form=form, landlord=lt.landlord)
#### /LANDLORD ####

##### PROPERTIES #####
@rp.route('/landlord/property', methods=['GET'])
@login_required
def properties():
    '''show properties
        params:     NONE
        returns:    GET: List of properties
    '''
    props = g.user.properties.all()
    return render_template('properties.html', props=props)

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
        return redirect(url_for('rentport.properties'))
    form=AddPropertyForm()
    if form.validate_on_submit():
        location=request.form['location']
        description=request.form['description']
        p=Property(location=location,
                description=description)
        g.user.properties.append(p)
        db.session.add(p)
        db.session.commit()
        flash("Property added")
        return redirect(url_for('rentport.properties'))
    return render_template('add_property.html', form=form)

@rp.route('/landlord/property/<int(min=1):prop_id>/modify', methods=['GET', 'POST'])
@login_required
def modify_property(prop_id):
    '''modify existing property
        params:     POST: <description> new property description
                    POST: <location> new location id
                    GET/POST: <prop_id> absolute location id
        returns:    POST: Redirect
                    GET: Modify property form
    '''
    prop=g.user.properties.filter(Property.id==prop_id).first()
    if not prop:
        flash('Not a valid property id')
        return redirect(url_for('rentport.properties'))
    form=ModifyPropertyForm()
    if form.validate_on_submit():
        location=request.form['location']
        description=request.form['description']
        prop.location=location
        prop.description=description
        db.session.add(prop)
        db.session.commit()
        flash("Property modified")
        return redirect(url_for('rentport.properties'))
    form.location.data=prop.location
    form.description.data=prop.description
    return render_template('modify_location.html', form=form, location=prop)
#### /PROPERTIES ####

#### TENANTS ####
# ALERT USER(S)
@rp.route('/tenant/confirm', defaults={'tenant': None}, methods=['GET'])
@rp.route('/tenant/<tenant>/confirm', methods=['POST'])
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
        if request.form.get('confirm', None) == 'True':
            lt.confirmed=True
            db.session.add(lt)
            db.session.commit()
            flash('Confirmed tenant request')
        else:
            db.session.delete(lt)
            db.session.commit()
            flash('Disallowed tenant request')
        return redirect(url_for('rentport.home'))
    tenants=g.user.unconfirmed_tenants().all()
    if not tenants:
        flash('No unconfirmed tenant requests')
        return redirect(url_for('rentport.home'))
    return render_template('unconfirmed_tenants.html', tenants=tenants, form=form)
#### /TENANTS ####

#### OAUTH ####
@rp.route('/oauth/authorize', methods=['GET'])
@login_required
def authorize():
    '''Authorize Stripe, or refresh'''
    if g.user.stripe:
        flash('Have stripe info already')
        return redirect(url_for('rentport.home'))
    oauth=OAuth2Session(current_app.config['STRIPE_CONSUMER_KEY'],
        redirect_uri=url_for('rentport.authorized', _external=True),
        scope=current_app.config['STRIPE_OAUTH_CONFIG']['scope'])
    auth_url, state=oauth.authorization_url(
            current_app.config['STRIPE_OAUTH_CONFIG']['authorize_url'])
    session['state']=state
    return redirect(auth_url)

@rp.route('/oauth/authorized', methods=['GET'])
@login_required
def authorized():
    if g.user.stripe:
        flash('Have stripe info already')
        return redirect(url_for('rentport.home'))
    oauth=OAuth2Session(current_app.config['STRIPE_CONSUMER_KEY'],
                    state=session['state'])
    token=oauth.fetch_token(
                    current_app.config['STRIPE_OAUTH_CONFIG']['access_token_url'],
                    current_app.config['STRIPE_CONSUMER_SECRET'],
                    authorization_response=request.url)
    s = StripeUserInfo(access_token=token['access_token'],
                       refresh_token=token['refresh_token'],
                       user_acct=token['stripe_user_id'],
                       pub_key=token['stripe_publishable_key'])
    g.user.stripe=s
    db.session.add(s)
    db.session.commit()
    flash('Authorized!')
    return redirect(url_for('rentport.home'))
#### /OAUTH ####

#### PAYMENTS ####
# RISK
# PAID ENDPOINT
# MUST BE CONFIRMED
# ALERT USER(S)
@rp.route('/pay/landlord', defaults={'amount': None}, methods=['GET'])
@rp.route('/pay/landlord/<int(min=10):amount>', methods=['POST', 'GET'])
@login_required
def pay_rent(amount):
    lt=g.user.landlords.filter(LandlordTenant.current==True).first()
    if not lt:
        flash('No current landlord')
        return redirect(url_for('rentport.payments'))
    if not lt.confirmed:
        flash('Need to be confirmed!')
        return redirect(url_for('rentport.payments'))
    if not lt.landlord.fee_paid():
        flash('Landlord has not paid service fee')
        return redirect(url_for('rentport.payments'))
    if not lt.landlord.stripe:
        flash('Landlord cannot accept CC')
        return redirect(url_for('rentport.payments'))
    if amount:
        cents=amount*100
        if request.method == 'POST':
            token = request.form['stripeToken']
            try:
                charge = stripe.Charge.create(
                      api_key=landlord.stripe.access_token,
                      amount=cents,
                      currency="usd",
                      card=token,
                      description=':'.join([g.user.id, g.user.username]))
                p = Payment(to_user_id=landlord.id, pay_id=charge.id)
                g.user.sent_payments.append(p)
                db.session.add(p)
                db.session.commit()
                flash('Payment processed')
                msg = Message('Rent payment', recipients=[landlord.email])
                msg.body = 'Rent from {0}: amt: {1}'.\
                        format(g.user.username, '$' + amount)
                mail.send(msg)
                flash('Landlord notified')
                return redirect(url_for('rentport.payments'))
            except stripe.error.CardError:
                flash('Card error')
                return redirect(url_for('rentport.pay_rent'))
            except stripe.error.AuthenticationError:
                flash('Authentication error')
                return redirect(url_for('rentport.pay_rent'))
            except Exception:
                flash(str(er()))
                return redirect(url_for('rentport.pay_rent'))
        else:
            return render_template('pay_landlord.html', landlord=landlord,
                                                        amount=amount)
    else:
        return render_template('get_pay_amount.html', landlord=landlord, user=g.user)

# RISK
@rp.route('/pay/fee', methods=['POST', 'GET'])
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
            flash('Payment processed')
            return redirect(url_for('rentport.fees'))
        except stripe.error.CardError:
            flash('Card error')
            return redirect(url_for('rentport.pay_fee'))
        except stripe.error.AuthenticationError:
            flash('Authentication error')
            return redirect(url_for('rentport.pay_fee'))
        except Exception:
            flash(str(er()))
            return redirect(url_for('rentport.pay_fee'))
    else:
        return render_template('pay_service_fee.html',
                                amount=current_app.config['FEE_AMOUNT'],
                                key=current_app.config['STRIPE_CONSUMER_KEY'])

@rp.route('/payments', methods=['GET'])
@rp.route('/payments/<int(min=1):page>', methods=['GET'])
@rp.route('/payments/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def payments(page=1, per_page=current_app.config['PAYMENTS_PER_PAGE']):
    '''main payments page
        params:     GET: <page> page to show
                    GET: <per_page> items per page
        returns:    GET: template'''
    allowed_sort={'id': Payment.id,
            'date': Payment.time,
            'status': Payment.status,
            'from': Payment.from_user,
            'to': Payment.to_user}
    sort_key=request.args.get('sort', 'id')
    sort = allowed_sort.get(sort_key, Payment.id)
    order_key = request.args.get('order', 'desc')
    if order_key =='asc':
        payments=g.user.payments().order_by(sort.asc()).\
                paginate(page, per_page, False)
    else:
        order_key='desc'
        payments=g.user.payments().order_by(sort.desc()).\
                paginate(page, per_page, False)
    return render_template('payments.html', payments=payments, sort=sort_key, order=order_key)

@rp.route('/payments/<int:pay_id>/show', methods=['GET'])
@login_required
def show_payment(pay_id):
    '''show extended payment info
        params:     GET: <pay_id> payment id
        returns:    GET: json-ed payment info'''
    payment=Payment.query.filter(Payment.id==pay_id).first()
    if not payment:
        flash('No payment with that id')
        return jsonify({'error': 'No payment with that id'})
    p = stripe.Charge.retrieve(payment.pay_id,
                    api_key=payment.from_user.stripe.access_token).to_dict()
    return jsonify({k:v for (k,v) in p.items() if k in \
            ['amount', 'currency', 'paid', 'refunded', 'description']})

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

@rp.route('/hook/stripe', methods=['POST'])
def stripe_hook():
    #TODO Add more hooks
    event=json.loads(request.data)
    c = stripe.Event.retrieve(event['id'],
            api_key=current_app.config['STRIPE_CONSUMER_SECRET'])
    acct=c.get('user_id', None)
    if c['type']=='account.application.deauthorized':
        t=StripeUserInfo.query.filter(StripeUserInfo.user_acct==acct).first()
        if not t: return ''
        db.session.delete(t)
        db.session.commit()
    elif c['data']['object']=='charge':
        i=Payment.query.filter(Payment.pay_id==c['data']['object']['id']).first() \
                or Fee.query.filter(Fee.pay_id==c['data']['object']['id']).first()
        if not i: return ''
        if c['type']=='charge.succeeded':
            i.status='Confirmed'
        elif c['type']=='charge.refunded':
            i.status='Refunded'
        elif c['type']=='charge.failed':
            i.status='Denied'
        db.session.add(i)
        db.session.commit()
    elif c['data']['object']=='dispute':
        pass
    elif c['data']['object']=='customer':
        pass
    elif c['data']['object']=='card':
        pass
    elif c['data']['object']=='subscription':
        pass
    elif c['data']['object']=='invoice':
        pass
    elif c['data']['object']=='plan':
        pass
    elif c['data']['object']=='transfer':
        pass
    elif c['data']['object']=='discount':
        pass
    elif c['data']['object']=='coupon':
        pass
    elif c['data']['object']=='balance':
        pass
    elif c['data']['object']=='account':
        pass
    else:
        pass
    return ''

@rp.route('/hook/twilio')
def twilio_hook():
    '''twilio hook'''
    #TODO
    return ''
#### /PAYMENTS ####

#### SESSION TESTING ####
@rp.route('/session/dump')
@login_required
def dump():
    return str(session['add'])

@rp.route('/session/add')
@login_required
def add():
    session['add']=gen_salt(1000)
    return redirect(url_for('.dump'))

@rp.route('/session/remove')
@login_required
def remove():
    session['add']=None
    return redirect(url_for('.dump'))
#### /SESSION TESTING ####
