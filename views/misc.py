from rentport.common.extensions import db
from rentport.common.model import (Issue, Property, User, LandlordTenant,
                        Fee, Payment, StripeUserInfo, Image, StripeEvent)
from flask.ext.security import login_required
from flask import (Blueprint, request, g, json,
                    jsonify, current_app, make_response)
from sys import exc_info as er
from rentport.common.utils import get_url, render_xhr_or_normal
import stripe
import logging

logger = logging.getLogger(__name__)

#### Blueprint ####
misc = Blueprint('misc', __name__, template_folder = '../templates/misc', static_folder='static')
#### /Blueprint ####

#### DEFAULT ####
@misc.route('/')
@login_required
def home():
    return render_xhr_or_normal('home.html')
#### /DEFAULT ####

#### HOOKS ####
@misc.route('/hook/stripe', methods=['POST'])
def stripe_hook():
    try:
        event=json.loads(request.data)['id']
        m = StripeEvent.query.filter(StripeEvent.event==event).first()
        if m: return 'Event already processed'
        c = stripe.Event.retrieve(event,
                api_key=current_app.config['STRIPE_CONSUMER_SECRET'])
        i=Fee.query.filter(Fee.pay_id==c['data']['object']['id']).first()
        if not i: return 'Charge not found.'
        if c['type']=='charge.succeeded':
            i.status='Confirmed'
        elif c['type']=='charge.refunded':
            i.status='Refunded'
        elif c['type']=='charge.failed':
            i.status='Denied'
        else:
            return 'Type not handled.'
        ev = StripeEvent(event=event)
        db.session.add(i)
        db.session.add(ev)
        db.session.commit()
        return 'Success'
    except KeyError:
        return 'Not an event or charge object'
    except ValueError:
        return 'Not valid JSON structure'
    except:
        return 'An exception occurred'
        #if c['type']=='account.application.deauthorized':
            #t=StripeUserInfo.query.filter(StripeUserInfo.user_acct==acct).first()
            #if not t: return 'not a user'
            #db.session.delete(t)
            #db.session.commit()
        #elif c['data']['object']=='dispute':
            #pass
        #elif c['data']['object']=='customer':
            #pass
        #elif c['data']['object']=='card':
            #pass
        #elif c['data']['object']=='subscription':
            #pass
        #elif c['data']['object']=='invoice':
            #pass
        #elif c['data']['object']=='plan':
            #pass
        #elif c['data']['object']=='transfer':
            #pass
        #elif c['data']['object']=='discount':
            #pass
        #elif c['data']['object']=='coupon':
            #pass
        #elif c['data']['object']=='balance':
            #pass
        #elif c['data']['object']=='account':
            #pass
        #else:
            #pass
        #return ''
    #except:
        #return str(er())

@misc.route('/hook/twilio')
def twilio_hook():
    '''twilio hook'''
    #TODO
    return ''
#### /HOOKS ####

@misc.route('/user/search', methods=['GET'])
@login_required
def search_user():
    """Search for users"""
    q = request.args.get('q')
    if not q:
        return jsonify({'results': []})
    r = ''.join((q,'%'))
    u = User.query.filter(User.username.ilike(r)).limit(10).with_entities(User.username).all()
    if u:
        t={'results': [{'username': t[0]} for t in u]}
    else:
        t={'results': []}
    return jsonify(t)


#### IMAGES ####
@misc.route('/img/<image_uuid>', methods=['GET'])
@login_required
def show_img(image_uuid):
    '''Use X-Accel-Redirect to let nginx handle static files'''
    #FIX Only allow current issues and properties! Discuss more!
    im=Image.query.join(Issue.images).join(Property.assocs).\
                filter(LandlordTenant.tenant == g.user, LandlordTenant.current == True).\
                filter(Image.uuid==image_uuid).first_or_404()
    #fs_path='/'.join([current_app.config['UPLOAD_FOLDER'], im.filename])
    ur_redirect='/'.join(['/srv/images', im.filename])
    response=make_response("")
    response.headers['X-Accel-Redirect']=ur_redirect
    return response
#### /IMAGES ####

__all__=['misc']
