from rentport.common.extensions import db, mail
from rentport.common.forms import OpenIssueForm, CloseIssueForm, CommentForm
from rentport.common.model import (Issue, LandlordTenant, Comment,
                                WorkOrder, Provider, Image)
from flask.ext.mail import Message
from flask.ext.security import login_required
from flask import Blueprint, request, g, url_for, flash, current_app
from sqlalchemy import or_
from werkzeug import secure_filename
from sys import exc_info as er
from os import path as fs
from uuid import uuid4
from rentport.common.utils import (redirect_xhr_or_normal,
                        render_xhr_or_normal, allowed_file)
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
#### /EMAIL STRINGS ####

#### Blueprint ####
issue = Blueprint('issue', __name__, template_folder = '../templates/issue', static_folder='static')
#### /Blueprint ####

#### ISSUES ####
@issue.route('/issues', defaults={'page':1, 'per_page':current_app.config['ISSUES_PER_PAGE']}, methods=['GET'])
@issue.route('/issues/<int(min=1):page>', defaults={'per_page':current_app.config['ISSUES_PER_PAGE']}, methods=['GET'])
@issue.route('/issues/<int(min=1):page>/<int(min=1):per_page>', methods=['GET'])
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
            'status': Issue.status,
            'type': Issue.area}
    sort_key=request.args.get('sort', 'id') #Default to id
    sort = allowed_sort.get(sort_key, Issue.id)
    order_key = request.args.get('order') #Default to descending
    if order_key == 'asc':
        issues=g.user.all_issues().order_by(sort.asc()).\
                paginate(page, per_page, False)
    else:
        order_key='desc'
        issues=g.user.all_issues().order_by(sort.desc()).\
                paginate(page, per_page, False)
    return render_xhr_or_normal('issues.html', issues=issues, sort=sort_key, order=order_key)

@issue.route('/issues/<int(min=1):ident>/show', methods=['GET'])
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
    contractor = Provider.query.join(WorkOrder).\
            filter(WorkOrder.issue == issue).first()
    if g.user.id == issue.landlord_id:
        close=CloseIssueForm()
        comment=CommentForm()
        if contractor is None:
            provider = ('Select provider',
                            url_for('provider.select_provider',
                                ident=issue.id))
        else:
            provider = ('View provider info',
                            url_for('provider.show_providers',
                                prov_id=contractor.id))
    else:
        if contractor is None:
            provider = ('No selected provider', None)
        else:
            provider = (contractor.name,
                            url_for('provider.show_providers',
                                prov_id=contractor.id))

    if issue.status == 'Closed':
        return render_xhr_or_normal('show_issue.html', issue=issue,
                                            comment=None,
                                            close=None,
                                            provider=provider)
    if getattr(g.user.landlords.filter(LandlordTenant.current==True).\
            first(), 'confirmed', None):
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
@issue.route('/issues/open', methods=['POST', 'GET'])
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
                    ex.open_path(fs.join(current_app.config['UPLOAD_FOLDER'],
                            filename))
                    ex.clear()
                    ex.save_file(fs.join(current_app.config['UPLOAD_FOLDER'],
                            filename))
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
@issue.route('/issues/<int(min=1):ident>/comment', methods=['POST'])
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
            return redirect_xhr_or_normal('profile.show_profile')
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

@issue.route('/issues/<int(min=1):ident>/close', methods=['GET', 'POST'])
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
#### /ISSUES ####

__all__=['issue']
