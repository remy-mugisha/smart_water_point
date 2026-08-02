from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from sqlalchemy import func
from wtforms import (
    BooleanField,
    DateTimeField,
    FileField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError

from app.models import TASK_PRIORITIES, User
from app.rwanda_geo import (
    BUGESERA_SECTORS,
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


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")


class AdminBootstrapForm(FlaskForm):
    """First-run form used to create the initial administrator account. The
    register route only serves this form while no admin user exists."""

    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=72, message="Password must be 8-72 characters"),
            Regexp(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)",
                message="Password must include an uppercase letter, a lowercase letter, and a digit",
            ),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )

    def validate_email(self, email):
        if User.query.filter(func.lower(User.email) == email.data.strip().lower()).first():
            raise ValidationError("Email already registered. Please use another.")


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


class CreateTechnicianForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=1, max=75)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=1, max=75)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone Number", validators=[Optional(), Length(max=20)])
    district = SelectField("District", choices=[], validators=[DataRequired()])
    sector = SelectField("Sector", choices=BUGESERA_SECTOR_CHOICES, validators=[Optional()])
    cell = SelectField("Cell", choices=all_cell_choices(), validators=[Optional()])
    village = SelectField("Village", choices=all_village_choices(), validators=[Optional()])

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError("Email already registered. Please use another.")

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        sector = self.sector.data
        cell = self.cell.data
        village = self.village.data
        if sector and sector not in BUGESERA_SECTORS:
            self.sector.errors.append("Select a sector from the list.")
            ok = False
        if sector and cell and cell not in cells_for_sector(sector):
            self.cell.errors.append("That cell is not in the selected sector.")
            ok = False
        if sector and cell and village and village not in villages_for_cell(sector, cell):
            self.village.errors.append("That village is not in the selected cell.")
            ok = False
        return ok


class SetPasswordForm(FlaskForm):
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
