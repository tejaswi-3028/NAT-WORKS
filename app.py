
import os
import secrets
from functools import wraps
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "NAT_SECRET_KEY", secrets.token_hex(32)
)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + str(BASE_DIR / "database.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

db = SQLAlchemy(app)

BRANCHES = [
    "CSE", "IOT", "CSIT", "IT", "AIML", "AIDS",
    "ECE", "VLSI", "EEE", "Mechanical", "Civil"
]
YEARS = ["1", "2", "3", "4"]
DOMAINS = [
    "Syllabus", "Notes", "Materials", "Lab Manuals",
    "Question Papers", "Placement Papers"
]
PLACEMENT_CATEGORIES = ["CSE Alliances", "Non IT"]


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class PDF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    domain = db.Column(db.String(80), nullable=False)
    branch = db.Column(db.String(80), nullable=False)
    year = db.Column(db.String(10), nullable=False)


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("student_id"):
            flash("Please login to access NAT WORKS.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def valid_location(domain, branch, year):
    if domain not in DOMAINS:
        return False
    if domain == "Placement Papers":
        return branch in PLACEMENT_CATEGORIES and year == "-"
    return branch in BRANCHES and year in YEARS


@app.route("/")
def home():
    if not session.get("student_id"):
        return redirect(url_for("login"))
    return render_template("index.html", domains=DOMAINS)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("Please fill in every field.")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.")
        elif password != confirm:
            flash("Passwords do not match.")
        elif Student.query.filter(
            (Student.username == username) | (Student.email == email)
        ).first():
            flash("Username or email already exists.")
        else:
            student = Student(
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(student)
            db.session.commit()
            flash("Registration successful. Please login.")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        student = Student.query.filter_by(username=username).first()

        if student and check_password_hash(student.password_hash, password):
            session.clear()
            session["student_id"] = student.id
            session["username"] = student.username
            return redirect(url_for("home"))

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/domain/<path:domain>")
@student_required
def domain_page(domain):
    if domain not in DOMAINS:
        abort(404)

    if domain == "Placement Papers":
        branches = PLACEMENT_CATEGORIES
    else:
        branches = BRANCHES

    return render_template(
        "domain.html", domain=domain, branches=branches
    )


@app.route("/domain/<path:domain>/<path:branch>")
@student_required
def year_page(domain, branch):
    if domain not in DOMAINS:
        abort(404)

    if domain == "Placement Papers":
        if branch not in PLACEMENT_CATEGORIES:
            abort(404)
        pdfs = PDF.query.filter_by(
            domain=domain, branch=branch, year="-"
        ).order_by(PDF.title).all()
        return render_template(
            "year.html", domain=domain, branch=branch,
            years=[], selected_year="-", pdfs=pdfs
        )

    if branch not in BRANCHES:
        abort(404)

    return render_template(
        "year.html", domain=domain, branch=branch,
        years=YEARS, selected_year=None, pdfs=[]
    )


@app.route("/domain/<path:domain>/<path:branch>/<year>")
@student_required
def resource_page(domain, branch, year):
    if not valid_location(domain, branch, year):
        abort(404)

    pdfs = PDF.query.filter_by(
        domain=domain, branch=branch, year=year
    ).order_by(PDF.title).all()

    return render_template(
        "year.html", domain=domain, branch=branch,
        years=[], selected_year=year, pdfs=pdfs
    )


@app.route("/pdf/<int:pdf_id>")
@student_required
def view_pdf(pdf_id):
    pdf = db.get_or_404(PDF, pdf_id)
    return send_from_directory(
        str(UPLOAD_DIR), pdf.filename, as_attachment=False
    )


@app.route("/download/<int:pdf_id>")
@student_required
def download_pdf(pdf_id):
    pdf = db.get_or_404(PDF, pdf_id)
    return send_from_directory(
        str(UPLOAD_DIR), pdf.filename,
        as_attachment=True, download_name=pdf.filename
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password_hash, password):
            session.clear()
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            return redirect(url_for("admin_panel"))

        flash("Invalid admin username or password.")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        domain = request.form.get("domain", "")
        branch = request.form.get("branch", "")
        year = request.form.get("year", "")
        file = request.files.get("pdf")

        if not title or not file or not file.filename:
            flash("Enter a title and choose a PDF.")
            return redirect(url_for("admin_panel"))

        if not valid_location(domain, branch, year):
            flash("Please select a valid domain, branch and year.")
            return redirect(url_for("admin_panel"))

        if not file.filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.")
            return redirect(url_for("admin_panel"))

        # Check the PDF signature, not just its extension.
        if file.stream.read(5) != b"%PDF-":
            flash("The selected file does not appear to be a PDF.")
            return redirect(url_for("admin_panel"))
        file.stream.seek(0)

        safe_name = secure_filename(file.filename)
        if not safe_name:
            flash("Invalid filename.")
            return redirect(url_for("admin_panel"))

        # Use a unique stored filename to avoid overwriting another PDF.
        stored_name = secrets.token_hex(8) + "_" + safe_name
        file.save(str(UPLOAD_DIR / stored_name))

        record = PDF(
            title=title, filename=stored_name,
            domain=domain, branch=branch, year=year
        )
        db.session.add(record)
        db.session.commit()
        flash("PDF uploaded successfully.")
        return redirect(url_for("admin_panel"))

    pdfs = PDF.query.order_by(PDF.domain, PDF.branch, PDF.year).all()
    return render_template(
        "admin.html", domains=DOMAINS, branches=BRANCHES,
        years=YEARS, placement_categories=PLACEMENT_CATEGORIES,
        pdfs=pdfs
    )


@app.route("/admin/delete/<int:pdf_id>", methods=["POST"])
@admin_required
def delete_pdf(pdf_id):
    pdf = db.get_or_404(PDF, pdf_id)
    path = UPLOAD_DIR / pdf.filename
    if path.is_file():
        path.unlink()
    db.session.delete(pdf)
    db.session.commit()
    flash("PDF deleted.")
    return redirect(url_for("admin_panel"))


@app.route("/learn-programming")
@student_required
def compiler():
    return render_template("compiler.html")


# Create tables and a first admin account on initial setup.
# Configure NAT_ADMIN_USER and NAT_ADMIN_PASSWORD before first run.
with app.app_context():
    db.create_all()
    admin_user = os.environ.get("NAT_ADMIN_USER", "admin")
    admin_password = os.environ.get("NAT_ADMIN_PASSWORD")
    if not Admin.query.filter_by(username=admin_user).first():
        if not admin_password:
            print(
                "ADMIN NOT CREATED: set NAT_ADMIN_PASSWORD before running "
                "again, then restart the app."
            )
        else:
            db.session.add(Admin(
                username=admin_user,
                password_hash=generate_password_hash(admin_password)
            ))
            db.session.commit()
            print(f"Created initial admin account: {admin_user}")


if __name__ == "__main__":
    app.run(debug=True)