# APP.PY MODULES
import os
import os.path
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import boto3
from dotenv import load_dotenv


# FORM.PY MODULES
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import (StringField, SubmitField, TextAreaField, PasswordField,
                     DateField, ValidationError, SelectField)
from wtforms.fields import TelField
from wtforms.validators import DataRequired, Email, EqualTo, Length
import phonenumbers
import pycountry


# FORM.PY CONTENTS
COUNTRY_CHOICES = [("", "--Select an option--")]+[(country.name, country.name) for country in pycountry.countries]
GENDER_CHOICES = [("", "--Select an option--"), ('Male', 'Male'), ('Female', 'Female')]
TITLE_CHOICES = [("", "--Select an option--"), ('Brother', 'Brother'), ('Sister', 'Sister'), ('Pastor', 'Pastor'),
                 ('Bible study', 'Bible study'), ('Teacher', 'Teacher'), ('Cell leader', 'Cell leader')]
BORN_AGAIN_CHOICES = [("", "--Select an option--"), ('1', 'Yes'), ('2', 'No')]
KNOW_US = [("", "--Select an option--"), ('1', 'Invited'), ('2', 'Social Media'), ('2', 'Television')]


# Create a Registration Form Class
class RegisterForm(FlaskForm):
    title = SelectField('Title:', validators=[DataRequired()], choices=TITLE_CHOICES)
    first_name = StringField("First name:", validators=[DataRequired()])
    middle_name = StringField("Middle name:", validators=[DataRequired()])
    last_name = StringField("Last name:", validators=[DataRequired()])
    address = TextAreaField("Address:", validators=[DataRequired()])
    email = StringField("Email: ", validators=[Email()])
    gender = SelectField("Gender:", validators=[DataRequired()], choices=GENDER_CHOICES)
    birth_date = DateField("Birth date", validators=[DataRequired()])
    phone = TelField('Phone: ', validators=[DataRequired()])
    country = SelectField('Country: ', validators=[DataRequired()], choices=COUNTRY_CHOICES)
    submit = SubmitField("Submit")

    def validate_phone(self, phone):
        try:
            p = phonenumbers.parse(phone.data)
            if not phonenumbers.is_valid_number(p):
                raise ValueError()
        except (phonenumbers.phonenumberutil.NumberParseException, ValueError):
            raise ValidationError('Invalid phone number')


# APP.PY CONTENT
session = boto3.Session(
    aws_access_key_id=os.environ["S3_KEY"],
    aws_secret_access_key=os.environ["S3_SECRET"]
)


app = Flask(__name__)
app.config.from_pyfile('config.py')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Create Model
class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(1024), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    gender = db.Column(db.String(50), nullable=False)
    birth_date = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Create String
    def __repr__(self):
        return "<Email %r>" % self.email


@app.route("/")
def index():
    return render_template("index.html")


# Registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    member_form = RegisterForm()
    if request.method == 'POST':
        if member_form.validate_on_submit():
            email = member_form.email.data
            checked_email = Members.query.filter_by(email=email).first()
            first_name = member_form.first_name.data
            if checked_email is None:
                reg_member = Members(title=member_form.title.data,
                                     first_name=member_form.first_name.data,
                                     middle_name=member_form.middle_name.data,
                                     last_name=member_form.last_name.data,
                                     address=member_form.address.data,
                                     email=member_form.email.data,
                                     gender=member_form.gender.data,
                                     birth_date=member_form.birth_date.data,
                                     phone=member_form.phone.data,
                                     country=member_form.country.data)
                db.session.add(reg_member)
                db.session.commit()
                email_id = Members.query.filter_by(email=email).first().id
                return redirect(url_for("upload", id=email_id))
            return render_template("registered.html", first_name=first_name)
    return render_template("register.html", member_form=member_form)


@app.route("/upload/<int:id>", methods=["GET", "POST"])
def upload(id):
    member_image_update = Members.query.get_or_404(id)
    if request.method == 'POST':
        file = request.files['file']
        ext = file.filename.split('.')[1]
        file_name = f"{member_image_update.first_name} {member_image_update.middle_name} {member_image_update.last_name}.{ext.lower()}"
        s3_resource = session.resource('s3')
        my_bucket = s3_resource.Bucket(os.environ["S3_BUCKET"])
        my_bucket.Object(file_name).put(Body=file)
        image_path = os.path.join(path, file_name)
        # my_bucket.download_file(file_name, image_path)
        return render_template("uploaded.html", first_name=member_image_update.first_name)
    return render_template("upload.html", first_name=member_image_update.first_name)


def success():
    return render_template("success.html")


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    member_form = RegisterForm()
    member_to_update = Members.query.get_or_404(id)
    if request.method == "POST":
        file = request.files['file']
        image = file.read()
        render_image = base64.b64encode(image).decode('ascii')
        ext = file.filename.split('.')[1]
        file_name = f"{member_form.first_name.data} {member_form.middle_name.data} {member_form.last_name.data}.{ext.lower()}"
        image_path = app.config['IMAGE_FOLDER'] + file_name
        secure_image = secure_filename(file_name)
        image_name = str(uuid1()) + "_" + secure_image
        if file_name in os.listdir(app.config['IMAGE_FOLDER']):
            os.remove(image_path)
        file.save(app.config['IMAGE_FOLDER'] + file_name)

        member_to_update.title = request.form['title']
        member_to_update.first_name = request.form['first_name']
        member_to_update.middle_name = request.form['middle_name']
        member_to_update.last_name = request.form['last_name']
        member_to_update.address = request.form['address']
        member_to_update.email = request.form['email']
        member_to_update.gender = request.form['gender']
        member_to_update.birth_date = request.form['birth_date']
        member_to_update.phone = request.form['phone']
        member_to_update.country = request.form['country']
        member_to_update.image_name = image_name
        member_to_update.image_data = image
        member_to_update.render_data = render_image
        try:
            db.session.commit()
            return render_template("updated.html",
                                   first_name=member_to_update.first_name)
        except:
            return render_template("update.html",
                                   member_form=member_form,
                                   member_to_update=member_to_update)
    else:
        return render_template("update.html",
                               member_form=member_form,
                               member_to_update=member_to_update)


@app.route('/delete/<int:id>')
def delete(id):
    member_to_delete = Members.query.get_or_404(id)
    try:
        db.session.delete(member_to_delete)
        db.session.commit()
        all_members = Members.query.order_by(Members.registration_date)
        return render_template("database.html", all_members=all_members)
    except:
        flash("There was a problem deleting that record, please try again!")
        all_members = Members.query.order_by(Members.registration_date)
        return render_template("database.html", all_members=all_members)


# invalid URL
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# Internal Server Error
@app.errorhandler(500)
def page_not_found(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
