from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    flash
)

from datetime import datetime

import os
import json
import shutil
import tempfile
import zipfile
import stat

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
# BACKUP FOLDER
# ==========================================

BACKUP_FOLDER = "backups"

os.makedirs(
    BACKUP_FOLDER,
    exist_ok=True
)
# ==========================================
# DOB FORMATTING
# ==========================================

def format_dob_for_html(dob):
    """
    Convert DOB into HTML date input format.

    CSV / stored DOB:
        15-08-2000

    HTML <input type="date">:
        2000-08-15
    """

    if not dob:
        return ""

    try:
        dob = str(dob).strip()

        return pd.to_datetime(
            dob,
            dayfirst=True
        ).strftime("%Y-%m-%d")

    except (ValueError, TypeError):
        return ""


def format_dob_for_csv(dob):
    """
    Convert HTML date input format into
    standard CSV format.

    HTML:
        2000-08-15

    CSV:
        15-08-2000
    """

    if not dob:
        return ""

    try:
        dob = str(dob).strip()

        return pd.to_datetime(
            dob,
            format="%Y-%m-%d"
        ).strftime("%d-%m-%Y")

    except (ValueError, TypeError):
        return ""
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
    "AnualIncome",

    "BankName",
    "Branch",
    "BankAccount",

    "IFSC",
    "MICR",

    "Aadhar",

    "BloodGroup",

    "UmisID",
    "EmisNo",
    "EmisID",

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

        df = pd.read_csv(
            path,
            dtype=str,
            engine="python",
            on_bad_lines="skip"
        )

        return df.fillna("")



    except Exception:

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
# BACKUP & RESTORE SYSTEM
# ==========================================

BACKUP_ALLOWED_FILES = {
    "admin.json",
    "activity.log"
}


def get_backup_filename():
    """
    Generate a unique backup filename.
    """

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    return f"StudentApp_Backup_{timestamp}.zip"


def is_safe_zip_member(member_name):
    """
    Prevent ZIP path traversal attacks.

    Reject paths such as:
        ../../admin.json
        ../../../something
    """

    normalized = os.path.normpath(member_name)

    if normalized.startswith(".."):
        return False

    if os.path.isabs(normalized):
        return False

    return True


def is_allowed_backup_member(member_name):
    """
    Only allow files/directories belonging to our
    StudentApp backup structure.
    """

    normalized = member_name.replace("\\", "/").strip("/")

    allowed_prefixes = (
        "data/",
        "static/photos/",
        "uploads/"
    )

    if normalized in BACKUP_ALLOWED_FILES:
        return True

    for prefix in allowed_prefixes:
        if normalized.startswith(prefix):
            return True

    return False


def validate_backup_zip(zip_path):
    """
    Validate that a ZIP is a StudentApp backup
    and doesn't contain dangerous paths/files.
    """

    try:

        with zipfile.ZipFile(zip_path, "r") as archive:

            members = archive.infolist()

            if not members:
                return False, "Backup ZIP is empty."

            valid_file_found = False

            for member in members:

                name = member.filename

                # Path traversal protection
                if not is_safe_zip_member(name):
                    return False, f"Unsafe path found: {name}"

                # Symlink protection
                mode = member.external_attr >> 16

                if stat.S_ISLNK(mode):
                    return False, "Backup contains an unsafe symbolic link."

                # Ignore directory entries
                if name.endswith("/"):
                    continue

                if not is_allowed_backup_member(name):
                    return False, f"Invalid backup file: {name}"

                valid_file_found = True

            if not valid_file_found:
                return False, "Backup contains no valid application files."

        return True, "Backup is valid."

    except zipfile.BadZipFile:
        return False, "The uploaded file is not a valid ZIP backup."

    except Exception as e:
        return False, str(e)


