import os
from flask import Flask, g
from flask.ext.security import SQLAlchemyUserDatastore, current_user
from rentport.config import DebugConfig
import sys


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
        logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                format='%(asctime)s:::%(levelname)s:::%(name)s: %(message)s')

        from rentport.common.extensions import (mail, db, security,
                                                bootstrap, kvsession, limiter)
        #from .extensions import images
        mail.init_app(app)
        db.init_app(app)
        bootstrap.init_app(app)
        limiter.init_app(app)
        #images.init_app(app)

        def bffr():
            db.create_all()

        from rentport.common.model import User, Role
        user_datastore = SQLAlchemyUserDatastore(db, User, Role)

        from rentport.common.forms import (RegisterForm,
                                            ExtendedLoginForm)
        security.init_app(app, user_datastore,
                register_form=RegisterForm,
                login_form=ExtendedLoginForm,
                confirm_register_form=RegisterForm)
        limiter.limit('20/minute;60/day')(app.blueprints['security'])



        from redis import StrictRedis
        from simplekv.memory.redisstore import RedisStore
        kv_store = RedisStore(StrictRedis())
        kvsession.init_app(app, kv_store)

        #bind before request(s)
        app.before_first_request(bffr)
        app.before_request(before_request)

        # NOTE: subtle path bugs with templates and routing
        # 
        #    The app object overrides the options set by the blueprint
        #    like, the template_folder and url_prefix
        from rentport.views import (issue, relation, housing,
                                    profile, fee, misc, provider)
        app.register_blueprint(misc)
        app.register_blueprint(issue)
        app.register_blueprint(relation)
        app.register_blueprint(housing)
        app.register_blueprint(profile)
        app.register_blueprint(fee)
        app.register_blueprint(provider)

    return app

__all__=['create_app']

if __name__ == "__main__":
    os.environ['DEBUG']="1"
    create_app().run(debug=True)
