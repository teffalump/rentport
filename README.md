# Functions
* pay rent/fees
* issues

# Software
* nginx (load  balancer/front)
* postgresql (db)
* python libraries
    + tornado (wsgi server)
    + stripe (payment)
    + redis (key-store)
    + sqlalchemy (sql modeling)
        + searchable (full text search)
    + flask (web framework)
        + limiter (limit endpoint calls)
        + security (user management, security, email, etc)
        + kvsession (server-side sessions) (broken!)
        + sqlalchemy (sql)
    + twilio (text)
    + dwolla (payment)

# Infrastructure
* linode (hosting) - $20/month
* mailgun (email) - free-ish ( < 10k/month )
* twilio (sms) - $1/month + $.0075/msg
* easydns (dns) - $20/yr

# Roadmap
1. User system
    + Using Flask-Security...already implemented
        + Configure email through Flask-Security
2. Issue tracking system
    + Simple issue tracker - DONE
3. Payment system
    + Stripe - TODO
    + Dwolla - TODO
4. Notification system
    + Twilio for sms - TODO
    + Mailgun for email - TODO
5. Prettify
    + Ajax-ify
    + Good templates
    + Works on Mobile, etc

# Security TODOs
    + Prevent CSRF by protecting forms - DEFAULT IN WTFORMS
    + Any DoS/spam/bruteforce-possible attack surfaces need throttling
        + Use Flask-Limiter for endpoints - TODO
    + go through OWASP top ten
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
                + Minimal info server-side = stronger security, privacy, etc.
            Cons:
                + Minimal info
                + User experience degradation
            + I think I need to store some info locally b/c...
                + Without, can't assign tenant to payment without doing lots of
                  weird querying (like, iterating prev landlord with stripe)
            + How to mitigate the info? Simply save the charge id, from, to
              info from the webhook, but only that!
    + Incorporate mylar: http://css.csail.mit.edu/mylar/

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
+ Notification levels
    1. Low: Only rent and new issue - Only allowed for now
    2. Medium: Low + landlord-request/end
    3. High: Medium + comments

# Other thoughts
+ rental agreements? seems security issues are too big... at the moment
+ Add Dwolla after Stripe (but Stripe is the minimum)
