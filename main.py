#!/usr/bin/env python2

import web
import model
import config
import sys
from uuid import uuid4
from web import form

urls = (
            '/agreement/(.+)', 'agreement_query',
            '/agreement/?', 'agreement',
            '/login/?', 'login',
            '/logout/?', 'logout',
            '/register/?', 'register',
            '/verify/?', 'verify',
            '/reset/?', 'reset',
            '/profile/?', 'profile',
            '/pay/(.+)', 'pay_query',
            '/pay/?', 'pay',
            '/search_users/?', 'search_users',
            '/.*', 'default'
        )

app = web.application(urls, globals())

#session settings
web.config.session_parameters['cookie_name']='rentport'
web.config.session_parameters['cookie_path']='/'
web.config.session_parameters['timeout']=900
web.config.session_parameters['ignore_expiry']=False
web.config.session_parameters['ignore_change_ip']=False
web.config.session_parameters['expired_message']='Session expired'
#web.config.session_parameters['secure']=True

#using session store with database
db = web.database(  dbn='postgres', 
                    db=config.db.name, 
                    user=config.db.user, 
                    pw=config.db.pw)
store = web.session.DBStore(db, 'sessions')
session = web.session.Session(app, store, initializer={'login': False, 'id': -1, 'verified': False, 'email': None, 'username': None})


#form validators
vemail = form.regexp(r"^.+@.+$", "must be a valid email address")
vname= form.regexp(r"^[A-Za-z0-9._+-]+$", "must be a valid username (numbers, letters, and . _ - +)")
vpass = form.regexp(r"^.{12,}$", 'must be at least 12 characters')

### UTILITY FUNCTIONS ###

#### prevent csrf
def csrf_token():
    if not session.has_key('csrf_token'):
        session.csrf_token=uuid4().hex
    return session.csrf_token

def csrf_protected(f):
    def decorated(*args,**kwargs):
        inp = web.input()
        if not (inp.has_key('csrf_token') and inp.csrf_token==session.pop('csrf_token',None)):
            raise web.HTTPError("400 Bad Request", 
                                {'content-type': 'text/html'},
                                'Sorry for the inconvenience, but this could be an CSRF attempt, so we blocked it. Fail safely')
        return f(*args,**kwargs)
    return decorated

def set_session_values(userid):
    '''set the default session values'''
    session.login=True
    session.id = userid
    info = model.get_user_info(userid)
    session.email = info['email']
    session.username = info['username']
    session.verified = info['verified']
    return True

##########################

#renderer
render = web.template.render('templates', globals={'context': session, 'csrf_token': csrf_token})

#upload form
upload_form = form.Form(
                    form.File("agreement"),
                    form.Textbox("title"),
                    form.Textbox("description"),
                    form.Button("submit", type="submit", html="Upload"))

#register form
register_form = form.Form(
                    form.Textbox("email", vemail),
                    form.Textbox("username", vname),
                    form.Password("password", vpass),
                    form.Button("submit", type="submit", html="Confirm"))

#login form
login_form = form.Form(
                    form.Textbox("login_id"),
                    form.Password("password", vpass),
                    form.Button("submit", type="submit", html="Confirm"))
#verify form
verify_form = form.Form(
                    form.Textbox("code"),
                    form.Button("submit", type="submit", html="Verify"),
                    form.Hidden("hidden", value="true", id="send_email"),
                    form.Button("send", type="submit", html="Send verification email"))

#reset form
request_reset_form = form.Form(
                    form.Textbox("email", vemail, id="reset_email"),
                    form.Button("submit", type="submit", html="Request reset email"))
#confirm reset form
confirm_reset_form = form.Form(
                    form.Textbox("email", vemail, id="confirm_email"),
                    form.Textbox("code"),
                    form.Button("confirm", type="submit", html="Confirm reset"))

#new password form
new_password_form = form.Form(
                    form.Textbox("password", vpass, autocomplete="off"),
                    form.Button("submit", type="submit", html="Submit"))

class default:
    def GET(self):
        return render.default()

class login:
    def GET(self):
        if session.login == True:
            raise web.seeother('/')
        else:
            f = login_form()
            return render.login(f)

    @csrf_protected
    def POST(self):
        '''REMEMBER: User can use email or username'''
        #f = login_form()
        #if not f.validates():
            #raise web.seeother('/login')

        ip = web.ctx.ip
        x = web.input()
        if not model.allow_login(x.login_id, ip):
            return 'throttled'
            #raise web.seeother('/login')

        userid = model.verify_password(x.password, x.login_id)
        if userid:
            model.clear_failed_logins(x.login_id, ip)
            set_session_values(userid)
            raise web.seeother('/')
        else:
            model.add_failed_login(x.login_id, ip)
            raise web.seeother('/login')

class logout:
    def GET(self):
        if session.login == True:
            session.kill()
        raise web.seeother('/')

class register:
    '''register an user'''
    def GET(self):
        if session.login == True:
            raise web.seeother('/')
        else:
            f = register_form()
            return render.register(f)

    @csrf_protected
    def POST(self):
        f = register_form()
        if not f.validates():
            raise web.seeother('/register')

        x = web.input()
        try:
            #TODO Some tuning here
            #TODO Return different errors on problems (taken username, etc)
            if model.save_user(email=x.email, username=x.username, password=x.password) == True:
                #if model.send_verification_email(x.email) == True:
                    #model.save_sent_email(web.ctx.ip, x.email,'verify')
                    #raise web.seeother('/login')
                #else:
                    #return "Error"
                raise web.seeother('/login')
            else:
                return "Error"
        except: 
            return "Error"

