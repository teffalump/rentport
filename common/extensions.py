# Initialize extensions

from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.mail import Mail
from flask.ext.security import Security
from flask.ext.limiter import Limiter
from flask.ext.bootstrap import Bootstrap
from flask.ext.kvsession import KVSessionExtension
#from flask.ext.images import Images

# SQLAlchemy
db = SQLAlchemy()

# Mail
mail = Mail()

# Security
security = Security()

# Limiter
limiter = Limiter()

# Bootstrap
bootstrap = Bootstrap()

# KVSession
kvsession = KVSessionExtension()

# Images
#images=Images()

__all__=['kvsession', 'bootstrap', 'limiter', 'security',
        'mail', 'db']
