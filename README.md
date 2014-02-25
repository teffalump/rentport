# Functions
* rental agreement
* pay rent/fees
* issues

# Software
* lighttpd (maybe)
* tornado
* dwolla
    + api
* stripe
    + python api
* python libraries
    + redis
    + sqlalchemy
    + flask (web framework)
        + limiter
        + security
        + kvsession (when py3 compat)
        + sqlalchemy
* postgresql

# Roadmap
1. Serve document - TODO
2. User system
    + Using Flask-Security...already implemented
        + Configure email through Flask-Security
3. Payment system
    + Stripe - TODO
    + Dwolla - TODO
4. Issue tracking system
    + Simple issue tracker - IN PROGRESS
5. Prettify
    + Ajax-ify
    + Good templates
    + Works on Mobile, etc

# Security TODOs
    + Prevent CSRF by protecting forms - INCLUDED IN WTFORMS
    + Any DoS/spam/bruteforce-possible attack surfaces need throttling
        + throttle logins/emails - Use Flask-Limiter for endpoints
        + go through owasp top ten
        + Do I import js plugins (e.g, jQuery)? Security considerations

# Other thoughts
+ Return json? Or valid html? Like tables, etc.
