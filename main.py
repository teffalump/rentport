#!/usr/bin/env python2

import web
import model
import config
from web import form


urls = (
            '/agreement(/.*)?', 'agreement',
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

class default:
    def GET(self):
        f = upload_form()
        return render.upload(f)

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
        return "Uploaded"

if __name__ == "__main__":
    app.run()
