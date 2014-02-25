from rentport import app, db
from flask import render_template, request, g, redirect, url_for, abort, flash
from flask.ext.security import login_required
from flask.ext.wtf import Form
from wtforms import SelectField, TextField, SubmitField, TextAreaField
from wtforms.validators import Length, DataRequired

class OpenIssueForm(Form):
    severity=SelectField('Severity', choices=[('Critical', 'Need fix now!'),
                                                ('Medium', 'Important'),
                                                ('Low', 'Can wait'),
                                                ('Future', 'Would be cool to have')])
    description=TextAreaField('Description', [DataRequired()])
    submit=SubmitField('Open')


@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/issues', methods=['GET'])
@app.route('/issues/<int:start>/<int:stop>/<int:page>', methods=['GET'])
@login_required
def issues(start=0, stop=10, page=1):
    '''display main issues page'''
    issues=g.user.issues_opened
    return render_template('issues.html', issues=issues, page=page)

@app.route('/issues/open', methods=['POST', 'GET'])
@login_required
def open_issue():
    '''open new issue

    post params:    severity = issue severity
                    description = issue description

    get returns:    form to upload issue
    '''
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

@app.route('/issues/close/<int:id>', methods=['POST', 'GET'])
@login_required
def close_issue():
    '''close issue - only opener or landlord can

    post params:     reason = reason to close issue

    returns:    issue, status, closed (time)'''
    if request.method == 'POST':

        ident=request.form['id']
        reason=request.form['reason']
        i.status='Closed'
        i.closed_because=reason
        db.session.add(i)
        db.session.commit()
        flash('Issue closed')
        redirect(url_for('issues'))
    else:
        return render_template('close_issue.html')

@app.route('/agreements')
@login_required
def agreements():
    '''main agreements page'''
    pass
        #a=model.get_documents(session.id)
            #return render.agreements(a)
        #except:
            #raise web.badrequest()

#@app.route('/agreements/delete', methods=['POST'])
#def delete_agreements():
    #'''delete agreement'''
    #if session.login:
        #try:
            #return dumps(dict(model.delete_document(session.id, x.id)))
        #except:
            #raise web.badrequest()
    #else:
        #raise web.unauthorized()

#@app.route('/agreement/post', methods=['POST', 'GET'])
#def post_agreement():
    #if request.method == 'POST':
        #def POST(self):
            ##save agreement, return info
            #if session.login == True:
                #x = web.input(agreement={})
                #try:
                    #return dumps(model.save_document(
                                        #user=session.id,
                                        #title=x.title,
                                        #description=x.description,
                                        #data_type=model.get_file_type(x.agreement.file),
                                        #filename=x.agreement.filename,
                                        #data=x.agreement.value
                                        #))
                #except:
                    #raise web.badrequest()
            #else:
                #raise web.unauthorized()
    #else:
        #if session.login == True:
            #try:
                #f=upload_form()
                #return render.post_agreement(f)
            #except:
                #return "Error"
        #else:
            #raise web.unauthorized()

#@app.route('/agreements/show/<int:doc_id>')
#def show_agreements(doc_id):
    #'''show agreements'''
    #if session.login == True:
        #try:
            #return model.get_document(session.id, x.id)
        #except AttributeError:
            #info=model.get_documents(session.id)
            #return render.list_agreements(info)
        #except:
            #raise web.badrequest
    #else:
        #raise web.unauthorized()

#@app.route('/profile', methods=['POST', 'GET'])
#def profile():
    #if request.method == 'POST':
        ##TODO Show what errors there were
        #if session.login == True:
            #x=web.input()
            #try:
                #return dumps(dict(model.update_user(session.id, **x)))
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()

    #else:
        #if session.login == True:
            #try:
                #f = new_password_form()
                #user_info=model.get_user_info(session.id,where='id')
                #user_info.update(model.get_relations(session.id))
                #return render.profile(user_info, f)
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()

#@app.route('/payments')
#def payments():
    #'''main payments page'''
    #if session.login == True:
        #return render.payments_home()
    #else:
        #raise web.unauthorized()

