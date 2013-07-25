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
            '/upload', 'upload',
            '/login', 'login',
            '/logout', 'logout',
            '/register/?', 'register',
            '/verify/?', 'verify',
            '/.*', 'default'
        )

app = web.application(urls, globals())

#session settings
web.config.session_parameters['cookie_name']='rentport'
web.config.session_parameters['cookie_path']='/'
web.config.session_parameters['timeout']=300
web.config.session_parameters['ignore_expiry']=False
web.config.session_parameters['ignore_change_ip']=False
web.config.session_parameters['expired_message']='Session expired: login again'
#web.config.session_parameters['secure']=True

#using session store with database
db = web.database(  dbn='postgres', 
                    db=config.db, 
                    user=config.user, 
                    pw=config.pw)
store = web.session.DBStore(db, 'sessions')
session = web.session.Session(app, store, initializer={'login': False, 'id': -1})

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
            model.save_user(email=x.email, password=x.password)
            raise web.seeother('/login')
        except: 
            return "Error"

class verify:
    '''verify email address with email/code combo; need to be logged in'''
    def GET(self):
        if not session.login:
            raise web.seeother('/')
        elif model.is_verified(session.id):
            raise web.seeother('/')
        else:
            f = verify_form()
            return render.verify(f)

    def POST(self):
        x = web.input()
        try:
            if session.login:
                if model.verify_email(session.id, code=x.code):
                    raise web.seeother('/')
                else:
                    raise web.seeother('/verify')
            else:
                raise web.unauthorized()
        except:
            return sys.exc_info()

class query:
    def GET(self, id):
        if session.login:
            try:
                int(id)
                f = model.get_document(session.id, id)
                web.header('Content-Type', f['data_type'])
                #i'm worried about the security of the following header, how i do it
                web.header('Content-Disposition', 'attachment; filename="{0}"'.format(re.escape(f['file_name'])))
                web.header('Content-Transfer-Encoding', 'binary')
                web.header('Cache-Control', 'no-cache')
                web.header('Pragma', 'no-cache')
                return f['data'].decode('base64')
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
                        return 'Deleted'
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
            return x.agreement.filename
        except: 
            return sys.exc_info()

if __name__ == "__main__":
    app.run()
