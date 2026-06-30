from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import BooleanField, FileField, PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError

from app.models import User

DISTRICT_CHOICES = [
    ("", "Select District"),
    ("Nyagatare", "Nyagatare"),
    ("Bugesera", "Bugesera"),
    ("Gatsibo", "Gatsibo"),
    ("Kayonza", "Kayonza"),
    ("Rwamagana", "Rwamagana"),
]


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=150)])
    phone = StringField("Phone Number", validators=[Optional(), Length(max=20)])
    district = SelectField("District", choices=DISTRICT_CHOICES, validators=[DataRequired()])
    role = SelectField(
        "Role",
        choices=[
            ("viewer", "Viewer - can view data only"),
            ("district_technician", "Technician - can upload data and view"),
            ("district_manager", "Manager - can manage district data"),
        ],
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters")],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError("Username already taken. Please choose another.")

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError("Email already registered. Please use another.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")


class AdminApprovalForm(FlaskForm):
    action = SelectField(
        "Action",
        choices=[("approve", "Approve User"), ("reject", "Reject User")],
        validators=[DataRequired()],
    )
    notes = TextAreaField("Notes (Optional)")


class DataUploadForm(FlaskForm):
    district = SelectField("District", choices=[], validators=[DataRequired()])
    data_file = FileField(
        "Water Point Data (CSV or Excel)",
        validators=[FileRequired(), FileAllowed(["csv", "xlsx"], "CSV and Excel files only.")],
    )
    notes = TextAreaField("Notes about this data")


class UserProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    phone = StringField("Phone Number", validators=[Optional(), Length(max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
