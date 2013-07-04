#!/usr/bin/env python2

import web

urls = (
            '/agreement', 'agreement',
            '/(.*)', 'hello'
        )

app = web.application(urls, globals())

#renderer
render = web.template.render('templates')

#using session store with database
db = web.database(dbn='postgres', db='rentport', user='blar', pw='blar')
store = web.session.DBStore(db, 'sessions')
session = web.session.Session(app, store)

#upload form
upload_form = form.Form(
                    form.File("agreement"),
                    form.Button("Upload")
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

if __name__ == "__main__":
    app.run()
