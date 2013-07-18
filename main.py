#!/usr/bin/env python2

import web
import model
import config
import sys
from web import form


urls = (
            '/agreement(/.*)?', 'agreement',
            '/login', 'login',
            '/logout', 'logout',
            '/register', 'register',
            '/.*', 'default'
        )

app = web.application(urls, globals())

#renderer
render = web.template.render('templates')

#using session store with database
web.config.session_parameters['cookie_path']='/'
db = web.database(  dbn='postgres', 
                    db=config.db, 
                    user=config.user, 
                    pw=config.pw)
store = web.session.DBStore(db, 'sessions')
session = web.session.Session(app, store, initializer={'login': False, 'id': -1})

#upload form
upload_form = form.Form(
                    form.File("agreement"),
                    )

#login/reg form
login_form = form.Form(
                    form.Textbox(name="email"),
                    form.Password(name="password"))

class default:
    def GET(self):
        f = upload_form()
        return render.upload(f)

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

class logout:
    def GET(self):
        if session.login:
            session.login=False
            session.kill()
        raise web.seeother('/')

class register:
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

class agreement:
    def GET(self, id):
        f = model.get_document(10)
        web.header('Content-Type', f['data_type'])
        web.header('Content-Disposition', 'attachment; filename="{0}"'.format(f['file_name']))
        web.header('Content-Transfer-Encoding', 'binary')
        web.header('Cache-Control', 'no-cache')
        web.header('Pragma', 'no-cache')
        return f['data'].decode('base64')

    def POST(self, id):
        x = web.input(agreement={})
        try:
            model.save_document(
                                user=session.id,
                                data_type=model.get_file_type(x.agreement.file),
                                filename=x.agreement.filename,
                                data=x.agreement.value
                                )
            return "Uploaded"
        except:
            return "Error"

if __name__ == "__main__":
    app.run()
