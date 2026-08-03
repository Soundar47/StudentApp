from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)
from flask import flash

from datetime import datetime

import os
import json
import pandas as pd

from werkzeug.utils import secure_filename
from functools import wraps

# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)

app.secret_key = "student_management_system_2026"



# ==========================================
# FOLDERS
# ==========================================

DATA_FOLDER = "data"

UG_FOLDER = os.path.join(
    DATA_FOLDER,
    "ug"
)

PG_FOLDER = os.path.join(
    DATA_FOLDER,
    "pg"
)


PHOTO_FOLDER = os.path.join(
    "static",
    "photos"
)

os.makedirs(
    UG_FOLDER,
    exist_ok=True
)


os.makedirs(
    PG_FOLDER,
    exist_ok=True
)


os.makedirs(
    PHOTO_FOLDER,
    exist_ok=True)

app.config["PHOTO_FOLDER"] = PHOTO_FOLDER


# ==========================================
# FILES
# ==========================================

ADMIN_FILE = "admin.json"

LOG_FILE = "activity.log"

# ==========================================
# PHOTO SETTINGS
# ==========================================

ALLOWED_EXTENSIONS = {

    "jpg",
    "jpeg",
    "png"

}
def allowed_photo(filename):

    return (
        "." in filename
        and
        filename.rsplit(".",1)[1].lower()
        in ALLOWED_EXTENSIONS

    )


# ==========================================
# COMMON STUDENT COLUMNS
# ==========================================


COMMON_COLUMNS = [

    "RegNo",
    "Name",
    "Course",
    "Batch",
    "DOB",

    "Community",

    "ParentName",
    "MotherName",

    "faOccupation",
    "moOccupation",

    "Address",
    "Pincode",

    "Mobile",

    "FirstGraduate",

    "BankName",
    "Branch",
    "BankAccount",

    "IFSC",
    "MICR",

    "Aadhar",

    "BloodGroup",

    "UmisID",
    "EmisNo",

    "Email",

    "Photo"

]





# ==========================================
# UG COLUMNS
# ==========================================


UG_COLUMNS = COMMON_COLUMNS + [

    "F1_IE",
    "F1_WE",
    "F1_TOT",
    "F1_MY",

    "F2_IE",
    "F2_WE",
    "F2_TOT",
    "F2_MY",

    "F3_IE",
    "F3_WE",
    "F3_TOT",
    "F3_MY",

    "F4_IE",
    "F4_WE",
    "F4_TOT",
    "F4_MY",


    "Attendance_I",
    "Attendance_II",
    "Attendance_III",
    "Attendance_IV",

    "Overall_Percentage",

    "Incharge"

]





# ==========================================
# PG COLUMNS
# ==========================================


PG_COLUMNS = COMMON_COLUMNS + [

    "26PCS1_IE",
    "26PCS1_WE",
    "26PCS1_TOT",
    "26PCS1_MY",

    "26PCS2_IE",
    "26PCS2_WE",
    "26PCS2_TOT",
    "26PCS2_MY",

    "26PCS3P_IE",
    "26PCS3P_WE",
    "26PCS3P_TOT",
    "26PCS3P_MY",


    "26PCS4_IE",
    "26PCS4_WE",
    "26PCS4_TOT",
    "26PCS4_MY",

    "26PCS5_IE",
    "26PCS5_WE",
    "26PCS5_TOT",
    "26PCS5_MY",


    "26PCS6P_IE",
    "26PCS6P_WE",
    "26PCS6P_TOT",
    "26PCS6P_MY",


    "26PCS7_IE",
    "26PCS7_WE",
    "26PCS7_TOT",
    "26PCS7_MY",

    "26PCS8_IE",
    "26PCS8_WE",
    "26PCS8_TOT",
    "26PCS8_MY",

    "26PCS9P_IE",
    "26PCS9P_WE",
    "26PCS9P_TOT",
    "26PCS9P_MY",


    "26PCS10_IE",
    "26PCS10_WE",
    "26PCS10_TOT",
    "26PCS10_MY",

    "26PCS11_IE",
    "26PCS11_WE",
    "26PCS11_TOT",
    "26PCS11_MY",



    "Attendance_I",
    "Attendance_II",
    "Attendance_III",
    "Attendance_IV",



    "Signature_I",
    "Signature_II",
    "Signature_III",
    "Signature_IV",
    "Signature_Cum",
    "Signature_Prov",


    "Overall_Percentage",

    "Overall_Grade",

    "Incharge"

]


