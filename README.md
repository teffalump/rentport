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
* sendgrid
* nexmo/twilio

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
    + Payment history? How to display that. Either:
        1. Store the payment history locally 
            Pros:
                + User experience (pagination, etc)
            Cons:
                + Security; DB leak = payment history (creepy)
                + Need to update it with hooks from stripe --> more code
        2. Query Stripe for the info (only access token/customer id from oauth)
            Pros:
                + Minimal info server-side = stronger security, privacy, etc
            Cons:
                + Minimal info
                + User experience degradation
            + For now, let's do 2 b/c it is simpler
            + I think I need to store some info locally b/c...
                + Without, can't assign tenant to payment without doing lots of
                  weird querying (like, iterating prev landlord with stripe)
            + How to mitigate info? Simply save the charge id, from, to info
              from the webhook but only that!
    + Incorporate mylar: http://css.csail.mit.edu/mylar/

# Other thoughts
+ rental agreements? seems security issues too big for me... at the moment
+ Add Dwolla after Stripe (but Stripe is the minimum)

# Service fee info
+ One level subscription for one year
+ If not paid?
    + Can't:
        1. Open new issues
        2. Add new properties
        3. Receive payments
    + But can:
        1. Comment on and close current issues
        2. Modify existing properties

