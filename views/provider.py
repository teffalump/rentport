from rentport.common.extensions import db, mail
from rentport.common.forms import (OpenIssueForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm,
                        AddProviderForm, ConnectProviderForm, SelectProviderForm,
                        ImportYelpURLForm)
from rentport.common.model import (Issue, Property, User, LandlordTenant,
                        Comment, WorkOrder, Fee, Payment, StripeUserInfo,
                        Address, SavedProvider, Provider, Image)
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

#### Blueprint ####
provider = Blueprint('provider', __name__, template_folder = '../templates/provider', static_folder='static')
#### /Blueprint ####

#### EMAIL STRINGS ####
def provider_issue_email(work_order):
    email='The landlord has picked a provider. Discuss with your landlord about fixing the issue - {0}:\n\nName: {1}\n\nEmail: {2}\n\nPhone: {3}\n\nWebsite: {4}'
    t = email.format(
            url_for('.show_issue', ident=work_order.issue.id, _external=True),
            work_order.provider.name,
            work_order.provider.email,
            work_order.provider.phone,
            work_order.provider.website)
    return t
#### /EMAIL STRINGS ####

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
    return redirect_xhr_or_normal('select_provider.html',
                    prev_url=url_for('.saved_providers', ident=issue.id),
                    yelp_url=url_for('.yelp_providers', ident=issue.id))

@provider.route('/issues/<int(min=1):ident>/provider/yelp', methods=['GET', 'POST'])
@login_required
def yelp_providers(ident):
    """List and select yelp provider for job"""
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
    form = ImportYelpURLForm()
    api=yelp()
    f=categories.get(issue.area, None)
    ad = ', '.join(issue.location.address.neighborhood,
                    issue.location.address.city,
                    issue.location.address.state)
    info=api.search_query(category_filter=f, limit=10, sort=2, location=ad)
    return redirect_xhr_or_normal('select_yelp_provider.html', results=info['businesses'])

@provider.route('/issues/<int(min=1):ident>/provider/saved', methods=['GET', 'POST'])
@login_required
def saved_providers(ident):
    issue=Issue.query.filter(Issue.landlord_id==g.user.id,
                Issue.status == 'Open',
                Issue.id == ident).first()
    if not issue:
        flash('Not an open issue')
        return redirect_xhr_or_normal('.show_issue', ident=ident)
    if issue.work_orders.first():
        flash('Provider already selected')
        return redirect_xhr_or_normal('.show_issue', ident=ident)
    form=SelectProviderForm()
    ps = [(str(prov.id), prov.name) for prov in g.user.providers]
    if not ps:
        flash('No previous providers!')
        return redirect_xhr_or_normal('.add_provider')
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

@provider.route('/landlord/provider/add', methods=['POST'])
@login_required
def add_provider():
    '''Add local provider'''
    form=AddProviderForm()
    if form.validate_on_submit():
        p=SavedProvider()
        p.service=request.form['area']
        p.name=request.form['name']
        p.email=request.form['email']
        p.website=request.form['website']
        p.phone=request.form['phone']
        p.by_user_id=g.user.id
        db.session.add(p)
        db.session.commit()
        flash('Provider added')
        return render_xhr_or_normal('show_provider.html', prov=p)
    return render_xhr_or_normal('add_provider.html', form=form)

@provider.route('/landlord/provider/yelp', defaults={'business_id': None},
                                                        methods=['GET'])
@provider.route('/landlord/provider/yelp/<business_id>', methods=['GET'])
@login_required
def get_yelp_providers(business_id):
    """Return yelp providers"""
    yelp_api=yelp()
    if business_id:
        info=yelp_api.business_query(id=business_id)
    else:
        info=yelp_api.search_query(dict(request.args.items()))
    return jsonify(info)


@provider.route('/landlord/provider', defaults={'prov_id': None}, methods=['GET'])
@provider.route('/landlord/provider/<int:prov_id>', methods=['GET'])
@login_required
def show_providers(prov_id):
    '''Show providers'''
    b=Provider.join(WorkOrder).query.filter(or_(Provider.by_user==g.user, Provider.by_user==g.user.current_landlord(), WorkOrder.issue.location==g.user.current_location()))
    if prov_id:
        x=b.filter(Provider.id==prov_id).first()
        if not x:
            flash('Not a valid provider')
            return redirect_xhr_or_normal('.show_providers')
        return render_xhr_or_normal('show_provider.html', prov=x)
    else:
        form=AddProviderForm()
        return render_xhr_or_normal('show_providers.html', providers=b.all(), form=form,
                action=url_for('.add_provider'))
#### /PROVIDER ####

__all__=['provider']