def create_backup(reason="Manual Backup"):
    """
    Create a complete ZIP backup of the StudentApp.

    Returns:
        backup_path
    """

    filename = get_backup_filename()

    backup_path = os.path.join(
        BACKUP_FOLDER,
        filename
    )

    with zipfile.ZipFile(
        backup_path,
        "w",
        compression=zipfile.ZIP_DEFLATED
    ) as archive:

        # -----------------------------
        # DATA
        # -----------------------------

        if os.path.exists(DATA_FOLDER):

            for root, dirs, files in os.walk(DATA_FOLDER):

                for file in files:

                    full_path = os.path.join(
                        root,
                        file
                    )

                    archive_name = os.path.relpath(
                        full_path,
                        "."
                    )

                    archive.write(
                        full_path,
                        archive_name
                    )

        # -----------------------------
        # PHOTOS
        # -----------------------------

        if os.path.exists(PHOTO_FOLDER):

            for root, dirs, files in os.walk(PHOTO_FOLDER):

                for file in files:

                    full_path = os.path.join(
                        root,
                        file
                    )

                    archive_name = os.path.relpath(
                        full_path,
                        "."
                    )

                    archive.write(
                        full_path,
                        archive_name
                    )

        # -----------------------------
        # UPLOADS
        # -----------------------------

        uploads_folder = "uploads"

        if os.path.exists(uploads_folder):

            for root, dirs, files in os.walk(
                uploads_folder
            ):

                for file in files:

                    full_path = os.path.join(
                        root,
                        file
                    )

                    archive_name = os.path.relpath(
                        full_path,
                        "."
                    )

                    archive.write(
                        full_path,
                        archive_name
                    )

        # -----------------------------
        # ADMIN FILE
        # -----------------------------

        if os.path.exists(ADMIN_FILE):

            archive.write(
                ADMIN_FILE,
                ADMIN_FILE
            )

        # -----------------------------
        # ACTIVITY LOG
        # -----------------------------

        if os.path.exists(LOG_FILE):

            archive.write(
                LOG_FILE,
                LOG_FILE
            )

    write_log(
        f"Backup Created | {reason} | {filename}"
    )

    return backup_path


def restore_backup(zip_path):
    """
    Safely restore a StudentApp backup.

    Before restoring, the current application is
    automatically backed up.
    """

    valid, message = validate_backup_zip(
        zip_path
    )

    if not valid:

        return False, message

    # ------------------------------------------
    # SAFETY BACKUP BEFORE RESTORE
    # ------------------------------------------

    try:

        safety_backup = create_backup(
            "Automatic Safety Backup Before Restore"
        )

    except Exception as e:

        return False, (
            "Could not create safety backup. "
            f"Restore cancelled: {e}"
        )

    # ------------------------------------------
    # TEMPORARY EXTRACTION
    # ------------------------------------------

    temp_folder = tempfile.mkdtemp(
        prefix="studentapp_restore_"
    )

    try:

        with zipfile.ZipFile(
            zip_path,
            "r"
        ) as archive:

            archive.extractall(
                temp_folder
            )

        # --------------------------------------
        # RESTORE DATA
        # --------------------------------------

        extracted_data = os.path.join(
            temp_folder,
            "data"
        )

        if os.path.exists(extracted_data):

            if os.path.exists(DATA_FOLDER):
                shutil.rmtree(DATA_FOLDER)

            shutil.copytree(
                extracted_data,
                DATA_FOLDER
            )

        # --------------------------------------
        # RESTORE PHOTOS
        # --------------------------------------

        extracted_photos = os.path.join(
            temp_folder,
            "static",
            "photos"
        )

        if os.path.exists(extracted_photos):

            if os.path.exists(PHOTO_FOLDER):
                shutil.rmtree(PHOTO_FOLDER)

            os.makedirs(
                PHOTO_FOLDER,
                exist_ok=True
            )

            shutil.copytree(
                extracted_photos,
                PHOTO_FOLDER,
                dirs_exist_ok=True
            )

        # --------------------------------------
        # RESTORE UPLOADS
        # --------------------------------------

        extracted_uploads = os.path.join(
            temp_folder,
            "uploads"
        )

        if os.path.exists(extracted_uploads):

            uploads_folder = "uploads"

            if os.path.exists(uploads_folder):
                shutil.rmtree(uploads_folder)

            shutil.copytree(
                extracted_uploads,
                uploads_folder
            )

        # --------------------------------------
        # RESTORE ADMIN
        # --------------------------------------

        extracted_admin = os.path.join(
            temp_folder,
            ADMIN_FILE
        )

        if os.path.exists(extracted_admin):

            shutil.copy2(
                extracted_admin,
                ADMIN_FILE
            )

        # --------------------------------------
        # RESTORE ACTIVITY LOG
        # --------------------------------------

        extracted_log = os.path.join(
            temp_folder,
            LOG_FILE
        )

        if os.path.exists(extracted_log):

            shutil.copy2(
                extracted_log,
                LOG_FILE
            )

        write_log(
            "Backup Restored Successfully"
        )

        return True, safety_backup

    except Exception as e:

        return False, (
            "Restore failed. "
            f"Your previous data is available in: "
            f"{safety_backup}"
        )

    finally:

        shutil.rmtree(
            temp_folder,
            ignore_errors=True
        )
