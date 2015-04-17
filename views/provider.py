from rentport.common.extensions import db, mail
from rentport.common.forms import (OpenIssueForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm,
                        AddProviderForm, ConnectProviderForm, SelectProviderForm,
                        ImportYelpURLForm, SelectYelpProviderForm,
                        ConfirmYelpChoiceForm)
from rentport.common.model import (Issue, Property, User, LandlordTenant,
                        Comment, WorkOrder, Fee, Payment, StripeUserInfo,
                        Address, SavedProvider, Provider, Image, YelpProvider)
from flask.ext.mail import Message
from flask.ext.security import login_required
from flask import (Blueprint, render_template, request, g, redirect, url_for,
                    abort, flash, session, json, jsonify, current_app,
                    make_response)
from sqlalchemy import or_
from sys import exc_info as er
from datetime import datetime as dt
from rentport.common.utils import (get_address, render_xhr_or_normal,
                                    redirect_xhr_or_normal, yelp)
from os import path as fs
from uuid import uuid4
from urllib.parse import urlparse

#### Blueprint ####
provider = Blueprint('provider', __name__, template_folder = '../templates/provider', static_folder='static')
#### /Blueprint ####

#### EMAIL STRINGS ####
def provider_issue_email(work_order):
    email='The landlord has picked a provider. Discuss with your landlord about fixing the issue - {0}:\n\nName: {1}\n\nEmail: {2}\n\nPhone: {3}\n\nWebsite: {4}'
    if isinstance(work_order.provider, YelpProvider):
        info=get_yelp_business_info(work_order.provider.yelp_id)
        name=info['name']
        email='<unknown>'
        phone=info['phone'] or '<unknown>'
        website=info['url']
    else:
        email=work_order.provider.email
        phone=work_order.provider.phone or '<unknown>'
        website=work_order.provider.website or '<unknown>'
        name=work_order.provider.name

    t = email.format(
            url_for('issue.show_issue', ident=work_order.issue.id, _external=True),
            name,
            email,
            phone,
            website)
    return t
#### /EMAIL STRINGS ####

#### UTIL ####
def get_yelp_business_info(id_):
    api=yelp()
    info=api.business_query(id_)
    return info
#### /UTIL ####

#### PROVIDER ####
@provider.route('/issues/<int(min=1):ident>/provider', methods=['GET'])
@login_required
def select_provider(ident):
    """Show selection screen"""
    issue=Issue.query.filter(Issue.landlord_id==g.user.id,
                Issue.status == 'Open',
                Issue.id == ident).first()
    form=CloseIssueForm()
    if not issue:
        flash('Issue closed or non-existent')
        return redirect_xhr_or_normal('issue.issues')
    return render_xhr_or_normal('select_provider.html',
                    prev_url=url_for('.saved_providers', ident=issue.id),
                    cust_url=url_for('.add_local_provider', next=url_for('.saved_providers', ident=ident)),
                    yelp_url=url_for('.yelp_providers', ident=issue.id))

@provider.route('/issues/<int(min=1):ident>/provider/yelp', methods=['GET', 'POST'])
@login_required
def yelp_providers(ident):
    """List and select new Yelp provider for job"""
    categories={'Plumbing': 'plumbing',
                'Heating/Air Conditioning': 'hvac',
                'Cleaning': 'homecleaning',
                'Electrical': 'electricians'}
    issue=Issue.query.filter(Issue.landlord_id==g.user.id,
                Issue.status == 'Open',
                Issue.id == ident).first()
    if not issue:
        flash('Issue closed or non-existent')
        return redirect_xhr_or_normal('issue.issues')
    form=SelectYelpProviderForm()
    if form.validate_on_submit():
        id_=request.form.getlist('id_')[-1]
        info=get_yelp_business_info(id_)
        if YelpProvider.query.filter(YelpProvider.yelp_id==info['id'],
                                    YelpProvider.by_user==g.user).first():
            flash('Business with same ID already saved')
            return redirect_xhr_or_normal('.saved_providers', ident=ident)
        y=YelpProvider()
        y.name = info['name']
        y.by_user=g.user
        y.yelp_id=info['id']
        #website = info['url']
        #location = info['location']['display_address']
        db.session.add(y)
        db.session.commit()
        flash("Saved {0}'s information".format(info['name']))
        return redirect_xhr_or_normal('.saved_providers', ident=ident)
        #t=ConfirmYelpChoiceForm()
        #action=url_for('.saved_providers', ident=ident)
        #return render_xhr_or_normal('confirm_yelp_choice.html',
                                    #name=info['name'],
                                    #id_=id_,
                                    #website=website,
                                    #location=', '.join(location),
                                    #action=action,
                                    #form=t)
    else:
        api=yelp()
        f=categories.get(issue.area, None)
        ad = ', '.join([issue.location.address.neighborhood,
                        issue.location.address.city,
                        issue.location.address.state])
        info=api.search_query(category_filter=f, limit=10, sort=2, location=ad)
        return render_xhr_or_normal('select_yelp_provider.html',
                                            results=info['businesses'],
                                            form=form,
                                            next=url_for('.saved_providers', ident=issue.id))

