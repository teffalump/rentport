from .extensions import db, mail
from .forms import (OpenIssueForm, CloseIssueForm,
                        AddLandlordForm, EndLandlordForm, ConfirmTenantForm,
                        CommentForm, AddPropertyForm, ModifyPropertyForm,
                        AddPhoneNumber, ChangeNotifyForm, ResendNotifyForm,
                        AddProviderForm, ConnectProviderForm, SelectProviderForm)
from .model import (Issue, Property, User, LandlordTenant, Comment, WorkOrder,
                        Fee, Payment, StripeUserInfo, Address, Provider, Image)
from flask.ext.mail import Message
from flask.ext.security import login_required
from requests_oauthlib import OAuth2Session
from flask import (Blueprint, render_template, request, g, redirect, url_for,
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
import stripe

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
    email='The landlord has picked a provider. Contact them about fixing the issue - {0}:\n\nName: {1}\n\nEmail: {2}\n\nPhone: {3}\n\nWebsite: {4}'
    t = email.format(
            url_for('.show_issue', ident=work_order.issue.id, _external=True),
            work_order.provider.name,
            work_order.provider.email,
            work_order.provider.phone,
            work_order.provider.website)
    return t
#### /EMAIL STRINGS ####

#### UTILS ####
def get_url(endpoint, **kw):
    '''Return endpoint url, or next arg url'''
    try:
        return request.args['next']
    except:
        return url_for(endpoint, **kw)

def allowed_file(filename):
    return '.' in filename and \
       filename.rsplit('.', 1)[1] in current_app.config['ALLOWED_EXTENSIONS']
#### /UTILS ####

#### Blueprint ####
rp = Blueprint('issue', __name__, template_folder = 'templates/issue', static_folder='static')
#### /Blueprint ####

#### ISSUES ####
@rp.route('/issues', methods=['GET'])
@rp.route('/issues/<int(min=1):page>', methods=['GET'])
@rp.route('/issues/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
@login_required
def issues(page=1, per_page=current_app.config['ISSUES_PER_PAGE']):
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
    return render_template('issues.html', issues=issues, sort=sort_key, order=order_key)

@rp.route('/issues/<int(min=1):ident>/show', methods=['GET'])
@login_required
def show_issue(ident):
    '''show issue
        params:     GET: <ident> absolute id
        returns:    GET: detailed issue page
    '''
    issue=g.user.all_issues().filter(Issue.status=='Open',
                    Issue.id==ident).first()
    comment = None
    close = None
    provider = None
    if not issue:
        flash('No issue with that id')
        return redirect(url_for('.issues'))
    if g.user.id == issue.landlord_id:
        close=CloseIssueForm()
        comment=CommentForm()
        if issue.work_orders.first() is None:
            #ps = [(str(prov.id), prov.name) for prov in issue.location.providers if prov.service == issue.area]
            ps = [(str(prov.id), prov.name) for prov in g.user.providers if prov.service == issue.area]
            if ps:
                provider=SelectProviderForm()
                provider.provider.choices=ps
    if getattr(g.user.landlords.filter(LandlordTenant.current==True).first(), 'confirmed', None):
        comment=CommentForm()
    if issue.creator_id == g.user.id:
        close=CloseIssueForm()
    return render_template('show_issue.html', issue=issue,
                                            comment=comment,
                                            close=close,
                                            provider=provider)

# PAID ENDPOINT
# MUST BE CONFIRMED
# ALERT USER(S)
@rp.route('/issues/open', methods=['POST', 'GET'])
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
        return redirect(url_for('.issues'))
    if not lt.confirmed:
        flash('Need to be confirmed!')
        return redirect(url_for('.issues'))
    if not lt.landlord.fee_paid():
        flash('Landlord needs to pay fee')
        return redirect(url_for('.issues'))
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
        flash('Landlord notified')
        return redirect(url_for('.issues'))
    return render_template('open_issue.html', form=form)

# MUST BE CONFIRMED
@rp.route('/issues/<int(min=1):ident>/comment', methods=['POST'])
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
        return jsonify({'error': 'No issue'})
    if g.user != issue.landlord:
        if not getattr(g.user.landlords.filter(LandlordTenant.current==True).first(),'confirmed', None):
            return jsonify({'error': 'Need to be confirmed by landlord!'})
    if form.validate_on_submit():
        d=request.form['comment']
        comment=Comment(text=d, user_id=g.user.id)
        issue.comments.append(comment)
        db.session.add(comment)
        db.session.commit()
        return jsonify({'success': 'Commented on issue',
                        'comment': comment.text,
                        'time': comment.posted.strftime('%Y/%m/%d'),
                        'username': comment.user.username})
    else:
        return jsonify({'error': 'Invalid input'})

@rp.route('/issues/<int(min=1):ident>/close', methods=['GET', 'POST'])
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
        return jsonify({'error': 'No issue'})
    if form.validate_on_submit():
        reason=request.form['reason']
        issue.status='Closed'
        issue.closed_because=reason
        db.session.add(issue)
        db.session.commit()
        return jsonify({'success': 'Issue closed',
                        'reason': reason})
    return render_template('close_issue.html', close=form, issue=issue)

@rp.route('/issues/<int(min=1):ident>/provider', methods=['GET', 'POST'])
@login_required
def authorize_provider(ident):
    issue=Issue.query.filter(Issue.landlord_id==g.user.id,
                Issue.status == 'Open',
                Issue.id == ident).first()
    if not issue:
        return jsonify({'error': 'No issue'})
    if issue.work_orders.first():
        return jsonify({'error': 'Provider already selected'})
    form=SelectProviderForm()
    #ps = [(str(prov.id), prov.name) for prov in issue.location.providers if prov.service == issue.area]
    ps = [(str(prov.id), prov.name) for prov in g.user.providers if prov.service == issue.area]
    if not ps:
        return jsonify({'error': 'No relevant providers'})
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
        return jsonify({'success': 'Selected provider',
                        'provider': w.provider.name})
    return render_template('select_issue_provider.html', issue=issue, form=form)
#### /ISSUES ####
