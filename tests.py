from . import create_app
from .config import TestConfig
from .model import User, Property, LandlordTenant, Role, Fee, Payment, Issue
from .extensions import mail, db, security, bootstrap, kvsession, limiter
import datetime
from flask.ext.security.utils import encrypt_password
from flask.ext.testing import TestCase


class MyTests(TestCase):
    #render_templates = False

    def create_app(self):
        return create_app(TestConfig)

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_register_user(self):
        m = self.client.post('/register', data=dict(email='teou@example.com',
                password='password', username='test', password_confirm='password'),
                follow_redirects=True)

        u = User.query.first()

        self.assertTemplateUsed('home.html')
        self.assertIn('Confirmation', str(m.data))
        self.assert200(m)
        self.assertEqual(u.id,1)
        self.assertEqual(u.email,'teou@example.com')
        self.assertEqual(u.username,'test')
        self.assertEqual(u.notify_confirmed,False)

    def test_add_property(self):
        l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(l)
        db.session.commit()

        self.login('l', 'password')
        r = self.client.post('/landlord/property/add', data=dict(
            location='place_1', description='blar'), follow_redirects=True)

        self.assertTemplateUsed('properties.html')
        self.assertIn('Property added', str(r.data))
        self.assertEqual(l.properties.first().id, 1)
        self.assertEqual(l.properties.first().owner, l)
        self.assertEqual(l.properties.first().owner_id, l.id)
        self.assertEqual(l.properties.first().location, 'place_1')
        self.assertEqual(l.properties.first().description, 'blar')

    def test_modify_property(self):
        l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(l)
        db.session.commit()

        self.login('l', 'password')
        r = self.client.post('/landlord/property/add', data=dict(
            location='place_1', description='blar'), follow_redirects=True)
        r = self.client.post('/landlord/property/1/modify', data=dict(
            location='place_new1', description='blar_new'), follow_redirects=True)
        self.assertTemplateUsed('properties.html')
        self.assertIn('Property modified', str(r.data))
        self.assertEqual(l.properties.first().location, 'place_new1')
        self.assertEqual(l.properties.first().description, 'blar_new')

    def test_relationship(self):
        t = User(email='t@example.net', password=encrypt_password('password'), username='t',
                confirmed_at=datetime.datetime.utcnow(), active=True)
        l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(t)
        db.session.add(l)
        db.session.commit()

        h=Property(location='place_1', description='blar')
        l.properties.append(h)
        db.session.add(h)
        db.session.commit()

        self.login('t', 'password')
        r = self.client.post('/landlord/l/add', data=dict(
                    location='1'), follow_redirects=True)
        self.assert200(r)
        self.assertIn('Added landlord', str(r.data))
        self.assertEqual(t.current_landlord(), l)
        self.assertEqual(t.current_location(), h)
        self.assertEqual(l.properties[0], h)
        self.assertEqual(l.current_tenants()[0], t)
        self.logout()

        self.login('l', 'password')
        k = self.client.post('/tenant/t/confirm', data=dict(disallow='True'),
                follow_redirects=True)

        self.assertTemplateUsed('home.html')
        self.assertIn('Disallowed tenant', str(k.data))
        self.assertEqual(l.tenants.first(), None)
        self.logout()

        self.login('t', 'password')
        r = self.client.post('/landlord/l/add', data=dict(
                    location='1'), follow_redirects=True)
        self.logout()

        self.login('l', 'password')
        k = self.client.post('/tenant/t/confirm', data=dict(confirm='True'),
                follow_redirects=True)

        self.assertTemplateUsed('home.html')
        self.assertIn('Confirmed tenant', str(k.data))
        self.assertEqual(l.tenants.first().tenant, t)
        self.assertEqual(l.tenants.first().current, True)
        self.assertEqual(l.tenants.first().confirmed, True)
        self.logout()

        self.login('t', 'password')
        m = self.client.post('/landlord/end', data=dict(end='True'),
                follow_redirects=True)
        self.assertTemplateUsed('home.html')
        self.assertIn('Ended landlord', str(m.data))
        self.assertEqual(l.tenants.first().tenant, t)
        self.assertTrue(l.tenants.first().stopped)
        self.assertEqual(l.tenants.first().current, False)

    def test_login_logout(self):
        t = User(email='t@example.net', password=encrypt_password('password'), username='t',
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(t)
        db.session.commit()

        r = self.login('t', 'password')
        self.assert200(r)
        self.assertIn('Rentport allows you to handle', str(r.data))
        self.assertTemplateUsed('home.html')

        r = self.logout()

        #since TESTING is enabled, login_required is disabled
        self.assert200(r)
        self.assertIn('Rentport allows you to handle', str(r.data))
        self.assertTemplateUsed('home.html')

    def test_open_issue(self):
        l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                confirmed_at=datetime.datetime.utcnow(), active=True)
        t= User(email='t@example.net', password=encrypt_password('password'), username='t',
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(t)
        db.session.add(l)
        db.session.commit()

        self.assertTrue(l.fee_paid())

        h=Property(location='place_1', description='blar')
        l.properties.append(h)
        db.session.add(h)
        db.session.commit()

        lt=LandlordTenant(location=h, confirmed=True)
        lt.tenant=t
        l.tenants.append(lt)
        db.session.add(lt)
        db.session.commit()

        self.login('t', 'password')
        r = self.client.post('/issues/open', data=dict(severity='Critical',
                        description='blar', type="Plumbing"), follow_redirects=True)

        self.assertTemplateUsed('issues.html')
        self.assertTrue(t.current_location_issues().all())
        self.assertEqual(t.current_location_issues().first().landlord, l)
        self.assertEqual(l.all_issues().first().landlord, l)
        self.assertEqual(l.all_issues().first().location, h)
        self.assertEqual(t.all_issues().first().description, 'blar')
        self.assertEqual(t.all_issues().first().severity, 'Critical')
        self.assertEqual(t.all_issues().first().status, 'Open')
        self.assertEqual(t.all_issues().first().num_of_comments(), 0)

    def test_comment_on_issue(self):
        l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                confirmed_at=datetime.datetime.utcnow(), active=True)
        t= User(email='t@example.net', password=encrypt_password('password'), username='t',
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(t)
        db.session.add(l)
        db.session.commit()

        self.assertTrue(l.fee_paid())

        h=Property(location='place_1', description='blar')
        l.properties.append(h)
        db.session.add(h)
        db.session.commit()

        lt=LandlordTenant(location=h, confirmed=True)
        lt.tenant=t
        l.tenants.append(lt)
        db.session.add(lt)
        db.session.commit()

        self.login('t', 'password')
        r = self.client.post('/issues/open', data=dict(severity='Critical',
                        description='blar', type="Plumbing"), follow_redirects=True)

        k = self.client.post('/issues/1/comment', data=dict(
                comment="this is a comment"), follow_redirects=True)

        self.assertTemplateUsed('show_issue.html')
        self.assertEqual(t.all_issues().first().num_of_comments(), 1)
        self.assertEqual(t.all_issues().first().comments.first().text, 'this is a comment')
        self.assertEqual(t.all_issues().first().comments.first().user, t)

    def test_close_issue(self):
        l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                confirmed_at=datetime.datetime.utcnow(), active=True)
        t= User(email='t@example.net', password=encrypt_password('password'), username='t',
                confirmed_at=datetime.datetime.utcnow(), active=True)
        m= User(email='m@example.net', password=encrypt_password('password'), username='m',
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(t)
        db.session.add(m)
        db.session.add(l)
        db.session.commit()

        self.assertTrue(l.fee_paid())

        h=Property(location='place_1', description='blar')
        l.properties.append(h)
        db.session.add(h)
        db.session.commit()

        lt=LandlordTenant(location=h, confirmed=True)
        lt.tenant=t
        l.tenants.append(lt)
        db.session.add(lt)
        db.session.commit()

        self.login('t', 'password')
        r = self.client.post('/issues/open', data=dict(severity='Critical',
                        description='blar', type="Plumbing"), follow_redirects=True)
        self.logout()

        self.login('m', 'password')
        r = self.client.post('/issues/1/close', data=dict(
                        reason='needed to'), follow_redirects=True)
        self.assertIn('No close-able issue with that id', str(r.data))
        self.logout()

        self.login('l', 'password')
        r = self.client.post('/issues/1/close', data=dict(
                        reason='needed to'), follow_redirects=True)

        self.assertTemplateUsed('issues.html')
        self.assertEqual(t.all_issues().first().status, 'Closed')
        self.assertEqual(t.all_issues().first().closed_because, 'needed to')

    def oauth_authorize(self):
        l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(l)
        db.session.commit()

        self.login('l', 'password')
        r = self.client.get('/oauth/authorize', follow_redirects=True)
        print(str(r.data))

    def test_add_phone(self):
        l= User(email='l@example.net', password=encrypt_password('password'), username='l',
                paid_through=datetime.datetime.utcnow() + datetime.timedelta(weeks=52),
                confirmed_at=datetime.datetime.utcnow(), active=True)
        db.session.add(l)
        db.session.commit()

        self.login('l', 'password')
        r = self.client.post('/profile/phone', data=dict(phone='aaaaaaaaaaaaaaaaaaaa', country='1'),
            follow_redirects=True)
        self.assertIn('Invalid number', str(r.data))
        self.assertTemplateUsed('profile.html')

        r = self.client.post('/profile/phone', data=dict(phone='1111', country='9'),
            follow_redirects=True)
        self.assertIn('Field must', str(r.data))
        self.assertTemplateUsed('profile.html')

        r = self.client.post('/profile/phone', data=dict(phone='11111111111111', country='a'),
            follow_redirects=True)
        self.assertIn('Not a valid choice', str(r.data))
        self.assertTemplateUsed('profile.html')

        r = self.client.post('/profile/phone', data=dict(phone='1111111111', country='1'),
            follow_redirects=True)

        self.assertIn('Validation text sent', str(r.data))
        self.assertTemplateUsed('profile.html')
        self.assertEqual(l.phone, '11111111111')
        self.assertEqual(l.phone_confirmed, False)

    def test_send_payment(self):
        pass

    def login(self, username, password):
        return self.client.post('/login', data=dict(
                email=username,
                password=password
            ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

