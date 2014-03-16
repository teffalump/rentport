from rentport import app, db
from requests_oauthlib import OAuth2Session
from rentport.model import Issue, Property, User, LandlordTenant, Comment
from flask import render_template, request, g, redirect, url_for, abort, flash, session, json
from flask.ext.security import login_required
from flask.ext.wtf import Form
from wtforms import SelectField, TextField, SubmitField, TextAreaField, HiddenField, FileField, RadioField
from wtforms.validators import Length, DataRequired, AnyOf
from sqlalchemy import or_
from werkzeug.security import gen_salt

FEE_AMOUNT=1000 #in cents
ISSUES_PER_PAGE=10
PAYMENTS_PER_PAGE=10

class stripe:
        redirect_uri='https://www.rentport.com/oauth/authorized'
        base_url='https://api.stripe.com'
        access_token_url='https://connect.stripe.com/oauth/token'
        authorize_url='https://connect.stripe.com/oauth/authorize'
        scope=['read_write']
        access_token_method='POST',

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
def issues(page=1, per_page=ISSUES_PER_PAGE):
    '''display main issues page'''
    #TODO Do the pagination stuff
    #TODO What issues to retrieve?
    issues=g.user.all_issues().paginate(page, per_page, False)
    return render_template('issues.html', issues=issues)

@app.route('/issues/<int(min=1):ident>/show', methods=['GET'])
@login_required
def show_issue(ident):
    '''show issue
        params:     GET: <ident> absolute id
        returns:    detailed issue page
    '''
    issue=g.user.all_issues().filter(Issue.status=='Open',
            Issue.id==ident).first_or_404()
    return render_template('show_issue.html', issue=issue)

# PAID ENDPOINT
@app.route('/issues/open', methods=['POST', 'GET'])
@login_required
def open_issue():
    '''open new issue
        params:     POST: <severity> issue severity
                        <description> issue description
        returns:    POST: Redirect for main issues
                    GET: Open issue form
    '''
    #TODO Email/text when opened
    if g.user.current_location() == None: abort(403)
    if not g.user.current_landlord().fee_paid: abort(403)
    form=OpenIssueForm()
    if form.validate_on_submit():
        i=g.user.open_issue()
        i.description=request.form['description']
        i.severity=request.form['severity']
        db.session.add(i)
        db.session.commit()
        flash('Issue opened')
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
    #TODO Email when there is a comment?
    form = CommentForm()
    issue=g.user.all_issues().filter(Issue.status=='Open',
            Issue.id==ident).first_or_404()
    if form.validate_on_submit():
        d=request.form['comment']
        comment=Comment(text=d, user_id=g.user.id)
        issue.comments.append(comment)
        db.session.add(comment)
        db.session.commit()
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
                Issue.id == ident).first_or_404()
    if form.validate_on_submit():
        reason=request.form['reason']
        issue.status='Closed'
        issue.closed_because=reason
        db.session.add(i)
        db.session.commit()
        flash('Issue closed')
        return redirect(url_for('issues'))
    return render_template('close_issue.html', form=form, issue=issue)
#### /ISSUES ####

#### PROFILE ####
@app.route('/profile', methods=['GET'])
@login_required
def profile():
    return render_template('profile.html', user=g.user)
#### /PROFILE ####

#### LANDLORD ####
@app.route('/landlord/<landlord>/add', methods=['GET', 'POST'])
@login_required
def add_landlord(landlord):
    #TODO Email when added?
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

@app.route('/landlord/end', methods=['POST', 'GET'])
@login_required
def end_relation():
    '''end relation'''
    form=EndLandlordForm()
    lt=LandlordTenant.query.\
            filter(LandlordTenant.tenant_id==g.user.id,
                    LandlordTenant.current==True).\
            first_or_404()
    if form.validate_on_submit():
        lt.current=False
        db.session.add(lt)
        db.session.commit()
        flash('Ended landlord relationship')
        return redirect(url_for('home'))
    return render_template('end_relation.html', form=form)
#### /LANDLORD ####

##### PROPERTIES #####
@app.route('/landlord/property', methods=['GET'])
@login_required
def properties():
    return render_template('properties.html', user=g.user)

# PAID ENDPOINT
@app.route('/landlord/property/add', methods=['GET', 'POST'])
@login_required
def add_property():
    if not g.user.fee_paid: abort(403)
    form=AddPropertyForm()
    if form.validate_on_submit():
        location=request.form['location']
        description=request.form['description']
        p=Property(location=location, description=description)
        g.user.properties.append(p)
        db.session.add(p)
        db.session.commit()
        flash("Property added")
        return redirect(url_for('/landlord/property'))
    return render_template('add_property.html', form=form)