#@app.route('/payments/show/<int:pay_id>')
#def show_payments(pay_id):
    #'''show payments'''
    #x=web.input()
    #if session.login == True:
        #try:
            #return model.get_payment(session.id, x.id)
        #except AttributeError:
            #payments_info = model.get_payments(session.id)
            #return render.payment_info(payments_info)
        #except:
            #raise web.badrequest
    #else:
        #raise web.unauthorized()

#@app.route('/pay/<user>', methods=['POST', 'GET'])
#def pay_user(user):
    #'''display pay username page and pay user'''
    #if request.method == 'POST':
        ##RISK Worried about js injection/poisoning
        #x=web.input()
        #if session.login == True:
            #x=web.input()
            #try:
                #info=model.get_user_info(x.user,where='username',id=True)
                #sk_key=model.get_user_sk(info['id'])
                #if sk_key:
                    #charge_id = model.authorize_payment(x.stripeToken,
                                                    #x.amount,
                                                    #sk_key,
                                                    #session.username,
                                                    #session.id,
                                                    #info['id'])
                    #if charge_id:
                        ##if model.capture_payment(charge, sk_key) == True:
                            ##model.save_payment(session.id,info['id'],charge_id)
                            ##return "Paid"
                        ##else
                            ##return "Payment error"
                        #pass
                    #else:
                        #return "Payment error"
                #else:
                    #return "Payment error"
            #except AttributeError:
                #return "Payment error"
            #except:
                #return "error"
        #else:
            #raise web.unauthorized()
    #else:
        #if session.login == True:
            ##RISK Leaks user info (accepts_cc, name, etc)
            ##RISK XSS? escape user?
            ##Need accepts_cc? Maybe just search for keys
            #try:
                #info=model.get_user_info(x.user,where='username',id=True,accepts_cc=True,username=True)
                #if info['accepts_cc'] == True:
                    #pk_key=model.get_user_pk(info['id'])
                    #if pk_key:
                        #return render.pay_person(pk_key, info['username'])
                    #else:
                        #return "Can't find key"
                #else:
                    ##not accepts cc
                    #raise web.badrequest()
            #except (KeyError,TypeError,AttributeError):
                ##not a user or bad parameters
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()

#@app.route('/landlord/search')
#def search_landlord():
    #'''landlord search'''
    #if session.login == True:
        #if model.get_user_info(session.id,where='id',category=True)['category'] == 'Tenant':
            #return render.search_landlord()
        #else:
            #raise web.seeother('/')
    #else:
        #raise web.unauthorized()

#@app.route('/landlord/request', methods=['POST', 'GET'])
#def request_relation():
    #'''make relation request'''
    ##TODO Give more info on errors
    #if request.method == 'POST':
        #x=web.input()
        #if session.login == True:
            #try:
                #return dumps(dict(model.make_relation_request(session.id,x.user,x.location)))
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()
    #else:
        #if session.login == True:
            #try:
                #f = relation_request_form()
                #return render.landlord_page(f)
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()

#@app.route('/landlord/confirm', methods=['POST', 'GET'])
#def confirm_relation():
    #'''confirm relation request from tenant'''
    #if request.method == 'POST':
        #x=web.input()
        #if session.login == True:
            #try:
                #return dumps(dict(model.confirm_relation_request(x.user, session.id)))
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()
    #else:
        #if session.login == True:
            #try:
                #f = confirm_relation_form()
                #return render.confirm_relation_form(f)
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()

#@app.route('/landlord/end', methods=['POST', 'GET'])
#def end_relation():
    #'''end relation'''
    #if request.method == 'POST':
        #x = web.input()
        #if session.login == True:
            #try:
                #if x.end == 'true':
                    #return dumps(dict(model.end_relation(session.id)))
                #else:
                    #raise web.badrequest()
            #except AttributeError:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()
    #else:
        #if session.login == True:
            #try:
                #f = end_relation_form()
                #return render.end_relation_form(f)
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()

