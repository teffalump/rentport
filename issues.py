#!/usr/bin/env python2

import model
import config
import web

urls = (
    '/close/(\d+)', "close_issue",
    '/post', 'post_issue',
    '/list/?', "list_issues",
    '/(\d+)', "issue",
    '/?', "redirect_issues"
    )

render = web.template.render('templates')

class redirect_issues:
    def GET(self):
        if web.ctx.session.login == True:
            raise web.seeother('/list/')
        else:
            raise web.seeother('/'.join([config.site.base, 'login']))

class list_issues:
    def GET(self):
        if web.ctx.session.login == True:
            issues = model.get_issues(web.ctx.session.id)
            return render.list_issues(issues)
        else:
            raise web.seeother('/'.join([config.site.base, 'login']))

class close_issue:
    @csrf_protected
    def POST(self, num):
        if web.ctx.session.login == True:
            x = web.input()
            if model.close_issue(web.ctx.session.id, num, reason=x.reason) == True:
                return 'issue closed'
            else:
                return web.unauthorized()
        else:
            raise web.seeother(config.site.base)

class issue:
    def GET(self,num):
        if web.ctx.session.login == True:
            issue = model.get_issues(web.ctx.session.id, start=num, limit=1)
            comments = model.get_comments(web.ctx.session.id, start=num, limit=1)
            return render.issue(issue, comments)
        else:
            raise web.seeother('/'.join([config.site.base, 'login']))

    @csrf_protected
    def POST(self,num):
        if web.ctx.session.login == True:
            x = web.input()
            try:
                if model.comment_on_issue(web.ctx.session.id, num, x.comment) == True:
                    return 'comment accepted'
            except:
                raise web.badrequest()
        else:
            raise web.seeother('/'.join([config.site.base, 'login']))

class post_issue:
    @csrf_protected
    def POST(self):
        if web.ctx.session.login == True:
            x = web.input()
            try:
                if model.open_issue(web.ctx.session.id, x.severity, x.description) == True:
                    return 'issue posted'
            except:
                raise web.badrequest()
        else:
            raise web.seeother(config.site.base)

issues_app = web.application(urls, locals())
