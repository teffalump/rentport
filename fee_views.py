
#### Blueprint ####
rp = Blueprint('fee', __name__, template_folder = 'templates', static_folder='static')
#### /Blueprint ####


#### FEES ####
@rp.route('/fees', methods=['GET'])
@rp.route('/fees/<int(min=1):page>', methods=['GET'])
@rp.route('/fees/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def fees(page=1, per_page=current_app.config['PAYMENTS_PER_PAGE']):
    '''main fees page
        params:     GET: <page> what page to show
                    GET: <per_page> how many items per page
        returns:    GET: template'''
    fees=g.user.fees.paginate(page, per_page, False)
    return render_template('fees.html', fees=fees)

@rp.route('/fees/<int:pay_id>/show', methods=['GET'])
@login_required
def show_fee(pay_id):
    '''show extended fee info
        params:     GET: <pay_id> payment id
        returns:    GET: json-ed payment info'''
    fee=g.user.fees.filter(Fee.id==pay_id).first()
    if not fee:
        flash('No fee with that id')
        return jsonify({'error': 'No fee with that id'})
    f = stripe.Charge.retrieve(fee.pay_id,
                    api_key=current_app.config['STRIPE_CONSUMER_SECRET'])\
                    .to_dict()
    return jsonify({k:v for (k,v) in f.items() if k in \
            ['amount', 'currency', 'paid', 'refunded','description']})
#### /FEES ####