class reset:
    '''reset user password'''
    def GET(self):
        x=web.input()
        if not session.login:
            try:
                t=confirm_reset_form()
                f=request_reset_form()
                return render.reset(f, t)
            except:
                return "Unknown error"
        else:
            raise web.badrequest()

    @csrf_protected
    def POST(self):
        '''Send reset email'''
        if not session.login:
            f = request_reset_form()
            t = confirm_reset_form()
            if not f.validates() or not t.validates():
                raise web.seeother('/reset')

            x=web.input()
            try:
                if model.verify_reset(x.email, x.code) == True:
                    set_session_values(model.get_id(x.email))
                    f = new_password_form()
                    return render.password_reset(f)
                else:
                    raise web.unauthorized()
            except AttributeError:
                if model.allow_email(x.email, 'reset', web.ctx.ip):
                    if model.send_reset_email(x.email) == True:
                        model.save_sent_email(web.ctx.ip,x.email,'reset')
                        return "Email sent"
                    else:
                        raise web.unauthorized()
                else:
                    return "Email throttled, wait 1 min"
            else:
                return "Unknown error"
        else:
            raise web.seeother('/')

class verify:
    '''verify email address with email/code combo; need to be logged in; send email
    TODO email shit and prevent email dos'''
    def GET(self):
        if not session.login:
            raise web.seeother('/')
        elif session.verified:
            raise web.seeother('/')
        else:
            f = verify_form()
            return render.verify(f)

    @csrf_protected
    def POST(self):
        x = web.input()
        if session.login and not session.verified:
            f = verify_form()
            if not f.validates():
                raise web.seeother('/verify')

            try:
                if model.verify_email(session.id, code=x.code):
                    raise web.seeother('/')
                else:
                    raise web.seeother('/verify')
            except AttributeError:
                if x.send_email == "true":
                    email=model.get_email(session.id)
                    if model.allow_email(email,'verify', web.ctx.ip) == True:
                        if model.send_verification_email(email) == True:
                            model.save_sent_email(web.ctx.ip,email,'reset')
                            return "Email sent"
                        else:
                            return "Email error"
                    else:
                        return "Email throttled, wait 1 min"
                else:
                    raise web.badrequest()
            else:
                raise web.badrequest()
        else:
            raise web.unauthorized()

class agreement_query:
    def GET(self, id):
        if session.login:
            try:
                model.get_document(session.id, id)
            except ValueError:
                return web.badrequest()
        else:
            return web.unauthorized()

    def DELETE(self, id):
            if session.login:
                try:
                    num=model.delete_document(session.id, id)
                    if num == 0:
                        return web.notfound()
                    else:
                        return '<verb>Delete</verb><object>{0}</object>'.format(id)
                except ValueError:
                    return web.badrequest()
            else:
                return web.unauthorized()

class agreement:
    def GET(self):
        if session.login:
            info=model.get_documents(session.id)
            f = upload_form()
            return render.agreement(f, info)
        else:
            return web.unauthorized()

    @csrf_protected
    def POST(self):
        x = web.input(agreement={})
        try:
            model.save_document(
                                user=session.id,
                                title=x.title,
                                description=x.description,
                                data_type=model.get_file_type(x.agreement.file),
                                filename=x.agreement.filename,
                                data=x.agreement.value
                                )
            return web.seeother('/agreement')
        except: 
            return sys.exc_info()

class profile:
    '''View and change info on profile'''
    #TODO change this a little, to support robust modifications
    def GET(self):
        if session.login:
            f = new_password_form()
            info = model.get_user_info(session.id)
            return render.profile(info, f)
        else:
            raise web.unauthorized()

    @csrf_protected
    def POST(self):
        if session.login:
            f = new_password_form()
            if not f.validates():
                raise web.seeother('/profile')

            x=web.input()
            try:
                if model.update_user(id=session.id, password=x.password) == True:
                    raise web.seeother('/')
                else:
                    raise web.badrequest()
            except AttributeError:
                raise web.badrequest()
            else:
                return sys.exc_info()
        else:
            raise web.unauthorized()

class pay:
    '''payment integration'''
    def GET(self):
        '''payment page, list payments'''
        if session.login == True:
            #TODO In future, make it possible to pay different users
            payments_info = model.get_payments(session.id)
            user_key=config.stripe.test_public_key
            return render.pay(payments_info)
        else:
            raise web.unauthorized()

    @csrf_protected
    def POST(self):
        '''payment info'''
        #TODO Worried about js injection/poisoning
        #TODO Another user, etc
        if session.login == True:
            x=web.input()
            try:
                amount=x.amount
                token=x.stripeToken
                charge = model.authorize_payment(token,amount,session.email,api_key)
                if charge:
                    pass
                    #if model.capture_payment(charge, api_key) == True:
                        #model.save_payment(session.id,to,charge)
                    #else
                        #return "Payment error"
                else:
                    return "Payment error"
            except AttributeError:
                return "Payment error"
        else:
            raise web.unauthorized()

class pay_query:
    '''return payment info from id, or display pay username page'''
    def GET(self, id):
        if session.login == True:
            if id.isdigit() == True:
                try:
                    charge=model.get_payment(session.id, id)
                    return charge
                except ValueError:
                    return web.badrequest()
            else:
                try:
                    #display pay to user page
                    pass
                except:
                    return "Error"
        else:
            raise web.unauthorized()

class search_users:
    '''grep similar usernames'''
    def GET(self):
        if session.login == True:
            x=web.input()
            return '<br />'.join([row['username'] for row in model.search_users(x.txt)])
        else:
            raise web.unauthorized()

if __name__ == "__main__":
    app.run()
