from rentport.common.extensions import db, mail
from rentport.common.forms import (OpenIssueForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm,
                        AddProviderForm, ConnectProviderForm, SelectProviderForm)
from rentport.common.model import (Issue, Property, User, LandlordTenant,
                        Comment, WorkOrder,
                        Fee, Payment, StripeUserInfo, Address, Provider, Image)
from flask.ext.mail import Message
from flask.ext.security import login_required
from requests_oauthlib import OAuth2Session
from flask import (Blueprint, request, g, redirect, url_for,
                    abort, flash, session, json, jsonify, current_app,
                    make_response)
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import or_
from werkzeug.security import gen_salt
from werkzeug import secure_filename
from sys import exc_info as er
from datetime import datetime as dt
from geopy.geocoders import Nominatim
from os import path as fs
from uuid import uuid4
from rentport.common.utils import (redirect_xhr_or_normal,
                        render_xhr_or_normal, allowed_file)
import stripe
import logging

logger = logging.getLogger(__name__)

try:
    from gi.repository import GExiv2 as exif_tool
    EXIF=True
except:
    EXIF=False

#### EMAIL STRINGS ####
def new_issue_email(issue):
    email='New issue! Unit: {0}, Address: {1}\n\nArea: {2}\n\nSeverity: {3}\n\nDescription: {4}\n\nURL: {5}'
    num = issue.location.apt_number or 'N/A'
    ad = ' '.join([str(issue.location.address.number), issue.location.address.street])
    nw=email.format(
            str(num),
            ad,
            issue.area,
            issue.severity,
            issue.description,
            url_for('.show_issue', ident=issue.id, _external=True))
    return nw

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

#### Blueprint ####
issue = Blueprint('issue', __name__, template_folder = 'templates/issue', static_folder='static')
#### /Blueprint ####

