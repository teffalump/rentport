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
        if web.ctx.session.login == True and web.ctx.session.category == 'Landlord':
            x = web.input()
            if model.close_issue(web.ctx.session.id, num) == True:
                return 'issue closed'
        else:
            raise web.seeother(config.site.base)

class issue:
    def GET(self,num):
        if web.ctx.session.login == True:
            issue = model.get_issue(web.ctx.session.id, num)
            return render.issue(issue)
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
        if web.ctx.session.login == True and web.ctx.session.category == 'Tenant':
            x = web.input()
            try:
                if model.open_issue(web.ctx.session.id, x.severity, x.description) == True:
                    return 'issue posted'
            except:
                raise web.badrequest()
        else:
            raise web.seeother(config.site.base)

issues_app = web.application(urls, locals())
