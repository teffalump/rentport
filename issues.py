#!/usr/bin/env python2

import model
import config
import web
import sys
from web import form
from uuid import uuid4
from sys import exc_info as error
from json import dumps

urls = (
    '/close/?', "close_issue",
    '/open/?', 'open_issue',
    '/show/?', "show_issues",
    '/comments/?', "get_comments",
    '/respond/?', "post_comment",
    '/?', "issues_home"
    )

def csrf_protected(f):
    def decorated(*args,**kwargs):
        inp = web.input()
        if not (inp.has_key('csrf_token') and inp.csrf_token==web.ctx.session.pop('csrf_token',None)):
            raise web.HTTPError("400 Bad Request",
                    {'content-type': 'text/html'},
                    'Sorry for the inconvenience, but this could be an CSRF attempt, so we blocked it. Fail safely')
        return f(*args,**kwargs)
    return decorated

#Forms
open_issue_form = form.Form(form.Textbox("description"),
                            form.Dropdown("severity",
                                args=['Critical', 'Medium', 'Low', 'Future'],
                                value='Critical'),
                            form.Button("submit", type="submit", html="Open"))

post_comment_form = form.Form(form.Textbox("comment"),
                            form.Button("submit", type="submit", html="Submit"))

render = web.template.render('templates')

class issues_home:
    '''display main issues page'''
    def GET(self):
        if web.ctx.session.login == True:
            issues = model.get_issues(web.ctx.session.id)
            return render.issues(issues)
        else:
            raise web.unauthorized()

class show_issues:
    '''get issues (no comments), except for querying one issue

    param:      id = relative issue id (optional)
                status = issue status (optional, default = Open)
                start = offset to start at (optional, default = 1)
                num = number of issues to return (optional, default = all)

    returns:    no id:
                    creator, owner, description,
                    num of cms, severity, status,
                    location
                w/ id:
                    all the above and comments'''
    def GET(self):
        x=web.input()
        if web.ctx.session.login == True:
            try:
                issue={'general': dict(model.get_issues(web.ctx.session.id, start=x.id, num=1)[0]),
                        'comments': list(model.get_comments(web.ctx.session.id, x.id))}
                return dumps(issue)
            except AttributeError:
                return dumps(list(model.get_issues(web.ctx.session.id, **x)))
            except IndexError:
                return {'error': 'No Issue'}
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

class get_comments:
    '''get comments

    param:      id = relative issue id
                start = offset to start at (optional, default = 1)
                num = number of comments to return (optional, default = all)
                status = issue status to query by (optional, default = 'Open')

    returns:    text, username, posted (time)'''
    def GET(self):
        if web.ctx.session.login == True:
            x = web.input()
            try:
                return dumps(list(model.get_comments(web.ctx.session.id, x.pop('id'), **x)))
            except KeyError:
                raise web.badrequest()
        else:
            raise web.unauthorized()

class post_comment:
    '''post comment

    get params:     id = relative issue id
    post params:    id = relative issue id
                    comment = the comment text

    get returns:    form to upload comment
    post returns:   text, username, issue, posted (time)'''
    def GET(self):
        if web.ctx.session.login == True:
            x=web.input()
            try:
                f = post_comment_form()
                return render.post_comment(f, x.id)
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

    @csrf_protected
    def POST(self):
        if web.ctx.session.login == True:
            x = web.input()
            try:
                a=model.comment_on_issue(web.ctx.session.id, x.id, x.comment)
                a['username']=web.ctx.session.username
                a['issue']=x.id
                return dumps(a)
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

class close_issue:
    '''close issue

    params:     id = relative issue id
                reason = reason to close issue

    returns:    issue, status, closed (time)'''
    #TODO maybe return more things to update
    #TODO Add reason parameter, when that is figured out
    @csrf_protected
    def POST(self):
        if web.ctx.session.login == True:
            x = web.input()
            try:
                return dumps(dict(model.close_issue(web.ctx.session.id, x.id)))
            except:
                raise web.badrequest()
        else:
            raise web.seeother(config.site.base)

class open_issue:
    '''open new issue

    post params:    severity = issue severity
                    description = issue description

    get returns:    form to upload issue
    post returns:   issue (owner, creator, location, description,
                    date opened, severity, status)'''
    def GET(self):
        if web.ctx.session.login == True:
            try:
                f = open_issue_form()
                return render.open_issue(f)
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

    @csrf_protected
    def POST(self):
        if web.ctx.session.login == True:
            x = web.input()
            try:
                #have the info but need to substitute ids for strings
                #maybe possible in one func, but w/e
                a=model.open_issue(web.ctx.session.id, x.severity, x.description)
                b=model.get_current_landlord_info(web.ctx.session.id)
                a['creator']=web.ctx.session.username
                a['location']=b['location']
                a['owner']=b['username']
                return dumps(a)
            except:
                raise web.badrequest()
        else:
            raise web.unauthorized()

issues_app = web.application(urls, locals())
