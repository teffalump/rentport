import os
from flask import Flask, g
from flask.ext.security import SQLAlchemyUserDatastore, current_user
from .config import DebugConfig


def before_request():
    g.user = current_user

def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(DebugConfig)
    if config is not None:
        app.config.from_object(config)
    app.config.from_envvar('RENTPORT_CONFIG', silent=True)

    with app.app_context():
        import logging
        logging.basicConfig(filename='flask.log', level=10)

        from .extensions import mail, db, security, bootstrap, kvsession, limiter
        mail.init_app(app)
        db.init_app(app)
        bootstrap.init_app(app)
        limiter.init_app(app)

        def bffr():
            db.create_all()

        from .model import User, Role
        user_datastore = SQLAlchemyUserDatastore(db, User, Role)

        from .forms import ExtendedRegisterForm, ExtendedLoginForm
        security.init_app(app, user_datastore,
                register_form=ExtendedRegisterForm,
                login_form=ExtendedLoginForm,
                confirm_register_form=ExtendedRegisterForm)


        from redis import StrictRedis
        from simplekv.memory.redisstore import RedisStore
        kv_store = RedisStore(StrictRedis())
        kvsession.init_app(app, kv_store)

        #bind before request(s)
        app.before_first_request(bffr)
        app.before_request(before_request)

        from .views import rp
        app.register_blueprint(rp)

    os.environ['DEBUG']="1"

    return app

if __name__ == "__main__":
    create_app().run(debug=True)
