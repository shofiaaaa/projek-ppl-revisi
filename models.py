from datetime import datetime
from flask_login import UserMixin
import enum
from extensions import db


# -----------------------------
# ENUM UNTUK ROLE
# -----------------------------
class Role(enum.Enum):
    student = 'student'
    teacher = 'teacher'


# -----------------------------
# USER MODEL
# -----------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.Enum(Role), default=Role.student)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # RELASI
    materials = db.relationship('Material', backref='author', lazy=True)
    quizzes = db.relationship('Quiz', backref='creator', lazy=True)
    submissions = db.relationship('Submission', backref='user', lazy=True)


# -----------------------------
# CATEGORY MODEL
# -----------------------------
class Category(db.Model):
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)

    # RELASI
    materials = db.relationship('Material', backref='category', lazy=True)
    quizzes = db.relationship('Quiz', backref='category', lazy=True)


# -----------------------------
# MATERIAL MODEL
# -----------------------------
class Material(db.Model):
    __tablename__ = 'material'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text)
    video_url = db.Column(db.String(512))
    image_filename = db.Column(db.String(256))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -----------------------------
# QUIZ MODEL
# -----------------------------
class Quiz(db.Model):
    __tablename__ = 'quiz'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    code = db.Column(db.String(20), unique=True, nullable=False)  # KODE MASUK QUIZ
    duration = db.Column(db.Integer, default=600)  # DALAM DETIK
    published = db.Column(db.Boolean, default=False)  # ✅ fixed
    subject = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.now())

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

    # ✅ Relasi ke Question
    questions = db.relationship(
        "Question",
        back_populates="quiz",
        lazy=True,
        cascade="all, delete-orphan"
    )

    submissions = db.relationship(
        'Submission',
        backref='quiz',
        lazy=True,
        cascade="all, delete-orphan"
    )


# -----------------------------
# QUESTION MODEL
# -----------------------------
class Question(db.Model):
    __tablename__ = "question"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255))
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)

    # ✅ Tambahkan relasi ke Quiz
    quiz = db.relationship("Quiz", back_populates="questions")

    choices = db.relationship("Choice", backref="question", cascade="all, delete-orphan")




# -----------------------------
# CHOICE MODEL
# -----------------------------
class Choice(db.Model):
    __tablename__ = 'choice'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    text = db.Column(db.String(512))
    image_filename = db.Column(db.String(256))
    is_correct = db.Column(db.Boolean, default=False)


# -----------------------------
# SUBMISSION MODEL
# -----------------------------
class Submission(db.Model):
    __tablename__ = 'submission'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    score = db.Column(db.Float)

    # RELASI
    answers = db.relationship('Answer', backref='submission', lazy=True, cascade="all, delete-orphan")


# -----------------------------
# ANSWER MODEL
# -----------------------------
class Answer(db.Model):
    __tablename__ = 'answer'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    choice_id = db.Column(db.Integer, db.ForeignKey('choice.id'))
    essay_filename = db.Column(db.String(256))
    text = db.Column(db.Text)

    choice = db.relationship("Choice", backref="answers")

