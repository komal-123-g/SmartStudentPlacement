from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv


load_dotenv(
    os.path.join(
        os.path.dirname(__file__),
        ".env"
    )
)


print("DB HOST =", os.getenv("DB_HOST"))
print("DB USER =", os.getenv("DB_USER"))
print("DB NAME =", os.getenv("DB_NAME"))

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")


# =========================
# DATABASE CONNECTION
# =========================

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
   


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template("home.html")


# ============================================================
# STUDENT MODULE
# ============================================================


# =========================
# STUDENT REGISTER
# =========================

@app.route("/student/register", methods=["GET", "POST"])
def student_register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        password = request.form["password"]
        course = request.form["course"]
        cgpa = request.form["cgpa"]
        skills = request.form["skills"]

        db = get_db_connection()
        cursor = db.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO students
                (name, email, mobile, password, course, cgpa, skills)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    name,
                    email,
                    mobile,
                    password,
                    course,
                    cgpa,
                    skills
                )
            )

            db.commit()

            cursor.close()
            db.close()

            return redirect(url_for("student_login"))

        except mysql.connector.Error as e:

            cursor.close()
            db.close()

            return "Registration Error: " + str(e)

    return render_template("student_register.html")


# =========================
# STUDENT LOGIN
# =========================

@app.route("/student/login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT id
            FROM students
            WHERE email = %s
            AND password = %s
            """,
            (
                email,
                password
            )
        )

        student = cursor.fetchone()

        cursor.close()
        db.close()

        if student:

            session["student_id"] = student[0]

            return redirect(
                url_for("student_dashboard")
            )

        return "Invalid Email or Password"

    return render_template("student_login.html")


# =========================
# STUDENT DASHBOARD
# =========================

@app.route("/student/dashboard")
def student_dashboard():

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    return render_template(
        "student_dashboard.html"
    )


# =========================
# STUDENT PROFILE
# =========================

@app.route("/student/profile")
def student_profile():

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM students
        WHERE id = %s
        """,
        (
            session["student_id"],
        )
    )

    student = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "student_profile.html",
        student=student
    )


# =========================
# STUDENT RESUME UPLOAD
# =========================

@app.route(
    "/student/upload-resume",
    methods=["POST"]
)
def upload_resume():

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    file = request.files.get("resume")

    if not file:
        return "Please select a resume file."

    if file.filename == "":
        return "Please select a resume file."

    if not file.filename.lower().endswith(".pdf"):
        return "Only PDF files are allowed."

    filename = secure_filename(file.filename)

    resume_folder = os.path.join(
        "static",
        "resumes"
    )

    os.makedirs(
        resume_folder,
        exist_ok=True
    )

    file_path = os.path.join(
        resume_folder,
        filename
    )

    file.save(file_path)

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE students
        SET resume = %s
        WHERE id = %s
        """,
        (
            filename,
            session["student_id"]
        )
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect(
        url_for("student_profile")
    )


# =========================
# AVAILABLE JOBS
# =========================

@app.route("/student/jobs")
def available_jobs():

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM jobs
        ORDER BY id DESC
        """
    )

    jobs = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "available_jobs.html",
        jobs=jobs
    )


# =========================
# JOB DETAILS
# =========================

