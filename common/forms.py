#### FORMS

from flask import current_app
from flask.ext.wtf import Form
from flask.ext.security.forms import RegisterForm, LoginForm
from wtforms import (SelectField, StringField, SubmitField, TextAreaField,
                HiddenField, FileField, RadioField, SelectField, IntegerField, ValidationError,
                PasswordField)
from wtforms.validators import Length, DataRequired, AnyOf, Regexp, NumberRange, Optional, Email, URL
from flask.ext.wtf.file import FileAllowed, FileField
from werkzeug.local import LocalProxy
from zxcvbn import password_strength


_datastore = LocalProxy(lambda: current_app.extensions['security'].datastore)

def good_enough_password(form, field):
    if password_strength(field.data)['score'] < 4:
        msg = 'Get a better password'
        raise ValidationError(msg)

def unique_user_username(form, field):
    if _datastore.find_user(username=field.data) is not None:
        msg = '{0} is already associated with an account.'.format(field.data)
        raise ValidationError(msg)

def unique_user_email(form, field):
    if _datastore.get_user(field.data) is not None:
        msg = '{} alread associated with an account'.format(field.data)
        raise ValidationError(msg)

class ExtendedRegisterForm(RegisterForm):
    username=StringField('Username', [DataRequired(),
                                    Regexp(r'^\w+$', message="Only alphanumeric characters"),
                                    Length(min=4, max=20),
                                    unique_user_username])
class RegisterForm(Form):
    email=StringField('Email', [DataRequired(), unique_user_email])
    username=StringField('Username', [DataRequired(),
                                    Regexp(r'^\w+$', message="Only alphanumeric characters"),
                                    Length(min=4, max=20),
                                    unique_user_username])
    password=PasswordField('Password', [DataRequired(), good_enough_password])
    submit=SubmitField('Register')

class ChangePasswordForm(Form):
    new_password=PasswordField('New password', [DataRequired(),
                                                good_enough_password])
    submit=SubmitField('Update')

class ExtendedLoginForm(LoginForm):
    email=StringField('Login', [DataRequired()])

class OpenIssueForm(Form):
    severity=SelectField('Severity', choices=[('Critical', 'Critical'),
                                                ('Medium', 'Medium'),
                                                ('Low', 'Low'),
                                                ('Future', 'Future')])
    type=SelectField('Type', choices=[('Plumbing', 'Plumbing'),
                                        ('Electrical', 'Electrical'),
                                        ('Heating/Air Conditioning', 'Heating/Air Conditioning'),
                                        ('Cleaning', 'Cleaning'),
                                        ('Other', 'Other')])
    photos=FileField('Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    description=TextAreaField('Description', [DataRequired()])
    submit=SubmitField('Open')

class CloseIssueForm(Form):
    reason=TextAreaField('Reason', [DataRequired()])
    submit=SubmitField('Close')

class AddLandlordForm(Form):
    location=SelectField('Location', coerce=int)
    submit=SubmitField('Add')

class EndLandlordForm(Form):
    end=HiddenField(default='True', validators=[AnyOf('True')])
    submit=SubmitField('End')

class ConfirmTenantForm(Form):
    confirm=SubmitField('Confirm', default='True')
    disallow=SubmitField('Disallow', default='False')

class AddTenantForm(Form):
    user=StringField('User', [DataRequired()])
    apt=SelectField('Property', coerce=int)
    submit=SubmitField('Invite')

class CommentForm(Form):
    comment=TextAreaField('Comment', [DataRequired()])
    submit=SubmitField('Add Comment')

class AddPropertyForm(Form):
    unit=IntegerField('Unit:', [Optional(), NumberRange(min=1)])
    address=StringField('Address:', [DataRequired()])
    city=StringField('City:', [DataRequired()])
    state=StringField('State:', [DataRequired()])
    description=TextAreaField('Description:', [DataRequired()])
    submit=SubmitField('Add Property')

class AddProviderForm(Form):
    name=StringField('Name:', [DataRequired()])
    area=SelectField('Area:', choices=[('Plumbing', 'Plumbing'),
                                        ('Electrical', 'Electrical'),
                                        ('Heating/Air Conditioning', 'Heating/Air Conditioning'),
                                        ('Cleaning', 'Cleaning'),
                                        ('Other', 'Other')])
    email=StringField('Email:', [Email(), DataRequired()])
    phone=StringField('Phone #:', [Optional(), Length(min=10)])
    website=StringField('Website:', [Optional(), URL()])
    submit=SubmitField('Add Provider')

class SelectProviderForm(Form):
    provider=SelectField('Provider:', choices=[])
    submit=SubmitField('Select Provider')

class ConnectProviderForm(Form):
    action=SubmitField('Connect')

class ModifyPropertyForm(Form):
    description=TextAreaField('Description:', [DataRequired()])
    submit=SubmitField('Modify Property')

class AddPhoneNumber(Form):
    phone=StringField('Phone #:', [DataRequired(), Length(min=10)])
    country=SelectField('Country', choices=[('1', 'US'), ('02', 'UK')])
    submit=SubmitField('Update number')

class ChangeNotifyForm(Form):
    method=SelectField('Method', choices=[('Email', 'Email'),
                                            ('None', 'None')])
    submit=SubmitField('Confirm')

class ResendNotifyForm(Form):
    resend=SubmitField('Resend email', default='True')

__all__=['AddLandlordForm', 'AddPhoneNumber', 'AddPropertyForm',
        'AddProviderForm', 'AddTenantForm', 'ChangeNotifyForm',
        'CloseIssueForm', 'CommentForm', 'ConfirmTenantForm',
        'ConnectProviderForm', 'EndLandlordForm', 'ExtendedLoginForm',
        'ExtendedRegisterForm', 'ModifyPropertyForm', 'OpenIssueForm',
        'ResendNotifyForm', 'SelectProviderForm']
