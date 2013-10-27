#!/usr/bin/env python2

import web
import model
import config
import sys
from uuid import uuid4
from web import form

urls = (
            '/agreement/post/?', 'post_agreement',
            '/agreement/list/?', 'list_agreements',
            '/agreement/(.+)', 'agreements',
            '/verify/confirm/?', 'confirm_verify',
            '/verify/request/?', 'request_verify',
            '/reset/confirm/?', 'confirm_reset',
            '/reset/request/?', 'request_reset',
            '/landlord/search/?', 'search_landlord',
            '/landlord/(.+)', 'landlord_query',
            '/pay/(.+)', 'pay_user',
            '/payment/list/?', 'list_payments',
            '/payment/(.+)', 'payment_info',
            '/login/?', 'login',
            '/logout/?', 'logout',
            '/register/?', 'register',
            '/profile/?', 'profile',
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
                    pw=config.db.pw
                )
store = web.session.DBStore(db, 'sessions')
session = web.session.Session(app, store, initializer={ 'login': False,
                                                        'id': -1, 
                                                        'verified': False, 
                                                        'email': None, 
                                                        'username': None})


#form validators
vemail = form.regexp(r"^.+@.+$", "must be a valid email address")
vname= form.regexp(r"^[A-Za-z0-9._+-]{3,}$", "must be a valid username (numbers, letters, and . _ - +)")
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
    info = model.get_user_info(userid,where='id')
    session.email = info['email']
    session.username = info['username']
    session.verified = info['verified']
    return True

def is_string(object):
    return isinstance(object, str)

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
                    form.Dropdown("category", args=['Tenant', 'Landlord', 'Both'], value='Tenant'),
                    form.Button("submit", type="submit", html="Confirm"))

#login form
login_form = form.Form(
                    form.Textbox("login_id"),
                    form.Password("password", vpass),
                    form.Button("submit", type="submit", html="Confirm"))
#confirm verify form
confirm_verify_form = form.Form(
                    form.Textbox("code"),
                    form.Button("submit", type="submit", html="Verify"))

#request verify form
request_verify_form = form.Form(
                    form.Hidden("send_email", value="true"),
                    form.Button("send", type="submit", html="Send verification email"))

#request reset form
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

#make relation request form
relation_request_form = form.Form(
                        form.Hidden("relation_type", value="request"),
                        form.Button("submit", type="submit", html="Request relation"))

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
            if model.save_user(email=x.email, username=x.username, password=x.password, category=x.category) == True:
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

class confirm_reset:
    '''reset user password'''
    def GET(self):
        try:
            if not session.login:
                f=confirm_reset_form()
                return render.confirm_reset(f)
            else:
                raise web.seeother('/')
        except:
            return "Unknown Error"

    @csrf_protected
    def POST(self):
        '''Verify the reset code'''
        if not session.login:
            t = confirm_reset_form()
            if not t.validates():
                raise web.seeother('/reset')

            try:
                x=web.input()
                user_info = model.get_user_info(x.email,where='email')
                if model.verify_code(user_info['id'], x.code, 'reset') == True:
                    set_session_values(user_id)
                    f = new_password_form()
                    return render.password_reset(f)
                else:
                    raise web.unauthorized()

            except:
                return "Error"
        else:
            raise web.seeother('/')

class request_reset:
    def GET(self):
        try:
            if not session.login:
                f=request_reset_form()
                return render.request_reset(f)
            else:
                raise web.seeother('/')
        except:
            return "Unknown Error"

    @csrf_protected
    def POST(self):
        if not session.login:
            f = request_reset_form()
            if not f.validates():
                raise web.seeother('/reset/request')

            if model.throttle_email_attempt(web.ctx.ip):
                return 'try again in six minutes'

            x=web.input()
            try:
                user_info = model.get_user_info(x.email,where='email',id=True)
                if user_info == False: 
                    #FIX I could lie, which prevents email harvesting...sort of
                    #timing attacks still possible but what if honest mistake?
                    #then misleading --> so think about this in the future
                    model.add_failed_email(web.ctx.ip)
                    return "No account associated with that email"

                if model.allow_email(x.email, 'reset', web.ctx.ip):
                    if model.send_reset_email(user_info['id'], x.email) == True:
                        model.save_sent_email(web.ctx.ip,x.email,'reset')
                        return "Email sent"
                    else:
                        raise web.unauthorized()
                else:
                    return "Email throttled, wait 1 min"

            except:
                raise "Error"
        else:
            raise web.unauthorized()

