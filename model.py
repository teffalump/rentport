from .extensions import db
from datetime import datetime, timedelta
from flask.ext.security import UserMixin, RoleMixin
from flask.ext.sqlalchemy import BaseQuery
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy_utils.types import TSVectorType
from sqlalchemy_searchable import SearchQueryMixin, make_searchable
from sqlalchemy import or_

make_searchable()

#### Created data types ####
issue_area = db.Enum('Plumbing', 'Electrical', 'Heating/Air Conditioning', 'Cleaning', 'Other', name="issue_area")
issue_severity=db.Enum('Future', 'Low', 'Medium', 'Critical', name='issue_severity')
issue_status = db.Enum('Open', 'Closed', name='issue_status')
payment_status = db.Enum('Pending', 'Confirmed', 'Refunded', 'Denied', name='payment_status')
payment_method = db.Enum('Dwolla', 'Stripe', name='payment_method')
notification_method = db.Enum('Email', 'Text', 'All', 'None', name='notification_method')
rating_level = db.Enum('1','2','3','4','5', name='rating_level')
#### MODELS ####
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

provs_props = db.Table('providers_properties',
        db.Column('provider_id', db.Integer(), db.ForeignKey('provider.id')),
        db.Column('property_id', db.Integer(), db.ForeignKey('property.id')))

class Role(db.Model, RoleMixin):
    '''Roles'''
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    active = db.Column(db.Boolean)
    paid_through = db.Column(db.DateTime, nullable=False, default=datetime.min)
    phone = db.Column(db.Text, unique=True)
    phone_confirmed = db.Column(db.Boolean, default=False)

    notify_confirmed = db.Column(db.Boolean, default=False)
    notify_method = db.Column(notification_method, default='Email')

    last_login_at=db.Column(db.DateTime)
    current_login_at=db.Column(db.DateTime)
    last_login_ip=db.Column(INET)
    current_login_ip=db.Column(INET)
    login_count=db.Column(db.Integer)

    roles = db.relationship('Role',secondary=roles_users,backref=db.backref('users', lazy='dynamic'))
    tenants = db.relationship('LandlordTenant',
                                backref=db.backref('landlord', lazy='joined'),
                                primaryjoin='LandlordTenant.landlord_id==User.id',
                                lazy='dynamic')
    landlords = db.relationship('LandlordTenant',
                                backref=db.backref('tenant', lazy='joined'),
                                primaryjoin='LandlordTenant.tenant_id==User.id',
                                lazy='dynamic')

    def __repr__(self):
        return '<User %r %r>' % (self.username, self.email)

    def fee_paid(self):
        '''Check if fee payment is current'''
        return self.paid_through >= datetime.utcnow()

    def all_issues(self):
        '''Return all issues at current location and user's properties'''
        return Issue.query.join(Property.issues).\
            filter(or_(Issue.landlord_id==self.id,
                Property.id==\
                        getattr(self.current_location(),'id', -1)))

    def open_issue(self):
        '''Open an issue with pre-filled fields'''
        try:
            return Issue(creator_id=self.id,
                        location_id=self.current_location().id,
                        landlord_id=self.current_landlord().id)
        except:
            return None

    def current_location(self):
        '''Return user's current location else None'''
        return getattr(self.landlords.filter(LandlordTenant.current==True).first(), 'location', None)
 
    def current_landlord(self):
        '''Return user's current landlord else None'''
        return getattr(self.landlords.filter(LandlordTenant.current==True,
                                            LandlordTenant.confirmed==True).first(), 'landlord', None)

    def current_location_issues(self):
        '''Return issues at user's current rental location'''
        return Issue.query.join(Property.issues).\
                join(LandlordTenant, LandlordTenant.location_id==Property.id).\
                filter(LandlordTenant.tenant_id==self.id,
                        LandlordTenant.current==True).\
                order_by(Issue.id.desc())

    def prev_location_issues(self):
        '''Return issues at user's previous residence(s);
            issues must be opened during user duration'''
        return Issue.query.join(Property.issues).\
                join(LandlordTenant, LandlordTenant.location_id==Property.id).\
                    filter(LandlordTenant.tenant_id==self.id,
                            LandlordTenant.current==False).\
                    filter((LandlordTenant.started < Issue.opened),
                            (Issue.opened < LandlordTenant.stopped)).\
                    order_by(Issue.id.desc())

    def current_tenants(self):
        '''Return user's current tenants'''
        return User.query.join(User.landlords).\
                filter(LandlordTenant.landlord_id==self.id, LandlordTenant.current == True)

    def fellow_tenants(self):
        '''Return user's fellow tenants'''
        try:
            return self.current_location().current_tenants().filter(User.id != self.id)
        except:
            return None

    def unconfirmed_tenants(self):
        return User.query.join(User.landlords).\
                filter(LandlordTenant.landlord_id==self.id,
                        LandlordTenant.current==True,
                        LandlordTenant.confirmed==False)

    def unconfirmed_requests(self):
        return User.query.join(User.landlords).\
                filter(LandlordTenant.tenant_id==self.id,
                        LandlordTenant.current==True,
                        LandlordTenant.confirmed==False)

    def payments(self):
        '''Return all relevant payments'''
        return Payment.query.filter(or_(Payment.from_user_id == self.id,
                        Payment.to_user_id == self.id))

