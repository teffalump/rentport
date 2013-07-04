#!/usr/bin/env python2

import web

urls = (
            '/agreement', 'agreement',
            '/(.*)', 'hello'
        )

#renderer
render = web.template.render('templates')

#using session store with database
db = web.database(dbn='postgres', db='rentport', user='blar', pw='blar')
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
    app = web.application(urls, globals())
    app.run()
