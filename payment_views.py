## Payment/Oauth routes

#### Blueprint ####
rp = Blueprint('payment', __name__, template_folder = 'templates/payment', static_folder='static')
#### /Blueprint ####

#### PAYMENTS ####
# RISK
# PAID ENDPOINT
# MUST BE CONFIRMED
# ALERT USER(S)
@rp.route('/pay/landlord', defaults={'amount': None}, methods=['GET'])
@rp.route('/pay/landlord/<int(min=10):amount>', methods=['POST', 'GET'])
@login_required
def pay_rent(amount):
    lt=g.user.landlords.filter(LandlordTenant.current==True).first()
    if not lt:
        flash('No current landlord')
        return redirect(url_for('rentport.payments'))
    if not lt.confirmed:
        flash('Need to be confirmed!')
        return redirect(url_for('rentport.payments'))
    if not lt.landlord.fee_paid():
        flash('Landlord has not paid service fee')
        return redirect(url_for('rentport.payments'))
    if not lt.landlord.stripe:
        flash('Landlord cannot accept CC')
        return redirect(url_for('rentport.payments'))
    if amount:
        cents=amount*100
        if request.method == 'POST':
            token = request.form['stripeToken']
            try:
                charge = stripe.Charge.create(
                      api_key=lt.landlord.stripe.access_token,
                      amount=cents,
                      currency="usd",
                      card=token,
                      description=': '.join(['From::', str(g.user.id), g.user.username]))
                p = Payment(to_user_id=lt.landlord.id, pay_id=charge.id)
                g.user.sent_payments.append(p)
                db.session.add(p)
                db.session.commit()
                flash('Payment processed')
                msg = Message('Rent payment', recipients=[lt.landlord.email])
                msg.body = 'Rent from {0}: amt: {1}'.\
                        format(g.user.username, '$' + str(amount))
                mail.send(msg)
                flash('Landlord notified')
            except stripe.error.CardError:
                flash('Card error')
            except stripe.error.AuthenticationError:
                flash('Authentication error')
            except Exception as inst:
                flash(type(inst))
                flash(inst)
                flash('Other payment error')
            finally:
                return redirect(url_for('rentport.payments'))
        else:
            return render_template('pay_landlord.html', landlord=lt.landlord,
                                                        amount=amount)
    else:
        return render_template('get_pay_amount.html', landlord=lt.landlord, user=g.user)

# RISK
@rp.route('/pay/fee', methods=['POST', 'GET'])
@login_required
def pay_fee():
    if request.method == 'POST':
        token = request.form['stripeToken']
        try:
            charge = stripe.Charge.create(
                  api_key=current_app.config['STRIPE_CONSUMER_SECRET'],
                  amount=current_app.config['FEE_AMOUNT'],
                  currency="usd",
                  card=token,
                  description=':'.join([str(g.user.id), g.user.username])
                  )
            c = Fee(pay_id=charge.id)
            g.user.fees.append(c)
            db.session.add(c)
            db.session.commit()
            g.user.paid_through=max(g.user.paid_through,dt.utcnow())+c.length
            db.session.add(g.user)
            db.session.commit()
            flash('Payment processed')
        except stripe.error.CardError:
            flash('Card error')
        except stripe.error.AuthenticationError:
            flash('Authentication error')
        except Exception:
            flash('Other payment error')
        finally:
            return redirect(url_for('rentport.fees'))

    else:
        return render_template('pay_service_fee.html',
                                amount=current_app.config['FEE_AMOUNT'],
                                key=current_app.config['STRIPE_CONSUMER_KEY'])

@rp.route('/payments', methods=['GET'])
@rp.route('/payments/<int(min=1):page>', methods=['GET'])
@rp.route('/payments/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def payments(page=1, per_page=current_app.config['PAYMENTS_PER_PAGE']):
    '''main payments page
        params:     GET: <page> page to show
                    GET: <per_page> items per page
        returns:    GET: template'''
    allowed_sort={'id': Payment.id,
            'date': Payment.time,
            'status': Payment.status,
            'from': Payment.from_user,
            'to': Payment.to_user}
    sort_key=request.args.get('sort', 'id')
    sort = allowed_sort.get(sort_key, Payment.id)
    order_key = request.args.get('order', 'desc')
    if order_key =='asc':
        payments=g.user.payments().order_by(sort.asc()).\
                paginate(page, per_page, False)
    else:
        order_key='desc'
        payments=g.user.payments().order_by(sort.desc()).\
                paginate(page, per_page, False)
    return render_template('payments.html', payments=payments, sort=sort_key, order=order_key)

@rp.route('/payments/<int:pay_id>/show', methods=['GET'])
@login_required
def show_payment(pay_id):
    '''show extended payment info
        params:     GET: <pay_id> payment id
        returns:    GET: json-ed payment info'''
    payment=Payment.query.filter(Payment.id==pay_id).first()
    if not payment:
        return jsonify({'error': 'No payment with that id'})
    try:
        p = stripe.Charge.retrieve(payment.pay_id,
                api_key=payment.to_user.stripe.access_token)
        if not p:
            return jsonify({'error': 'No payment with that charge id'})
        m = p.to_dict()
    except Exception as inst:
        return jsonify({'error': 'Error retrieving payment'})

    return jsonify({k:v for (k,v) in m.items() if k in \
            ['amount', 'currency', 'paid', 'refunded', 'description']})

#### OAUTH ####
@rp.route('/oauth/authorize', methods=['GET'])
@login_required
def authorize():
    '''Authorize Stripe, or refresh'''
    if g.user.stripe:
        flash('Have stripe info already')
        return redirect(url_for('rentport.home'))
    oauth=OAuth2Session(current_app.config['STRIPE_CLIENT_ID'],
        redirect_uri=url_for('rentport.authorized', _external=True),
        scope=current_app.config['STRIPE_OAUTH_CONFIG']['scope'])
    auth_url, state=oauth.authorization_url(
            current_app.config['STRIPE_OAUTH_CONFIG']['authorize_url'])
    session['state']=state
    return redirect(auth_url)

@rp.route('/oauth/authorized', methods=['GET'])
@login_required
def authorized():
    if g.user.stripe:
        flash('Have stripe info already')
        return redirect(url_for('rentport.home'))
    try:
        oauth=OAuth2Session(current_app.config['STRIPE_CLIENT_ID'],
                        state=session['state'])
        token=oauth.fetch_token(
                        token_url=current_app.config['STRIPE_OAUTH_CONFIG']['access_token_url'],
                        client_secret=current_app.config['STRIPE_CONSUMER_SECRET'],
                        authorization_response=request.url)
        s = StripeUserInfo(access_token=token['access_token'],
                           refresh_token=token['refresh_token'],
                           user_acct=token['stripe_user_id'],
                           pub_key=token['stripe_publishable_key'])
        g.user.stripe=s
        db.session.add(s)
        db.session.commit()
        flash('Authorized!')
    except InvalidClientError:
        flash('Invalid authentication')
    except MismatchingStateError:
        flash('CSRF mismatch')
    except:
        flash('OAuth2 flow error')
    finally:
        return redirect(url_for('rentport.home'))
#### /OAUTH ####
