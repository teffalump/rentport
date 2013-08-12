# Functions
* rental agreement
* pay rent/fees
* issues

# Software
* lighttpd
* stripe
    + python api
* sendgrid
    + python api
* python libraries
    + scrypt
    + web.py
    + magic
* request tracker
* postgresql

# Roadmap
1. Serve document
    + implement basic (!) CRUD - DONE
    + Display old rental agreements, etc with interface
        + Done fugly, polish? But otherwise DONE
2. User system
    + Basic func, no email - DONE
    + Verify system - Sorta done
    + Reset system - Sorta done
    + Need email system - use sendgrid - untested code
3. Payment system
    + Should I include paypal? evil!
4. issue tracking system

# Security TODOs
    + Prevent CSRF by protecting forms
    + Any DoS/spam/bruteforce-possible attack surfaces need throttling
        + throttle logins