@app.route('/landlord/property/<int(min=1):prop_id>/modify', methods=['GET', 'POST'])
@login_required
def modify_property(prop_id):
    prop=g.user.properties.filter(Property.id==prop_id).first_or_404()
    form=ModifyPropertyForm()
    if form.validate_on_submit():
        location=request.form['location']
        description=request.form['description']
        prop.location=location
        prop.description=description
        db.session.add(prop)
        db.session.commit()
        flash("Property modified")
        return redirect(url_for('/landlord/property'))
    form.location.data=prop.location
    form.description.data=prop.description
    return render_template('modify_location.html', form=form, location=prop)

@app.route('/landlord/property/<int(min=1):prop_id>/show', methods=['GET'])
@login_required
def show_property(prop_id):
    prop=g.user.properties.filter(Property.id==prop_id).first_or_404()
    return render_template('show_property.html', location=prop)
#### /PROPERTIES ####

#### TENANTS ####
@app.route('/tenant/confirm', methods=['GET'])
@app.route('/tenant/<tenant>/confirm', methods=['POST', 'GET'])
@login_required
def confirm_relation(tenant=None):
    if tenant == None:
        tenants=User.query.join(User.landlords).\
                filter(LandlordTenant.landlord_id==g.user.id,
                        LandlordTenant.current==True,
                        LandlordTenant.confirmed==False)
        return render_template('unconfirmed_tenants.html', tenants=tenants)
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
    return render_template('confirm_relation.html', form=form)

#### /TENANTS ####

#### PAYMENTS ####
@app.route('/oauth/authorize', methods=['GET'])
@login_required
def authorize():
    oauth=OAuth2Session(app.config['STRIPE_CONSUMER_KEY'], 
            redirect_uri=stripe.redirect_uri, scope=stripe.scope)
    auth_url, state=oauth.authorization_url(stripe.authorize_url)
    session['state']=state
    return str(auth_url)
    #return redirect(auth_url)

@app.route('/oauth/authorized', methods=['GET'])
@login_required
def authorized():
    #TODO Save token
    oauth=OAuth2Session(app.config['STRIPE_CONSUMER_KEY'],
                    state=session['state'])
    token=oauth.fetch_token(stripe.access_token_url,
                    app.config['STRIPE_CONSUMER_SECRET'],
                    authorization_response=request.url)
    return 'blar'

#RISK
#PAID ENDPOINT
@app.route('/pay/landlord', methods=['GET'])
@app.route('/pay/landlord/<int(min=100):amount>', methods=['POST', 'GET'])
@login_required
def pay_rent(amount=None):
    #TODO Add dynamic payment amount
    landlord=g.user.current_landlord() or abort(403)
    if not landlord.fee_paid: abort(403)
    if amount != None:
        cents=amount*100
        if request.method == 'POST':
            token = request.form['stripeToken']
            try:
                charge = stripe.Charge.create(
                      amount=cents,
                      currency="usd",
                      card=token,
                      description=':'.join([g.user.id, g.user.username])
                      )
            except stripe.CardError:
                flash('Card error')
                abort(400)
            except Exception:
                flash('Error occurred')
                abort(400)
            else:
                flash('Payment processed')
                redirect(url_for('/payments'))
        else:
            return render_template('pay_landlord.html', landlord=landlord, amount=cents)
    else:
        return 'Need amount'

#RISK
@app.route('/pay/fee', methods=['POST', 'GET'])
@login_required
def pay_fee():
    #TODO Store charge
    if request.method == 'POST':
        token = request.form['stripeToken']
        try:
            charge = stripe.Charge.create(
                  amount=FEE_AMOUNT,
                  currency="usd",
                  card=token,
                  description=':'.join([g.user.id, g.user.username])
                  )
        except stripe.CardError:
            flash('Card error')
            abort(400)
        except Exception:
            flash('Error occurred')
            abort(400)
        else:
            flash('Payment processed')
            redirect(url_for('/payments'))

    else:
        return render_template('pay_service_fee.html',
                                amount=FEE_AMOUNT,
                                key=app.config['STRIPE_CONSUMER_KEY'])

@app.route('/payments', methods=['GET'])
@app.route('/payments/<int(min=1):page>', methods=['GET'])
@app.route('/payments/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def payments(page=1, per_page=PAYMENTS_PER_PAGE):
    '''main payments page'''
    payments=g.user.payments().paginate(page, per_page, False)
    return render_template('payments.html', payments=payments, user=g.user)

@app.route('/payments/<int:pay_id>/show', methods=['GET'])
def show_payments(pay_id):
    '''show payments'''
    payment=self.payments().filter(Payment.id==pay_id).first_or_404()
    return render_template('show_payment.html', payment=payment)

@app.route('/hook/valid_charge', methods=['POST'])
def charge_hook():
    #TODO
    charge=json.loads(request.data)
    return 'got it'
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
