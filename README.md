# Functions
* pay rent/fees
* issues

# Software
* nginx (load  balancer/front)
* postgresql (db)
* python libraries
    + tornado (wsgi server)
    * supervisord (process management)
    + stripe (payment)
    + redis (key-store)
    + sqlalchemy (sql modeling)
        + searchable (full text search)
    + flask (web framework)
        + limiter (limit endpoint calls)
        + security (user management, security, email, etc)
        + kvsession (server-side sessions)
        + sqlalchemy (sql)
    + twilio (text)
    + dwolla (payment)
    + geopy (location)

# Infrastructure
* linode (hosting) - $10/month
* mailgun (email) - free-ish ( < 10k/month )
* twilio (sms) - $1/month + $.0075/msg
* easydns (dns) - $20/yr
* namecheap (ssl) - $10/yr

# Roadmap
1. User system - DONE
2. Issue tracking system - DONE
3. Payment system(s) --- PUT ON HOLD!
    + Stripe - NEEDS TESTING
    + Dwolla - TODO (optional)
    + Bitcoin - TODO (optional)
4. Notification system(s)
    + Mailgun for email - NEEDS TESTING
    + Twilio for sms - TODO
5. Location services
6. Prettify
    + Good, robust templates - Almost there
    + Add searching along issues and comments - TODO
    + Ajax-ify - TODO

# Security TODOs
    + Prevent CSRF by protecting forms - DEFAULT IN WTFORMS
    + Any DoS/spam/bruteforce-possible attack surfaces need throttling
        + Use Flask-Limiter for endpoints - TODO
    + go through OWASP top ten
    + Do I import js plugins (e.g, jQuery)? No, store locally
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
+ Notification events
    + Rent payment
    + New issue
    + ... Any other?

# Other thoughts
+ rental agreements? seems security issues are too big... at the moment