@app.route(
    "/student/job/<int:job_id>"
)
def job_details(job_id):

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = %s
        """,
        (
            job_id,
        )
    )

    job = cursor.fetchone()

    cursor.close()
    db.close()

    if not job:
        return "Job not found."

    return render_template(
        "job_details.html",
        job=job
    )


# =========================
# APPLY JOB
# =========================

@app.route(
    "/student/apply/<int:job_id>",
    methods=["GET", "POST"]
)
def apply_job(job_id):

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    try:

        # Check whether the student has already applied
        cursor.execute(
            """
            SELECT id
            FROM applications
            WHERE student_id = %s
            AND job_id = %s
            """,
            (
                session["student_id"],
                job_id
            )
        )

        existing_application = cursor.fetchone()

        if existing_application:
            cursor.close()
            db.close()

            return redirect(
                url_for("my_applications")
            )

        # Insert new application
        cursor.execute(
            """
            INSERT INTO applications
            (student_id, job_id, status)
            VALUES (%s, %s, 'Applied')
            """,
            (
                session["student_id"],
                job_id
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("my_applications")
        )

    except mysql.connector.Error as e:

        cursor.close()
        db.close()

        return "Application Error: " + str(e)


# =========================
# MY APPLICATIONS
# =========================

@app.route("/student/applications")
def my_applications():

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT
            jobs.id,
            jobs.job_title,
            jobs.company_name,
            jobs.location,
            jobs.job_type,
            applications.application_date,
            applications.status,
            applications.id
        FROM applications
        INNER JOIN jobs
            ON applications.job_id = jobs.id
        WHERE applications.student_id = %s
        ORDER BY applications.id DESC
        """,
        (
            session["student_id"],
        )
    )

    applications = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "my_applications.html",
        applications=applications
    )


# =========================
# CANCEL APPLICATION
# =========================

@app.route("/student/cancel-application/<int:application_id>", methods=["POST"])
def cancel_application(application_id):

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM applications
            WHERE id = %s
            AND student_id = %s
            """,
            (
                application_id,
                session["student_id"]
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("my_applications")
        )

    except mysql.connector.Error as e:

        cursor.close()
        db.close()

        return "Cancel Application Error: " + str(e)


# =========================
# STUDENT PLACEMENT STATUS
# =========================

@app.route("/student/placement-status")
def placement_status():

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT
            jobs.job_title,
            jobs.company_name,
            applications.application_date,
            applications.status
        FROM applications
        INNER JOIN jobs
            ON applications.job_id = jobs.id
        WHERE applications.student_id = %s
        ORDER BY applications.id DESC
        """,
        (
            session["student_id"],
        )
    )

    placements = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "placement_status.html",
        placements=placements
    )


# =========================
# RECOMMENDED JOBS
# =========================