#### ISSUES ####
@fee.route('/issues', defaults={'page':1, 'per_page':current_app.config['ISSUES_PER_PAGE']}, methods=['GET'])
@fee.route('/issues/<int(min=1):page>', defaults={'per_page':current_app.config['ISSUES_PER_PAGE']}, methods=['GET'])
@fee.route('/issues/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def issues(page, per_page):
    '''display main issues page
        params:     GET: <page> page number (optional)
                    GET: <per_page> # of issues per page (optional)
        returns:    GET: list of issues
    '''
    allowed_sort={'id': Issue.id,
            'date': Issue.opened,
            'severity': Issue.severity,
            'status': Issue.status}
    sort_key=request.args.get('sort', 'id')
    sort = allowed_sort.get(sort_key, Issue.id)
    order_key = request.args.get('order')
    if order_key =='asc':
        issues=g.user.all_issues().order_by(sort.asc()).\
                paginate(page, per_page, False)
    else:
        order_key='desc'
        issues=g.user.all_issues().order_by(sort.desc()).\
                paginate(page, per_page, False)
    return render_xhr_or_normal('issues.html', issues=issues, sort=sort_key, order=order_key)

@fee.route('/issues/<int(min=1):ident>/show', methods=['GET'])
@login_required
def show_issue(ident):
    '''show issue
        params:     GET: <ident> absolute id
        returns:    GET: detailed issue page
    '''
    issue=g.user.all_issues().filter(
                    Issue.id==ident).first()
    comment = None
    close = None
    if not issue:
        flash('No issue with that id')
        return redirect_xhr_or_normal('.issues')
    contractor = Provider.query.join(WorkOrder).filter(WorkOrder.issue == issue).first()
    if g.user.id == issue.landlord_id:
        close=CloseIssueForm()
        comment=CommentForm()
        if contractor is None:
            ps = Provider.query.filter(Provider.by_user == g.user, Provider.service == issue.area).first()
            if ps:
                provider = ('Select provider', url_for('.authorize_provider', ident=issue.id))
            else:
                provider = ('No available providers', url_for('property.add_provider'))
        else:
            provider = (contractor.name, url_for('property.show_providers', prov_id=contractor.id))
    else:
        if contractor is None:
            provider = ('No selected provider', None)
        else:
            provider = (contractor.name, url_for('property.show_providers', prov_id=contractor.id))

    if issue.status == 'Closed':
        return render_xhr_or_normal('show_issue.html', issue=issue,
                                            comment=None,
                                            close=None,
                                            provider=provider)
    if getattr(g.user.landlords.filter(LandlordTenant.current==True).first(), 'confirmed', None):
        comment=CommentForm()
    if issue.creator_id == g.user.id:
        close=CloseIssueForm()
    return render_xhr_or_normal('show_issue.html', issue=issue,
                                            comment=comment,
                                            close=close,
                                            provider=provider)

# PAID ENDPOINT
# MUST BE CONFIRMED
# ALERT USER(S)
@fee.route('/issues/open', methods=['POST', 'GET'])
@login_required
def open_issue():
    '''open new issue at current location
        params:     POST:   <severity> issue severity
                    POST:   <description> issue description
        returns:    POST:   Redirect for main issues
                    GET:    Open issue form
    '''
    lt = g.user.landlords.filter(LandlordTenant.current==True).first()
    if not lt:
        flash('No current landlord')
        return redirect_xhr_or_normal('.issues')
    if not lt.confirmed:
        flash('Need to be confirmed!')
        return redirect_xhr_or_normal('.issues')
    if not lt.landlord.fee_paid():
        flash('Landlord needs to pay fee')
        return redirect_xhr_or_normal('.issues')
    form=OpenIssueForm()
    if form.validate_on_submit():
        i=g.user.open_issue()
        i.description=request.form['description']
        i.severity=request.form['severity']
        i.area=request.form['type']
        files=request.files.getlist("photos")
        db.session.add(i)
        db.session.commit()
        for f in files:
            if allowed_file(f.filename):
                original_name=secure_filename(f.filename)
                uuid=uuid4().hex
                filename='.'.join([uuid, original_name.split('.')[-1]])
                f.save(fs.join(current_app.config['UPLOAD_FOLDER'], filename))
                f.close()
                if EXIF:
                    #optimize this eventually
                    # can't figure how to get GExiv2 to create save file
                    ex = exif_tool.Metadata()
                    ex.open_path(fs.join(current_app.config['UPLOAD_FOLDER'], filename))
                    ex.clear()
                    ex.save_file(fs.join(current_app.config['UPLOAD_FOLDER'], filename))
                m=Image()
                m.uuid=uuid
                m.filename=filename
                m.original_filename=original_name
                m.uploader_id=g.user.id
                i.images.append(m)
                db.session.add(m)
                db.session.commit()
                flash('File uploaded')
        flash('Issue opened')
        msg = Message('New issue', recipients=[i.landlord.email])
        msg.body = new_issue_email(i)
        mail.send(msg)
        logger.info('mail sent: {0}'.format(msg))
        flash('Landlord notified')
        return redirect_xhr_or_normal('.issues')
    return render_xhr_or_normal('open_issue.html', form=form)

# MUST BE CONFIRMED
@fee.route('/issues/<int(min=1):ident>/comment', methods=['POST'])
@login_required
def comment(ident):
    '''comment on issue
        params:     POST: <comment> comment text
                    POST: <ident> absolute id
        returns:    POST: Redirect to main issues page
    '''
    form = CommentForm()
    issue=g.user.all_issues().\
            filter(Issue.status=='Open',Issue.id==ident).first()
    if not issue:
        flash('No issue')
        return redirect_xhr_or_normal('issue.issues')
    if g.user != issue.landlord:
        if not getattr(g.user.landlords.filter(LandlordTenant.current==True).first(),'confirmed', None):
            flash('Need to be confirmed')
            return redirect_xhr_or_normal('profile.profile')
    if form.validate_on_submit():
        d=request.form['comment']
        comment=Comment(text=d, user_id=g.user.id)
        issue.comments.append(comment)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added')
        return redirect_xhr_or_normal('issue.show_issue', ident=ident)
    else:
        flash('Bad input')
        return redirect_xhr_or_normal('issue.show_issue', ident=ident)

@fee.route('/issues/<int(min=1):ident>/close', methods=['GET', 'POST'])
@login_required
def close_issue(ident):
    '''close issue - only opener or landlord can
        params:     POST: <reason> reason (to close issue)
                    POST: <ident> absolute id
        returns:    POST: Redirect to main issues page
    '''
    issue=Issue.query.filter(or_(Issue.landlord_id==g.user.id,
                Issue.creator_id==g.user.id),
                Issue.status == 'Open',
                Issue.id == ident).first()
    form=CloseIssueForm()
    if not issue:
        flash('Issue closed')
        return redirect_xhr_or_normal('.issues')
    if form.validate_on_submit():
        reason=request.form['reason']
        issue.status='Closed'
        issue.closed_because=reason
        db.session.add(issue)
        db.session.commit()
        flash('Issue closed')
        return redirect_xhr_or_normal('.issues')
    return render_xhr_or_normal('close_issue.html', close=form, issue=issue)

@fee.route('/issues/<int(min=1):ident>/provider', methods=['GET', 'POST'])
@login_required
def authorize_provider(ident):
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
    ps = [(str(prov.id), prov.name) for prov in g.user.providers if prov.service == issue.area]
    if not ps:
        flash('No relevant providers')
        return redirect_xhr_or_normal('property.add_provider')
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
        return redirect_xhr_or_normal('.show_issue', ident=ident)
    return render_xhr_or_normal('select_issue_provider.html', issue=issue, form=form)
#### /ISSUES ####

__all__=['issue']
