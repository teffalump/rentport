#!/usr/bin/env python2
#Route WSGI apps

from werkzeug.wsgi import DispatcherMiddleware
from main import wsgi_app as frontend
from issue_tracker import app as backend
from flup.server.fcgi import WSGIServer

application = DispatcherMiddleware(frontend, {
    '/issues':     backend
})

if __name__ == '__main__':
    WSGIServer(application).run()
