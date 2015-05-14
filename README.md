# Functions
* pay rent/fees
* issue management

# Software
* nginx (load  balancer/front)
* postgresql (db)
* python libraries
    + tornado (wsgi server)
    * supervisord (process management)
    + stripe (payment)
    + redis (key-store)
    + requests (easy http)
        + oauthlib (oauth)
    + sqlalchemy (sql modeling)
        + searchable (full text search) (unused at the moment)
        + utils
    + limits (flask-limiter)
    + flask (web framework)
        + bootstrap (prettify)
        + limiter (limit endpoint calls)
        + security (user management, security, email, etc)
        + kvsession (server-side sessions)
        + sqlalchemy (sql)
    + zxcvbn (ported to py 3, server side check)
    + yelpapi (yelp api)
    + geopy (location)
    + twilio (text) (unused at the moment)
    + dwolla (payment) (unused at the moment)
* jQuery/Javascript libs
    + Marco Polo autocomplete
    + pwstrength

# Infrastructure
* linode (hosting) - $10/month
* mailgun (email) - free-ish ( < 10k/month )
* twilio (sms) - $1/month + $.0075/msg
* easydns (dns) - $20/yr
* namecheap (ssl) - $10/yr

# Roadmap
1. User system - DONE
2. Issue tracking system - DONE
3. Fee system(s)
    + Stripe (accept CC) -- DONE
    + Paygarden
    + Dwolla
4. Payment system(s) --- PUT ON HOLD!
    + Stripe - NEEDS TESTING
    + Dwolla - TODO (optional)
    + Bitcoin - TODO (optional)
5. Notification system(s)
    + Mailgun for email - DONE
    + Twilio for sms - TODO
6. Location services
7. Prettify --- IN PROGRESS
    + Good, robust templates
    + Add searching along issues and comments
    + Ajax-ify
8. WebRTC

# Security
    + Prevent CSRF by protecting forms - DONE
    + Any possible attack surface need throttling
        + Use Flask-Limiter for endpoints - DONE
    + Vulnerability scanners
        + ZAP (OWASP)
    + Store and server js locally
    + Fee/payment history: store minimal info server-side
    + No rental agreements at the moment
    + Incorporate mylar: http://css.csail.mit.edu/mylar/ - WAY IN FUTURE

# Service info
+ One level subscription for one year
+ If not paid?
    + Can't:
        1. Open new issues
        2. Add new properties
        3. Receive payments
    + Can:
        1. Comment on and close current issues
        2. Modify existing properties
+ Notification events
    + New issue
    + ... Any other?
