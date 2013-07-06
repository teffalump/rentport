#!/usr/bin/env python2

import web
import model
import config
from web import form


urls = (
            '/agreement', 'agreement',
            '/(.*)', 'hello'
        )

app = web.application(urls, globals())

#renderer
render = web.template.render('templates')

#using session store with database
web.config.session_paramaters['cookie_path']='/'
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

class hello:
    def GET(self, name):
        if not name:
            name = 'World'
        return 'Hello, ' + name + '!'

class agreement:
    def GET(self):
        f = upload_form()
        return render.upload(f)

    def POST(self):
        x = web.input(agreement={})
        return (x.agreement.filename)

if __name__ == "__main__":
    app.run()
