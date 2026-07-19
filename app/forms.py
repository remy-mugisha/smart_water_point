from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import (
    BooleanField,
    DateTimeField,
    FileField,
    FloatField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError

from app.models import TASK_PRIORITIES, User
from app.rwanda_geo import (
    BUGESERA_DISTRICT,
    BUGESERA_SECTOR_CHOICES,
    all_cell_choices,
    all_village_choices,
    cells_for_sector,
    villages_for_cell,
)

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
    # This project's case study is Bugesera District only, so the address is
    # scoped to it rather than offering all of Rwanda's districts.
    district = SelectField("District", choices=[(BUGESERA_DISTRICT, BUGESERA_DISTRICT)], validators=[DataRequired()])
    sector = SelectField("Sector", choices=BUGESERA_SECTOR_CHOICES, validators=[DataRequired()])
    cell = SelectField("Cell", choices=all_cell_choices(), validators=[DataRequired()])
    village = SelectField("Village", choices=all_village_choices(), validators=[DataRequired()])
    role = SelectField(
        "Role",
        choices=[
            ("viewer", "Viewer"),
            ("district_technician", "Technician"),
            ("district_manager", "Admin"),
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
    agree_terms = BooleanField(
        "I agree to the Privacy Policy",
        validators=[DataRequired(message="You must agree to the Privacy Policy to register.")],
    )

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError("Username already taken. Please choose another.")

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError("Email already registered. Please use another.")

    def validate_cell(self, cell):
        if cell.data not in cells_for_sector(self.sector.data):
            raise ValidationError("Selected cell does not belong to the selected sector.")

    def validate_village(self, village):
        if village.data not in villages_for_cell(self.sector.data, self.cell.data):
            raise ValidationError("Selected village does not belong to the selected cell.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")


class AdminApprovalForm(FlaskForm):
    action = SelectField(
        "Action",
        choices=[("approve", "Approve User"), ("reject", "Reject User")],
        validators=[DataRequired()],
    )
    notes = TextAreaField("Notes (Optional)")


class ChangeRoleForm(FlaskForm):
    role = SelectField(
        "Role",
        choices=[
            ("viewer", "Viewer"),
            ("district_technician", "Technician"),
            ("district_manager", "Manager"),
            ("admin", "Admin"),
        ],
        validators=[DataRequired()],
    )


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


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=8, max=72, message="Password must be 8-72 characters"),
            Regexp(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)",
                message="Password must include an uppercase letter, a lowercase letter, and a digit",
            ),
        ],
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match")],
    )


class PreferencesForm(FlaskForm):
    theme = SelectField("Theme", choices=[("light", "Light"), ("dark", "Dark")], validators=[DataRequired()])
    notifications_enabled = BooleanField("Enable in-app notifications")


class TaskCreateForm(FlaskForm):
    water_point = SelectField("Water Point", choices=[], validators=[DataRequired()])
    technician = SelectField("Assign To", choices=[], validators=[Optional()])
    title = StringField("Task Title", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[Optional()])
    priority = SelectField(
        "Priority", choices=[(p, p.capitalize()) for p in TASK_PRIORITIES], validators=[DataRequired()]
    )
    deadline = DateTimeField("Deadline", format="%Y-%m-%d", validators=[Optional()])


class TaskAssignForm(FlaskForm):
    technician = SelectField("Assign To", choices=[], validators=[DataRequired()])


class TaskProgressForm(FlaskForm):
    note = TextAreaField("Progress Update", validators=[DataRequired(), Length(max=1000)])


class TaskCompleteForm(FlaskForm):
    resulting_status = SelectField(
        "Water Point Status After Repair",
        choices=[("Functional", "Functional"), ("At Risk", "At Risk"), ("Non-Functional", "Non-Functional")],
        validators=[DataRequired()],
    )
    completion_notes = TextAreaField(
        "Completion Notes (actions taken, parts replaced)", validators=[DataRequired(), Length(max=2000)]
    )


class TaskVerifyForm(FlaskForm):
    note = TextAreaField("Verification Notes (Optional)", validators=[Optional(), Length(max=1000)])


class SystemSettingsForm(FlaskForm):
    app_name = StringField("System Name", validators=[DataRequired(), Length(max=150)])
    admin_email = StringField("Admin Contact Email", validators=[DataRequired(), Email()])
    risk_threshold = FloatField("At-Risk Probability Threshold", validators=[DataRequired()])
    session_cookie_secure = BooleanField("Secure Cookies (HTTPS only)")
    max_upload_mb = IntegerField("Max Upload Size (MB)", validators=[DataRequired()])
    default_district = SelectField("Default District", choices=DISTRICT_CHOICES)
    submit = SubmitField("Save Settings")