# ==========================================
# LOGIN REQUIRED DECORATOR
# ==========================================
#
# Every admin-only route must confirm session["admin"] is set,
# both for direct URL access and for browser Back/Forward
# navigation after logout. Wrapping the check in a decorator
# means every protected route gets the same check, and a new
# route can't accidentally be added without it.

def login_required(view_func):

    @wraps(view_func)
    def wrapped(*args, **kwargs):

        if not session.get("admin"):

            return redirect(
                url_for("admin_login")
            )

        return view_func(*args, **kwargs)

    return wrapped


# ==========================================
# ADMIN FUNCTIONS
# ==========================================


def load_admin():


    if not os.path.exists(ADMIN_FILE):

        data = {

            "username":"admin",

            "password":"admin12"

        }


        with open(
            ADMIN_FILE,
            "w"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )


        return data




    with open(
        ADMIN_FILE,
        "r"
    ) as file:


        return json.load(file)





def save_admin(data):


    with open(
        ADMIN_FILE,
        "w"
    ) as file:


        json.dump(
            data,
            file,
            indent=4
        )





# ==========================================
# LOG SYSTEM
# ==========================================


def write_log(message):


    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as file:


        file.write(

            datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            +

            " | "

            +

            message

            +

            "\n"

        )





# ==========================================
# CSV PATH
# ==========================================


def get_csv_path(course,batch):


    batch = batch.replace(
        "-",
        "_"
    )



    if course == "UG":

        return os.path.join(
            UG_FOLDER,
            batch+".csv"
        )


    else:

        return os.path.join(
            PG_FOLDER,
            batch+".csv"
        )





# ==========================================
# LOAD CSV
# ==========================================


def load_csv(course,batch):


    path = get_csv_path(
        course,
        batch
    )



    if not os.path.exists(path):

        return None



    try:

        return pd.read_csv(
            path,
            dtype=str
        ).fillna("")



    except:

        return None





# ==========================================
# SAVE CSV
# ==========================================


def save_csv(df,course,batch):


    path = get_csv_path(
        course,
        batch
    )


    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig"
    )
# ==========================================
# CREATE EMPTY BATCH
# ==========================================

def create_empty_batch(course,batch):

    path = get_csv_path(
        course,
        batch
    )


    # Already batch exists
    if os.path.exists(path):
        return False


    columns = (
        UG_COLUMNS
        if course=="UG"
        else PG_COLUMNS
    )


    df = pd.DataFrame(
        columns=columns
    )


    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig"
    )


    return True
# ==========================================
# ADMIN LOGIN
# ==========================================


@app.route(
    "/admin-login",
    methods=["GET","POST"]
)
def admin_login():


    if request.method=="POST":


        username=request.form["username"]

        password=request.form["password"]


        admin=load_admin()



        if (
            username==admin["username"]
            and
            password==admin["password"]
        ):
            session["admin"]=True
            session["last_login"] = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")

            write_log(
                "Admin Login"
            )


            return redirect(
                url_for("admin")
            )



        return render_template(
            "admin_login.html",
            error="Invalid Username or Password"
        )

    return render_template(
        "admin_login.html"
    )


# ==========================================
# LOGOUT
# ==========================================


@app.route("/logout")
def logout():

    write_log(
        "Admin Logout"
    )

    # Clear the whole session (not just the "admin" key) so no
    # leftover session data (last_login, etc.) survives logout.
    session.clear()

    return redirect(
        url_for("admin_login")
    )


# ==========================================
# NO-CACHE FOR PROTECTED PAGES
# ==========================================
#
# Without this, the browser can serve the admin dashboard HTML
# straight from its cache when the Back button is pressed after
# logout — even though the session is gone. These headers force
# the browser to always re-request the page, so the server-side
# login_required check in each route actually runs and redirects
# to the login page.