class LandlordTenant(db.Model):
    '''Class to model Landlord-Tenant relationships'''
    id = db.Column(db.Integer, primary_key=True)
    landlord_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    current = db.Column(db.Boolean, default=True, nullable=False)

    confirmed = db.Column(db.Boolean, default=False, nullable=False)

    started = db.Column(db.DateTime, default=datetime.utcnow)
    stopped = db.Column(db.DateTime)

    location = db.relationship("Property", backref=db.backref("assocs", lazy='dynamic'), foreign_keys="LandlordTenant.location_id")

    __table_args__=(db.Index('only_one_current_landlord',
            landlord_id,
            tenant_id,
            postgresql_where=current,
            unique=True),)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    apt_number=db.Column(db.Integer)
    description = db.Column(db.Text)
    owner = db.relationship("User", backref=db.backref('properties', order_by=id, lazy='dynamic'))
    address = db.relationship("Address", backref=db.backref('properties', lazy='dynamic'), foreign_keys="Property.address_id")
    providers = db.relationship("Provider", secondary=provs_props, backref="properties")

    def current_tenants(self):
        return User.query.join(User.landlords).\
                filter(LandlordTenant.current == True,
                        LandlordTenant.location_id == self.id)

    def prev_tenants(self):
        return User.query.join(User.landlords).\
                filter(LandlordTenant.location_id == self.id,
                        LandlordTenant.current == False)

    def all_tenants(self):
        return User.query.join(User.landlords).\
                filter(LandlordTenant.location_id == self.id)

    def __init__(self, description, apt_number=None):
        self.apt_number=apt_number
        self.description=description

    def __repr__(self):
        return '<Property %r %r >' % (self.apt_number, self.description)

class StripeUserInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    user_acct = db.Column(db.Text, nullable=False)
    pub_key = db.Column(db.Text, nullable=False)
    retrieved = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship("User", backref=db.backref('stripe', uselist=False), uselist=False)

class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    paid_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    length = db.Column(db.Interval, nullable=False, default=timedelta(days=365))
    status = db.Column(payment_status, nullable=False, default='Pending')
    method = db.Column(payment_method, nullable=False, default='Stripe')
    pay_id = db.Column(db.Text, nullable=False)
    user = db.relationship("User", backref=db.backref("fees", lazy='dynamic', order_by=id))

class StripeEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paid_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event = db.Column(db.Text, nullable=False)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    pay_id = db.Column(db.Text, nullable=False, unique=True)
    method = db.Column(payment_method, nullable=False, default='Stripe')
    status = db.Column(payment_status, nullable=False, default='Pending')
    from_user=db.relationship("User", backref=db.backref("sent_payments", lazy='dynamic'), foreign_keys="Payment.from_user_id")
    to_user=db.relationship("User", backref=db.backref("rec_payments", lazy='dynamic'), foreign_keys="Payment.to_user_id")

class CommentQuery(BaseQuery, SearchQueryMixin):
    pass

class Comment(db.Model):
    query_class = CommentQuery
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    search_vector = db.Column(TSVectorType('text'))
    user = db.relationship("User", backref=db.backref('comments', lazy='dynamic'),  foreign_keys="Comment.user_id")
    issue = db.relationship("Issue", backref=db.backref('comments', lazy='dynamic'), foreign_keys="Comment.issue_id")

    def __repr__(self):
        return '<Comment %r %r >' % (self.text, self.posted)

class IssueQuery(BaseQuery, SearchQueryMixin):
    pass

class Issue(db.Model):
    query_class = IssueQuery
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    landlord_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    area = db.Column(issue_area, nullable=False)
    severity = db.Column(issue_severity, nullable=False)
    status = db.Column(issue_status, nullable=False, default='Open')
    opened = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    closed_because = db.Column(db.Text)
    search_vector = db.Column(TSVectorType('description'))
    creator = db.relationship("User", backref=db.backref('issues_opened', lazy='dynamic'), foreign_keys="Issue.creator_id")
    landlord = db.relationship("User", backref=db.backref('owner_issues', lazy='dynamic', order_by=id), foreign_keys="Issue.landlord_id")
    location = db.relationship("Property", backref=db.backref('issues', lazy='dynamic'), foreign_keys="Issue.location_id")

    def num_of_comments(self):
        return self.comments.count()

    def __repr__(self):
        return '<Issue %r %r %r >' % (self.status, self.severity, self.area)

class Image(db.Model):
    uuid = db.Column(db.Text, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename=db.Column(db.Text, nullable=False)
    original_filename=db.Column(db.Text, nullable=False)
    issue = db.relationship("Issue", backref=db.backref('images', lazy='dynamic'), foreign_keys='Image.issue_id')
    uploader = db.relationship("User", backref=db.backref('images', lazy='dynamic'), foreign_keys='Image.uploader_id')

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat=db.Column(db.Float, nullable=False)
    lon=db.Column(db.Float, nullable=False)
    number=db.Column(db.Integer)
    street=db.Column(db.Text)
    neighborhood=db.Column(db.Text)
    city=db.Column(db.Text)
    county=db.Column(db.Text)
    state=db.Column(db.Text)
    postcode=db.Column(db.Text)
    country=db.Column(db.Text)

class Provider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service = db.Column(issue_area, nullable=False)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    phone = db.Column(db.Text)
    website = db.Column(db.Text)
    by_user = db.relationship("User", backref=db.backref('providers', lazy='dynamic'))

class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(rating_level)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('provider.id'), nullable=False)
    issue = db.relationship("Issue", backref=db.backref('work_orders', lazy='dynamic'), foreign_keys='WorkOrder.issue_id')
    provider = db.relationship("Provider", backref=db.backref('work_orders', lazy='dynamic'), foreign_keys='WorkOrder.provider_id')

    __table_args__=(db.Index('one_order_per_provider_per_issue',
            issue_id,
            provider_id,
            unique=True),)
#### /MODELS ####

#### LISTENERS ####
@db.event.listens_for(Issue.status, 'set')
def set_stopped_value(target, value, old_value, initiator):
    '''This listener will update the closed_at column;
    when status set to False; closed_at set to now'''
    if value == 'Closed':
        target.closed_at = datetime.utcnow()

@db.event.listens_for(LandlordTenant.current, 'set')
def set_stopped_value(target, value, old_value, initiator):
    '''This listener will update the stopped column;
    when current set to False, stopped set to now'''
    if value == False:
        target.stopped = datetime.utcnow()
#### /LISTENERS ####
