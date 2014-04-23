from rentport import app, db, mail
from requests_oauthlib import OAuth2Session
from rentport.model import Issue, Property, User, LandlordTenant, Comment, Fee, Payment, StripeUserInfo
from flask import render_template, request, g, redirect, url_for, abort, flash, session, json
from flask.ext.security import login_required
from flask.ext.mail import Message
from flask.ext.wtf import Form
from wtforms import SelectField, TextField, SubmitField, TextAreaField, HiddenField, FileField, RadioField
from wtforms.validators import Length, DataRequired, AnyOf
from sqlalchemy import or_
from werkzeug.security import gen_salt
from sys import exc_info as er
from datetime import datetime as dt
import stripe

#### UTILS ####
def get_url(endpoint, **kw):
    '''Return endpoint url, or next arg url'''
    try:
        return request.args['next']
    except:
        return url_for(endpoint, **kw)
#### /UTILS ####

#### FORMS ####
class FileUploadForm(Form):
    upload=FileField('File', [DataRequired()])
    title=TextField('Title')
    description=TextAreaField('Description')
    submit=SubmitField('Upload')

class OpenIssueForm(Form):
    severity=SelectField('Severity', choices=[('Critical', 'Critical'),
                                                ('Medium', 'Medium'),
                                                ('Low', 'Low'),
                                                ('Future', 'Future')])
    description=TextAreaField('Description', [DataRequired()])
    submit=SubmitField('Open')

class PostCommentForm(Form):
    text=TextAreaField('Comment', [DataRequired()])
    submit=SubmitField('Respond')

class CloseIssueForm(Form):
    reason=TextAreaField('Reason', [DataRequired()])
    submit=SubmitField('Close')

class AddLandlordForm(Form):
    location=SelectField('Location', coerce=int)
    submit=SubmitField('Add')

class EndLandlordForm(Form):
    end=HiddenField(default='True', validators=[AnyOf('True')])
    submit=SubmitField('End')

class ConfirmTenantForm(Form):
    confirm=RadioField('Confirm?', choices=[('True', 'Confirm'),
                                        ('False', 'Disallow')])
    submit=SubmitField('Submit')

class CommentForm(Form):
    comment=TextAreaField('Comment', [DataRequired()])
    submit=SubmitField('Add Comment')

class AddPropertyForm(Form):
    location=TextField('Location:', [DataRequired()])
    description=TextAreaField('Description:', [DataRequired()])
    submit=SubmitField('Add Property')

class ModifyPropertyForm(AddPropertyForm):
    submit=SubmitField('Modify Property')

class AddPhoneNumber(Form):
    phone=TextField('Phone #:', [DataRequired()])
    submit=SubmitField('Validate number')
#### /FORMS ####

#### DEFAULT ####
@app.route('/')
@login_required
def home():
    return render_template('home.html')
#### /DEFAULT ####

