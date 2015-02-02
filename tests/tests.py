from rentport import create_app
from rentport.config import TestConfig
from rentport.common.model import User, Property, LandlordTenant, Role, Fee, Payment, Issue
from rentport.common.extensions import mail, db, security, bootstrap, kvsession, limiter
from flask import g
from flask.ext.security.utils import encrypt_password
from flask.ext.testing import TestCase
import datetime
import unittest


class MyTests(TestCase):
    #render_templates = False

    def create_app(self):
        return create_app(TestConfig)

    def setUp(self):
        db.create_all()

    def add_users(self):
        l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                confirmed_at=datetime.datetime.utcnow(), active=True)
        t= User(email='t@example.net', password=encrypt_password('password'), username='t',
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(t)
        db.session.add(l)
        db.session.commit()
        return l,t

    def add_tenant_and_landlord(self):
        l,t=self.add_users()
        self.login('l', 'password')
        self.add_property()
        lt=LandlordTenant(location_id=1, confirmed=True)
        lt.tenant=t
        l.tenants.append(lt)
        db.session.add(lt)
        db.session.commit()
        self.logout()
        return l,t

    def add_property(self):
        return self.client.post('/landlord/property/add', data=dict(
                        address='1 Market St',
                        city='San Francisco',
                        state='California', description='home'),
                        follow_redirects=True)

    def open_issue(self):
        return self.client.post('/issues/open', data=dict(severity='Critical',
                        description='blar', type="Plumbing"), follow_redirects=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_register_user(self):
        m = self.client.post('/register', data=dict(email='teou@example.com',
                password='password', username='test', password_confirm='password'),
                follow_redirects=True)

        u = User.query.first()

        self.assertTemplateUsed('home.html')
        self.assert200(m)
        self.assertEqual(u.id,1)
        self.assertEqual(u.email,'teou@example.com')
        self.assertEqual(u.username,'test')
        self.assertEqual(u.notify_confirmed,True)

    def test_add_property(self):
        l,t = self.add_users()

        self.login('l', 'password')
        r = self.add_property()
        self.assertTemplateUsed('properties.html')
        self.assertIn('Property added', str(r.data))
        self.assertEqual(l.properties.first().id, 1)
        self.assertEqual(l.properties.first().owner, l)
        self.assertEqual(l.properties.first().owner_id, l.id)
        self.assertEqual(l.properties.first().description, 'home')

    def test_modify_property(self):
        l,t = self.add_users()

        self.login('l', 'password')
        r = self.add_property()
        r = self.client.post('/landlord/property/1/modify', data=dict(
                       description='blar_new'), follow_redirects=True)
        self.assertTemplateUsed('properties.html')
        self.assertIn('Property modified', str(r.data))
        self.assertEqual(l.properties.first().description, 'blar_new')

    def test_add_tenant(self):
        l,t=self.add_users()
        self.login('l', 'password')
        self.add_property()
        r = self.client.post('/tenant/add', data=dict(
                    apt='1', user='t'), follow_redirects=True)
        self.assert200(r)
        self.assertEqual(l.current_tenants()[0], t)
        self.assertEqual(l.tenants[0].confirmed, False)
        self.assertIn('Invited tenant', str(r.data))
        #self.assertEqual(t.current_landlord(), l)
        #self.assertEqual(t.current_location().id, 1)
        self.logout()

        #self.login('l', 'password')
        #k = self.client.post('/tenant/t/confirm', data=dict(disallow='True'),
                #follow_redirects=True)

        #self.assertTemplateUsed('home.html')
        #self.assertIn('Disallowed tenant', str(k.data))
        #self.assertEqual(l.tenants.first(), None)
        #self.logout()

        #self.login('t', 'password')
        #r = self.client.post('/landlord/l/add', data=dict(
                    #location='1'), follow_redirects=True)
        #self.logout()

        #self.login('l', 'password')
        #k = self.client.post('/tenant/t/confirm', data=dict(confirm='True'),
                #follow_redirects=True)

        #self.assertTemplateUsed('home.html')
        #self.assertIn('Confirmed tenant', str(k.data))
        #self.assertEqual(l.tenants.first().tenant, t)
        #self.assertEqual(l.tenants.first().current, True)
        #self.assertEqual(l.tenants.first().confirmed, True)
        #self.logout()

        #self.login('t', 'password')
        #m = self.client.post('/landlord/end', data=dict(end='True'),
                #follow_redirects=True)
        #self.assertTemplateUsed('home.html')
        #self.assertIn('Ended landlord', str(m.data))
        #self.assertEqual(l.tenants.first().tenant, t)
        #self.assertTrue(l.tenants.first().stopped)
        #self.assertEqual(l.tenants.first().current, False)

    def test_login(self):
        l,t = self.add_users()

        r = self.login('t', 'password')
        self.assert200(r)
        self.assertIn('Rentport allows', str(r.data))
        self.assertTemplateUsed('home.html')

    def test_open_issue(self):
        l,t = self.add_tenant_and_landlord()

        r = self.login('t', 'password')
        self.open_issue()

        self.assertTemplateUsed('issues.html')
        self.assertTrue(t.current_location_issues().all())
        self.assertEqual(t.current_location_issues().first().landlord, l)
        self.assertEqual(l.all_issues().first().landlord, l)
        self.assertEqual(l.all_issues().first().location_id, 1)
        self.assertEqual(t.all_issues().first().description, 'blar')
        self.assertEqual(t.all_issues().first().severity, 'Critical')
        self.assertEqual(t.all_issues().first().status, 'Open')
        self.assertEqual(t.all_issues().first().area, 'Plumbing')
        self.assertEqual(t.all_issues().first().num_of_comments(), 0)

    def test_comment_on_issue(self):
        l,t = self.add_tenant_and_landlord()
        self.login('t', 'password')
        r = self.open_issue()
        r = self.client.post('/issues/1/comment', data=dict(
                comment="this is a comment"), follow_redirects=True)

        self.assertTemplateUsed('show_issue.html')
        self.assertEqual(t.all_issues().first().num_of_comments(), 1)
        self.assertEqual(t.all_issues().first().comments.first().text, 'this is a comment')
        self.assertEqual(t.all_issues().first().comments.first().user, t)

    #def test_close_issue(self):
        #l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                #paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                #confirmed_at=datetime.datetime.utcnow(), active=True)
        #t= User(email='t@example.net', password=encrypt_password('password'), username='t',
                #confirmed_at=datetime.datetime.utcnow(), active=True)
        #m= User(email='m@example.net', password=encrypt_password('password'), username='m',
                #confirmed_at=datetime.datetime.utcnow(), active=True)
        #db.session.add(t)
        #db.session.add(m)
        #db.session.add(l)
        #db.session.commit()

        #self.assertTrue(l.fee_paid())

        #h=Property(location='place_1', description='blar')
        #l.properties.append(h)
        #db.session.add(h)
        #db.session.commit()

        #lt=LandlordTenant(location=h, confirmed=True)
        #lt.tenant=t
        #l.tenants.append(lt)
        #db.session.add(lt)
        #db.session.commit()

        #self.login('t', 'password')
        #r = self.client.post('/issues/open', data=dict(severity='Critical',
                        #description='blar', type="Plumbing"), follow_redirects=True)
        #self.logout()

        #self.login('m', 'password')
        #r = self.client.post('/issues/1/close', data=dict(
                        #reason='needed to'), follow_redirects=True)
        #self.assertIn('No close-able issue with that id', str(r.data))
        #self.logout()

        #self.login('l', 'password')
        #r = self.client.post('/issues/1/close', data=dict(
                        #reason='needed to'), follow_redirects=True)

        #self.assertTemplateUsed('issues.html')
        #self.assertEqual(t.all_issues().first().status, 'Closed')
        #self.assertEqual(t.all_issues().first().closed_because, 'needed to')

    #def oauth_authorize(self):
        #l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                #paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                #confirmed_at=datetime.datetime.utcnow(), active=True)
        #db.session.add(l)
        #db.session.commit()

        #self.login('l', 'password')
        #r = self.client.get('/oauth/authorize', follow_redirects=True)
        #print(str(r.data))

    #def test_add_phone(self):
        #l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                #paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                #confirmed_at=datetime.datetime.utcnow(), active=True)
        #db.session.add(l)
        #db.session.commit()

        #self.login('l', 'password')
        #r = self.client.post('/profile/phone', data=dict(phone='aaaaaaaaaaaaaaaaaaaa', country='1'),
            #follow_redirects=True)
        #self.assertIn('Invalid number', str(r.data))
        #self.assertTemplateUsed('profile.html')

        #r = self.client.post('/profile/phone', data=dict(phone='1111', country='9'),
            #follow_redirects=True)
        #self.assertIn('Field must', str(r.data))
        #self.assertTemplateUsed('profile.html')

        #r = self.client.post('/profile/phone', data=dict(phone='11111111111111', country='a'),
            #follow_redirects=True)
        #self.assertIn('Not a valid choice', str(r.data))
        #self.assertTemplateUsed('profile.html')

        #r = self.client.post('/profile/phone', data=dict(phone='1111111111', country='1'),
            #follow_redirects=True)

        #self.assertIn('Validation text sent', str(r.data))
        #self.assertTemplateUsed('profile.html')
        #self.assertEqual(l.phone, '11111111111')
        #self.assertEqual(l.phone_confirmed, False)

    #def test_send_payment(self):
        #pass

    def login(self, username, password):
        return self.client.post('/login', data=dict(
                email=username,
                password=password
            ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout')

__all__=['MyTests']

if __name__=='__main__':
    unittest.main()
