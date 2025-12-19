from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField,
    IntegerField, SelectField, FileField, BooleanField
)
from wtforms.validators import DataRequired, Length, Email


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('student', 'Student'), ('teacher', 'Teacher')])
    submit = SubmitField('Register')


class MaterialForm(FlaskForm):
    title = StringField('Judul', validators=[DataRequired()])
    content = TextAreaField('Konten (teks)')
    image = FileField('Gambar (opsional)')
    video_url = StringField('URL Video (opsional)')
    category = SelectField('Kategori', coerce=int)
    submit = SubmitField('Simpan')


class QuizForm(FlaskForm):
    title = StringField('Judul Quiz', validators=[DataRequired()])
    duration = IntegerField('Durasi (detik)', default=600)
    category = SelectField('Kategori', coerce=int)
    submit = SubmitField('Buat Quiz')


# TODO: Tambahkan forms untuk Question & Choice sesuai kebutuhan
