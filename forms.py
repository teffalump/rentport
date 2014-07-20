#### FORMS

from flask.ext.wtf import Form
from flask.ext.security.forms import RegisterForm, LoginForm
from wtforms import (SelectField, StringField, SubmitField, TextAreaField,
                HiddenField, FileField, RadioField, SelectField, IntegerField)
from wtforms.validators import Length, DataRequired, AnyOf, Regexp, NumberRange, Optional

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
    description=TextAreaField('Description:', [DataRequired()])
    submit=SubmitField('Add Property')

class ModifyPropertyForm(AddPropertyForm):
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