@app.after_request
def add_no_cache_headers(response):

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )
# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin")
@login_required
def admin():

    ug_batches = []
    pg_batches = []

    total_ug_students = 0
    total_pg_students = 0

    # -------------------------------
    # UG Batches & Students
    # -------------------------------

    for file in os.listdir(UG_FOLDER):

        if file.endswith(".csv"):

            batch = file.replace(".csv", "")
            ug_batches.append(batch)

            df = load_csv("UG", batch)

            if df is not None:
                total_ug_students += len(df)

    # -------------------------------
    # PG Batches & Students
    # -------------------------------

    for file in os.listdir(PG_FOLDER):

        if file.endswith(".csv"):

            batch = file.replace(".csv", "")
            pg_batches.append(batch)

            df = load_csv("PG", batch)

            if df is not None:
                total_pg_students += len(df)

    # -------------------------------
    # Dashboard Statistics
    # -------------------------------

    total_students = total_ug_students + total_pg_students

    total_ug_batches = len(ug_batches)
    total_pg_batches = len(pg_batches)

    total_batches = total_ug_batches + total_pg_batches

    # -------------------------------
    # Latest Uploaded Batch
    # -------------------------------

    latest_batch = "-"

    all_batches = []

    for batch in ug_batches:
        all_batches.append(("UG", batch))

    for batch in pg_batches:
        all_batches.append(("PG", batch))

    if all_batches:

        latest_course, latest = sorted(all_batches, key=lambda x: x[1])[-1]

        latest_batch = f"{latest_course} - {latest}"

    # -------------------------------
    # Last Login
    # -------------------------------

    last_login = session.get("last_login", "-")

    # -------------------------------
    # Recent Activities
    # -------------------------------

    recent_logs = []

    if os.path.exists("activity.log"):

        with open("activity.log", "r", encoding="utf-8") as file:

            recent_logs = [
                line.strip()
                for line in file.readlines()[-5:]
            ]

        recent_logs.reverse()

    # -------------------------------
    # Render
    # -------------------------------

    return render_template(

        "admin.html",

        ug_batches=sorted(ug_batches),
        pg_batches=sorted(pg_batches),

        total_students=total_students,

        total_ug_students=total_ug_students,
        total_pg_students=total_pg_students,

        total_ug_batches=total_ug_batches,
        total_pg_batches=total_pg_batches,

        total_batches=total_batches,

        latest_batch=latest_batch,

        last_login=last_login,

        recent_logs=recent_logs

    )

# ==========================================
# UPLOAD DATA
# ==========================================


@app.route(
    "/upload-data",
    methods=["POST"]
)
@login_required
def upload_data():


    course=request.form["course"].upper()


    batch=request.form["batch"]\
        .strip()\
        .replace("-","_")



    file=request.files.get(
        "datafile"
    )



    if not file:

        return redirect(
            url_for("admin")
        )



    try:


        filename=file.filename.lower()



        if filename.endswith(".csv"):


            df=pd.read_csv(
                file,
                dtype=str
            )



        elif (
            filename.endswith(".xls")
            or
            filename.endswith(".xlsx")
        ):


            df=pd.read_excel(
                file,
                dtype=str
            )


        else:


            return render_template(
                "admin.html",
                error="Only CSV/XLS/XLSX allowed"
            )



    except Exception as e:


        return render_template(
            "admin.html",
            error=str(e)
        )



    df=df.fillna("")



    columns = (
        UG_COLUMNS
        if course=="UG"
        else PG_COLUMNS
    )



    for col in columns:


        if col not in df.columns:

            df[col]=""



    df=df[columns]



    save_csv(
        df,
        course,
        batch
    )



    write_log(
        f"Uploaded {course} {batch}"
    )


    return redirect(
        url_for("admin")
    )

# ==========================================
# ADD STUDENT PAGE
# ==========================================


@app.route("/add-student")
@login_required
def add_student():


    course=request.args.get(
        "course"
    )

    batch=request.args.get(
        "batch"
    )



    df=load_csv(
        course,
        batch
    )



    if df is None:

        return redirect(
            url_for("admin")
        )



    return render_template(
        "add_student.html",
        course=course,
        batch=batch,
        columns=df.columns
    )







# ==========================================
# SAVE NEW STUDENT
# ==========================================


@app.route(
    "/save-new-student",
    methods=["POST"]
)
@login_required
def save_new_student():


    course=request.form["course"]

    batch=request.form["batch"]


    df=load_csv(
        course,
        batch
    )


    if df is None:

        return redirect(
            url_for("admin")
        )



    new_student={}



    for col in df.columns:


        new_student[col]=request.form.get(
            col,
            ""
        )



    regno=request.form["RegNo"]



    # PHOTO

    if "Photo" in request.files:


        photo=request.files["Photo"]



        if photo.filename:


            if allowed_photo(
                photo.filename
            ):


                ext=os.path.splitext(
                    photo.filename
                )[1]


                filename=regno+ext


                photo.save(
                    os.path.join(
                        PHOTO_FOLDER,
                        filename
                    )
                )


                new_student["Photo"]=filename




    df.loc[len(df)] = new_student



    save_csv(
        df,
        course,
        batch
    )


    write_log(
        f"Added Student {regno}"
    )



    return redirect(
        url_for("admin")
    )