class confirm_verify:
    '''confirm email address with email/code combo'''
    def GET(self):
        if session.login and not session.verified:
            f = confirm_verify_form()
            return render.confirm_verify(f)
        else:
            raise web.seeother('/')

    @csrf_protected
    def POST(self):
        x = web.input()
        if session.login and not session.verified:
            f = verify_form()
            if not f.validates():
                raise web.seeother('/verify')

            try:
                if model.verify_code(session.id, x.code, 'reset'):
                    raise web.seeother('/')
                else:
                    raise web.seeother('/verify')
            except:
                return "Error"
        else:
            raise web.seeother('/')

class request_verify:
    '''send verify email'''
    def GET(self):
        if session.login and not session.verified:
            f = request_verify_form()
            return render.request_verify(f)
        else:
            raise web.seeother('/')

    @csrf_protected
    def POST(self):
        if session.login and not session.verified:
            x=web.input()
            if x.send_email == "true":
                if model.allow_email(session.email,'verify', web.ctx.ip) == True:
                    if model.send_verification_email(session.id, session.email) == True:
                        model.save_sent_email(web.ctx.ip,session.email,'reset')
                        return "Email sent"
                    else:
                        return "Email error"
                else:
                    return "Email throttled, wait 1 min"
            else:
                raise web.badrequest()
        else:
            raise web.seeother('/')

class agreements:
    def GET(self, num):
        if session.login:
            try:
                model.get_document(session.id, num)
            except ValueError:
                return web.badrequest()
        else:
            return web.unauthorized()

    def DELETE(self, num):
            if session.login:
                try:
                    if model.delete_document(session.id, num) == True:
                        return '<verb>Deleted</verb><object>{0}</object>'.format(id)
                    else:
                        return web.notfound()
                except ValueError:
                    return web.badrequest()
            else:
                return web.unauthorized()

class post_agreement:
    def GET(self):
        try:
            if session.login == True:
                f=upload_form()
                return render.post_agreement(f)

            else:
                raise web.unauthorized()
        except:
            return sys.exc_info()

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
            raise web.seeother('/agreement/list')
        except: 
            return sys.exc_info()

class list_agreements:
    def GET(self):
        if session.login:
            info=model.get_documents(session.id)
            return render.list_agreements(info)
        else:
            return web.unauthorized()

class profile:
    '''View and change info on profile'''
    def GET(self):
        if session.login:
            f = new_password_form()
            user_info=model.get_user_info(session.id,where='id')
            try:
                #TODO Clean this up
                relations=[]
                for k,v in model.get_relations(session.id).items():
                    if is_string(v): relations.append((k,v))
                    else: relations.append((k,', '.join(v)))

                info = dict(user_info.items() + relations)
                return render.profile(info, f)
            except:
                return render.profile(user_info, f)
        else:
            raise web.unauthorized()

    @csrf_protected
    def POST(self):
        #TODO Show what errors there were
        #TODO This section is getting too big, simplify or push to backend
        if session.login == True:
            allowed_changes=['email', 'password']
            x=web.input()
            for key in x.keys():
                if key not in allowed_changes:
                    del x[key]
                elif key == 'password':
                    if not vpass.valid(x['password']): raise web.seeother('/profile')
                elif key == 'email':
                    if not vemail.valid(x[key]): raise web.seeother('/profile')
                else:
                    pass

            try:
                if model.update_user(id=session.id, **x) == True:
                    raise web.seeother('/')
                else:
                    raise web.badrequest()
            except AttributeError:
                raise web.badrequest()
            else:
                return sys.exc_info()
        else:
            raise web.unauthorized()

