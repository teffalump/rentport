### DB MODEL NEED TO INTEGRATE FUNCS #####
from rentport import db
from datetime import datetime
from flask import g
from flask.ext.security import UserMixin, RoleMixin
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.associationproxy import association_proxy

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    accepts_cc = db.Column(db.Boolean, nullable=False, default=False)
    joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
    confirmed_at = db.Column(db.DateTime)
    active = db.Column(db.Boolean)
    roles = db.relationship('Role',secondary=roles_users,backref=db.backref('users', lazy='dynamic'))

    last_login_at=db.Column(db.DateTime)
    current_login_at=db.Column(db.DateTime)
    last_login_ip=db.Column(postgresql.INET)
    current_login_ip=db.Column(postgresql.INET)
    login_count=db.Column(db.Integer)

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

    def open_issue(self):
        if self.current_location != None:
            return Issue(creator_id=self.id,
                        location_id=self.current_location().id)

    def current_location(self):
        return getattr(self.landlords.filter(LandlordTenant.current==True).first(), 'location', None)
 
    def current_landlord(self):
        return getattr(self.landlords.filter(LandlordTenant.current==True).first(), 'landlord', None)

    def current_open_issues(self):
        return self.issues_opened.union(Issue.query.\
                join(self.properties, (self.properties.id==Issue.location_id))).\
                filter(Issue.status=='Open').order_by(Issue.id.desc())


    def current_tenants(self):
        return User.query.join(LandlordTenant, LandlordTenant.tenant_id==User.id).\
                filter(LandlordTenant.landlord_id==self.id, LandlordTenant.current == True).all()

    def fellow_tenants(self):
        return User.query.join(LandlordTenant, LandlordTenant.tenant_id==User.id).\
                filter(LandlordTenant.landlord_id==self.current_landlord().id,
                        LandlordTenant.current==True, User.id != self.id).all()

class LandlordTenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    landlord_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    current = db.Column(db.Boolean, default=True, nullable=False)

    confirmed = db.Column(db.Boolean, default=False, nullable=False)

    started = db.Column(db.DateTime, default=datetime.utcnow())
    stopped = db.Column(db.DateTime)

    location_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    location = db.relationship("Property", backref="assocs", foreign_keys="LandlordTenant.location_id")

    __table_args__=(db.Index('only_one_current_landlord',
            landlord_id,
            tenant_id,
            postgresql_where=current,
            unique=True),)

#TODO Add another listener to update previous relationship to false? Or write func to handle?

@db.event.listens_for(LandlordTenant.current, 'set')
def set_stopped_value(target, value, old_value, initiator):
    if value == False:
        target.stopped = datetime.utcnow()

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)

    owner = db.relationship("User", backref=db.backref('properties', order_by=id))

    def __init__(self, location, description):
        self.location=location
        self.description=description

    def __repr__(self):
        return '<Property %r %r >' % (self.location, self.description)

class Agreement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    #uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    #uploader = db.relationship("User", backref=db.backref('agreements', order_by=id), foreign_keys="agreement.uploader_id")

    #assoc_id = db.Column(db.Integer, db.ForeignKey('landlord_tenant.id'), nullable=True)
    #assoc = db.relationship("LandlordTenant", backref=db.backref('agreements', order_by=id), foreign_keys="agreement.assoc_id")

    file_name = db.Column(db.Text, nullable=False)
    data_type = db.Column(db.Text, nullable=False)
    data = db.Column(db.Text, nullable=False)
    title = db.Column(db.Text)
    description = db.Column(db.Text)
    posted_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())

    def __init__(self, file_name, data_type, data):
        self.file_name=file_name

class FailedLogin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.Text, nullable=False)
    ip = db.Column(postgresql.INET, nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())

class FailedEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.Text, nullable=False)
    ip = db.Column(postgresql.INET, nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())

class SentEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ip = db.Column(postgresql.INET, nullable=False)
    type = db.Column(db.Enum('verify', 'reset', 'issue', 'comment', 'relation', 'payment', name='email_types'), nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
    account = db.relationship("User", backref='sent_emails')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stripe_id = db.Column(db.Text, nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
    from_user = db.relationship("User", backref='sent_payments', order_by=id, foreign_keys="Payment.from_user_id")
    to_user = db.relationship("User", backref='rec_payments', order_by=id, foreign_keys="Payment.to_user_id")

class UserKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    pub_key = db.Column(db.Text, nullable=False)
    sec_key = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    retrieved = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
    user = db.relationship("User", backref='user_keys', order_by=id)

class Code(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.Enum('verify', 'reset', name='code_types'), nullable=False)
    value = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
    user = db.relationship("User", backref='codes')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())

    user = db.relationship("User", backref='comments', order_by=id, foreign_keys="Comment.user_id")
    issue = db.relationship("Issue", backref='comments', order_by=id, foreign_keys="Comment.issue_id")

    def __repr__(self):
        return '<Comment %r %r >' % (self.text, self.posted)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.Enum('Critical', 'Medium', 'Low', 'Future', name='issue_severity'), nullable=False)
    status = db.Column(db.Enum('Open', 'Closed', 'Pending', name='issue_status'), nullable=False, default='Open')
    opened = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
    closed_at = db.Column(db.DateTime)
    closed_because = db.Column(db.Text)

    creator = db.relationship("User", backref='issues_opened', order_by=id, foreign_keys="Issue.creator_id")
    location = db.relationship("Property", backref='issues', order_by=id, foreign_keys="Issue.location_id")

    def __repr__(self):
        return '<Issue %r %r >' % (self.status, self.severity)

@db.event.listens_for(Issue.status, 'set')
def set_stopped_value(target, value, old_value, initiator):
    if value == 'Closed':
        target.closed_at = datetime.utcnow()