# ==========================================
# SAVE PG STUDENT EDIT
# ==========================================

@app.route("/save-pg", methods=["POST"])
@login_required
def save_pg():

    course = request.form["course"].upper()
    batch = request.form["batch"].replace("-", "_")
    regno = request.form["RegNo"]

    df = load_csv(course, batch)

    if df is None:
        return redirect(url_for("admin"))

    index = df[
        df["RegNo"].astype(str) == regno
    ].index

    if len(index) == 0:
        return redirect(url_for("admin"))

    row = index[0]

    # Remove Photo
    if request.form.get("remove_photo") == "1":

        old_photo = df.loc[row, "Photo"]

        if old_photo:

            photo_path = os.path.join(PHOTO_FOLDER, old_photo)

            if os.path.exists(photo_path):
                os.remove(photo_path)

        df.loc[row, "Photo"] = ""

    # Update all fields
    for column in df.columns:

        if column in request.form:
            df.loc[row, column] = request.form.get(column, "")

    # Upload New Photo
    if "Photo" in request.files:

        photo = request.files["Photo"]

        if photo.filename != "":

            if allowed_photo(photo.filename):

                ext = os.path.splitext(photo.filename)[1]

                filename = regno + ext

                photo.save(
                    os.path.join(PHOTO_FOLDER, filename)
                )

                df.loc[row, "Photo"] = filename

    save_csv(df, course, batch)

    write_log(f"Updated PG Student | {regno}")

    student = df.loc[row].to_dict()

    return render_template(
        "pg_result.html",
        student=student,
        course=course,
        batch=batch,
        message="Student details updated successfully"
    )
# ==========================================
# SAVE UG STUDENT EDIT
# ==========================================

@app.route("/save-ug", methods=["POST"])
@login_required
def save_ug():

    course = request.form["course"].upper()
    batch = request.form["batch"].replace("-", "_")
    regno = request.form["RegNo"]

    df = load_csv(course, batch)

    if df is None:
        return redirect(url_for("admin"))

    student_index = df[
        df["RegNo"].astype(str) == regno
    ].index

    if len(student_index) == 0:
        return redirect(url_for("admin"))

    row = student_index[0]

    # Remove Photo
    if request.form.get("remove_photo") == "1":

        old_photo = df.loc[row, "Photo"]

        if old_photo:

            photo_path = os.path.join(PHOTO_FOLDER, old_photo)

            if os.path.exists(photo_path):
                os.remove(photo_path)

        df.loc[row, "Photo"] = ""

    # Update values
    for column in df.columns:

        if column in request.form:
            df.loc[row, column] = request.form.get(column, "")

    # Upload New Photo
    if "Photo" in request.files:

        photo = request.files["Photo"]

        if photo.filename != "":

            if allowed_photo(photo.filename):

                ext = os.path.splitext(photo.filename)[1]

                filename = regno + ext

                photo.save(
                    os.path.join(PHOTO_FOLDER, filename)
                )

                df.loc[row, "Photo"] = filename

    save_csv(df, course, batch)

    write_log(f"Updated UG Student | {regno}")

    student = df.loc[row].to_dict()

    return render_template(
        "ug_result.html",
        student=student,
        course=course,
        batch=batch,
        message="Student details updated successfully"
    )
# ==========================================
# ACTIVITY LOG
# ==========================================

@app.route("/activity-log")
@login_required
def activity_log():

    logs=[]


    if os.path.exists(LOG_FILE):

        with open(
            LOG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            logs=file.readlines()


    logs.reverse()


    return render_template(
        "activity_log.html",
        logs=logs
    )
# ==========================================
# DELETE STUDENT
# ==========================================

@app.route("/delete-student", methods=["POST"])
@login_required
def delete_student():

    course=request.form["course"]

    batch=request.form["batch"]

    regno=request.form["RegNo"]


    df=load_csv(
        course,
        batch
    )


    if df is not None:


        df=df[
            df["RegNo"].astype(str)!=regno
        ]


        save_csv(
            df,
            course,
            batch
        )


        write_log(
            f"Deleted Student {regno}"
        )


    return redirect(
        url_for("admin")
    )
# ==========================================
# CHANGE PASSWORD
# ==========================================

@app.route(
    "/change-password",
    methods=["GET","POST"]
)
@login_required
def change_password():

    if request.method=="POST":


        new_password=request.form["password"]


        admin=load_admin()


        admin["password"]=new_password


        save_admin(admin)


        write_log(
            "Password Changed"
        )


        return redirect(
            url_for("admin")
        )


    return render_template(
        "change_password.html"
    )
# ==========================================
# VIEW STUDENTS
# ==========================================

@app.route("/view-students", methods=["GET", "POST"])
@login_required
def view_students():

    students = []

    error = ""

    course = ""

    batch = ""


    if request.method == "POST":


        course = request.form.get(
            "course",
            ""
        ).upper()


        batch = request.form.get(
            "batch",
            ""
        )


        if batch:

            batch = batch.strip().replace(
                "-",
                "_"
            )



        df = load_csv(
            course,
            batch
        )



        if df is None:

            error = "Student file not found"


        else:

            df = df.fillna("")


            students = df.to_dict(
                orient="records"
            )



    return render_template(
        "view_students.html",
        students=students,
        course=course,
        batch=batch,
        error=error
    )
# ==========================================
# CLEAR ACTIVITY LOG
# ==========================================

@app.route("/clear-log", methods=["POST"])
@login_required
def clear_log():

    if os.path.exists(LOG_FILE):

        open(
            LOG_FILE,
            "w",
            encoding="utf-8"
        ).close()


    write_log(
        "Activity Log Cleared"
    )


    return redirect(
        url_for("activity_log")
    )

# ==========================================
#  TIME TABLE
# ==========================================
@app.route("/timetable")
@login_required
def timetable():
    return render_template("time_table.html")
# ==========================================
# DELETE BATCH
# ==========================================

@app.route("/delete-batch", methods=["POST"])
@login_required
def delete_batch():

    course = request.form["course"].upper()
    batch = request.form["batch"].strip().replace("-", "_")

    path = get_csv_path(course, batch)

    if os.path.exists(path):

        os.remove(path)

        write_log(
            f"Deleted {course} Batch {batch}"
        )

    else:
        write_log(
            f"Delete Failed | {course} Batch {batch} Not Found"
        )

    return redirect(url_for("admin"))
# ==========================================
# ADD BATCHES
# ==========================================
@app.route("/add-batch", methods=["POST"])
@login_required
def add_batch():

    course = request.form["course"].upper()

    batch = request.form["batch"].strip()
    batch = batch.replace("-", "_")


    result = create_empty_batch(course,batch)
    if result:

        flash(
            f"{course} {batch} Batch Created Successfully",
            "success"
        )

    else:

        flash(
            "Failed to create batch",
            "error"
        )

    return redirect(
        url_for("admin")
    )

# ==========================================
# STUDENT SEARCH
# ==========================================
@app.route("/student-search", methods=["GET", "POST"])
@login_required
def student_search():

    # Searching only reads data, so searches submitted from the UI use GET.
    # This keeps the search URL in browser history without a POST resubmission
    # warning when the user clicks Back or Refresh.
    search_data = request.args if request.method == "GET" else request.form

    course = search_data["course"].upper()
    batch = search_data["batch"].strip().replace("-", "_")
    search_type = search_data["search_type"]
    keyword = search_data["keyword"].strip()

    df = load_csv(course, batch)
    if df is None:
        flash("Batch not found.", "error")
        return redirect(url_for("admin"))

    # Register Number Search
    if search_type == "regno":

        student = df[df["RegNo"].astype(str) == keyword]

        if student.empty:
            flash("Student not found.", "error")
            return redirect(url_for("admin"))

        data = student.iloc[0].to_dict()

        if course == "UG":
            return render_template(
                "ug_result.html",
                student=data,
                course=course,
                batch=batch
            )

        return render_template(
            "pg_result.html",
            student=data,
            course=course,
            batch=batch
        )

    # Name Search
    students = df[
        df["Name"].astype(str).str.contains(keyword, case=False, na=False)
    ]

    if students.empty:
        flash("Student not found.", "error")
        return redirect(url_for("admin"))

    return render_template(
        "name_result.html",
        students=students.to_dict(orient="records"),
        course=course,
        batch=batch
    )
# ==========================================
# RUN SERVER
# ==========================================

if __name__=="__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
