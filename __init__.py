from flask import Flask
from flask.ext.kvsession import KVSessionExtension

import redis
store = RedisStore(redis.StrictRedis())

app = Flask(__name__)

KVSessionExtension(store, app)

import rentport.views
import issues
import model
import config

urls = ('/issues', issues.issues_app)

#session settings
web.config.session_parameters['cookie_name']='rentport'
web.config.session_parameters['cookie_path']='/'
web.config.session_parameters['timeout']=900
web.config.session_parameters['ignore_expiry']=False
web.config.session_parameters['ignore_change_ip']=False
web.config.session_parameters['expired_message']='Session expired'
#web.config.session_parameters['secure']=True

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

if __name__ == "__main__":
    app.run()
