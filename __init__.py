from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required
#import redis
#from flask.ext.kvsession import KVSessionExtension
#from simplekv.memory.redisstore import RedisStore
#store = RedisStore(redis.StrictRedis())

app = Flask(__name__)

#KVSessionExtension(store, app)

db = SQLAlchemy(app)

import rentport.views
import rentport.model
import issues
import config

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

urls = ('/issues', issues.issues_app)

#upload form
upload_form = form.Form(
                    form.File("agreement"),
                    form.Textbox("title"),
                    form.Textbox("description"),
                    form.Button("submit", type="submit", html="Upload", onclick="return sendForm(this.form, this.files)"))

#register form
register_form = form.Form(
                    form.Textbox("email", vemail),
                    form.Textbox("username", vname),
                    form.Password("password", vpass),
                    form.Dropdown("category", args=['Tenant', 'Landlord', 'Both'], value='Tenant'),
                    form.Button("submit", type="submit", html="Confirm"))

#login form
login_form = form.Form(
                    form.Textbox("login_id"),
                    form.Password("password", vpass),
                    form.Button("submit", type="submit", html="Confirm"))

#confirm verify form
confirm_verify_form = form.Form(
                    form.Textbox("code"),
                    form.Button("submit", type="submit", html="Verify"))

#request verify form
request_verify_form = form.Form(
                    form.Hidden("send_email", value="true"),
                    form.Button("send", type="submit", html="Send verification email"))

#request reset form
request_reset_form = form.Form(
                    form.Textbox("email", vemail, id="reset_email"),
                    form.Button("submit", type="submit", html="Request reset email"))

#confirm reset form
confirm_reset_form = form.Form(
                    form.Textbox("email", vemail, id="confirm_email"),
                    form.Textbox("code"),
                    form.Button("confirm", type="submit", html="Confirm reset"))

#new password form
new_password_form = form.Form(
                    form.Textbox("password", vpass, autocomplete="off"),
                    form.Button("submit", type="submit", html="Submit"))

#make relation request form
relation_request_form = form.Form(
                        form.Textbox("location", id="location"),
                        form.Textbox("user", id="username"),
                        form.Button("submit", type="submit", html="Request relation"))

#confirm relation request form
confirm_relation_form = form.Form(
                        form.Textbox("tenant"),
                        form.Button("submit", type="submit", html="Confirm relation"))

#end relation form
end_relation_form = form.Form(
                    form.Hidden("end", value="true"),
                    form.Button("submit", type="submit", html="End current relation"))
#open issue form
open_issue_form = form.Form(form.Textbox("description"),
                            form.Dropdown("severity",
                                args=['Critical', 'Medium', 'Low', 'Future'],
                                value='Critical'),
                            form.Button("submit", type="submit", html="Open"))

#post comment form
post_comment_form = form.Form(form.Textbox("comment"),
                            form.Button("submit", type="submit", html="Submit"))

if __name__ == "__main__":
    app.run()
