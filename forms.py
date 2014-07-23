#### FORMS

from flask.ext.wtf import Form
from flask.ext.security.forms import RegisterForm, LoginForm
from wtforms import (SelectField, StringField, SubmitField, TextAreaField,
                HiddenField, FileField, RadioField, SelectField, IntegerField)
from wtforms.validators import Length, DataRequired, AnyOf, Regexp, NumberRange, Optional, Email, URL
from flask.ext.wtf.file import FileAllowed, FileField

class ExtendedRegisterForm(RegisterForm):
    username=StringField('Username', [DataRequired(),
                                    Regexp(r'^\w+$', message="Only alphanumeric characters"),
                                    Length(min=4, max=20)])

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

class PostCommentForm(Form):
    text=TextAreaField('Comment', [DataRequired()])
    submit=SubmitField('Respond')

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

class ConnectProviderForm(Form):
    connect=SubmitField('Connect', default='True')

class DisconnectProviderForm(Form):
    disconnect=SubmitField('Disconnect', default='True')

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
