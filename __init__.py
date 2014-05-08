import os
from flask import Flask, g
from flask.ext.security import SQLAlchemyUserDatastore, current_user

def before_request():
    g.user = current_user

def create_app(config='rentport.config'):
    app = Flask(__name__)
    with app.app_context():
        app.config.from_object(config)

        from rentport.extensions import mail
        mail.init_app(app)

        from rentport.extensions import db
        db.init_app(app)

        from rentport.model import User, Role
        user_datastore = SQLAlchemyUserDatastore(db, User, Role)

        from rentport.extensions import security
        from rentport.forms import ExtendedRegisterForm, ExtendedLoginForm
        security.init_app(app, user_datastore,
                register_form=ExtendedRegisterForm,
                login_form=ExtendedLoginForm,
                confirm_register_form=ExtendedRegisterForm)

        from rentport.extensions import bootstrap
        bootstrap.init_app(app)


        #from redis import StrictRedis
        #from flask.extensions import kvsession
        #from simplekv.memory.redisstore import RedisStore
        #kv_store = RedisStore(redis.StrictRedis())
        #kvsession.init_app(app, kv_store)

        #bind before request
        app.before_request(before_request)

        from rentport.views import rp
        app.register_blueprint(rp)

        os.environ['DEBUG']="1"

    return app

if __name__ == "__main__":
    create_app().run(debug=True)
