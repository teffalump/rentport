#!/usr/bin/env python2

# obtain the WSGI request dispatcher
from roundup.cgi.wsgi_handler import RequestDispatcher
tracker_home = '/opt/roundup/trackers/support/'
app = RequestDispatcher(tracker_home)
