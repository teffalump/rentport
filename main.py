#!/usr/bin/env python2

import re
import web
import model
import config
import sys
from web import form

urls = (
            '/agreement/(.+)', 'query',
            '/agreement/?', 'agreement',
            '/upload/?', 'upload',
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

#renderer
render = web.template.render('templates', globals={'context': session})

#upload form
upload_form = form.Form(
                    form.File("agreement"),
                    form.Textbox(name="title"),
                    form.Textbox(name="description")
                    )

#login/reg form
login_form = form.Form(
                    form.Textbox(name="email"),
                    form.Password(name="password"))

#verify form
verify_form = form.Form(
                    form.Textbox(name="code"))

#request reset form
request_reset_form = form.Form(
                    form.Textbox(name="email"))

#new password form
new_password_form = form.Form(
                    form.Textbox(name="password"))

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

    def POST(self):
        x = web.input()
        userid = model.verify_password(x.password, x.email)
        if userid:
            session.login=True
            session.id = userid
            if model.is_verified(userid):
                session.verified = True
            raise web.seeother('/')
        else:
            raise web.seeother('/login')

class upload:
    def GET(self):
        if session.login:
            f = upload_form()
            return render.upload(f)
        else:
            return web.unauthorized()

class logout:
    def GET(self):
        if session.login:
            session.kill()
        raise web.seeother('/')

class register:
    '''register an user
    TODO Add email
    '''
    def GET(self):
        if session.login:
            raise web.seeother('/')
        else:
            f = login_form()
            return render.register(f)

    def POST(self):
        x = web.input()
        try:
            #TODO Some tuning here
            model.save_user(email=x.email, password=x.password)
            model.send_verification_email(x.email)
            raise web.seeother('/login')
        except: 
            return "Error"

class reset:
    '''reset user password'''
    def GET(self):
        x=web.input()
        if not session.login:
            try:
                if model.verify_reset(x.email, x.code) == True:
                    #if code/email combo matches, login and present new password form
                    session.id = model.get_id(x.email)
                    session.login = True
                    if model.is_verified(session.id):
                        session.verified = True

                    f = new_password_form()
                    return render.password_reset(f)
                else:
                    raise web.unauthorized()
            except AttributeError:
                f=request_reset_form()
                return render.reset(f)
            else:
                return "Unknown error"
        else:
            raise web.badrequest()

    def POST(self):
        x=web.input()
        if not session.login:
            try:
                if model.send_reset_email(x.email) == True:
                    return "Email sent"
                else:
                    raise web.unauthorized()
            except AttributeError:
                web.badrequest()
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

    def POST(self):
        x = web.input()
        if session.login and not session.verified:
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
            return render.agreement(info)
        else:
            return web.unauthorized()

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
    '''Change info on profile
    TODO change this a little, to support robust modifications'''
    def POST(self):
        if session.login:
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