@provider.route('/issues/<int(min=1):ident>/provider/saved', methods=['GET', 'POST'])
@login_required
def saved_providers(ident):
    """List from saved providers"""
    issue=Issue.query.filter(Issue.landlord_id==g.user.id,
                Issue.status == 'Open',
                Issue.id == ident).first()
    if not issue:
        flash('Not an open issue')
        return redirect_xhr_or_normal('issue.show_issue', ident=ident)
    if issue.work_orders.first():
        flash('Provider already selected')
        return redirect_xhr_or_normal('issue.show_issue', ident=ident)
    form=SelectProviderForm()
    ps = [(str(prov.id), prov.name) for prov in g.user.providers]
    if not ps:
        flash('No previous providers!')
        return redirect_xhr_or_normal('.select_provider', ident=ident)
    form.provider.choices=ps
    if form.validate_on_submit():
        w=WorkOrder()
        w.provider_id=int(request.form['provider'])
        issue.work_orders.append(w)
        db.session.add(w)
        db.session.commit()
        msg = Message('Issue provider', recipients=[u.email for u in issue.location.current_tenants().all()])
        msg.body=provider_issue_email(w)
        mail.send(msg)
        logger.info('mail sent: {0}'.format(msg))
        flash('Provider selected')
        return redirect_xhr_or_normal('issue.show_issue', ident=ident)
    return render_xhr_or_normal('select_previous_provider.html', issue=issue, form=form)

@provider.route('/landlord/provider/custom', methods=['GET', 'POST'])
@login_required
def add_local_provider():
    '''Add local provider'''
    form=AddProviderForm()
    n = request.args.get('next')
    if form.validate_on_submit():
        p=SavedProvider()
        p.service=request.form.get('area')
        p.name=request.form.get('name')
        p.email=request.form.get('email')
        p.website=request.form.get('website')
        p.phone=request.form.get('phone')
        p.by_user_id=g.user.id
        db.session.add(p)
        db.session.commit()
        flash('Saved provider information')
        return redirect_xhr_or_normal('.show_providers', prov_id=p.id) 
    return render_xhr_or_normal('add_provider.html', form=form, next=n)

@provider.route('/landlord/provider/yelp', methods=['GET', 'POST'])
@login_required
def add_yelp_provider():
    """Add yelp provider"""
    n = request.args.get('next')
    form=ImportYelpURLForm()
    if form.validate_on_submit():
        # Submitted url
        url=request.form.get('url')
        b_id=urlparse(url)[2].split('/')[-1] #id is last part of path
        if not b_id:
            flash("Cannot find business's Yelp page")
            return redirect_xhr_or_normal('.show_providers')
        try:
            info=get_yelp_business_info(b_id)
        except:
            flash("Cannot find business info. Incorrect Yelp URL?")
            return render_xhr_or_normal('import_from_yelp_url.html', form=form, next=n)
        p=YelpProvider.query.filter(YelpProvider.yelp_id==info['id'],
                                YelpProvider.by_user==g.user).first()
        if p:
            flash('Business with same ID already saved')
            return redirect_xhr_or_normal('.show_providers', prov_id=p.id, next=n)
        name = info['name']
        id_ = info['id']
        y=YelpProvider()
        y.name = name
        y.yelp_id=id_
        y.by_user=g.user
        db.session.add(y)
        db.session.commit()
        flash("Saved {0}'s information".format(name))
        return redirect_xhr_or_normal('.show_providers', prov_id=y.id, next=n)
    return render_xhr_or_normal('import_from_yelp_url.html', form=form, next=n)

@provider.route('/landlord/provider', defaults={'prov_id': None}, methods=['GET'])
@provider.route('/landlord/provider/<int:prov_id>', methods=['GET'])
@login_required
def show_providers(prov_id):
    '''Show providers'''
    b=Provider.query.filter(
                    or_(Provider.by_user == g.user,
                    Provider.by_user == g.user.current_landlord() ))

    if prov_id:
        x=b.filter(Provider.id == prov_id).first()
        if not x:
            flash('Not a valid provider')
            return redirect_xhr_or_normal('.show_providers')
        if isinstance(x, YelpProvider):
            i = get_yelp_business_info(x.yelp_id)
            x.website = i['url']
            x.phone = i['phone']
            x.email = '<unknown email>'
            x.service = ', '.join([x[0] for x in i['categories']])
        return render_xhr_or_normal('show_provider.html', prov=x)
    else:
        #form=AddProviderForm()
        return render_xhr_or_normal('show_providers.html', providers=b.all())# form=form,
                #action=url_for('.select_provider'))
#### /PROVIDER ####

__all__=['provider']
