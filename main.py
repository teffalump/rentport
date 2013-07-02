#!/usr/bin/env python2

import web

urls = (
            '/(.*)', 'hello'
        )

app = web.application(urls, globals())

#using session store with database
db = web.database(dbn='postgres', db='rentport', user='blar', pw='blar')
store = web.session.DBStore(db, 'sessions')
session = web.session.Session(app, store)

class hello:
    def GET(self, name):
        if not name:
            name = 'World'
        return 'Hello, ' + name + '!'

if __name__ == "__main__":
    app.run()
