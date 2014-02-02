from rentport import app

@app.route('/')
def default():
    return default()

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        ip = web.ctx.ip
        x = web.input()
        if not model.allow_login(x.login_id, ip):
            return 'throttled'

        user_info = model.verify_password(x.password, x.login_id)
        if user_info['login'] == True:
            model.clear_failed_logins(x.login_id, ip)
            set_session_values(**user_info)
            raise web.seeother('/')
        else:
            model.add_failed_login(x.login_id, ip)
            raise web.seeother('/login')

    else:
        if session.login == True:
            raise web.seeother('/')
        else:
            f = login_form()
            return render.login(f)


@app.route('/logout')
def logout():
    if session.login == True: session.kill()
    raise web.seeother('/')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        f = register_form()
        if not f.validates():
            raise web.seeother('/register')

        x = web.input()
        try:
            #TODO Some tuning here
            #TODO Return different errors on problems (taken username, etc)
            if model.save_user(email=x.email, username=x.username, password=x.password, category=x.category) == True:
                #if model.send_verification_email(x.email) == True:
                    #model.save_sent_email(web.ctx.ip, x.email,'verify')
                    #raise web.seeother('/login')
                #else:
                    #return "Error"
                raise web.seeother('/login')
            else:
                return "Error"
        except: 
            return "Error"

    else:
        if session.login == True:
            raise web.seeother('/')
        else:
            f = register_form()
            return render.register(f)

@app.route('/reset/confirm', methods=['POST', 'GET'])
def confirm_reset():
    '''reset user password'''
    if request.method == 'POST':
        if not session.login:
            try:
                x=web.input()
                user_info = model.get_user_info(x.email,where='email')
                if model.verify_code(user_info['id'], x.code, 'reset') == True:
                    user_info['login']=True
                    set_session_values(**user_info)
                    f = new_password_form()
                    return render.password_reset(f)
                else:
                    raise web.unauthorized()

            except:
                return "Error"
        else:
            raise web.seeother('/')
    else:
        try:
            if not session.login:
                f=confirm_reset_form()
                return render.confirm_reset(f)
            else:
                raise web.seeother('/')
        except:
            return "Unknown Error"

@app.route('/reset/request', methods=['POST', 'GET'])
def request_reset():
    if request.method == 'POST':
        if not session.login:
            f = request_reset_form()
            if not f.validates():
                raise web.seeother('/reset/request')

            if model.throttle_email_attempt(web.ctx.ip):
                return 'try again in six minutes'

            x=web.input()
            try:
                user_info = model.get_user_info(x.email,where='email',id=True)
                if user_info == False: 
                    #FIX I could lie, which prevents email harvesting...sort of
                    #timing attacks still possible but what if honest mistake?
                    #then misleading --> so think about this in the future
                    model.add_failed_email(web.ctx.ip)
                    return "No account associated with that email"

                if model.allow_email(x.email, 'reset', web.ctx.ip):
                    if model.send_reset_email(user_info['id'], x.email) == True:
                        model.save_sent_email(web.ctx.ip,x.email,'reset')
                        return "Email sent"
                    else:
                        raise web.unauthorized()
                else:
                    return "Email throttled, wait 1 min"

            except:
                return "Error"
        else:
            raise web.unauthorized()
    else:
        try:
            if not session.login:
                f=request_reset_form()
                return render.request_reset(f)
            else:
                raise web.seeother('/')
        except:
            return "Unknown Error"

@app.route('/verify/confirm', methods=['POST', 'GET'])
def confirm_verify():
    '''confirm email address with email/code combo'''
    if request.method == 'POST':
        x = web.input()
        if session.login and not session.verified:
            f = verify_form()
            if not f.validates():
                raise web.seeother('/verify')

            try:
                if model.verify_code(session.id, x.code, 'reset'):
                    raise web.seeother('/')
                else:
                    raise web.seeother('/verify')
            except:
                return "Error"
        else:
            raise web.seeother('/')
    else:
        if session.login and not session.verified:
            f = confirm_verify_form()
            return render.confirm_verify(f)
        else:
            raise web.seeother('/')