# ==========================================
# CREATE BACKUP ROUTE
# ==========================================

@app.route(
    "/create-backup",
    methods=["POST"]
)
@login_required
def create_backup_route():

    try:

        backup_path = create_backup(
            "Manual Backup"
        )

        filename = os.path.basename(
            backup_path
        )

        flash(
            f"Backup created successfully: {filename}",
            "success"
        )

    except Exception as e:

        flash(
            f"Backup creation failed: {e}",
            "error"
        )

    return redirect(
        url_for("backup_restore")
    )

def get_backup_files():
    """
    Return available backup ZIP files,
    newest first.
    """

    backups = []

    if not os.path.exists(
        BACKUP_FOLDER
    ):
        return backups

    for filename in os.listdir(
        BACKUP_FOLDER
    ):

        if not filename.lower().endswith(
            ".zip"
        ):
            continue

        path = os.path.join(
            BACKUP_FOLDER,
            filename
        )

        if not os.path.isfile(path):
            continue

        try:

            size = os.path.getsize(path)

            modified = os.path.getmtime(path)

            backups.append({

                "filename": filename,

                "size": size,

                "size_mb": round(
                    size / (1024 * 1024),
                    2
                ),

                "modified": datetime.fromtimestamp(
                    modified
                ).strftime(
                    "%d-%m-%Y %I:%M:%S %p"
                ),

                "timestamp": modified

            })

        except OSError:
            continue

    backups.sort(
        key=lambda x: x["timestamp"],
        reverse=True
    )

    return backups
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

            df = load_csv(
                "UG",
                batch
            )

            if df is not None:

                total_ug_students += len(df)

    # -------------------------------
    # PG Batches & Students
    # -------------------------------

    for file in os.listdir(PG_FOLDER):

        if file.endswith(".csv"):

            batch = file.replace(".csv", "")

            pg_batches.append(batch)

            df = load_csv(
                "PG",
                batch
            )

            if df is not None:

                total_pg_students += len(df)

    # -------------------------------
    # Dashboard Statistics
    # -------------------------------

    total_students = (
        total_ug_students
        +
        total_pg_students
    )

    total_ug_batches = len(
        ug_batches
    )

    total_pg_batches = len(
        pg_batches
    )

    total_batches = (
        total_ug_batches
        +
        total_pg_batches
    )

    # -------------------------------
    # Latest Uploaded Batch
    # -------------------------------

    latest_batch = "-"

    all_batches = []

    for batch in ug_batches:

        all_batches.append(
            ("UG", batch)
        )

    for batch in pg_batches:

        all_batches.append(
            ("PG", batch)
        )

    if all_batches:

        latest_course, latest = sorted(
            all_batches,
            key=lambda x: x[1]
        )[-1]

        latest_batch = (
            f"{latest_course} - {latest}"
        )

    # -------------------------------
    # Last Login
    # -------------------------------

    last_login = session.get(
        "last_login",
        "-"
    )

    # -------------------------------
    # Recent Activities
    # -------------------------------

    recent_logs = []

    if os.path.exists(LOG_FILE):

        with open(
            LOG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            recent_logs = [
                line.strip()
                for line in file.readlines()[-5:]
            ]

        recent_logs.reverse()

    # -------------------------------
    # IMPORTANT: RETURN TEMPLATE
    # -------------------------------

    return render_template(

        "admin.html",

        ug_batches=sorted(
            ug_batches
        ),

        pg_batches=sorted(
            pg_batches
        ),

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
# BACKUP & RESTORE PAGE
# ==========================================

@app.route("/backup-restore")
@login_required
def backup_restore():

    backups = get_backup_files()

    return render_template(
        "backup_restore.html",
        backups=backups
    )
# ==========================================
# DOWNLOAD BACKUP
# ==========================================

@app.route(
    "/download-backup/<filename>"
)
@login_required
def download_backup(filename):

    filename = secure_filename(
        filename
    )

    path = os.path.join(
        BACKUP_FOLDER,
        filename
    )

    if not os.path.isfile(path):

        flash(
            "Backup file not found.",
            "error"
        )

        return redirect(
            url_for("backup_restore")
        )

    return send_file(
        path,
        as_attachment=True,
        download_name=filename
    )
# ==========================================
# UPLOAD BACKUP
# ==========================================

@app.route(
    "/upload-backup",
    methods=["POST"]
)
@login_required
def upload_backup():

    file = request.files.get(
        "backup_file"
    )

    if not file or not file.filename:

        flash(
            "Please select a backup ZIP file.",
            "error"
        )

        return redirect(
            url_for("backup_restore")
        )

    filename = secure_filename(
        file.filename
    )

    if not filename.lower().endswith(".zip"):

        flash(
            "Only ZIP backup files are allowed.",
            "error"
        )

        return redirect(
            url_for("backup_restore")
        )

    # Add upload timestamp to prevent accidental overwrite
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"Uploaded_{timestamp}_{filename}"
    )

    path = os.path.join(
        BACKUP_FOLDER,
        filename
    )

    try:

        file.save(path)

        valid, message = validate_backup_zip(
            path
        )

        if not valid:

            os.remove(path)

            flash(
                f"Invalid backup: {message}",
                "error"
            )

            return redirect(
                url_for("backup_restore")
            )

        write_log(
            f"Backup Uploaded | {filename}"
        )

        flash(
            f"Backup uploaded successfully: {filename}",
            "success"
        )

    except Exception as e:

        if os.path.exists(path):
            os.remove(path)

        flash(
            f"Backup upload failed: {e}",
            "error"
        )

    return redirect(
        url_for("backup_restore")
    )
# ==========================================
# RESTORE BACKUP
# ==========================================

@app.route(
    "/restore-backup",
    methods=["POST"]
)
@login_required
def restore_backup_route():

    filename = request.form.get(
        "filename",
        ""
    )

    filename = secure_filename(
        filename
    )

    if not filename:

        flash(
            "Invalid backup filename.",
            "error"
        )

        return redirect(
            url_for("backup_restore")
        )

    path = os.path.join(
        BACKUP_FOLDER,
        filename
    )

    if not os.path.isfile(path):

        flash(
            "Backup file not found.",
            "error"
        )

        return redirect(
            url_for("backup_restore")
        )

    success, result = restore_backup(
        path
    )

    if success:

        flash(
            "Backup restored successfully. "
            "A safety backup was created automatically.",
            "success"
        )

        # The restored admin.json may contain a different
        # password, so the current session should be removed.
        session.clear()

        return redirect(
            url_for("admin_login")
        )

    flash(
        f"Restore failed: {result}",
        "error"
    )

    return redirect(
        url_for("backup_restore")
    )
# ==========================================
# DELETE BACKUP
# ==========================================

@app.route(
    "/delete-backup",
    methods=["POST"]
)
@login_required
def delete_backup():

    filename = request.form.get(
        "filename",
        ""
    )

    filename = secure_filename(
        filename
    )

    if not filename:

        flash(
            "Invalid backup filename.",
            "error"
        )

        return redirect(
            url_for("backup_restore")
        )

    path = os.path.join(
        BACKUP_FOLDER,
        filename
    )

    if not os.path.isfile(path):

        flash(
            "Backup file not found.",
            "error"
        )

        return redirect(
            url_for("backup_restore")
        )

    try:

        os.remove(path)

        write_log(
            f"Backup Deleted | {filename}"
        )

        flash(
            "Backup deleted successfully.",
            "success"
        )

    except Exception as e:

        flash(
            f"Could not delete backup: {e}",
            "error"
        )

    return redirect(
        url_for("backup_restore")
    )
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
# BULK STUDENT PHOTO UPLOAD
# ==========================================

@app.route(
    "/upload-student-photos",
    methods=["GET", "POST"]
)
@login_required
def upload_student_photos():

    if request.method == "GET":

        return render_template(
            "upload_student_photos.html"
        )

    # --------------------------------------
    # GET COURSE AND BATCH
    # --------------------------------------

    course = request.form.get(
        "course",
        ""
    ).upper().strip()

    batch = request.form.get(
        "batch",
        ""
    ).strip().replace("-", "_")

    if course not in ["UG", "PG"]:

        flash(
            "Please select UG or PG.",
            "error"
        )

        return redirect(
            url_for("upload_student_photos")
        )

    if not batch:

        flash(
            "Please enter/select a batch.",
            "error"
        )

        return redirect(
            url_for("upload_student_photos")
        )

    # --------------------------------------
    # LOAD CSV
    # --------------------------------------

    df = load_csv(
        course,
        batch
    )

    if df is None:

        flash(
            f"{course} {batch} CSV file not found.",
            "error"
        )

        return redirect(
            url_for("upload_student_photos")
        )

    # --------------------------------------
    # GET MULTIPLE PHOTOS
    # --------------------------------------

    photos = request.files.getlist(
        "photos"
    )

    if not photos:

        flash(
            "Please select student photos.",
            "error"
        )

        return redirect(
            url_for("upload_student_photos")
        )

    uploaded = 0
    failed = []

    # --------------------------------------
    # PROCESS EACH PHOTO
    # --------------------------------------

    for photo in photos:

        if not photo or not photo.filename:
            continue

        original_filename = secure_filename(
            photo.filename
        )

        # Check extension
        if not allowed_photo(
            original_filename
        ):

            failed.append(
                f"{original_filename} - Invalid image format"
            )

            continue

        # ----------------------------------
        # GET REGISTER NUMBER FROM FILENAME
        # ----------------------------------

        regno = os.path.splitext(
            original_filename
        )[0].strip()

        if not regno:

            failed.append(
                f"{original_filename} - Register number missing"
            )

            continue

        # ----------------------------------
        # FIND STUDENT
        # ----------------------------------

        student_index = df[
            df["RegNo"].astype(str).str.strip()
            == regno
        ].index

        if len(student_index) == 0:

            failed.append(
                f"{original_filename} - Student {regno} not found"
            )

            continue

        row = student_index[0]

        # ----------------------------------
        # DELETE OLD PHOTO IF EXISTS
        # ----------------------------------

        old_photo = str(
            df.loc[row, "Photo"]
        ).strip()

        if old_photo:

            old_photo_path = os.path.join(
                PHOTO_FOLDER,
                old_photo
            )

            if os.path.exists(
                old_photo_path
            ):

                try:

                    os.remove(
                        old_photo_path
                    )

                except OSError:
                    pass

        # ----------------------------------
        # SAVE PHOTO
        # ----------------------------------

        ext = os.path.splitext(
            original_filename
        )[1].lower()

        filename = (
            secure_filename(regno)
            + ext
        )

        photo_path = os.path.join(
            PHOTO_FOLDER,
            filename
        )

        photo.save(
            photo_path
        )

        # ----------------------------------
        # UPDATE CSV PHOTO COLUMN
        # ----------------------------------

        df.loc[row, "Photo"] = filename

        uploaded += 1

    # --------------------------------------
    # SAVE CSV
    # --------------------------------------

    save_csv(
        df,
        course,
        batch
    )

    # --------------------------------------
    # LOG
    # --------------------------------------

    write_log(
        f"Bulk Photo Upload | "
        f"{course} {batch} | "
        f"Uploaded: {uploaded} | "
        f"Failed: {len(failed)}"
    )

    # --------------------------------------
    # RESULT
    # --------------------------------------

    if uploaded > 0:

        flash(
            f"{uploaded} student photo(s) uploaded successfully.",
            "success"
        )

    if failed:

        flash(
            f"{len(failed)} photo(s) could not be matched.",
            "error"
        )

        for error in failed:

            flash(
                error,
                "error"
            )

    return redirect(
        url_for(
            "upload_student_photos"
        )
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

    validation_error = validate_student_details(request.form, df, is_new=True)
    if validation_error:
        flash(validation_error, "error")
        return redirect(url_for("add_student", course=course, batch=batch))



    new_student={}



    for col in df.columns:


        new_student[col]=request.form.get(
            col,
            ""
        )
        new_student["DOB"] = format_dob_for_csv(
    new_student.get("DOB", "")
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
            else:
                flash("Photo must be a JPG, JPEG, or PNG file.", "error")
                return redirect(url_for("add_student", course=course, batch=batch))




    df.loc[len(df)] = new_student



    save_csv(
        df,
        course,
        batch
    )


    write_log(
        f"Added Student {regno}"
    )



    flash("Student record saved successfully.", "success")
    return redirect(url_for("view_students", course=course, batch=batch))
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
    # Convert DOB from HTML format to CSV format
    df.loc[row, "DOB"] = format_dob_for_csv(
    df.loc[row, "DOB"]
)

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

    return redirect(url_for(
        "student_search",
        course=course,
        batch=batch,
        search_type="regno",
        keyword=regno,
        message="Student details updated successfully"
    ))
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
            # Convert DOB from HTML format to CSV format
    df.loc[row, "DOB"] = format_dob_for_csv(
    df.loc[row, "DOB"]
)

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

    return redirect(url_for(
        "student_search",
        course=course,
        batch=batch,
        search_type="regno",
        keyword=regno,
        message="Student details updated successfully"
    ))
#=====================================
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


    if request.method == "POST" or request.args.get("course"):

        source = request.form if request.method == "POST" else request.args
        course = source.get(
            "course",
            ""
        ).upper()


        batch = source.get(
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
        data["DOB"] = format_dob_for_html(data.get("DOB", ""))

        if course == "UG":
            return render_template(
                "ug_result.html",
                student=data,
                course=course,
                batch=batch,
                message=search_data.get("message")
            )

        return render_template(
            "pg_result.html",
            student=data,
            course=course,
            batch=batch,
            message=search_data.get("message")
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
# STUDENT VALIDATION
# ==========================================

def validate_student_details(
    form,
    dataframe,
    is_new=False
):

    """Return a clear validation message for
    the fields common to all records."""

    regno = form.get(
        "RegNo",
        ""
    ).strip()

    name = form.get(
        "Name",
        ""
    ).strip()

    if not regno:

        return "Register number is required."

    if not name:

        return "Student name is required."

    if (
        is_new
        and
        not dataframe[
            dataframe["RegNo"].astype(str) == regno
        ].empty
    ):

        return (
            "A student with this register number "
            "already exists in this batch."
        )

    email = form.get(
        "Email",
        ""
    ).strip()

    if (
        email
        and
        (
            "@" not in email
            or email.startswith("@")
            or email.endswith("@")
        )
    ):

        return "Enter a valid email address."

    return ""
# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
