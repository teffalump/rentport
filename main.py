#!/usr/bin/env python2

import re
import web
import model
import config
import sys
from uuid import uuid4
from web import form

urls = (
            '/agreement/(.+)', 'query',
            '/agreement/?', 'agreement',
            '/login/?', 'login',
            '/logout/?', 'logout',
            '/register/?', 'register',
            '/verify/?', 'verify',
            '/reset/?', 'reset',
            '/profile/?', 'profile',
            '/.*', 'default'
        )

app = web.application(urls, globals())

#session settings
web.config.session_parameters['cookie_name']='rentport'
web.config.session_parameters['cookie_path']='/'
web.config.session_parameters['timeout']=300
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
session = web.session.Session(app, store, initializer={'login': False, 'id': -1, 'verified': False})


#form validators
vemail = form.regexp(r".*@.*", "must be a valid email address")
vpass = form.regexp(r".{15,}$", 'must be at least 15 characters')

#prevent csrf
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
                                'CSRF')
        return f(*args,**kwargs)
    return decorated

#renderer
render = web.template.render('templates', globals={'context': session, 'csrf_token': csrf_token})

#upload form
upload_form = form.Form(
                    form.File("agreement"),
                    form.Textbox("title"),
                    form.Textbox("description"),
                    form.Button("submit", type="submit", html="Upload"))


#login/register form
login_form = form.Form(
                    form.Textbox("email", vemail),
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
        if session.login:
            raise web.seeother('/')
        else:
            f = login_form()
            return render.login(f)

    @csrf_protected
    def POST(self):
        f = login_form()
        if not f.validates():
            raise web.seeother('/login')

        ip = web.ctx.ip
        x = web.input()
        if not model.allow_login(x.email, ip):
            raise web.seeother('/login')

        userid = model.verify_password(x.password, x.email)
        if userid:
            model.clear_login_attempts(x.email, ip)
            session.login=True
            session.id = userid
            if model.is_verified(userid):
                session.verified = True
            raise web.seeother('/')
        else:
            model.add_login_attempt(x.email, ip)
            raise web.seeother('/login')

class logout:
    def GET(self):
        if session.login:
            session.kill()
        raise web.seeother('/')

class register:
    '''register an user'''
    def GET(self):
        if session.login:
            raise web.seeother('/')
        else:
            f = login_form()
            return render.register(f)

    @csrf_protected
    def POST(self):
        f = login_form()
        if not f.validates():
            raise web.seeother('/register')

        x = web.input()
        try:
            #TODO Some tuning here
            model.save_user(email=x.email, password=x.password)
            #model.send_verification_email(x.email)
            raise web.seeother('/login')
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
                return render.reset(f, t )
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
                    session.id = model.get_id(x.email)
                    session.login = True
                    if model.is_verified(session.id):
                        session.verified = True

                    f = new_password_form()
                    return render.password_reset(f)
                else:
                    raise web.unauthorized()
            except AttributeError:
                if model.send_reset_email(x.email) == True:
                    return "Email sent"
                else:
                    raise web.unauthorized()
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
                    #TODO maybe some tuning here
                    if model.send_verification_email(model.get_email(session.id)) == True:
                        return "Email sent"
                    else:
                        return "Email error"
                else:
                    raise web.badrequest()
            else:
                raise web.badrequest()
        else:
            raise web.unauthorized()

class query:
    def GET(self, id):
        if session.login:
            try:
                int(id)
                f = model.get_document(session.id, id)
                web.header('Content-Type', f['data_type'])
                #i'm worried about the security of the following header, how i do it
                web.header('Content-Disposition', 'attachment; filename="{0}"'.format(re.escape(f['file_name'])))
                web.header('Cache-Control', 'no-cache')
                web.header('Pragma', 'no-cache')
                return f['data']
            except ValueError:
                return web.badrequest()
        else:
            return web.unauthorized()

    def DELETE(self, id):
            if session.login:
                try:
                    int(id)
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
    '''View and change info on profile
    TODO change this a little, to support robust modifications'''
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

if __name__ == "__main__":
    app.run()
