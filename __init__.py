from flask import Flask, render_template, g
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.limiter import Limiter
from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
from flask.ext.security.utils import encrypt_password
from flask.ext.security.forms import RegisterForm, LoginForm
from flask.ext.wtf import Form
from wtforms import SelectField, TextField
from wtforms.validators import Length, DataRequired

import redis
r=redis.StrictRedis(host='localhost', port=43413, db=0)

#from flask.ext.kvsession import KVSessionExtension
#from simplekv.memory.redisstore import RedisStore
#store = RedisStore(redis.StrictRedis())

app = Flask(__name__)
app.config.from_object('rentport.config')
app.config['SECURITY_USER_IDENTITY_ATTRIBUTES'] = 'username,email'
app.config['RATELIMIT_STORE_URL']='redis://localhost:43413'
app.config['RATELIMIT_STRATEGY']='moving-window'

#KVSessionExtension(store, app)

db = SQLAlchemy(app)
limiter = Limiter(app, global_limits=['60 per minute'])

from rentport.views import *
from rentport.model import *

user_datastore = SQLAlchemyUserDatastore(db, User, Role)

class OpenIssueForm(Form):
    severity=SelectField('Severity', choices=[('Critical', 'Need fix now!'),
                                                ('Medium', 'Important'),
                                                ('Low', 'Can wait'),
                                                ('Future', 'Would be cool to have')])
    description=TextField('Description', [DataRequired()])

class ExtendedRegisterForm(RegisterForm):
    username=TextField('Username', [DataRequired(), Length(min=3, max=20)])

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


#upload form
#upload_form = form.Form(
                    #form.File("agreement"),
                    #form.Textbox("title"),
                    #form.Textbox("description"),
                    #form.Button("submit", type="submit", html="Upload", onclick="return sendForm(this.form, this.files)"))

##make relation request form
#relation_request_form = form.Form(
                        #form.Textbox("location", id="location"),
                        #form.Textbox("user", id="username"),
                        #form.Button("submit", type="submit", html="Request relation"))

##confirm relation request form
#confirm_relation_form = form.Form(
                        #form.Textbox("tenant"),
                        #form.Button("submit", type="submit", html="Confirm relation"))

##end relation form
#end_relation_form = form.Form(
                    #form.Hidden("end", value="true"),
                    #form.Button("submit", type="submit", html="End current relation"))
##open issue form
#open_issue_form = form.Form(form.Textbox("description"),
                            #form.Dropdown("severity",
                                #args=['Critical', 'Medium', 'Low', 'Future'],
                                #value='Critical'),
                            #form.Button("submit", type="submit", html="Open"))

##post comment form
#post_comment_form = form.Form(form.Textbox("comment"),
                            #form.Button("submit", type="submit", html="Submit"))

if __name__ == "__main__":
    app.run()
