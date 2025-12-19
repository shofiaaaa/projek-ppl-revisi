import os
import csv
import secrets
from datetime import datetime
from random import shuffle
from flask import (
    Flask, render_template, redirect, url_for, flash,
    request, send_from_directory
)
from flask_login import (
    LoginManager, login_user, current_user,
    login_required, logout_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from werkzeug.utils import secure_filename

from config import Config
from extensions import db
from models import (
    User, Role, Material, Category,
    Quiz, Question, Choice, Submission, Answer
)
from sqlalchemy import func, case, desc, cast, Float
from sqlalchemy import Integer
from flask import session
from io import StringIO
from flask import session, Response

from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO



# ==============================================
# Konfigurasi Upload
# ==============================================
ALLOWED_IMG = {"png", "jpg", "jpeg", "gif"}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Inisialisasi Database & Login ---
    db.init_app(app)
    Migrate(app, db)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # --- Folder Upload ---
    upload_folder = app.config.get("UPLOAD_FOLDER") or os.path.join(
        os.path.dirname(__file__), "uploads"
    )
    app.config["UPLOAD_FOLDER"] = upload_folder
    os.makedirs(upload_folder, exist_ok=True)

    # ==============================================
    # Fungsi Utilitas
    # ==============================================
    def allowed_file(filename, allowed_set=ALLOWED_IMG):
        return bool(filename) and "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set

    def save_upload(fileobj):
        """Simpan file, beri nama unik, dan kembalikan nama file yang disimpan."""
        if not fileobj or not getattr(fileobj, "filename", None):
            return None
        ext = fileobj.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_IMG:
            return None
        fname = secrets.token_hex(8) + "." + ext
        path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
        fileobj.save(path)
        return fname

    # ==============================================
    # ROUTES UTAMA
    # ==============================================
    @app.route("/")
    def index():
        return render_template("index.html")

    # ==============================================
    # AUTH
    # ==============================================
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", None)

            if not username or not email or not password or not role:
                flash("Lengkapi semua field.")
                return redirect(url_for("register"))

            if User.query.filter_by(username=username).first():
                flash("Username sudah dipakai!")
                return redirect(url_for("register"))

            try:
                role_enum = Role[role]
            except Exception:
                flash("Role tidak valid.")
                return redirect(url_for("register"))

            u = User(username=username, email=email, role=role_enum)
            u.password_hash = generate_password_hash(password)
            db.session.add(u)
            db.session.commit()

            flash("Registrasi berhasil, silakan login.")
            return redirect(url_for("login"))

        return render_template("auth/register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            u = User.query.filter_by(username=username).first()
            if u and check_password_hash(u.password_hash, password):
                login_user(u)
                flash("Login berhasil.")
                if u.role == Role.teacher:
                    return redirect(url_for("teacher_dashboard"))
                return redirect(url_for("student_dashboard"))
            else:
                flash("Username atau password salah.")

        return render_template("auth/login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Berhasil logout.")
        return redirect(url_for("index"))

    # ==============================================
    # DASHBOARD GURU
    # ==============================================
    @app.route("/teacher/dashboard")
    @login_required
    def teacher_dashboard():
        if current_user.role != Role.teacher:
            flash("Akses ditolak.")
            return redirect(url_for("index"))

        quizzes = Quiz.query.filter_by(created_by=current_user.id).all()
        categories = Category.query.all()
        materials = Material.query.filter_by(created_by=current_user.id).all()
        return render_template(
            "teacher/dashboard.html",
            quizzes=quizzes,
            categories=categories,
            materials=materials
        )

    # ==============================================
    # CRUD KATEGORI (alias untuk kompatibilitas template)
    # ==============================================
    @app.route('/teacher/categories')
    @app.route('/teacher/category/list')
    @login_required
    def teacher_categories():
        if current_user.role != Role.teacher:
            flash("Akses ditolak.", "danger")
            return redirect(url_for('index'))

        categories = Category.query.all()
        return render_template('teacher/categories.html', categories=categories)

    @app.route('/teacher/categories/create', methods=['GET', 'POST'])
    @app.route('/teacher/category/create', methods=['GET', 'POST'])  # alias
    @login_required
    def create_category():
        if current_user.role != Role.teacher:
            flash("Akses ditolak.", "danger")
            return redirect(url_for('index'))

        if request.method == 'POST':
            name = request.form.get('name')
            if not name:
                flash("Nama kategori wajib diisi.", "warning")
                return redirect(url_for('create_category'))

            new_category = Category(name=name)
            db.session.add(new_category)
            db.session.commit()
            flash("Kategori berhasil dibuat!", "success")
            return redirect(url_for('teacher_categories'))

        return render_template('teacher/create_category.html')

    @app.route('/teacher/categories/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_category(id):
        if current_user.role != Role.teacher:
            flash("Akses ditolak.", "danger")
            return redirect(url_for('index'))

        category = Category.query.get_or_404(id)
        if request.method == 'POST':
            category.name = request.form.get('name')
            db.session.commit()
            flash("Kategori berhasil diperbarui.", "success")
            return redirect(url_for('teacher_categories'))

        return render_template('teacher/edit_category.html', category=category)

    @app.route('/teacher/categories/<int:id>/delete', methods=['POST'])
    @login_required
    def delete_category(id):
        if current_user.role != Role.teacher:
            flash("Akses ditolak.", "danger")
            return redirect(url_for('index'))

        category = Category.query.get_or_404(id)
        db.session.delete(category)
        db.session.commit()
        flash("Kategori berhasil dihapus.", "success")
        return redirect(url_for('teacher_categories'))

    # ==============================================
    # CRUD MATERI
    # ==============================================
    @app.route("/teacher/material/create", methods=["GET", "POST"])
    @login_required
    def create_material():
        if current_user.role != Role.teacher:
            flash("Hanya guru yang bisa menambah materi.")
            return redirect(url_for("index"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            cat_id = request.form.get("category")

            if not title:
                flash("Judul materi wajib diisi.")
                return redirect(url_for("create_material"))

            m = Material(title=title, content=content, category_id=cat_id, created_by=current_user.id)

            file = request.files.get("image")
            if file and allowed_file(file.filename):
                saved = save_upload(file)
                if saved:
                    m.image_filename = saved

            db.session.add(m)
            db.session.commit()

            flash("Materi berhasil ditambahkan.")
            return redirect(url_for("teacher_dashboard"))

        categories = Category.query.all()
        return render_template("teacher/create_material.html", categories=categories)

    # teacher view material (teacher-only)
    @app.route("/teacher/material/<int:material_id>/view")
    @login_required
    def teacher_view_material(material_id):
        if current_user.role != Role.teacher:
            flash("Akses ditolak.")
            return redirect(url_for("index"))

        material = Material.query.get_or_404(material_id)
        return render_template("teacher/view_material.html", material=material)

    # public/student view material (alias used in templates)
    @app.route("/material/<int:material_id>")
    @login_required
    def view_material(material_id):
        material = Material.query.get_or_404(material_id)
        return render_template("student/view_material.html", material=material)

    @app.route("/teacher/material/<int:material_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_material(material_id):
        if current_user.role != Role.teacher:
            flash("Akses ditolak.")
            return redirect(url_for("index"))

        material = Material.query.get_or_404(material_id)
        if material.created_by != current_user.id:
            flash("Anda tidak memiliki izin untuk mengedit materi ini.", "danger")
            return redirect(url_for("teacher_dashboard"))

        if request.method == "POST":
            material.title = request.form.get("title", "").strip()
            material.content = request.form.get("content", "").strip()
            cat_id = request.form.get("category")
            if cat_id:
                material.category_id = cat_id

            file = request.files.get("image")
            if file and allowed_file(file.filename):
                saved = save_upload(file)
                if saved:
                    material.image_filename = saved

            db.session.commit()
            flash("Materi berhasil diperbarui.", "success")
            return redirect(url_for("teacher_dashboard"))

        categories = Category.query.all()
        return render_template("teacher/edit_material.html", material=material, categories=categories)

    @app.route("/teacher/material/<int:material_id>/delete", methods=["POST"])
    @login_required
    def delete_material(material_id):
        material = Material.query.get_or_404(material_id)
        if current_user.role != Role.teacher or material.created_by != current_user.id:
            flash("Akses ditolak.")
            return redirect(url_for("teacher_dashboard"))

        db.session.delete(material)
        db.session.commit()
        flash("Materi berhasil dihapus.", "success")
        return redirect(url_for("teacher_dashboard"))

    # ==============================================
    # CRUD QUIZ & PERTANYAAN
    # ==============================================
    @app.route("/teacher/quiz/create", methods=["GET", "POST"])
    @login_required
    def create_quiz():
        if current_user.role != Role.teacher:
            flash("Hanya guru yang bisa membuat quiz.")
            return redirect(url_for("index"))

        categories = Category.query.all()

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            code = request.form.get("code", "").strip()
            category_id = request.form.get("category")
            duration_min_raw = request.form.get("duration", "").strip()

            try:
                duration_sec = int(duration_min_raw) * 60 if duration_min_raw else 600
            except ValueError:
                duration_sec = 600

            if not title or not code:
                flash("Judul dan kode wajib diisi.")
                return redirect(url_for("create_quiz"))

            if Quiz.query.filter_by(code=code).first():
                flash("Kode quiz sudah digunakan.")
                return redirect(url_for("create_quiz"))

            quiz = Quiz(
                title=title,
                description=description,
                code=code,
                category_id=category_id,
                created_by=current_user.id,
                published=False,
                duration=duration_sec,
            )
            db.session.add(quiz)
            db.session.commit()

            flash("Quiz berhasil dibuat. Tambahkan pertanyaan sekarang!")
            return redirect(url_for("add_question", quiz_id=quiz.id))

        return render_template("teacher/create_quiz.html", categories=categories)

    @app.route("/teacher/quiz/<int:quiz_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_quiz(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)
        if current_user.role != Role.teacher or quiz.created_by != current_user.id:
            flash("Akses ditolak.")
            return redirect(url_for("teacher_dashboard"))

        categories = Category.query.all()

        if request.method == "POST":
            quiz.title = request.form.get("title", "").strip()
            quiz.description = request.form.get("description", "").strip()
            quiz.code = request.form.get("code", "").strip()
            quiz.category_id = request.form.get("category")
            duration_min_raw = request.form.get("duration", "").strip()
            try:
                quiz.duration = int(duration_min_raw) * 60 if duration_min_raw else quiz.duration
            except ValueError:
                pass

            db.session.commit()
            flash("Quiz berhasil diperbarui.", "success")
            return redirect(url_for("teacher_dashboard"))

        return render_template("teacher/edit_quiz.html", quiz=quiz, categories=categories)

    @app.route("/teacher/quiz/<int:quiz_id>/delete", methods=["POST"])
    @login_required
    def delete_quiz(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)
        if current_user.role != Role.teacher or quiz.created_by != current_user.id:
            flash("Akses ditolak.")
            return redirect(url_for("teacher_dashboard"))

        # Hapus question -> choice & submissions -> answers
        for q in quiz.questions:
            Choice.query.filter_by(question_id=q.id).delete()
        Question.query.filter_by(quiz_id=quiz.id).delete()

        for s in quiz.submissions:
            Answer.query.filter_by(submission_id=s.id).delete()
        Submission.query.filter_by(quiz_id=quiz.id).delete()

        db.session.delete(quiz)
        db.session.commit()
        flash("Quiz dan semua datanya berhasil dihapus.", "success")
        return redirect(url_for("teacher_dashboard"))

    @app.route("/quiz/<int:quiz_id>/add_question", methods=["GET", "POST"])
    @login_required
    def add_question(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)

        if request.method == "POST":
            text = request.form.get("question")
            image = request.files.get("question_image")
            correct_answer = request.form.get("correct_answer")

            image_filename = None
            if image and image.filename:
                image_filename = secure_filename(image.filename)
                image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))

            question = Question(text=text, quiz_id=quiz.id, image_filename=image_filename)
            db.session.add(question)
            db.session.commit()

            # Simpan pilihan jawaban
            for opt in ['a', 'b', 'c', 'd']:
                choice_text = request.form.get(f"option_{opt}")
                choice_image = request.files.get(f"image_{opt}")
                choice_filename = None
                if choice_image and choice_image.filename:
                    choice_filename = secure_filename(choice_image.filename)
                    choice_image.save(os.path.join(app.config["UPLOAD_FOLDER"], choice_filename))

                is_correct = (correct_answer.lower() == opt)
                choice = Choice(
                    text=choice_text,
                    image_filename=choice_filename,
                    is_correct=is_correct,
                    question=question
                )
                db.session.add(choice)

            db.session.commit()
            flash("Soal berhasil ditambahkan!", "success")
            return redirect(url_for("add_question", quiz_id=quiz.id))

        # ambil semua soal quiz
        questions = Question.query.filter_by(quiz_id=quiz.id).all()
        return render_template("teacher/add_question.html", quiz=quiz, questions=questions)


    @app.route("/teacher/question/<int:question_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_question(question_id):
        question = Question.query.get_or_404(question_id)
        quiz = Quiz.query.get_or_404(question.quiz_id)

        if current_user.role != Role.teacher or quiz.created_by != current_user.id:
            flash("Anda tidak memiliki izin untuk mengedit soal ini.", "danger")
            return redirect(url_for("teacher_dashboard"))

        if request.method == "POST":
            question.text = request.form.get("question", "").strip()
            correct_answer = request.form.get("correct_answer", "").strip().lower()

            choices = Choice.query.filter_by(question_id=question.id).all()
            for i, opt in enumerate(["a", "b", "c", "d"]):
                if i < len(choices):
                    choices[i].text = request.form.get(f"option_{opt}", "").strip()
                    choices[i].is_correct = (correct_answer == opt)

            img = request.files.get("question_image")
            if img and img.filename != "":
                saved = save_upload(img)
                if saved:
                    question.image_filename = saved

            db.session.commit()
            flash("Soal berhasil diperbarui!", "success")
            return redirect(url_for("add_question", quiz_id=quiz.id))

        return render_template("teacher/edit_question.html", question=question, quiz=quiz)

    @app.route("/teacher/question/<int:question_id>/delete", methods=["POST"])
    @login_required
    def delete_question(question_id):
        question = Question.query.get_or_404(question_id)
        quiz = Quiz.query.get_or_404(question.quiz_id)

        if current_user.role != Role.teacher or quiz.created_by != current_user.id:
            flash("Anda tidak memiliki izin untuk menghapus soal ini.", "danger")
            return redirect(url_for("teacher_dashboard"))

        # Hapus file gambar soal jika ada
        if question.image_filename:
            try:
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], question.image_filename))
            except Exception:
                pass

        Choice.query.filter_by(question_id=question.id).delete()
        db.session.delete(question)
        db.session.commit()
        flash("Soal berhasil dihapus.", "success")
        return redirect(url_for("add_question", quiz_id=quiz.id))

    
    # ==============================================
    # HASIL QUIZ & REKAP NILAI
    # ==============================================
    @app.route("/teacher/quiz/<int:quiz_id>/results")
    @login_required
    def quiz_results(quiz_id):
        if current_user.role != Role.teacher:
            flash("Akses ditolak.", "danger")
            return redirect(url_for("index"))

        quiz = Quiz.query.get_or_404(quiz_id)

        # Ambil semua submission untuk quiz ini
        submissions = Submission.query.filter(
            Submission.quiz_id == quiz_id,
            Submission.finished_at.isnot(None)  # hanya yang sudah selesai mengerjakan
        ).order_by(Submission.finished_at.desc()).all()


        hasil_list = []
        for sub in submissions:
            total_benar = sum(1 for ans in sub.answers if ans.choice and ans.choice.is_correct)
            total_soal = len(sub.quiz.questions)
            nilai = (total_benar / total_soal * 100) if total_soal else 0
            hasil_list.append({
                "nama": sub.user.username,
                "nilai": nilai,
                "tanggal": sub.finished_at.strftime("%d %B %Y") if sub.finished_at else "-"
            })


        # Data untuk Chart.js
        labels = [h["nama"] for h in hasil_list]
        values = [h["nilai"] for h in hasil_list]

        # --- REKAP NILAI PER MINGGU UNTUK SQLITE (MINGGU KALENDER BIASA) ---

        rekap_query = (
            db.session.query(
                func.strftime("%Y", Submission.finished_at).label("tahun"),
                func.strftime("%W", Submission.finished_at).label("minggu"),

                func.avg(
                    case(
                        (Choice.is_correct == True, 1),
                        else_=0
                    )
                ).label("rata_rata"),

                func.count(func.distinct(Submission.id)).label("jumlah")  # FIX double-count
            )
            .join(Answer, Submission.id == Answer.submission_id)
            .join(Choice, Choice.id == Answer.choice_id)
            .filter(
                Submission.quiz_id == quiz.id,
                Submission.finished_at.isnot(None)
            )
            .group_by("tahun", "minggu")
            .order_by("tahun", "minggu")
            .all()
        )


        rekap = [{
            "tahun": int(r.tahun),
            "minggu": int(r.minggu),
            "rata_rata": float(r.rata_rata),
            "jumlah": int(r.jumlah)
        } for r in rekap_query]



        return render_template(
            "teacher/quiz_results.html",
            quiz=quiz,
            hasil_list=hasil_list,
            labels=labels,
            values=values,
            rekap=rekap
        )


    # ===== LEADERBOARD: per-quiz (teacher) =====
    @app.route("/teacher/quiz/<int:quiz_id>/leaderboard")
    @login_required
    def quiz_leaderboard(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)

        # FIX QUERY LEADERBOARD
        rows = (
            db.session.query(
                User.username.label("username"),
                db.func.avg(Submission.score).label("percentage"),
                db.func.count(Submission.id).label("attempts")
            )
            .join(Submission, Submission.user_id == User.id)
            .filter(Submission.quiz_id == quiz.id)
            .group_by(User.id)
            .order_by(db.func.avg(Submission.score).desc())
            .all()
        )

        return render_template(
            "teacher/quiz_leaderboard.html",
            quiz=quiz,
            rows=rows
        )


    # ===== LEADERBOARD GLOBAL: semua siswa =====
    @app.route("/leaderboard")
    @login_required
    def leaderboard():

        raw_lb = (
            db.session.query(
                User.username,
                Submission.score,
                Submission.finished_at,
                Quiz.title.label("quiz_title")
            )
            .join(User, Submission.user_id == User.id)
            .join(Quiz, Submission.quiz_id == Quiz.id)
            .filter(Submission.score.isnot(None))
            .order_by(Submission.score.desc(), Submission.finished_at.asc())
            .limit(20)
            .all()
        )

        leaderboard = []
        for r in raw_lb:
            leaderboard.append({
                "username": r[0],
                "score": float(r[1]) if r[1] else 0,
                "finished_at": r[2],
                "quiz_title": r[3]
            })

        # ======= RETURN WAJIB ADA DI SINI =======
        return render_template(
            "leaderboard.html",
            leaderboard=leaderboard
        )



    # ==============================================
    # SORTIR / PILIH SOAL UNTUK QUIZ
    # ==============================================
    @app.route('/quiz_select_questions/<int:quiz_id>', methods=['GET', 'POST'])
    @login_required
    def quiz_select_questions(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)
        # ambil semua soal sesuai topik quiz
        questions = Question.query.filter_by(quiz_id=quiz.id).all()


        if request.method == 'POST':
            selected_ids = request.form.getlist('question_ids')
            selected_questions = Question.query.filter(Question.id.in_(selected_ids)).all()
            quiz.questions = selected_questions
            db.session.commit()
            flash('Soal berhasil dipilih untuk quiz ini!', 'success')
            return redirect(url_for('teacher_dashboard'))

        return render_template('quiz_select_questions.html', quiz=quiz, questions=questions)


    @app.route("/teacher/quiz/<int:quiz_id>/publish")
    @login_required
    def publish_quiz(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)

        if current_user.role != Role.teacher:
            flash("Akses ditolak", "danger")
            return redirect(url_for("teacher_dashboard"))

        quiz.published = True
        db.session.commit()

        flash("Quiz berhasil dipublikasikan!", "success")
        return redirect(url_for("teacher_dashboard"))


    # ==============================================
    # SISWA: DASHBOARD & AMBIL QUIZ
    # ==============================================
    @app.route("/student/dashboard", methods=["GET", "POST"])
    @login_required
    def student_dashboard():
        # Pastikan user adalah siswa
        if current_user.role != Role.student:
            flash("Akses ditolak.")
            return redirect(url_for("index"))

        # Jika siswa memasukkan kode quiz
        if request.method == "POST":
            code = request.form.get("code", "").strip()
            if code:
                quiz = Quiz.query.filter_by(code=code, published=True).first()
                if quiz:
                    return redirect(url_for("start_quiz", quiz_id=quiz.id))

            flash("Kode quiz tidak ditemukan atau belum aktif.")

        # Ambil daftar materi
        materials = Material.query.all()

        # Ambil seluruh riwayat quiz siswa (list)
        submissions = Submission.query.filter_by(
            user_id=current_user.id
        ).order_by(Submission.finished_at.desc()).all()

        # Riwayat Quiz per Quiz ID (diringkas)
        history = {}
        for sub in submissions:
            qid = sub.quiz_id
            if qid not in history:
                history[qid] = {
                    "quiz": sub.quiz,
                    "count": 0
                }
            history[qid]["count"] += 1

        # Leaderboard global (ambil top 20)
        # Query mengembalikan Row-like items — kita ubah ke list of dict agar Jinja aman.
        raw_lb = (
            db.session.query(
                User.username,
                Submission.score,
                Submission.finished_at,
                Quiz.title.label("quiz_title")
            )
            .join(User, Submission.user_id == User.id)
            .join(Quiz, Submission.quiz_id == Quiz.id)
            .filter(Submission.score.isnot(None))
            .order_by(Submission.score.desc(), Submission.finished_at.asc())
            .limit(20)
            .all()
        )

        leaderboard = []
        for r in raw_lb:
            # r bisa berupa tuple/Row — ambil via index untuk aman
            username = r[0]
            score = r[1]
            finished_at = r[2]
            quiz_title = r[3]
            leaderboard.append({
                "username": username,
                "score": float(score) if score is not None else None,
                "finished_at": finished_at,
                "quiz_title": quiz_title
            })

        # Kembalikan template dengan semua data
        return render_template(
            "student/dashboard.html",
            materials=materials,
            submissions=submissions,
            history=history,
            leaderboard=leaderboard
        )

    # START QUIZ (SOAL RANDOM + SATU-SATU)

    @app.route("/quiz/<int:quiz_id>/start")
    @login_required
    def start_quiz(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)

        # Cegah ulang quiz
        done = Submission.query.filter(
            Submission.quiz_id == quiz.id,
            Submission.user_id == current_user.id,
            Submission.finished_at.isnot(None)
        ).first()

        if done:
            flash("Kamu sudah mengerjakan quiz ini.", "warning")
            return redirect(url_for("quiz_result", submission_id=done.id))

        submission = Submission(
            quiz_id=quiz.id,
            user_id=current_user.id,
            started_at=datetime.utcnow()
        )
        db.session.add(submission)
        db.session.commit()

        # RANDOM SOAL
        order = [q.id for q in quiz.questions]
        shuffle(order)

        session["question_order"] = order
        session["index"] = 0

        return redirect(url_for("do_question", submission_id=submission.id))



    # ==============================================
    # SISWA MENGERJAKAN QUIZ (ONE BY ONE QUESTION)
    # ==============================================

    @app.route("/quiz/do/<int:submission_id>", methods=["GET", "POST"])
    @login_required
    def do_question(submission_id):
        submission = Submission.query.get_or_404(submission_id)
        quiz = submission.quiz

        order = session.get("question_order", [])
        index = session.get("index", 0)

        # selesai
        if index >= len(order):
            submission.finished_at = datetime.utcnow()
            total = len(order)
            benar = sum(1 for a in submission.answers if a.choice and a.choice.is_correct)
            submission.score = (benar / total * 100) if total else 0
            db.session.commit()

            session.pop("question_order", None)
            session.pop("index", None)

            return redirect(url_for("quiz_result", submission_id=submission.id))

        question = Question.query.get_or_404(order[index])
        choices = Choice.query.filter_by(question_id=question.id).all()

        if request.method == "POST":
            choice_id = request.form.get("choice")
            if choice_id:
                db.session.add(Answer(
                    submission_id=submission.id,
                    question_id=question.id,
                    choice_id=int(choice_id)
                ))
                db.session.commit()
                session["index"] = index + 1
                return redirect(url_for("do_question", submission_id=submission.id))

        return render_template(
            "student/quiz_single.html",
            quiz=quiz,
            question=question,
            choices=choices,
            nomor=index + 1,
            total=len(order)
        )


    # ================================
    # Lihat Riwayat Per Quiz
    # ================================
    @app.route("/student/history/<int:quiz_id>")
    @login_required
    def student_quiz_history(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)

        submissions = Submission.query.filter_by(
            user_id=current_user.id,
            quiz_id=quiz_id
        ).order_by(Submission.finished_at.desc()).all()

        return render_template(
            "student/quiz_history.html",
            quiz=quiz,
            submissions=submissions
        )


    
    # ================================
    # Upload Serving
    # ================================
    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)



    # ================================
    # Halaman Hasil Quiz
    # ================================
    @app.route("/quiz/result/<int:submission_id>")
    @login_required
    def quiz_result(submission_id):
        submission = Submission.query.get_or_404(submission_id)
        quiz = submission.quiz
        answers = submission.answers

        return render_template(
            "student/quiz_result.html",
            submission=submission,
            quiz=quiz,
            answers=answers
        )

    # PROGRESS SISWA (GURU BISA LIHAT)

    @app.route("/teacher/quiz/<int:quiz_id>/progress")
    @login_required
    def quiz_progress(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)

        total_soal = len(quiz.questions)
        data = []

        submissions = Submission.query.filter_by(quiz_id=quiz.id).all()

        for s in submissions:
            data.append({
                "nama": s.user.username,
                "status": "Selesai" if s.finished_at else "Mengerjakan",
                "progress": f"{len(s.answers)}/{total_soal}",
                "nilai": s.score if s.score is not None else "-"
            })

        return render_template(
            "teacher/quiz_progress.html",
            quiz=quiz,
            rows=data
        )

    # download rekap nilai

    @app.route("/teacher/quiz/<int:quiz_id>/download")
    @login_required
    def download_quiz_result(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)

        submissions = Submission.query.filter(
            Submission.quiz_id == quiz.id,
            Submission.finished_at.isnot(None)
        ).all()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # Judul
        elements.append(Paragraph(
            f"<b>Rekap Nilai Quiz</b><br/>{quiz.title}",
            styles["Title"]
        ))

        elements.append(Paragraph("<br/>", styles["Normal"]))

        # Data tabel
        data = [["Nama Siswa", "Nilai", "Tanggal"]]

        for s in submissions:
            data.append([
                s.user.username,
                f"{s.score:.2f}" if s.score is not None else "-",
                s.finished_at.strftime("%d %B %Y") if s.finished_at else "-"
            ])

        table = Table(data, colWidths=[200, 80, 120])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        elements.append(table)

        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"rekap_quiz_{quiz.id}.pdf",
            mimetype="application/pdf"
        )


    # ==============================================
    # ADMIN / GURU: LIST PROGRES SEMUA SISWA
    # ==============================================
    @app.route("/teacher/students")
    @login_required
    def teacher_students():
        if current_user.role != Role.teacher:
            flash("Akses ditolak.", "danger")
            return redirect(url_for("index"))

        students = User.query.filter_by(role=Role.student).all()

        return render_template(
            "teacher/students.html",
            students=students
        )

    # ==============================================
    # ADMIN / GURU: PROGRES PER SISWA
    # ==============================================
    @app.route("/teacher/student/<int:user_id>/progress")
    @login_required
    def teacher_student_progress(user_id):
        if current_user.role != Role.teacher:
            flash("Akses ditolak.", "danger")
            return redirect(url_for("index"))

        student = User.query.get_or_404(user_id)

        quizzes = Quiz.query.filter_by(published=True).all()

        data = []

        for quiz in quizzes:
            submission = Submission.query.filter_by(
                quiz_id=quiz.id,
                user_id=student.id
            ).order_by(Submission.started_at.desc()).first()

            if not submission:
                status = "Belum Mengerjakan"
                progress = "-"
                score = "-"
            elif submission.finished_at:
                status = "Selesai"
                progress = f"{len(submission.answers)}/{len(quiz.questions)}"
                score = f"{submission.score:.1f}%"
            else:
                status = "Mengerjakan"
                progress = f"{len(submission.answers)}/{len(quiz.questions)}"
                score = "-"

            data.append({
                "quiz": quiz,
                "status": status,
                "progress": progress,
                "score": score
            })

        return render_template(
            "teacher/student_progress.html",
            student=student,
            rows=data
        )


    @app.route("/teacher/student/<int:user_id>/download")
    @login_required
    def download_student_progress(user_id):
        if current_user.role != Role.teacher:
            flash("Akses ditolak.", "danger")
            return redirect(url_for("index"))

        student = User.query.get_or_404(user_id)
        quizzes = Quiz.query.filter_by(published=True).all()

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()
        elements = []

        # ===== JUDUL =====
        elements.append(
            Paragraph(
                f"<b>Laporan Progres Quiz Siswa</b><br/>Nama: {student.username}",
                styles["Title"]
            )
        )

        elements.append(Paragraph("<br/>", styles["Normal"]))

        # ===== DATA TABEL =====
        data = [
            ["Quiz", "Status", "Progress", "Nilai"]
        ]

        for quiz in quizzes:
            submission = Submission.query.filter_by(
                quiz_id=quiz.id,
                user_id=student.id
            ).order_by(Submission.started_at.desc()).first()

            if not submission:
                status = "Belum Mengerjakan"
                progress = "-"
                score = "-"
            elif submission.finished_at:
                status = "Selesai"
                progress = f"{len(submission.answers)}/{len(quiz.questions)}"
                score = f"{submission.score:.1f}%"
            else:
                status = "Mengerjakan"
                progress = f"{len(submission.answers)}/{len(quiz.questions)}"
                score = "-"

            data.append([
                quiz.title,
                status,
                progress,
                score
            ])

        table = Table(data, colWidths=[200, 100, 80, 80])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ]))

        elements.append(table)

        doc.build(elements)

        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Progres_{student.username}.pdf",
            mimetype="application/pdf"
        )











    return app
# ==============================================
# APP INSTANCE UNTUK GUNICORN (WAJIB)
# ==============================================
app = create_app()

# ==============================================
# MAIN ENTRY POINT (LOCAL ONLY)
# ==============================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)