#@app.route('/search_users/<search>')
#def search_users(search):
    #'''grep similar username, given constrants'''
    ##RISK This is available to any user, be very careful of the keys allowed!
    ##RISK do on backend to insure rigor
    #x=web.input()
    #if session.login == True:
        #try:
            #return dumps(list(model.search_users(x.username, **x)))
        #except:
            #raise web.badrequest()
    #else:
        #raise web.unauthorized()

#@app.route('/oauth/stripe/authorize')
#def authorize_stripe():
    #'''authorize stripe: oauth2'''
    ##TODO CSRF protection with state variable
    #c = Client(auth_endpoint=config.stripe.oauth_site + config.stripe.authorize_uri,
        #client_id=config.stripe.client_id)

    #state=None
    #raise web.seeother(c.auth_uri(state=state,
                                #scope='read_write',
                                #response_type='code',
                                #redirect_uri="https://www.rentport.com/oauth/callback"
                                #))

#@app.route('/oauth/stripe/callback')
#def callback_stripe():
    #'''redirect uri from stripe: oauth2'''
    ##TODO CSRF protection with state variable
    #x = web.input()
    #state, code=x.state, x.code
    #c = Client(token_endpoint=config.stripe.oauth_site + config.stripe.token_uri,
        #client_id=config.stripe.client_id,
        #client_secret=config.stripe.test_private_key)

    #c.request_token(
            #code=code,
            #grant_type='authorization_code')

    ##save keys
    #if model.save_user_keys(session.id,
                        #c.access_token,
                        #c.stripe_publishable_key,
                        #c.refresh_token) != True:
        #return "Error"

    ##change to accept cc
    #if model.update_user(session.id, accepts_cc=True) != True:
        #return "Error"

    #return "Authorized and keys received!"


#@app.route('/issues/show', methods=['GET'])
#def show_issues():
    #'''get issues (no comments), except for querying one issue

    #param:      id = relative issue id (optional)
                #status = issue status (optional, default = Open)
                #start = offset to start at (optional, default = 1)
                #num = number of issues to return (optional, default = all)

    #returns:    no id:
                    #creator, owner, description,
                    #num of cms, severity, status,
                    #location
                #w/ id:
                    #all the above and comments'''
    #def GET(self):
        #x=web.input()
        #if web.ctx.session.login == True:
            #try:
                #issue={'general': dict(model.get_issues(web.ctx.session.id, start=x.id, num=1)[0]),
                        #'comments': list(model.get_comments(web.ctx.session.id, x.id))}
                #return dumps(issue)
            #except AttributeError:
                #return dumps(list(model.get_issues(web.ctx.session.id, **x)))
            #except IndexError:
                #return {'error': 'No Issue'}
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()

#@app.route('/issues/comments', methods=['GET'])
#def get_comments():
    #'''get comments

    #param:      id = relative issue id
                #start = offset to start at (optional, default = 1)
                #num = number of comments to return (optional, default = all)
                #status = issue status to query by (optional, default = 'Open')

    #returns:    text, username, posted (time)'''
    #def GET(self):
        #if web.ctx.session.login == True:
            #x = web.input()
            #try:
                #return dumps(list(model.get_comments(web.ctx.session.id, x.pop('id'), **x)))
            #except KeyError:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()

#@app.route('/issues/respond', methods=['POST', 'GET'])
#def post_comment():
    #'''post comment

    #get params:     id = relative issue id
    #post params:    id = relative issue id
                    #comment = the comment text

    #get returns:    form to upload comment
    #post returns:   text, username, issue, posted (time)'''
    #if request.method == 'POST':
        #if web.ctx.session.login == True:
            #x = web.input()
            #try:
                #a=model.comment_on_issue(web.ctx.session.id, x.id, x.comment)
                #a['username']=web.ctx.session.username
                #a['issue']=x.id
                #return dumps(a)
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()
    #else:
        #if web.ctx.session.login == True:
            #x=web.input()
            #try:
                #f = post_comment_form()
                #return render.post_comment(f, x.id)
            #except:
                #raise web.badrequest()
        #else:
            #raise web.unauthorized()