@app.route("/student/recommended-jobs")
def recommended_jobs():

    if "student_id" not in session:
        return redirect(
            url_for("student_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT
            course,
            cgpa,
            skills
        FROM students
        WHERE id = %s
        """,
        (
            session["student_id"],
        )
    )

    student = cursor.fetchone()

    if not student:
        cursor.close()
        db.close()
        return "Student not found."

    student_course = student[0].lower()
    student_cgpa = float(student[1])
    student_skills = [
        skill.strip().lower()
        for skill in student[2].split(",")
    ]

    cursor.execute(
        """
        SELECT *
        FROM jobs
        WHERE min_cgpa <= %s
        """,
        (
            student_cgpa,
        )
    )

    all_jobs = cursor.fetchall()

    recommended = []

    for job in all_jobs:

        job_course = job[5].lower()
        job_skills = [
            skill.strip().lower()
            for skill in job[7].split(",")
        ]

        course_match = (
            student_course in job_course
        )

        matched_skills = []

        for skill in student_skills:

            if skill in job_skills:
                matched_skills.append(skill)

        skill_match = len(matched_skills)

        if course_match or skill_match > 0:

            recommended.append(
                (
                    job,
                    skill_match,
                    len(job_skills)
                )
            )

    cursor.close()
    db.close()

    return render_template(
        "recommended_jobs.html",
        jobs=recommended
    )


# ============================================================
# COMPANY MODULE
# ============================================================


# =========================
# COMPANY REGISTER
# =========================

@app.route(
    "/company/register",
    methods=["GET", "POST"]
)
def company_register():

    if request.method == "POST":

        company_name = request.form["company_name"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        password = request.form["password"]
        location = request.form["location"]
        description = request.form["description"]

        db = get_db_connection()
        cursor = db.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO companies
                (
                    company_name,
                    email,
                    mobile,
                    password,
                    location,
                    description
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    company_name,
                    email,
                    mobile,
                    password,
                    location,
                    description
                )
            )

            db.commit()

            cursor.close()
            db.close()

            return redirect(
                url_for("company_login")
            )

        except mysql.connector.Error as e:

            cursor.close()
            db.close()

            return "Registration Error: " + str(e)

    return render_template(
        "company_register.html"
    )


# =========================
# COMPANY LOGIN
# =========================

@app.route(
    "/company/login",
    methods=["GET", "POST"]
)
def company_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT id
            FROM companies
            WHERE email = %s
            AND password = %s
            """,
            (
                email,
                password
            )
        )

        company = cursor.fetchone()

        cursor.close()
        db.close()

        if company:

            session["company_id"] = company[0]

            return redirect(
                url_for("company_dashboard")
            )

        return "Invalid Email or Password"

    return render_template(
        "company_login.html"
    )


# =========================
# COMPANY DASHBOARD
# =========================

@app.route("/company/dashboard")
def company_dashboard():

    if "company_id" not in session:
        return redirect(
            url_for("company_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE id = %s
        """,
        (
            session["company_id"],
        )
    )

    company = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "company_dashboard.html",
        company=company
    )


# =========================
# COMPANY PROFILE
# =========================

@app.route("/company/profile")
def company_profile():

    if "company_id" not in session:
        return redirect(
            url_for("company_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE id = %s
        """,
        (
            session["company_id"],
        )
    )

    company = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "company_profile.html",
        company=company
    )


# =========================
# POST JOB
# =========================

@app.route(
    "/company/post-job",
    methods=["GET", "POST"]
)
def post_job():

    if "company_id" not in session:
        return redirect(
            url_for("company_login")
        )

    if request.method == "POST":

        job_title = request.form["job_title"]
        location = request.form["location"]
        job_type = request.form["job_type"]
        required_course = request.form["required_course"]
        min_cgpa = request.form["min_cgpa"]
        required_skills = request.form["required_skills"]
        description = request.form["description"]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT company_name
            FROM companies
            WHERE id = %s
            """,
            (
                session["company_id"],
            )
        )

        company = cursor.fetchone()

        if not company:

            cursor.close()
            db.close()

            return "Company not found."

        company_name = company[0]

        cursor.execute(
            """
            INSERT INTO jobs
            (
                job_title,
                company_name,
                location,
                job_type,
                required_course,
                min_cgpa,
                required_skills,
                description,
                company_id
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                job_title,
                company_name,
                location,
                job_type,
                required_course,
                min_cgpa,
                required_skills,
                description,
                session["company_id"]
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("company_jobs")
        )

    return render_template(
        "post_job.html"
    )


# =========================
# COMPANY MY JOBS
# =========================

@app.route("/company/jobs")
def company_jobs():

    if "company_id" not in session:
        return redirect(
            url_for("company_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM jobs
        WHERE company_id = %s
        ORDER BY id DESC
        """,
        (
            session["company_id"],
        )
    )

    jobs = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "my_jobs.html",
        jobs=jobs
    )


# =========================
# COMPANY APPLICANTS
# =========================

@app.route("/company/applicants")
def company_applicants():

    if "company_id" not in session:
        return redirect(
            url_for("company_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT
            students.name,
            students.email,
            students.mobile,
            jobs.job_title,
            applications.application_date,
            applications.status,
            applications.id
        FROM applications
        INNER JOIN students
            ON applications.student_id = students.id
        INNER JOIN jobs
            ON applications.job_id = jobs.id
        WHERE jobs.company_id = %s
        ORDER BY applications.id DESC
        """,
        (
            session["company_id"],
        )
    )

    applicants = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "applicants.html",
        applicants=applicants
    )


# =========================
# UPDATE APPLICATION STATUS
# =========================

@app.route(
    "/company/update-status/<int:application_id>",
    methods=["POST"]
)
def update_status(application_id):

    if "company_id" not in session:
        return redirect(
            url_for("company_login")
        )

    status = request.form["status"]

    allowed_statuses = [
        "Applied",
        "Shortlisted",
        "Interview",
        "Selected",
        "Rejected"
    ]

    if status not in allowed_statuses:
        return "Invalid status."

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE applications
        INNER JOIN jobs
            ON applications.job_id = jobs.id
        SET applications.status = %s
        WHERE applications.id = %s
        AND jobs.company_id = %s
        """,
        (
            status,
            application_id,
            session["company_id"]
        )
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect(
        url_for("company_applicants")
    )


# ============================================================
# ADMIN MODULE
# ============================================================


# =========================
# ADMIN LOGIN
# =========================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT id
            FROM admin
            WHERE email = %s
            AND password = %s
            """,
            (
                email,
                password
            )
        )

        admin = cursor.fetchone()

        cursor.close()
        db.close()

        if admin:

            session["admin_id"] = admin[0]

            return redirect(
                url_for("admin_dashboard")
            )

        return "Invalid Admin Email or Password"

    return render_template(
        "admin_login.html"
    )


# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin/dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    return render_template(
        "admin_dashboard.html"
    )


# =========================
# ADMIN STUDENTS
# =========================

@app.route("/admin/students")
def admin_students():

    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM students
        ORDER BY id DESC
        """
    )

    students = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_students.html",
        students=students
    )


# =========================
# ADMIN COMPANIES
# =========================

@app.route("/admin/companies")
def admin_companies():

    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM companies
        ORDER BY id DESC
        """
    )

    companies = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_companies.html",
        companies=companies
    )


# =========================
# ADMIN JOBS
# =========================

@app.route("/admin/jobs")
def admin_jobs():

    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM jobs
        ORDER BY id DESC
        """
    )

    jobs = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_jobs.html",
        jobs=jobs
    )


# =========================
# ADMIN APPLICATIONS
# =========================

@app.route("/admin/applications")
def admin_applications():

    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT
            applications.id,
            students.name,
            students.email,
            jobs.job_title,
            jobs.company_name,
            applications.application_date,
            applications.status
        FROM applications
        INNER JOIN students
            ON applications.student_id = students.id
        INNER JOIN jobs
            ON applications.job_id = jobs.id
        ORDER BY applications.id DESC
        """
    )

    applications = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_applications.html",
        applications=applications
    )


# =========================
# PLACEMENT REPORTS
# =========================

@app.route("/admin/placement-reports")
def placement_reports():

    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    # Total Students
    cursor.execute(
        "SELECT COUNT(*) FROM students"
    )

    total_students = cursor.fetchone()[0]

    # Total Companies
    cursor.execute(
        "SELECT COUNT(*) FROM companies"
    )

    total_companies = cursor.fetchone()[0]

    # Total Jobs
    cursor.execute(
        "SELECT COUNT(*) FROM jobs"
    )

    total_jobs = cursor.fetchone()[0]

    # Total Applications
    cursor.execute(
        "SELECT COUNT(*) FROM applications"
    )

    total_applications = cursor.fetchone()[0]

    # Applied
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM applications
        WHERE status = 'Applied'
        """
    )

    total_applied = cursor.fetchone()[0]

    # Shortlisted
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM applications
        WHERE status = 'Shortlisted'
        """
    )

    total_shortlisted = cursor.fetchone()[0]

    # Interview
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM applications
        WHERE status = 'Interview'
        """
    )

    total_interview = cursor.fetchone()[0]

    # Selected
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM applications
        WHERE status = 'Selected'
        """
    )

    total_selected = cursor.fetchone()[0]

    # Rejected
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM applications
        WHERE status = 'Rejected'
        """
    )

    total_rejected = cursor.fetchone()[0]

    cursor.close()
    db.close()

    return render_template(
        "placement_reports.html",
        total_students=total_students,
        total_companies=total_companies,
        total_jobs=total_jobs,
        total_applications=total_applications,
        total_applied=total_applied,
        total_shortlisted=total_shortlisted,
        total_interview=total_interview,
        total_selected=total_selected,
        total_rejected=total_rejected
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )