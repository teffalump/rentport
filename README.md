# Functions
* pay rent/fees
* issues

# Software
* lighttpd (maybe)
* tornado server
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
        + kvsession (when fixed)
        + sqlalchemy
* postgresql

# Roadmap
1. User system
    + Using Flask-Security...already implemented
        + Configure email through Flask-Security
2. Issue tracking system
    + Simple issue tracker - DONE
3. Payment system
    + Stripe - TODO
    + Dwolla - TODO
4. Prettify
    + Ajax-ify
    + Good templates
    + Works on Mobile, etc

# Security TODOs
    + Prevent CSRF by protecting forms - DEFAULT IN WTFORMS
    + Any DoS/spam/bruteforce-possible attack surfaces need throttling
        + Use Flask-Limiter for endpoints - TODO
    + go through owasp top ten
    + Do I import js plugins (e.g, jQuery)? Security considerations
    + I'v decided to store NO payment history/info, query stripe for everything
        + Store customer stripe/dwolla id, that's it
        + Data issues, but fuck that

# Other thoughts
+ Return json? Or valid html? Like tables, etc.
+ rental agreements? seems security issues too big for me... at the moment