@app.route('/verify/request', methods=['POST','GET'])
def request_verify():
    '''send verify email'''
    if request.method == 'POST':
        if session.login and not session.verified:
            x=web.input()
            if x.send_email == "true":
                if model.allow_email(session.email,'verify', web.ctx.ip) == True:
                    if model.send_verification_email(session.id, session.email) == True:
                        model.save_sent_email(web.ctx.ip,session.email,'reset')
                        return "Email sent"
                    else:
                        return "Email error"
                else:
                    return "Email throttled, wait 1 min"
            else:
                raise web.badrequest()
        else:
            raise web.seeother('/')
    else:
        if session.login and not session.verified:
            f = request_verify_form()
            return render.request_verify(f)
        else:
            raise web.seeother('/')

@app.route('/agreements')
def agreements():
    '''main agreements page'''
    if session.login == True:
        try:
            a=model.get_documents(session.id)
            return render.agreements(a)
        except:
            raise web.badrequest()
    else:
        raise web.unauthorized()

@app.route('/agreements/delete', methods=['POST'])
def delete_agreements():
    '''delete agreement'''
    if session.login:
        try:
            return dumps(dict(model.delete_document(session.id, x.id)))
        except:
            raise web.badrequest()
    else:
        raise web.unauthorized()

@app.route('/agreement/post', methods=['POST', 'GET'])
def post_agreement():
    if request.method == 'POST':
        def POST(self):
            #save agreement, return info
            if session.login == True:
                x = web.input(agreement={})
                try:
                    return dumps(model.save_document(
                                        user=session.id,
                                        title=x.title,
                                        description=x.description,
                                        data_type=model.get_file_type(x.agreement.file),
                                        filename=x.agreement.filename,
                                        data=x.agreement.value
                                        ))
                except:
                    raise web.badrequest()
            else:
                raise web.unauthorized()
    else:
        if session.login == True:
            try:
                f=upload_form()
                return render.post_agreement(f)
            except:
                return "Error"
        else:
            raise web.unauthorized()

@app.route('/agreements/show/<int:doc_id>')
def show_agreements(doc_id):
    '''show agreements'''
    if session.login == True:
        try:
            return model.get_document(session.id, x.id)
        except AttributeError:
            info=model.get_documents(session.id)
            return render.list_agreements(info)
        except:
            raise web.badrequest
    else:
        raise web.unauthorized()

@app.route('/profile', methods=['POST', 'GET'])
def profile():
    if request.method == 'POST':
        #TODO Show what errors there were
        if session.login == True:
            x=web.input()
            try:
                return dumps(dict(model.update_user(session.id, **x)))
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

    else:
        if session.login == True:
            try:
                f = new_password_form()
                user_info=model.get_user_info(session.id,where='id')
                user_info.update(model.get_relations(session.id))
                return render.profile(user_info, f)
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()


@app.route('/payments')
def payments():
    '''main payments page'''
    if session.login == True:
        return render.payments_home()
    else:
        raise web.unauthorized()

@app.route('/payments/show/<int:pay_id>')
def show_payments(pay_id):
    '''show payments'''
    x=web.input()
    if session.login == True:
        try:
            return model.get_payment(session.id, x.id)
        except AttributeError:
            payments_info = model.get_payments(session.id)
            return render.payment_info(payments_info)
        except:
            raise web.badrequest
    else:
        raise web.unauthorized()