#### ISSUES ####
@app.route('/issues', methods=['GET'])
@app.route('/issues/<int(min=1):page>', methods=['GET'])
@app.route('/issues/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def issues(page=1, per_page=app.config['ISSUES_PER_PAGE']):
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

@app.route('/issues/<int(min=1):ident>/show', methods=['GET'])
@login_required
def show_issue(ident):
    '''show issue
        params:     GET: <ident> absolute id
        returns:    GET: detailed issue page
    '''
    issue=g.user.all_issues().filter(Issue.status=='Open',
            Issue.id==ident).first()
    if not issue:
        flash('No issue with that id')
        return redirect(url_for('issues'))
    return render_template('show_issue.html', issue=issue)

# PAID ENDPOINT
# ALERT USER(S)
@app.route('/issues/open', methods=['POST', 'GET'])
@login_required
def open_issue():
    '''open new issue at current location
        params:     POST:   <severity> issue severity
                    POST:   <description> issue description
        returns:    POST:   Redirect for main issues
                    GET:    Open issue form
    '''
    if not g.user.current_landlord():
        flash('No current landlord')
        return redirect(url_for('issues'))
    if not g.user.current_landlord().fee_paid():
        flash('Landlord needs to pay fee')
        return redirect(url_for('issues'))
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
        return redirect(url_for('issues'))
    return render_template('open_issue.html', form=form)

@app.route('/issues/<int(min=1):ident>/comment', methods=['GET', 'POST'])
@login_required
def comment(ident):
    '''comment on issue
        params:     POST: <comment> comment text
                    GET/POST: <ident> absolute id
        returns:    POST: Redirect to main issues page
                    GET: Comment form
    '''
    form = CommentForm()
    issue=g.user.all_issues().filter(Issue.status=='Open',
            Issue.id==ident).first()
    if not issue:
        flash('No issue with that id')
        return redirect(url_for('issues'))
    if form.validate_on_submit():
        d=request.form['comment']
        comment=Comment(text=d, user_id=g.user.id)
        issue.comments.append(comment)
        db.session.add(comment)
        db.session.commit()
        flash('Commented on issue')
        return redirect(url_for('issues'))
    return render_template('comment.html', form=form, issue=issue)

@app.route('/issues/<int(min=1):ident>/close', methods=['POST', 'GET'])
@login_required
def close_issue(ident):
    '''close issue - only opener or landlord can
        params:     POST: <reason> reason (to close issue)
                    GET/POST: <ident> absolute id
        returns:    GET: Form to close issue
                    POST: Redirect to main issues page
    '''
    form=CloseIssueForm()
    issue=Issue.query.filter(or_(Issue.landlord_id==g.user.id,
                Issue.creator_id==g.user.id),
                Issue.status == 'Open',
                Issue.id == ident).first()
    if not issue:
        flash('No issue with that id')
        return redirect(url_for('issues'))
    if form.validate_on_submit():
        reason=request.form['reason']
        issue.status='Closed'
        issue.closed_because=reason
        db.session.add(issue)
        db.session.commit()
        flash('Issue closed')
        return redirect(url_for('issues'))
    return render_template('close_issue.html', form=form, issue=issue)
#### /ISSUES ####

#### PROFILE ####
@app.route('/profile', methods=['GET'])
@login_required
def profile():
    tenants = [ x.username for x in g.user.current_tenants().all() ]
    return render_template('profile.html', tenants=tenants)

@app.route('/profile/phone', methods=['GET', 'POST'])
@login_required
def phone():
    #TODO
    pass
#### /PROFILE ####

#### LANDLORD ####
# ALERT USER(S)
@app.route('/landlord/<landlord>/add', methods=['GET', 'POST'])
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
        return redirect(url_for('end_relation', next=url_for('add_landlord', landlord=landlord)))
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
        return redirect(url_for('home'))
    return render_template('add_landlord.html', form=form, landlord=landlord)

# ALERT USER(S)
@app.route('/landlord/end', methods=['POST', 'GET'])
@login_required
def end_relation():
    '''end landlord relation
        params:     POST: <end> = True
        returns:    POST: Redirect
                    GET: End relation form
    '''
    if not g.user.current_landlord():
        flash('No current landlord')
        return redirect(url_for('home'))
    form=EndLandlordForm()
    lt=LandlordTenant.query.\
            filter(LandlordTenant.tenant_id==g.user.id,
                    LandlordTenant.current==True).\
            first()
    if not lt:
        flash('No relationship to end')
        return redirect(url_for('home'))
    if form.validate_on_submit():
        lt.current=False
        db.session.add(lt)
        db.session.commit()
        flash('Ended landlord relationship')
        return redirect(get_url('home'))
    return render_template('end_relation.html', form=form, landlord=lt.landlord)
#### /LANDLORD ####

##### PROPERTIES #####
@app.route('/landlord/property', methods=['GET'])
@login_required
def properties():
    '''show properties
        params:     NONE
        returns:    GET: List of properties
    '''
    return render_template('properties.html', user=g.user)

# PAID ENDPOINT
@app.route('/landlord/property/add', methods=['GET', 'POST'])
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
        return redirect(url_for('properties'))
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
        return redirect(url_for('properties'))
    return render_template('add_property.html', form=form)

@app.route('/landlord/property/<int(min=1):prop_id>/modify', methods=['GET', 'POST'])
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
        return redirect(url_for('properties'))
    form=ModifyPropertyForm()
    if form.validate_on_submit():
        location=request.form['location']
        description=request.form['description']
        prop.location=location
        prop.description=description
        db.session.add(prop)
        db.session.commit()
        flash("Property modified")
        return redirect(url_for('properties'))
    form.location.data=prop.location
    form.description.data=prop.description
    return render_template('modify_location.html', form=form, location=prop)

@app.route('/landlord/property/<int(min=1):prop_id>/show', methods=['GET'])
@login_required
def show_property(prop_id):
    '''show detailed info on property
        params:     GET: <prop_id> absolute property id
        returns:    GET: Detaild property info
    '''
    prop=g.user.properties.filter(Property.id==prop_id).first()
    if not prop:
        flash('Not a valid property id')
        return redirect(url_for('properties'))
    return render_template('show_property.html', location=prop)
#### /PROPERTIES ####

#### TENANTS ####
# ALERT USER(S)
@app.route('/tenant/confirm', methods=['GET'])
@app.route('/tenant/<tenant>/confirm', methods=['POST', 'GET'])
@login_required
def confirm_relation(tenant=None):
    '''confirm tenant request'''
    if tenant == None:
        tenants=User.query.join(User.landlords).\
                filter(LandlordTenant.landlord_id==g.user.id,
                        LandlordTenant.current==True,
                        LandlordTenant.confirmed==False)
        return render_template('unconfirmed_tenants.html', tenants=tenants)
    else:
        t=User.query.join(User.landlords).\
                filter(LandlordTenant.landlord_id==g.user.id,
                        LandlordTenant.current==True,
                        LandlordTenant.confirmed==False,
                        User.username==tenant).first()
        if not t:
            flash('No unconfirmed tenant request')
            return redirect(url_for('confirm_relation'))
    form=ConfirmTenantForm()
    if form.validate_on_submit():
        lt=LandlordTenant.query.\
                join(User.landlords).filter(LandlordTenant.landlord_id==g.user.id,
                        LandlordTenant.current==True,
                        LandlordTenant.confirmed==False,
                        User.username==tenant).\
                first_or_404()
        if request.form['confirm']=='True':
            lt.confirmed=True
            db.session.add(lt)
            db.session.commit()
            flash('Confirmed tenant')
        else:
            db.session.delete(lt)
            db.session.commit()
            flash('Disallowed tenant')
        return redirect(url_for('home'))
    return render_template('confirm_relation.html', form=form, tenant=t)
#### /TENANTS ####

#### OAUTH ####
@app.route('/oauth/authorize', methods=['GET'])
@login_required
def authorize():
    '''Authorize Stripe, or refresh'''
    if g.user.stripe:
        flash('Have stripe info already')
        return redirect(url_for('home'))
    oauth=OAuth2Session(app.config['STRIPE_CONSUMER_KEY'],
        redirect_uri=url_for('authorized', _external=True),
        scope=app.config['STRIPE_OAUTH_CONFIG']['scope'])
    auth_url, state=oauth.authorization_url(
            app.config['STRIPE_OAUTH_CONFIG']['authorize_url'])
    session['state']=state
    return redirect(auth_url)

@app.route('/oauth/authorized', methods=['GET'])
@login_required
def authorized():
    if g.user.stripe:
        flash('Have stripe info already')
        return redirect(url_for('home'))
    oauth=OAuth2Session(app.config['STRIPE_CONSUMER_KEY'],
                    state=session['state'])
    token=oauth.fetch_token(
                    app.config['STRIPE_OAUTH_CONFIG']['access_token_url'],
                    app.config['STRIPE_CONSUMER_SECRET'],
                    authorization_response=request.url)
    s = StripeUserInfo(access_token=token['access_token'],
                       refresh_token=token['refresh_token'],
                       user_acct=token['stripe_user_id'],
                       pub_key=token['stripe_publishable_key'])
    g.user.stripe=s
    db.session.add(s)
    db.session.commit()
    flash('Authorized!')
    return redirect(url_for('home'))
#### /OAUTH ####

#### PAYMENTS ####
#RISK
#PAID ENDPOINT
# ALERT USER(S)
@app.route('/pay/landlord', methods=['GET'])
@app.route('/pay/landlord/<int(min=10):amount>', methods=['POST', 'GET'])
@login_required
def pay_rent(amount=None):
    landlord=g.user.current_landlord()
    if not landlord:
        flash('No current landlord')
        return redirect(url_for('home'))
    if not landlord.fee_paid():
        flash('Landlord has not paid service fee')
        return redirect(url_for('payments'))
    if not landlord.stripe:
        flash('Landlord cannot accept CC')
        return redirect(url_for('payments'))
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
                return redirect(url_for('payments'))
            except stripe.error.CardError:
                flash('Card error')
                return redirect(url_for('pay_rent'))
            except stripe.error.AuthenticationError:
                flash('Authentication error')
                return redirect(url_for('pay_rent'))
            except Exception:
                flash(str(er()))
                return redirect(url_for('pay_rent'))
        else:
            return render_template('pay_landlord.html', landlord=landlord,
                                                        amount=amount)
    else:
        return render_template('get_pay_amount.html', landlord=landlord, user=g.user)

#RISK
@app.route('/pay/fee', methods=['POST', 'GET'])
@login_required
def pay_fee():
    if request.method == 'POST':
        token = request.form['stripeToken']
        try:
            charge = stripe.Charge.create(
                  api_key=app.config['STRIPE_CONSUMER_SECRET'],
                  amount=app.config['FEE_AMOUNT'],
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
            return redirect(url_for('fees'))
        except stripe.error.CardError:
            flash('Card error')
            return redirect(url_for('pay_fee'))
        except stripe.error.AuthenticationError:
            flash('Authentication error')
            return redirect(url_for('pay_fee'))
        except Exception:
            flash(str(er()))
            return redirect(url_for('pay_fee'))

    else:
        return render_template('pay_service_fee.html',
                                amount=app.config['FEE_AMOUNT'],
                                key=app.config['STRIPE_CONSUMER_KEY'])

@app.route('/payments', methods=['GET'])
@app.route('/payments/<int(min=1):page>', methods=['GET'])
@app.route('/payments/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def payments(page=1, per_page=app.config['PAYMENTS_PER_PAGE']):
    '''main payments page'''
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

@app.route('/payments/<int:pay_id>/show', methods=['GET'])
@login_required
def show_payment(pay_id):
    '''show detailed payment info'''
    payment=g.user.payments().filter(Payment.id==pay_id).first()
    if not payment:
        flash('No payment with that id')
        return redirect(url_for('payments'))
    p = stripe.Charge.retrieve(payment.pay_id,
                    api_key=payment.from_user.stripe.access_token).to_dict()
    return render_template('show_payment.html', payment=p)

@app.route('/fees', methods=['GET'])
@app.route('/fees/<int(min=1):page>', methods=['GET'])
@app.route('/fees/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def fees(page=1, per_page=app.config['PAYMENTS_PER_PAGE']):
    '''main fees page'''
    fees=g.user.fees.paginate(page, per_page, False)
    return render_template('fees.html', fees=fees)

@app.route('/fees/<int:pay_id>/show', methods=['GET'])
@login_required
def show_fee(pay_id):
    '''show detailed fee info'''
    fee=g.user.fees.filter(Fee.id==pay_id).first()
    if not fee:
        flash('No fee with that id')
        return redirect(url_for('fees'))
    f = stripe.Charge.retrieve(fee.pay_id,
                    api_key=app.config['STRIPE_CONSUMER_SECRET'])\
                    .to_dict()
    return render_template('show_fee.html', fee=f)

@app.route('/hook/stripe', methods=['POST'])
def stripe_hook():
    #TODO Add more hooks
    event=json.loads(request.data)
    c = stripe.Event.retrieve(event['id'],
            api_key=app.config['STRIPE_CONSUMER_SECRET'])
    try:
        acct=c['user_id']
    except:
        acct=None
    if c['type']=='account.application.deauthorized':
        t=StripeUserInfo.query.filter(StripeUserInfo.user_acct==acct).first()
        if not t: return
        db.session.delete(t)
        db.session.commit()
    elif c['data']['object']=='charge':
        i=Payment.query.filter(Payment.pay_id==c['data']['object']['id']).first() \
                or Fee.query.filter(Fee.pay_id==c['data']['object']['id']).first()
        if not i: return
        if c['type']=='charge.succeeded':
            i.status='Confirmed'
        elif c['type']=='charge.refunded':
            i.status='Refunded'
        elif c['type']=='charge.failed':
            i.status='Denied'
        else:
            return
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
    return

@app.route('/hook/twilio')
def twilio_hook():
    #TODO
    pass
#### /PAYMENTS ####

#### SESSION TESTING ####
@app.route('/session/dump')
@login_required
def dump():
    return str(session['add'])

@app.route('/session/add')
@login_required
def add():
    session['add']=gen_salt(1000)
    return redirect(url_for('dump'))

@app.route('/session/remove')
@login_required
def remove():
    session['add']=None
    return redirect(url_for('dump'))
#### /SESSION TESTING ####
