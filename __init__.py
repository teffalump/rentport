import os
from flask import Flask, render_template, g
from flask.ext.sqlalchemy import SQLAlchemy
#from flask.ext.limiter import Limiter
from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
from flask.ext.security.utils import encrypt_password
from flask.ext.security.forms import RegisterForm, LoginForm
from flask.ext.wtf import Form
from wtforms import SelectField, TextField
from wtforms.validators import Length, DataRequired, Regexp
from flask.ext.kvsession import KVSessionExtension
from flask.ext.bootstrap import Bootstrap
from flask.ext.mail import Mail, Message
from simplekv.memory.redisstore import RedisStore
import redis


app = Flask(__name__)
app.config.from_object('rentport.config')

store = RedisStore(redis.StrictRedis())
os.environ['DEBUG']="1"

db = SQLAlchemy(app)
mail = Mail(app)
#KVSessionExtension(store, app)
#limiter = Limiter(app, global_limits=['15 per minute'])
Bootstrap(app)


from rentport.views import *
from rentport.model import *

user_datastore = SQLAlchemyUserDatastore(db, User, Role)

class ExtendedRegisterForm(RegisterForm):
    username=TextField('Username', [DataRequired(),
                                    Regexp(r'^\w+$', message="Only alphanumeric characters"),
                                    Length(min=4, max=20)])

class ExtendedLoginForm(LoginForm):
    email=TextField('Login', [DataRequired()])

security = Security(app, user_datastore,
            register_form=ExtendedRegisterForm,
            login_form=ExtendedLoginForm)

@app.before_request
def before_request():
    g.user = current_user

@app.before_first_request
def create_user():
    db.create_all()
    user_datastore.create_user(email='t4@example.net', password=encrypt_password('password'), username='t4')
    user_datastore.create_user(email='t@example.net', password=encrypt_password('password'), username='t')
    user_datastore.create_user(email='t2@example.net', password=encrypt_password('password'), username='t2')
    user_datastore.create_user(email='t3@example.net', password=encrypt_password('password'), username='t3')
    user_datastore.create_user(email='l@example.net', password=encrypt_password('password'), username='l')
    user_datastore.create_user(email='l2@example.net', password=encrypt_password('password'), username='l2')
    user_datastore.create_user(email='l3@example.net', password=encrypt_password('password'), username='l3')
    db.session.commit()
    l=User.query.filter(User.username=='l').first()
    l2=User.query.filter(User.username=='l2').first()
    l2=User.query.filter(User.username=='l2').first()
    h=Property(location='place_1', description='blar')
    h2=Property(location='place_2', description='blar2')
    h3=Property(location='place_3', description='blar3')
    l.properties.append(h)
    l.properties.append(h2)
    l2.properties.append(h3)
    db.session.commit()
    lt=LandlordTenant(location_id=h.id)
    lt2=LandlordTenant(location_id=h.id)
    lt3=LandlordTenant(location_id=h3.id)
    t=User.query.filter(User.username=='t').first()
    t2=User.query.filter(User.username=='t2').first()
    t3=User.query.filter(User.username=='t3').first()
    lt.tenant=t
    lt2.tenant=t2
    lt3.tenant=t3
    l.tenants.append(lt)
    l.tenants.append(lt2)
    l2.tenants.append(lt3)
    db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