@app.route('/pay/<user>', methods=['POST', 'GET'])
def pay_user(user):
    '''display pay username page and pay user'''
    if request.method == 'POST':
        #RISK Worried about js injection/poisoning
        x=web.input()
        if session.login == True:
            x=web.input()
            try:
                info=model.get_user_info(x.user,where='username',id=True)
                sk_key=model.get_user_sk(info['id'])
                if sk_key:
                    charge_id = model.authorize_payment(x.stripeToken,
                                                    x.amount,
                                                    sk_key,
                                                    session.username,
                                                    session.id,
                                                    info['id'])
                    if charge_id:
                        #if model.capture_payment(charge, sk_key) == True:
                            #model.save_payment(session.id,info['id'],charge_id)
                            #return "Paid"
                        #else
                            #return "Payment error"
                        pass
                    else:
                        return "Payment error"
                else:
                    return "Payment error"
            except AttributeError:
                return "Payment error"
            except:
                return "error"
        else:
            raise web.unauthorized()
    else:
        if session.login == True:
            #RISK Leaks user info (accepts_cc, name, etc)
            #RISK XSS? escape user?
            #Need accepts_cc? Maybe just search for keys
            try:
                info=model.get_user_info(x.user,where='username',id=True,accepts_cc=True,username=True)
                if info['accepts_cc'] == True:
                    pk_key=model.get_user_pk(info['id'])
                    if pk_key:
                        return render.pay_person(pk_key, info['username'])
                    else:
                        return "Can't find key"
                else:
                    #not accepts cc
                    raise web.badrequest()
            except (KeyError,TypeError,AttributeError):
                #not a user or bad parameters
                raise web.badrequest()
        else:
            raise web.unauthorized()

@app.route('/landlord/search')
def search_landlord():
    '''landlord search'''
    if session.login == True:
        if model.get_user_info(session.id,where='id',category=True)['category'] == 'Tenant':
            return render.search_landlord()
        else:
            raise web.seeother('/')
    else:
        raise web.unauthorized()

@app.route('/landlord/request', methods=['POST', 'GET'])
def request_relation():
    '''make relation request'''
    #TODO Give more info on errors
    if request.method == 'POST':
        x=web.input()
        if session.login == True:
            try:
                return dumps(dict(model.make_relation_request(session.id,x.user,x.location)))
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()
    else:
        if session.login == True:
            try:
                f = relation_request_form()
                return render.landlord_page(f)
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

@app.route('/landlord/confirm', methods=['POST', 'GET'])
def confirm_relation():
    '''confirm relation request from tenant'''
    if request.method == 'POST':
        x=web.input()
        if session.login == True:
            try:
                return dumps(dict(model.confirm_relation_request(x.user, session.id)))
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()
    else:
        if session.login == True:
            try:
                f = confirm_relation_form()
                return render.confirm_relation_form(f)
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

@app.route('/landlord/end', methods=['POST', 'GET'])
def end_relation():
    '''end relation'''
    if request.method == 'POST':
        x = web.input()
        if session.login == True:
            try:
                if x.end == 'true':
                    return dumps(dict(model.end_relation(session.id)))
                else:
                    raise web.badrequest()
            except AttributeError:
                raise web.badrequest()
        else:
            raise web.unauthorized()
    else:
        if session.login == True:
            try:
                f = end_relation_form()
                return render.end_relation_form(f)
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

@app.route('/search_users/<search>')
def search_users(search):
    '''grep similar username, given constrants'''
    #RISK This is available to any user, be very careful of the keys allowed!
    #RISK do on backend to insure rigor
    x=web.input()
    if session.login == True:
        try:
            return dumps(list(model.search_users(x.username, **x)))
        except:
            raise web.badrequest()
    else:
        raise web.unauthorized()

@app.route('/oauth/stripe/authorize')
def authorize_stripe():
    '''authorize stripe: oauth2'''
    #TODO CSRF protection with state variable
    c = Client(auth_endpoint=config.stripe.oauth_site + config.stripe.authorize_uri,
        client_id=config.stripe.client_id)

    state=None
    raise web.seeother(c.auth_uri(state=state,
                                scope='read_write',
                                response_type='code',
                                redirect_uri="https://www.rentport.com/oauth/callback"
                                ))

@app.route('/oauth/stripe/callback')
def callback_stripe():
    '''redirect uri from stripe: oauth2'''
    #TODO CSRF protection with state variable
    x = web.input()
    state, code=x.state, x.code
    c = Client(token_endpoint=config.stripe.oauth_site + config.stripe.token_uri,
        client_id=config.stripe.client_id,
        client_secret=config.stripe.test_private_key)

    c.request_token(
            code=code,
            grant_type='authorization_code')

    #save keys
    if model.save_user_keys(session.id,
                        c.access_token,
                        c.stripe_publishable_key,
                        c.refresh_token) != True:
        return "Error"

    #change to accept cc
    if model.update_user(session.id, accepts_cc=True) != True:
        return "Error"

    return "Authorized and keys received!"