class list_payments:
    def GET(self):
        '''list payments'''
        if session.login == True:
            payments_info = model.get_payments(session.id)
            return render.payment_info(payments_info)
        else:
            raise web.unauthorized()

class payment_info:
    def GET(self, arg):
        if session.login == True:
            try:
                charge=model.get_payment(session.id, arg)
                return charge
            except:
                return web.badrequest()
        else:
            raise web.unauthorized()

class pay_user:
    '''display pay username page and pay user'''
    def GET(self, arg):
        if session.login == True:
            #RISK Leaks user info (accepts_cc, name, etc)
            try:
                info=model.get_user_info(arg,where='username',id=True,accepts_cc=True)
                if info['accepts_cc'] == True:
                    pk_key=model.get_user_pk(info['id'])
                    if pk_key:
                        return render.pay_person(pk_key, arg)
                    else:
                        return "error"
                else:
                    #not accepts cc
                    raise web.badrequest()
            except:
                #not a user
                raise web.badrequest()
        else:
            raise web.unauthorized()

    @csrf_protected
    def POST(self, arg):
        #RISK Worried about js injection/poisoning
        if session.login == True:
            x=web.input()
            try:
                info=model.get_user_info(arg,where='username',id=True)
                sk_key=model.get_user_sk(info['id'])
                if sk_key:
                    charge = model.authorize_payment(x.stripeToken,
                                                    x.amount,
                                                    sk_key,
                                                    session.username,
                                                    session.id,
                                                    info['id'])
                    if charge:
                        #if model.capture_payment(charge, sk_key) == True:
                            #model.save_payment(session.id,,charge)
                        #else
                            #return "Payment error"
                        pass
                    else:
                        return "Payment error"
                else:
                    return "Payment error"
            except AttributeError:
                return "Payment error"
            except:
                return "error"
        else:
            raise web.unauthorized()

class search_landlord:
    '''landlord search'''
    def GET(self):
        if session.login == True:
            if model.get_user_info(session.id,where='id',category=True)['category'] == 'Tenant':
                return render.search_landlord()
            else:
                raise web.seeother('/')
        else:
            raise web.unauthorized()

class landlord_query:
    '''get landlord info/make request/end relation'''
    #TODO Shorten, and give more info on errors
    def GET(self, arg):
        if session.login == True:
            try:
                info=model.get_user_info(arg,
                                        where='username',
                                        category=True,
                                        username=True,
                                        email=True)
                if info['category'] == 'Landlord':
                    f = relation_request_form()
                    return render.landlord_page(info, f)
                else:
                    raise web.badrequest()
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

    @csrf_protected
    def POST(self, name):
        x=web.input()
        if session.login == True:
                try:
                    x=web.input()
                    lan=model.get_user_info(name,where='username',id=True,category=True)
                    if lan['category'] == 'Landlord':
                        if x.relation_type == 'request':
                            if model.make_relation_request(session.id,lan['id']):
                                return 'made request'
                            else:
                                return "no request"
                        elif x.relation_type == 'end':
                            if model.end_relation(session.id,land['id']):
                                return 'ended relationship'
                            else:
                                return 'unknown relation'
                        else:
                            return 'weird request type'
                    else:
                        return 'not landlord'
                except:
                    raise web.badrequest()
        else:
            raise web.unauthorized()

class search_users:
    '''grep similar username, given constrants'''
    #RISK This is available to any user, be very careful of the keys allowed!
    def GET(self):
        allowed_keys=['accepts_cc', 'category']
        try:
            if session.login == True:
                x=web.input()
                username=x.username
                for key in x.keys():
                    if key not in allowed_keys:
                        del x[key]
                return '<br />'.join([row['username'] for row in model.search_users(username, **x)])
            else:
                raise web.unauthorized()
        except:
            raise web.badrequest()

if __name__ == "__main__":
    app.run()
