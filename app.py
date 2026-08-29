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

from datetime import datetime, date

import os
import json
import re
import hashlib
import shutil
import tempfile
import zipfile
import stat
import secrets
import threading

import pandas as pd

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)

# Load a project-local .env before reading configuration.  This is optional;
# deployment platforms should provide real environment variables instead.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

# Never use a publicly known fallback key.  A random development fallback is
# safe against forged cookies but intentionally invalidates sessions on restart;
# production must set SECRET_KEY to retain sessions across restarts/workers.
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(48)
if not os.environ.get("SECRET_KEY"):
    app.logger.warning("SECRET_KEY is not configured; generated a temporary key. Set SECRET_KEY in production.")

# SECURITY FIX: basic cookie hardening. SESSION_COOKIE_SECURE is left
# controllable via an environment variable (default off) so local HTTP
# development is not broken; set SESSION_COOKIE_SECURE=1 once the app is
# served over HTTPS.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_REQUEST_MB", "1024")) * 1024 * 1024
app.config["MAX_FORM_MEMORY_SIZE"] = int(os.environ.get("MAX_FORM_MEMORY_MB", "1")) * 1024 * 1024

# Always resolve local configuration relative to this file, not the directory
# from which Flask/VS Code happened to start the process.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# FOLDERS
# ==========================================

DATA_FOLDER = os.path.join(BASE_DIR, "data")

UG_FOLDER = os.path.join(
    DATA_FOLDER,
    "ug"
)

PG_FOLDER = os.path.join(
    DATA_FOLDER,
    "pg"
)


PHOTO_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "photos"
)

# DEPLOYMENT FIX: previously "uploads" (relative to the process's current
# working directory). Anchoring it to BASE_DIR means uploads/backups land in
# the same place regardless of which directory the app was launched from
# (e.g. a WSGI server started with a different cwd).
UPLOADS_FOLDER = os.path.join(BASE_DIR, "uploads")

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

# DEPLOYMENT FIX: anchored to BASE_DIR for the same reason as UPLOADS_FOLDER
# above (was the bare relative string "backups").
BACKUP_FOLDER = os.path.join(BASE_DIR, "backups")

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
        try:
            parsed_dob = pd.to_datetime(dob, format="%Y-%m-%d")
        except (ValueError, TypeError):
            # Google Sheets may return its locale-formatted date rather than the
            # ISO value used by the HTML form.  Keep the application's existing
            # day-first interpretation for those values.
            parsed_dob = pd.to_datetime(dob, dayfirst=True)
        return parsed_dob.strftime("%d-%m-%Y")

    except (ValueError, TypeError):
        return ""
# ==========================================
# FILES
# ==========================================

ADMIN_FILE = os.path.join(BASE_DIR, "admin.json")

LOG_FILE = os.path.join(BASE_DIR, "activity.log")
LOG_MAX_BYTES = int(os.environ.get("ACTIVITY_LOG_MAX_MB", "10")) * 1024 * 1024
LOG_ROTATION_COUNT = int(os.environ.get("ACTIVITY_LOG_ROTATIONS", "5"))

# This is deliberately separate from the student CSVs. It is an audit ledger of
# successfully seen Form response rows; RegNo remains the duplicate protection
# because repeated imports intentionally update an existing student.
GOOGLE_IMPORT_LOG_FILE = os.path.join(BASE_DIR, "google_import_log.json")

# ID of the existing Form response spreadsheet. An explicit environment value
# still takes precedence so deployments can override it.
DEFAULT_GOOGLE_SHEET_ID = "153RHUhM2Kms340iFLhQrY-KkC7mMmuecTUFNvyqe-Y8"

# Each key is the application/CSV column and each value lists acceptable Google
# Form or Sheet header names. Add an alias here if a Form question is renamed;
# the CSV and import logic do not need to change.
GOOGLE_FORM_FIELD_MAPPING = {
    "RegNo": ("RegNo", "Register Number", "Registration Number"),
    "Name": ("Name", "Student Name"),
    "Course": ("Course", "Programme", "Program"),
    "Batch": ("Batch", "Academic Batch"),
    "DOB": ("DOB", "Date of Birth"),
    "Community": ("Community",),
    "ParentName": ("ParentName", "Father Name", "Parent Name"),
    "MotherName": ("MotherName", "Mother Name"),
    "faOccupation": ("faOccupation", "Father Occupation"),
    "moOccupation": ("moOccupation", "Mother Occupation"),
    "AnualIncome": ("AnualIncome", "Annual Income"),
    "Address": ("Address",), "Pincode": ("Pincode", "PIN Code"),
    "Mobile": ("Mobile", "Mobile Number", "Phone Number"),
    "FirstGraduate": ("FirstGraduate", "First Graduate"),
    "BankName": ("BankName", "Bank Name"), "Branch": ("Branch",),
    "BankAccount": ("BankAccount", "Bank Account", "Account Number"),
    "IFSC": ("IFSC", "IFSC Code"), "MICR": ("MICR", "MICR Code"),
    "Aadhar": ("Aadhar", "Aadhaar", "Aadhaar Number"),
    "BloodGroup": ("BloodGroup", "Blood Group"),
    "UmisID": ("UmisID", "UMIS ID"), "EmisNo": ("EmisNo", "EMIS No"),
    "Email": ("Email", "Email Address"), "Photo": ("Photo", "Student Photo")
}

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


GOOGLE_FORM_FIELDS = [
    "RegNo", "Name", "Course", "Batch", "DOB", "Community",
    "ParentName", "MotherName", "faOccupation", "moOccupation",
    "AnualIncome", "Address", "Pincode", "Mobile", "FirstGraduate",
    "BankName", "Branch", "BankAccount", "IFSC", "MICR", "Aadhar",
    "BloodGroup", "UmisID", "EmisNo", "Email", "Photo"
]

GOOGLE_FORM_REQUIRED_FIELDS = {"RegNo", "Name", "Course", "Batch"}
ALLOWED_BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"}

# Cap on how many per-response records are kept in the (client-side, cookie
# based) Flask session after a Google Form import. Without this cap a large
# import's full "records" list can exceed the browser's ~4KB cookie limit and
# silently fail to round-trip. The aggregate counts (new/updated/skipped/
# failed) are never trimmed, only the detailed per-row list.
GOOGLE_IMPORT_SESSION_RECORD_LIMIT = 300
GOOGLE_IMPORT_SESSION_DETAIL_LIMIT = 20
MAX_PHOTO_BYTES = int(os.environ.get("MAX_PHOTO_MB", "10")) * 1024 * 1024
MAX_PHOTO_PIXELS = int(os.environ.get("MAX_PHOTO_PIXELS", "25000000"))
MAX_BACKUP_BYTES = int(os.environ.get("MAX_BACKUP_MB", "1024")) * 1024 * 1024
MAX_BACKUP_MEMBERS = int(os.environ.get("MAX_BACKUP_MEMBERS", "20000"))
MAX_BACKUP_EXPANDED_BYTES = int(os.environ.get("MAX_BACKUP_EXPANDED_MB", "4096")) * 1024 * 1024


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


# Flask's built-in session is signed but cookies are still sent automatically
# by browsers.  Require an unpredictable per-session token on every state
# changing request so another site cannot trigger an authenticated action.
def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.context_processor
def inject_security_helpers():
    return {"csrf_token": csrf_token}


@app.before_request
def protect_from_csrf():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        submitted = request.form.get("_csrf_token", "") or request.headers.get("X-CSRF-Token", "")
        expected = session.get("_csrf_token", "")
        if not expected or not submitted or not secrets.compare_digest(expected, submitted):
            app.logger.warning("CSRF validation failed for %s", request.path)
            return "Invalid or missing CSRF token.", 400


# ==========================================
# BASIC LOGIN LOCKOUT (BRUTE-FORCE MITIGATION)
# ==========================================
#
# SECURITY FIX: the original app had no protection against repeated login
# guesses. This is a lightweight, dependency-free mitigation: after
# LOGIN_MAX_ATTEMPTS failures from the same client address within
# LOGIN_LOCKOUT_SECONDS, further attempts are blocked until the window
# expires.
#
# Limitation (documented, not silently hidden): this state is in-process
# memory. It resets on restart and is NOT shared across multiple worker
# processes (e.g. multiple Gunicorn workers). For real production use behind
# multiple workers, replace this with Flask-Limiter backed by Redis or a
# similar shared store.

_failed_logins = {}
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300


def _login_identifier():
    return request.remote_addr or "unknown"


def is_login_locked_out(identifier):
    entry = _failed_logins.get(identifier)
    if not entry:
        return False
    count, first_attempt = entry
    if count < LOGIN_MAX_ATTEMPTS:
        return False
    if (datetime.now() - first_attempt).total_seconds() > LOGIN_LOCKOUT_SECONDS:
        _failed_logins.pop(identifier, None)
        return False
    return True


def register_failed_login(identifier):
    count, first_attempt = _failed_logins.get(identifier, (0, datetime.now()))
    if (datetime.now() - first_attempt).total_seconds() > LOGIN_LOCKOUT_SECONDS:
        count, first_attempt = 0, datetime.now()
    _failed_logins[identifier] = (count + 1, first_attempt)


def clear_failed_login(identifier):
    _failed_logins.pop(identifier, None)


# ==========================================
# ADMIN FUNCTIONS
# ==========================================


def load_admin():


    if not os.path.exists(ADMIN_FILE):

        # SECURITY FIX: the default admin password is now stored hashed
        # rather than as plain text. The default credential itself is
        # unchanged (username "admin", password "admin12") so existing
        # documentation/first-login flow still works.
        data = {

            "username":"admin",

            "password": generate_password_hash("admin12")

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


def verify_admin_password(admin, password):
    """
    Verify a login attempt against the stored admin record.

    SECURITY FIX / migration path: newly created or already-migrated
    admin.json files store a werkzeug password hash (recognizable by the
    "pbkdf2:" or "scrypt:" prefix). Older admin.json files created by a
    previous version of this app may still contain the raw plaintext
    password - those are still accepted here so existing installs are not
    locked out, and are transparently upgraded to a hash on next successful
    login (see admin_login()).
    """

    stored_password = admin.get("password", "")

    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        try:
            return check_password_hash(stored_password, password)
        except ValueError:
            app.logger.warning("Admin password hash is invalid")
            return False

    # Legacy plaintext password from an older install.
    return stored_password == password


def save_admin(data):
    temporary_path = ADMIN_FILE + ".tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, ADMIN_FILE)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)





# ==========================================
# LOG SYSTEM
# ==========================================


def write_log(message):
    # Keep the audit trail bounded on long-running deployments while retaining
    # several historical files.  Backups include these rotated files too.
    try:
        if os.path.isfile(LOG_FILE) and os.path.getsize(LOG_FILE) >= LOG_MAX_BYTES:
            oldest = f"{LOG_FILE}.{LOG_ROTATION_COUNT}"
            if os.path.exists(oldest):
                os.remove(oldest)
            for index in range(LOG_ROTATION_COUNT - 1, 0, -1):
                source, destination = f"{LOG_FILE}.{index}", f"{LOG_FILE}.{index + 1}"
                if os.path.exists(source):
                    os.replace(source, destination)
            os.replace(LOG_FILE, f"{LOG_FILE}.1")
    except OSError:
        app.logger.exception("Activity log rotation failed")
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





def read_recent_log_lines(limit=500):
    """Read the newest log entries without loading an unbounded file into RAM."""

    if not os.path.isfile(LOG_FILE):
        return []
    with open(LOG_FILE, "rb") as file:
        file.seek(0, os.SEEK_END)
        position = file.tell()
        data = b""
        while position > 0 and data.count(b"\n") <= limit:
            size = min(8192, position)
            position -= size
            file.seek(position)
            data = file.read(size) + data
    return [line.decode("utf-8", "replace").rstrip("\r")
            for line in data.splitlines()[-limit:]]


# ==========================================
# CSV PATH
# ==========================================


def normalize_course(course):
    """Normalize course names to the app's canonical values."""
    return str(course or "").strip().upper()


def get_csv_path(course, batch):
    """Return the CSV path for an exact course/batch combination."""
    course = normalize_course(course)
    batch = normalize_batch(batch)

    if not re.fullmatch(r"\d{4}_\d{4}", batch):
        raise ValueError("Invalid batch")

    if course == "UG":
        return os.path.join(UG_FOLDER, f"{batch}.csv")

    if course == "PG":
        return os.path.join(PG_FOLDER, f"{batch}.csv")

    raise ValueError("Course must be UG or PG")





# ==========================================
# LOAD CSV
# ==========================================


def load_csv(course,batch):

    # BUG FIX: get_csv_path() can raise ValueError for an invalid course
    # (e.g. a bad/missing "course" query-string value). Previously that call
    # sat outside this function's try/except, so an invalid course produced
    # an unhandled 500 instead of the same "not found" behavior every other
    # bad-CSV case gets. Wrapping the whole thing makes this function
    # consistently return None for any reason the CSV can't be loaded.
    try:

        path = get_csv_path(
            course,
            batch
        )

        if not os.path.exists(path):

            return None

        # Do not silently skip malformed rows: accepting a damaged CSV and
        # later saving it would permanently discard the skipped students.
        df = pd.read_csv(path, dtype=str, engine="python")

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


    temporary_path = path + ".tmp"
    try:
        df.to_csv(temporary_path, index=False, encoding="utf-8-sig")
        # Flush the replacement file before publishing it.  os.replace keeps
        # the previous CSV intact if writing or flushing fails.
        with open(temporary_path, "rb") as temporary_file:
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


# ==========================================
# GOOGLE FORM IMPORT
# ==========================================

class GoogleImportConfigurationError(RuntimeError):
    """A safe, admin-displayable Google import configuration error."""


def google_credentials_path():
    """Return an absolute service-account path without exposing its contents."""

    configured_path = (
        os.environ.get("GOOGLE_CREDENTIALS_FILE")
        or os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        or os.path.join("secrets", "google-service-account.json")
    )
    if not os.path.isabs(configured_path):
        configured_path = os.path.join(BASE_DIR, configured_path)
    return os.path.abspath(configured_path)


def google_response_range(sheets_service, sheet_id):
    """Use a configured range or find the worksheet with Form response headers."""

    configured_range = os.environ.get("GOOGLE_SHEET_RANGE", "").strip()
    if configured_range:
        return configured_range

    spreadsheet = sheets_service.spreadsheets().get(
        spreadsheetId=sheet_id,
        fields="sheets.properties(title,hidden)"
    ).execute()
    sheets = spreadsheet.get("sheets", [])
    visible_titles = [
        item.get("properties", {}).get("title", "")
        for item in sheets
        if not item.get("properties", {}).get("hidden", False)
    ]
    if not visible_titles:
        raise GoogleImportConfigurationError("No accessible worksheet was found.")
    # A title such as "Form Responses 1" is a useful preference, but it is not
    # enough by itself: admins can rename tabs or add unrelated worksheets.
    # Require the fields that identify this application's Form response sheet.
    ordered_titles = sorted(
        visible_titles,
        key=lambda title: not title.casefold().startswith("form responses")
    )
    required_fields = {"RegNo", "Name", "Course", "Batch"}
    for title in ordered_titles:
        quoted_title = "'" + title.replace("'", "''") + "'"
        header_row = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range=f"{quoted_title}!1:1"
        ).execute().get("values", [])
        headers = [str(value).strip() for value in (header_row[0] if header_row else [])]
        matched_fields = {
            field for field, aliases in GOOGLE_FORM_FIELD_MAPPING.items()
            if any(alias.casefold() in {header.casefold() for header in headers}
                   for alias in aliases)
        }
        has_timestamp = any(header.casefold() == "timestamp" for header in headers)
        if has_timestamp and required_fields.issubset(matched_fields):
            return quoted_title

    raise GoogleImportConfigurationError("Google Form response sheet not found.")


def google_safe_error_reason(error):
    """Convert Google/credential exceptions to an admin-safe diagnostic."""

    if isinstance(error, GoogleImportConfigurationError):
        return str(error)
    if isinstance(error, FileNotFoundError):
        return "Service account credentials not found."
    if isinstance(error, PermissionError):
        return "Service account credentials could not be read."
    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return "Network connection to Google API failed. Check internet access and try again."

    status = getattr(getattr(error, "resp", None), "status", None)
    error_text = str(error).lower()
    if status == 404:
        # Google can return 404 for inaccessible private files, so it is not
        # safe to claim which of these two causes occurred. The full exception
        # remains in the Flask server log.
        return "Spreadsheet not found, or the service account does not have permission to access it."
    if status == 403:
        if "accessnotconfigured" in error_text or "has not been used" in error_text:
            return "Google Sheets or Google Drive API is not enabled for the service-account project."
        return "Service account does not have permission to access the spreadsheet or uploaded photos."
    if status == 401:
        return "Google service account credentials are invalid or disabled."
    if "malformed" in error_text or "service account" in error_text or "private key" in error_text:
        return "Service account credentials are invalid."
    if "timeout" in error_text or "timed out" in error_text or "connection" in error_text:
        return "Network connection to Google API failed. Check internet access and try again."
    return "Google API connection failed. See the server log for the underlying error."

def get_google_credentials():
    """Load service-account credentials from the configured private JSON file."""

    from google.oauth2 import service_account

    credentials_file = google_credentials_path()
    if not os.path.isfile(credentials_file):
        raise GoogleImportConfigurationError("Service account credentials not found.")

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"
            ]
        )
    except (OSError, ValueError) as error:
        raise GoogleImportConfigurationError("Service account credentials are invalid.") from error

    return credentials


def google_services():
    """Create scoped Google API clients without exposing credentials."""

    from googleapiclient.discovery import build

    credentials = get_google_credentials()
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", DEFAULT_GOOGLE_SHEET_ID).strip()
    if not sheet_id:
        raise GoogleImportConfigurationError("Google Sheet ID is not configured.")

    # This email is safe to record and tells the administrator exactly which
    # account must be granted Viewer access to the Sheet and upload folder.
    app.logger.info("Google import using service account: %s", credentials.service_account_email)
    return (
        build("sheets", "v4", credentials=credentials, cache_discovery=False),
        build("drive", "v3", credentials=credentials, cache_discovery=False),
        sheet_id
    )


def get_google_sheet():
    """Return the configured Sheets client and spreadsheet ID for admin tasks."""

    sheets_service, _drive_service, sheet_id = google_services()
    return sheets_service, sheet_id


def get_google_form_responses():
    """Read the detected Form response tab using the existing API clients."""

    sheets_service, drive_service, sheet_id = google_services()
    response_range = google_response_range(sheets_service, sheet_id)
    values = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=response_range
    ).execute().get("values", [])
    return values, response_range, drive_service, sheet_id


def normalize_batch(batch):
    """Use the application's underscore batch convention for paths."""
    return str(batch or "").strip().replace("-", "_")


def get_photo_folder(course, batch):
    """Return the existing static photo directory for one exact course/batch."""
    course = normalize_course(course)
    if course not in {"UG", "PG"}:
        raise ValueError("Course must be UG or PG")
    batch = normalize_batch(batch)
    if not re.fullmatch(r"\d{4}_\d{4}", batch):
        raise ValueError("Invalid batch")
    return os.path.join(PHOTO_FOLDER, course.lower(), batch)


def get_photo_path(course, batch, filename):
    """Safely construct a course/batch photo path without storing it in CSV."""
    filename = secure_filename(str(filename or ""))
    if not filename or filename != os.path.basename(filename):
        raise ValueError("Invalid photo filename")
    return os.path.join(get_photo_folder(course, batch), filename)


def save_uploaded_photo(photo, course, batch, regno):
    """Save an uploaded student photo using the register number as its name."""
    if not photo or not photo.filename:
        return ""
    if not allowed_photo(photo.filename):
        raise ValueError("Photo must be a JPG, JPEG, or PNG file.")

    raw_regno = str(regno or "").strip()
    safe_regno = secure_filename(raw_regno)
    if not safe_regno or safe_regno != raw_regno:
        raise ValueError("Invalid register number for photo filename.")

    extension = os.path.splitext(secure_filename(photo.filename))[1].lower()
    filename = f"{safe_regno}{extension}"
    photo_path = get_photo_path(course, batch, filename)
    photo_folder = os.path.dirname(photo_path)
    os.makedirs(photo_folder, exist_ok=True)

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=photo_folder, prefix=f".{safe_regno}.", suffix=extension,
            delete=False
        ) as temporary:
            temporary_path = temporary.name
        photo.save(temporary_path)
        photo_size = os.path.getsize(temporary_path)
        if photo_size == 0:
            raise ValueError("The selected photo is empty.")
        if photo_size > MAX_PHOTO_BYTES:
            raise ValueError("The selected photo is too large.")
        from PIL import Image, UnidentifiedImageError
        try:
            with Image.open(temporary_path) as image:
                image.verify()
            with Image.open(temporary_path) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise ValueError("Photo must be a JPG, JPEG, or PNG image.")
                if image.width * image.height > MAX_PHOTO_PIXELS:
                    raise ValueError("The selected photo has too many pixels.")
        except (OSError, UnidentifiedImageError) as error:
            raise ValueError("The selected photo is not a valid image.") from error
        os.replace(temporary_path, photo_path)
        return filename
    except (OSError, ValueError) as error:
        app.logger.warning("Student photo save failed for %s: %s", regno, error)
        raise ValueError("The student photo could not be saved.") from error
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


def get_existing_photo_path(course, batch, filename):
    """Use nested storage, with a read/delete fallback for older flat photos."""
    course = normalize_course(course)
    batch = normalize_batch(batch)
    nested_path = get_photo_path(course, batch, filename)
    if os.path.isfile(nested_path):
        return nested_path
    return os.path.join(PHOTO_FOLDER, secure_filename(str(filename or "")))


def get_photo_static_path(course, batch, filename):
    """Return an existing static-relative path, or an empty value for no image."""
    course = normalize_course(course)
    batch = normalize_batch(batch)
    filename = secure_filename(str(filename or ""))
    if not filename:
        return ""
    nested_path = get_photo_path(course, batch, filename)
    if os.path.isfile(nested_path):
        return f"photos/{course.lower()}/{batch}/{filename}"
    legacy_path = os.path.join(PHOTO_FOLDER, filename)
    if os.path.isfile(legacy_path):
        return f"photos/{filename}"
    return ""


@app.context_processor
def inject_photo_helpers():
    return {"photo_static_path": get_photo_static_path}


def validate_google_form_row(row):
    """Return an error string, or an empty string for a valid response."""

    for field in GOOGLE_FORM_REQUIRED_FIELDS:
        if not str(row.get(field, "")).strip():
            return f"Missing {field}"

    regno = str(row["RegNo"]).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", regno):
        return "Invalid register number"

    course = str(row["Course"]).strip().upper()
    if course not in {"UG", "PG"}:
        return "Course must be UG or PG"

    if not re.fullmatch(r"\d{4}[-_]\d{4}", str(row["Batch"]).strip()):
        return "Invalid Batch (use YYYY-YYYY)"

    for field, pattern in {
        "Mobile": r"\d{7,15}", "Pincode": r"\d{4,10}",
        "Aadhar": r"\d{12}", "BankAccount": r"\d{6,24}",
        "IFSC": r"[A-Za-z]{4}0[A-Za-z0-9]{6}"
    }.items():
        value = str(row.get(field, "")).strip()
        if value and not re.fullmatch(pattern, value):
            return f"Invalid {field}"

    email = str(row.get("Email", "")).strip()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return "Invalid Email"
    if row.get("FirstGraduate") and row["FirstGraduate"].title() not in {"Yes", "No"}:
        return "FirstGraduate must be Yes or No"
    if row.get("BloodGroup") and row["BloodGroup"] not in ALLOWED_BLOOD_GROUPS:
        return "Invalid BloodGroup"
    return ""


def load_google_import_log():
    """Return IDs of response rows previously processed by the import."""

    try:
        with open(GOOGLE_IMPORT_LOG_FILE, "r", encoding="utf-8") as file:
            entries = json.load(file)
        return set(entries) if isinstance(entries, list) else set()
    except (OSError, ValueError, TypeError):
        return set()


def save_google_import_log(entries):
    """Atomically save the local response ledger; never touch the source Sheet."""

    temporary_path = GOOGLE_IMPORT_LOG_FILE + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(sorted(entries), file, indent=2)
    os.replace(temporary_path, GOOGLE_IMPORT_LOG_FILE)


def response_row_id(sheet_row_number, headers, values_row):
    """Stable ID for one submitted Sheet response, including its physical row."""

    payload = json.dumps(
        {"row": sheet_row_number, "headers": headers, "values": values_row},
        ensure_ascii=False,
        separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def add_import_group_count(result, course, batch, key):
    label = f"{course} / {batch.replace('_', '-')}"
    group = result["groups"].setdefault(
        label, {"new": 0, "updated": 0, "photos": 0, "skipped": 0, "failed": 0}
    )
    group[key] += 1


def add_import_record(result, row, status, message, photo=""):
    """Add a secret-free, per-response result for the admin dashboard."""

    result.setdefault("records", []).append({
        "regno": str(row.get("RegNo", "")).strip() or "(blank)",
        "name": str(row.get("Name", "")).strip() or "-",
        "status": status,
        "photo": photo,
        "message": message
    })


def google_drive_file_id(value):
    """Extract a Drive ID from common Forms response formats."""

    match = re.search(r"[-\w]{20,}", str(value or "").strip())
    return match.group(0) if match else ""


def download_google_photo(drive_service, photo_value, course, batch, regno):
    """Download one Drive image into its exact course/batch photo folder."""

    from googleapiclient.http import MediaIoBaseDownload

    file_id = google_drive_file_id(photo_value)
    if not file_id:
        raise ValueError("Photo reference does not contain a Drive file ID")
    metadata = drive_service.files().get(
        fileId=file_id, fields="name,mimeType", supportsAllDrives=True
    ).execute()
    extension = os.path.splitext(secure_filename(metadata.get("name", "")))[1].lower()
    if metadata.get("mimeType") not in {"image/jpeg", "image/png"} \
            or extension not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("Photo is not a JPG, JPEG, or PNG image")

    # The application always stores a single canonical JPEG name per RegNo,
    # regardless of whether the Form upload was JPG, JPEG, or PNG.
    filename = secure_filename(regno) + ".jpg"
    destination = get_photo_path(course, batch, filename)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    temporary_path = None
    converted_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temporary:
            temporary_path = temporary.name
            downloader = MediaIoBaseDownload(
                temporary,
                drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
            )
            done = False
            while not done:
                _, done = downloader.next_chunk()

        from PIL import Image, UnidentifiedImageError
        try:
            with Image.open(temporary_path) as image:
                image.verify()
            with Image.open(temporary_path) as image:
                if image.width * image.height > MAX_PHOTO_PIXELS:
                    raise ValueError("Downloaded photo has too many pixels")
                if image.mode in {"RGBA", "LA"}:
                    background = Image.new("RGB", image.size, "white")
                    background.paste(image, mask=image.getchannel("A"))
                    image = background
                elif image.mode != "RGB":
                    image = image.convert("RGB")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as converted:
                    converted_path = converted.name
                image.save(converted_path, "JPEG")
        except (OSError, UnidentifiedImageError, ValueError) as error:
            raise ValueError("Downloaded photo is not a valid image") from error

        os.replace(converted_path, destination)
        converted_path = None
        return os.path.basename(destination)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)
        if converted_path and os.path.exists(converted_path):
            os.remove(converted_path)


def google_sheet_row(headers, values_row):
    """Map configurable Form headers while accepting duplicate `Batch` columns."""

    source_row = {}
    for position, header in enumerate(headers):
        value = str(values_row[position]).strip() if position < len(values_row) else ""
        header = str(header).strip()
        # Branching Forms may produce two identically titled Batch columns.  The
        # selected branch is the one non-empty value, so retain it.
        if value or header not in source_row:
            source_row[header] = value

    normalized_source = {
        header.casefold(): value for header, value in source_row.items()
    }
    row = {}
    for field, aliases in GOOGLE_FORM_FIELD_MAPPING.items():
        row[field] = next(
            (normalized_source.get(alias.casefold(), "") for alias in aliases
             if normalized_source.get(alias.casefold(), "")),
            ""
        )
    return row


def google_api_status():
    """Safely test Google Sheets and Drive connectivity for the admin page."""

    try:
        sheets_service, drive_service, sheet_id = google_services()

        # Test Spreadsheet access
        spreadsheet = sheets_service.spreadsheets().get(
            spreadsheetId=sheet_id,
            fields="spreadsheetId,properties(title)"
        ).execute()

        spreadsheet_title = (
            spreadsheet.get("properties", {}).get("title", "")
        )

        # Detect Form response worksheet
        response_range = google_response_range(
            sheets_service,
            sheet_id
        )

        # Test response data access
        values = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=response_range
        ).execute().get("values", [])

        # Test Drive API itself
        drive_service.files().list(
            pageSize=1,
            fields="files(id,name)"
        ).execute()

        return {
            "connection": "SUCCESS",
            "spreadsheet": "Connected",
            "spreadsheet_title": spreadsheet_title,
            "worksheet": response_range,
            "responses_found": max(len(values) - 1, 0),
            "sheets": "Connected",
            "drive": "Connected"
        }

    except Exception as error:
        app.logger.exception(
            "Google API diagnostic failed: %s",
            error
        )

        return {
            "connection": "FAILED",
            "spreadsheet": "Not connected",
            "worksheet": "",
            "responses_found": 0,
            "sheets": "Not connected",
            "drive": "Not connected",
            "reason": google_safe_error_reason(error)
        }


def import_google_form_responses():
    """Merge new Form rows without replacing existing CSV rows or columns."""

    values, response_range, drive_service, sheet_id = get_google_form_responses()
    result = {"new": 0, "updated": 0, "photos": 0, "skipped": 0,
              "failed": 0, "errors": [], "groups": {},
              "connection": "SUCCESS", "spreadsheet": "Connected",
              "worksheet": response_range, "responses_found": max(len(values) - 1, 0),
              "records": []}
    if not values:
        return result

    headers = [str(header).strip() for header in values[0]]
    imported_ids = load_google_import_log()
    backup_created = False
    for sheet_row_number, values_row in enumerate(values[1:], start=2):
        import_id = response_row_id(sheet_row_number, headers, values_row)
        row = google_sheet_row(headers, values_row)
        row = {field: str(row.get(field, "")).strip() for field in GOOGLE_FORM_FIELDS}
        if import_id in imported_ids:
            # A successful, unchanged response has already been merged.  A
            # changed response has a different content hash and is therefore
            # still processed as an update.
            result["skipped"] += 1
            add_import_record(result, row, "SKIPPED", "Previously imported")
            continue
        validation_error = validate_google_form_row(row)
        regno = row.get("RegNo", "") or "(blank)"
        if validation_error:
            result["skipped"] += 1
            result["errors"].append({"regno": regno, "reason": validation_error})
            add_import_record(result, row, "SKIPPED", validation_error)
            write_log(f"Skipped Google Form record | {regno} | {validation_error}")
            continue

        course = row["Course"].upper()
        batch = row["Batch"].replace("-", "_")
        csv_path = get_csv_path(course, batch)
        if not os.path.isfile(csv_path):
            reason = f"CSV not found for {course} / {batch.replace('_', '-')}"
            result["skipped"] += 1
            add_import_group_count(result, course, batch, "skipped")
            result["errors"].append({"regno": regno, "reason": reason})
            add_import_record(result, row, "SKIPPED", reason)
            write_log(f"Skipped Google Form record | {regno} | {reason}")
            continue
        dataframe = load_csv(course, batch)
        if dataframe is None or "RegNo" not in dataframe.columns:
            result["failed"] += 1
            add_import_group_count(result, course, batch, "failed")
            result["errors"].append({
                "regno": regno,
                "reason": "Target batch CSV could not be loaded"
            })
            add_import_record(result, row, "FAILED", "Target batch CSV could not be loaded")
            write_log(f"Failed Google Form record | {regno} | Target batch CSV unavailable")
            continue

        # Reuse the application's complete backup facility once per import run,
        # before the first CSV or photo is changed.
        if not backup_created:
            try:
                create_backup("Automatic Backup Before Google Form Import")
                backup_created = True
            except Exception as error:
                result["failed"] += 1
                add_import_group_count(result, course, batch, "failed")
                result["errors"].append({
                    "regno": regno,
                    "reason": "Safety backup could not be created"
                })
                add_import_record(result, row, "FAILED", "Safety backup could not be created")
                write_log(f"Failed Google Form record | {regno} | Backup failed: {error}")
                continue

        matches = dataframe[dataframe["RegNo"].astype(str).str.strip() == regno].index
        is_new = len(matches) == 0
        if is_new:
            row_index = max(dataframe.index, default=-1) + 1
            dataframe.loc[row_index] = {column: "" for column in dataframe.columns}
        else:
            row_index = matches[0]

        for field in GOOGLE_FORM_FIELDS:
            if field != "Photo" and field in dataframe.columns:
                value = row[field]
                dataframe.loc[row_index, field] = format_dob_for_csv(value) if field == "DOB" else value

        photo_failed = False
        if row.get("Photo"):
            try:
                photo_filename = download_google_photo(
                    drive_service, row["Photo"], course, batch, regno
                )
                old_photo = str(dataframe.loc[row_index, "Photo"]).strip() if "Photo" in dataframe.columns else ""
                if "Photo" in dataframe.columns:
                    dataframe.loc[row_index, "Photo"] = photo_filename
                if old_photo and old_photo != photo_filename:
                    old_path = get_existing_photo_path(course, batch, old_photo)
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                result["photos"] += 1
                add_import_group_count(result, course, batch, "photos")
                write_log(f"Photo downloaded | {regno}")
            except Exception:
                result.setdefault("photo_warnings", []).append({
                    "regno": regno,
                    "reason": "Photo download failed"
                })
                write_log(f"Photo warning | {regno} | Photo download failed")
                photo_failed = True

        save_csv(dataframe, course, batch)
        if is_new:
            result["new"] += 1
            add_import_group_count(result, course, batch, "new")
            write_log(f"New student from Google Form | {regno}")
            add_import_record(
                result, row, "NEW",
                "Imported; photo download failed" if photo_failed else "Imported",
                "Warning" if photo_failed else ("Downloaded" if row.get("Photo") else "Not provided")
            )
        else:
            result["updated"] += 1
            add_import_group_count(result, course, batch, "updated")
            write_log(f"Existing student updated from Google Form | {regno}")
            add_import_record(
                result, row, "UPDATED",
                "Updated; photo download failed" if photo_failed else "Updated",
                "Warning" if photo_failed else ("Downloaded" if row.get("Photo") else "Not provided")
            )
        # Keep a local audit trail. Repeated imports still merge by Course,
        # Batch, and RegNo so the row is updated rather than duplicated.
        if not photo_failed:
            imported_ids.add(import_id)

    save_google_import_log(imported_ids)
    return result


def trim_import_result_for_session(result):
    """
    Cap the per-response 'records' list before storing an import result in
    the session.

    DATA-SAFETY FIX: Flask's default session is a signed, client-side
    cookie with a small (~4KB) size limit. A large Google Form import can
    produce a 'records' entry per response row, which can silently exceed
    that limit. The aggregate counters (new/updated/skipped/failed/photos)
    are always kept intact; only the detailed list is capped, with a note
    added so the admin knows some rows were left out of the detail view
    (they are still fully present in activity.log).
    """

    result = dict(result)
    for key in ("records", "errors", "photo_warnings"):
        values = result.get(key)
        if isinstance(values, list) and len(values) > GOOGLE_IMPORT_SESSION_DETAIL_LIMIT:
            result[key] = values[:GOOGLE_IMPORT_SESSION_DETAIL_LIMIT]
            result[f"{key}_truncated"] = len(values) - GOOGLE_IMPORT_SESSION_DETAIL_LIMIT
    return result
# ==========================================
# BACKUP & RESTORE SYSTEM
# ==========================================

BACKUP_ALLOWED_FILES = {
    "admin.json",
    "activity.log",
    "google_import_log.json"
}


def get_backup_filename():
    """
    Generate a unique backup filename.
    """

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")

    return f"StudentApp_Backup_{timestamp}.zip"


def is_safe_zip_member(member_name):
    """
    Prevent ZIP path traversal attacks.

    Reject paths such as:
        ../../admin.json
        ../../../something
    """

    if not member_name or "\x00" in member_name:
        return False
    normalized = member_name.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return False
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    return ".." not in parts


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
    if re.fullmatch(r"activity\.log\.\d+", normalized):
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
            if len(members) > MAX_BACKUP_MEMBERS:
                return False, "Backup contains too many files."

            valid_file_found = False
            names = set()
            total_uncompressed = 0

            for member in members:

                name = member.filename

                normalized_name = name.replace("\\", "/").rstrip("/")
                if normalized_name in names:
                    return False, "Backup contains duplicate file paths."
                names.add(normalized_name)

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

                total_uncompressed += member.file_size
                if total_uncompressed > MAX_BACKUP_EXPANDED_BYTES:
                    return False, "Backup expands beyond the configured safe limit."

                # A very high ratio is characteristic of ZIP bombs.  Small
                # text files are exempt because their normal compression ratio
                # can be high without posing a disk-exhaustion risk.
                if member.file_size > 1024 * 1024 and member.compress_size and \
                        member.file_size / member.compress_size > 100:
                    return False, "Backup has an unsafe compression ratio."

                if not is_allowed_backup_member(name):
                    return False, f"Invalid backup file: {name}"

                valid_file_found = True

            if not valid_file_found:
                return False, "Backup contains no valid application files."

        return True, "Backup is valid."

    except zipfile.BadZipFile:
        return False, "The uploaded file is not a valid ZIP backup."

    except Exception:
        app.logger.exception("Backup ZIP validation failed")
        return False, "Backup ZIP could not be validated."


def save_limited_upload(upload, destination, byte_limit):
    """Stream an upload to disk without allowing an unbounded temporary file."""

    written = 0
    try:
        with open(destination, "xb") as output:
            while True:
                chunk = upload.stream.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > byte_limit:
                    raise ValueError("The uploaded backup exceeds the configured size limit.")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        if os.path.exists(destination):
            os.remove(destination)
        raise


def create_backup(reason="Manual Backup"):
    """
    Create a complete ZIP backup of the StudentApp.

    Returns:
        backup_path
    """

    filename = get_backup_filename()
    backup_path = os.path.join(BACKUP_FOLDER, filename)
    temporary_backup_path = backup_path + ".tmp"

    def add_tree(archive, folder):
        if not os.path.isdir(folder):
            return
        for root, dirs, files in os.walk(folder, followlinks=False):
            dirs[:] = [name for name in dirs if not os.path.islink(os.path.join(root, name))]
            for file_name in files:
                full_path = os.path.join(root, file_name)
                if os.path.islink(full_path):
                    app.logger.warning("Skipped symlink in backup: %s", full_path)
                    continue
                archive.write(full_path, os.path.relpath(full_path, BASE_DIR))

    try:
        with zipfile.ZipFile(temporary_backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            add_tree(archive, DATA_FOLDER)
            add_tree(archive, PHOTO_FOLDER)
            add_tree(archive, UPLOADS_FOLDER)
            files_to_add = [ADMIN_FILE, LOG_FILE, GOOGLE_IMPORT_LOG_FILE]
            files_to_add.extend(f"{LOG_FILE}.{index}" for index in range(1, LOG_ROTATION_COUNT + 1))
            for file_path in files_to_add:
                if os.path.isfile(file_path) and not os.path.islink(file_path):
                    archive.write(file_path, os.path.basename(file_path))
        os.replace(temporary_backup_path, backup_path)
    finally:
        if os.path.exists(temporary_backup_path):
            os.remove(temporary_backup_path)

    write_log(
        f"Backup Created | {reason} | {filename}"
    )

    return backup_path


def atomic_replace_dir(source_dir, target_dir):
    """
    Replace target_dir's contents with source_dir's, without ever leaving
    the application with neither the old nor the new data.

    DATA-SAFETY FIX: the previous restore implementation did
    shutil.rmtree(target_dir) followed by shutil.copytree(source_dir,
    target_dir). If the copy failed partway (disk full, permissions,
    truncated archive), the original directory was already gone and the
    new one was incomplete - a genuine, irreversible data-loss window
    (a safety backup is taken earlier, but the live app would still be
    broken until someone noticed and manually restored it).

    This copies the new directory to a staging location FIRST (so a failed
    copy never touches the live directory at all), then swaps it in with
    os.rename (a near-atomic operation on the same filesystem), keeping the
    previous directory until the swap has fully succeeded.
    """

    staging_dir = target_dir + ".restore_tmp"
    old_dir = target_dir + ".restore_old"

    # Never blindly delete a previous restore's ``.restore_old`` directory:
    # after a crash it may be the only complete copy of live data.  Recover it
    # when the target is absent; otherwise require operator review instead of
    # guessing which copy is authoritative.
    if os.path.exists(old_dir):
        if not os.path.exists(target_dir):
            os.rename(old_dir, target_dir)
        else:
            raise OSError(f"Previous restore cleanup is pending for {target_dir}")
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir, ignore_errors=True)

    # If this raises, target_dir has not been touched at all.
    shutil.copytree(source_dir, staging_dir)

    try:
        if os.path.exists(target_dir):
            os.rename(target_dir, old_dir)
        os.rename(staging_dir, target_dir)
    except Exception:
        # Roll back: restore the previous directory if the swap failed
        # partway, so the live app is never left without a data folder.
        if os.path.exists(old_dir) and not os.path.exists(target_dir):
            os.rename(old_dir, target_dir)
        raise
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    shutil.rmtree(old_dir, ignore_errors=True)


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

            # DATA-SAFETY FIX: staged atomic swap instead of
            # rmtree-then-copytree (see atomic_replace_dir() docstring).
            atomic_replace_dir(extracted_data, DATA_FOLDER)

        # --------------------------------------
        # RESTORE PHOTOS
        # --------------------------------------

        extracted_photos = os.path.join(
            temp_folder,
            "static",
            "photos"
        )

        if os.path.exists(extracted_photos):

            atomic_replace_dir(extracted_photos, PHOTO_FOLDER)

        # --------------------------------------
        # RESTORE UPLOADS
        # --------------------------------------

        extracted_uploads = os.path.join(
            temp_folder,
            "uploads"
        )

        if os.path.exists(extracted_uploads):

            atomic_replace_dir(extracted_uploads, UPLOADS_FOLDER)

        # --------------------------------------
        # RESTORE ADMIN
        # --------------------------------------

        # BUG FIX (critical): previously os.path.join(temp_folder, ADMIN_FILE)
        # - since ADMIN_FILE is an absolute path, os.path.join() ignores
        # temp_folder entirely and this always pointed at the LIVE admin.json,
        # not the extracted one, making the admin.json restore a no-op (and,
        # combined with the arcname bug above, it could never have worked).
        extracted_admin = os.path.join(
            temp_folder,
            os.path.basename(ADMIN_FILE)
        )

        if os.path.exists(extracted_admin):

            shutil.copy2(
                extracted_admin,
                ADMIN_FILE
            )

        # --------------------------------------
        # RESTORE ACTIVITY LOG
        # --------------------------------------

        # BUG FIX (critical): same issue as ADMIN_FILE above.
        extracted_log = os.path.join(
            temp_folder,
            os.path.basename(LOG_FILE)
        )

        if os.path.exists(extracted_log):

            shutil.copy2(
                extracted_log,
                LOG_FILE
            )

        for index in range(1, LOG_ROTATION_COUNT + 1):
            live_rotated_log = f"{LOG_FILE}.{index}"
            extracted_rotated_log = os.path.join(temp_folder, f"activity.log.{index}")
            if os.path.exists(extracted_rotated_log):
                shutil.copy2(extracted_rotated_log, live_rotated_log)
            elif os.path.exists(live_rotated_log):
                os.remove(live_rotated_log)

        extracted_google_log = os.path.join(temp_folder, os.path.basename(GOOGLE_IMPORT_LOG_FILE))
        if os.path.exists(extracted_google_log):
            shutil.copy2(extracted_google_log, GOOGLE_IMPORT_LOG_FILE)

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

def create_empty_batch(course, batch):

    path = get_csv_path(
        course,
        batch
    )

    # Always make sure the batch photo folder exists
    os.makedirs(
        get_photo_folder(course, batch),
        exist_ok=True
    )

    # Already batch exists
    if os.path.exists(path):
        return False

    columns = (
        UG_COLUMNS
        if course == "UG"
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


        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        identifier = _login_identifier()

        # SECURITY FIX: basic brute-force lockout (see is_login_locked_out()
        # docstring for the documented limitations of this in-memory
        # implementation).
        if is_login_locked_out(identifier):
            return render_template(
                "admin_login.html",
                error="Too many failed attempts. Please try again in a few minutes."
            )

        admin=load_admin()



        if (
            username==admin["username"]
            and
            verify_admin_password(admin, password)
        ):
            clear_failed_login(identifier)

            # SECURITY FIX: transparently upgrade a legacy plaintext password
            # to a hash on first successful login after this update, without
            # requiring the admin to do anything or changing their password.
            if not admin["password"].startswith(("pbkdf2:", "scrypt:")):
                admin["password"] = generate_password_hash(password)
                save_admin(admin)

            session.clear()
            session["admin"]=True
            session["last_login"] = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")

            write_log(
                "Admin Login"
            )


            return redirect(
                url_for("admin")
            )


        register_failed_login(identifier)

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


@app.route("/logout", methods=["POST"])
@login_required
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

    recent_logs = list(reversed(read_recent_log_lines(5)))

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

        recent_logs=recent_logs,

        import_result=session.pop("import_result", None),

        google_status=session.pop("google_status", None)

    )


@app.route("/import-google-form", methods=["POST"])
@app.route("/import-google-responses", methods=["POST"])
@login_required
def import_google_responses_route():

    write_log("Google Form import started")
    try:
        result = import_google_form_responses()
        session["import_result"] = trim_import_result_for_session(result)
        write_log(
            "Google Form import completed | "
            f"New: {result['new']} | Updated: {result['updated']} | "
            f"Photos: {result['photos']} | Skipped: {result['skipped']} | "
            f"Failed: {result['failed']}"
        )
    except Exception as error:
        app.logger.exception("Google API connection failed")
        safe_reason = google_safe_error_reason(error)
        session["import_result"] = {
            "new": 0, "updated": 0, "photos": 0, "skipped": 0,
            "connection": "FAILED",
            "spreadsheet": "Not connected",
            "failed": 1, "errors": [{
                "regno": "-",
                "reason": safe_reason
            }]
        }
        write_log(f"Google Form import failed | {safe_reason}")

    return redirect(url_for("admin"))


@app.route("/google-api-status", methods=["POST"])
@app.route("/admin/google-api-status", methods=["POST"])
@login_required
def google_api_status_route():
    """Admin-only, secret-free diagnostic for the existing Google connection."""

    try:
        session["google_status"] = google_api_status()
    except Exception as error:
        app.logger.exception("Google API diagnostic failed")
        safe_reason = google_safe_error_reason(error)
        session["google_status"] = {
            "connection": "FAILED",
            "spreadsheet": "Not connected",
            "reason": safe_reason
        }
        write_log(f"Google API diagnostic failed | {safe_reason}")
    return redirect(url_for("admin"))
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    filename = (
        f"Uploaded_{timestamp}_{filename}"
    )

    path = os.path.join(
        BACKUP_FOLDER,
        filename
    )

    try:

        save_limited_upload(file, path, MAX_BACKUP_BYTES)

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
# ==========================================
# UPLOAD DATA
# ==========================================
#
# NOTE: a large block of unreachable, duplicate dashboard-statistics code
# previously sat here (after delete_backup()'s return statement, at the same
# indentation level as its body, so Python treated it as dead code inside
# that function - it never executed, but relied on undefined names like
# ug_batches/pg_batches/total_ug_students and duplicated the working /admin
# route above almost verbatim). It has been removed as part of this audit;
# the real, correct dashboard logic is the /admin route above.


@app.route(
    "/upload-data",
    methods=["POST"]
)
@login_required
def upload_data():

    course = normalize_course(request.form.get("course", ""))
    batch = normalize_batch(request.form.get("batch", ""))
    file = request.files.get("datafile")

    if course not in {"UG", "PG"} or not re.fullmatch(r"\d{4}_\d{4}", batch):
        flash("Choose UG or PG and a batch in YYYY-YYYY format.", "error")
        return redirect(url_for("admin"))

    if not file or not file.filename:
        try:
            if create_empty_batch(course, batch):
                flash(f"{course} {batch} batch created successfully.", "success")
            else:
                flash("Select a CSV/Excel file to replace an existing batch.", "error")
        except OSError:
            app.logger.exception("Could not create batch")
            flash("Could not create the batch.", "error")
        return redirect(url_for("admin"))



    try:


        filename = secure_filename(file.filename).lower()



        if filename.endswith(".csv"):


            df = pd.read_csv(file, dtype=str, engine="python")



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


            flash("Only CSV, XLS, and XLSX files are allowed.", "error")
            return redirect(url_for("admin"))



    except Exception:
        app.logger.exception("Student data upload could not be read")
        flash("The uploaded CSV/Excel file could not be read.", "error")
        return redirect(url_for("admin"))



    df = df.fillna("")
    if df.empty:
        flash("The uploaded file contains no student records.", "error")
        return redirect(url_for("admin"))
    if not {"RegNo", "Name"}.issubset(df.columns):
        flash("The uploaded file must include RegNo and Name columns.", "error")
        return redirect(url_for("admin"))



    columns = (
        UG_COLUMNS
        if course=="UG"
        else PG_COLUMNS
    )



    for col in columns:


        if col not in df.columns:

            df[col]=""



    df = df[columns]
    df["RegNo"] = df["RegNo"].astype(str).str.strip()
    df["Name"] = df["Name"].astype(str).str.strip()
    if (df["RegNo"] == "").any() or (df["Name"] == "").any():
        flash("Every uploaded student must have a RegNo and Name.", "error")
        return redirect(url_for("admin"))
    if not df["RegNo"].str.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}").all():
        flash("One or more register numbers are invalid.", "error")
        return redirect(url_for("admin"))
    if df["RegNo"].duplicated().any():
        flash("The uploaded file contains duplicate register numbers.", "error")
        return redirect(url_for("admin"))
    df["Course"] = course
    df["Batch"] = batch
    df["DOB"] = df["DOB"].map(format_dob_for_csv)



    try:
        if os.path.exists(get_csv_path(course, batch)):
            create_backup(f"Automatic Backup Before Replacing {course} {batch}")
        save_csv(df, course, batch)
    except Exception:
        app.logger.exception("Student data upload could not be saved")
        flash("The uploaded data was not saved; the previous batch was kept.", "error")
        return redirect(url_for("admin"))



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

        old_photo = str(
            df.loc[row, "Photo"]
        ).strip()
        try:
            filename = save_uploaded_photo(photo, course, batch, regno)
        except ValueError:
            failed.append(f"{original_filename} - Photo could not be saved")
            continue

        if old_photo and old_photo != filename:
            old_photo_path = get_existing_photo_path(course, batch, old_photo)
            if os.path.isfile(old_photo_path):
                try:
                    os.remove(old_photo_path)
                except OSError:
                    pass

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


    course = normalize_course(request.form.get("course", ""))
    batch = normalize_batch(request.form.get("batch", ""))


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



    # BUG FIX: strip RegNo so a value with stray leading/trailing whitespace
    # can't slip past the duplicate check in validate_student_details()
    # (which compares the stripped value) while still being stored differently.
    regno = request.form.get("RegNo", "").strip()
    new_student["RegNo"] = regno



    # PHOTO

    # BUG FIX: this previously saved the uploaded photo directly with
    # photo.save(), bypassing save_uploaded_photo()'s safety checks (empty
    # file check, atomic temp-file write, and - critically - the ValueError
    # that get_photo_path() can raise for a RegNo that secure_filename()
    # alters, which was unhandled here and would 500 the request). Routing
    # through the same helper used everywhere else in the app makes photo
    # handling consistent and this failure mode safe.
    if "Photo" in request.files:

        photo = request.files["Photo"]

        if photo.filename:

            if allowed_photo(photo.filename):

                try:
                    filename = save_uploaded_photo(photo, course, batch, regno)
                except ValueError as error:
                    flash(str(error), "error")
                    return redirect(url_for("add_student", course=course, batch=batch))

                if filename:
                    new_student["Photo"] = filename
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

    course = normalize_course(request.form.get("course", ""))
    batch = normalize_batch(request.form.get("batch", ""))
    regno = request.form.get("RegNo", "").strip()

    if course != "PG" or not re.fullmatch(r"\d{4}_\d{4}", batch):
        flash("Invalid course or batch.", "error")
        return redirect(url_for("admin"))

    df = load_csv(course, batch)

    if df is None:
        return redirect(url_for("admin"))

    index = df[
        df["RegNo"].astype(str) == regno
    ].index

    if len(index) == 0:
        return redirect(url_for("admin"))

    row = index[0]

    validation_error = validate_student_details(request.form, df, is_new=False)
    if validation_error:
        flash(validation_error, "error")
        return redirect(url_for("student_search", course=course, batch=batch,
                                search_type="regno", keyword=regno))

    # Remove Photo
    photo = request.files.get("Photo")
    if request.form.get("remove_photo") == "1" and not (photo and photo.filename):

        old_photo = df.loc[row, "Photo"]

        if old_photo:

            photo_path = get_existing_photo_path(course, batch, old_photo)

            if os.path.exists(photo_path):
                os.remove(photo_path)

        df.loc[row, "Photo"] = ""

    # Update all fields
    for column in df.columns:

        if column in request.form and column not in {"RegNo", "Course", "Batch", "Photo"}:
            df.loc[row, column] = request.form.get(column, "")
    # Convert DOB from HTML format to CSV format
    df.loc[row, "DOB"] = format_dob_for_csv(
    df.loc[row, "DOB"]
)

    if photo and photo.filename:
        old_photo = str(df.loc[row, "Photo"]).strip()
        try:
            filename = save_uploaded_photo(photo, course, batch, regno)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("student_search", course=course, batch=batch,
                                    search_type="regno", keyword=regno))
        df.loc[row, "Photo"] = filename
        if old_photo and old_photo != filename:
            old_path = get_existing_photo_path(course, batch, old_photo)
            if os.path.isfile(old_path):
                os.remove(old_path)

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

    course = normalize_course(request.form.get("course", ""))
    batch = normalize_batch(request.form.get("batch", ""))
    regno = request.form.get("RegNo", "").strip()

    if course != "UG" or not re.fullmatch(r"\d{4}_\d{4}", batch):
        flash("Invalid course or batch.", "error")
        return redirect(url_for("admin"))

    df = load_csv(course, batch)

    if df is None:
        return redirect(url_for("admin"))

    student_index = df[
        df["RegNo"].astype(str) == regno
    ].index

    if len(student_index) == 0:
        return redirect(url_for("admin"))

    row = student_index[0]

    validation_error = validate_student_details(request.form, df, is_new=False)
    if validation_error:
        flash(validation_error, "error")
        return redirect(url_for("student_search", course=course, batch=batch,
                                search_type="regno", keyword=regno))

    # Remove Photo
    photo = request.files.get("Photo")
    if request.form.get("remove_photo") == "1" and not (photo and photo.filename):

        old_photo = df.loc[row, "Photo"]

        if old_photo:

            photo_path = get_existing_photo_path(course, batch, old_photo)

            if os.path.exists(photo_path):
                os.remove(photo_path)

        df.loc[row, "Photo"] = ""

    # Update values
    for column in df.columns:

        if column in request.form and column not in {"RegNo", "Course", "Batch", "Photo"}:
            df.loc[row, column] = request.form.get(column, "")
            # Convert DOB from HTML format to CSV format
    df.loc[row, "DOB"] = format_dob_for_csv(
    df.loc[row, "DOB"]
)

    if photo and photo.filename:
        old_photo = str(df.loc[row, "Photo"]).strip()
        try:
            filename = save_uploaded_photo(photo, course, batch, regno)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("student_search", course=course, batch=batch,
                                    search_type="regno", keyword=regno))
        df.loc[row, "Photo"] = filename
        if old_photo and old_photo != filename:
            old_path = get_existing_photo_path(course, batch, old_photo)
            if os.path.isfile(old_path):
                os.remove(old_path)

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


    logs = list(reversed(read_recent_log_lines(500)))


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

    course = normalize_course(request.form.get("course", ""))
    batch = normalize_batch(request.form.get("batch", ""))
    regno = request.form.get("RegNo", "").strip()


    df=load_csv(
        course,
        batch
    )


    if df is not None:

        matches = df[df["RegNo"].astype(str).str.strip() == regno]
        if matches.empty:
            flash("Student not found.", "error")
            return redirect(url_for("admin"))
        old_photo = str(matches.iloc[0].get("Photo", "")).strip()


        df=df[
            df["RegNo"].astype(str).str.strip()!=regno
        ]


        save_csv(
            df,
            course,
            batch
        )


        # Do this only after the CSV is safely replaced, so an I/O failure
        # never removes a photo while the student record still references it.
        if old_photo:
            photo_path = get_existing_photo_path(course, batch, old_photo)
            if os.path.isfile(photo_path):
                try:
                    os.remove(photo_path)
                except OSError:
                    write_log(f"Photo cleanup failed after deleting student | {regno}")


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


        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")


        admin=load_admin()

        if not verify_admin_password(admin, current_password):
            return render_template("change_password.html", error="Current password is incorrect.")
        if len(new_password) < 12:
            return render_template("change_password.html", error="New password must be at least 12 characters.")
        if new_password != confirm_password:
            return render_template("change_password.html", error="New passwords do not match.")


        # SECURITY FIX: store the new password hashed rather than in plain
        # text (see load_admin()/verify_admin_password() for the migration
        # path for existing plaintext admin.json files).
        admin["password"]=generate_password_hash(new_password)


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

    course = normalize_course(request.form.get("course", ""))
    batch = normalize_batch(request.form.get("batch", ""))

    try:
        path = get_csv_path(course, batch)
    except ValueError:
        flash("Invalid course or batch.", "error")
        return redirect(url_for("admin"))

    if os.path.exists(path):
        try:
            # A batch deletion is irreversible without a backup and must also
            # remove its nested photographs, which otherwise retain personal
            # data and accumulate as inaccessible files.
            create_backup(f"Automatic Backup Before Deleting {course} {batch}")
            photo_folder = get_photo_folder(course, batch)
            pending_photo_folder = photo_folder + ".delete_pending"
            pending_csv_path = path + ".delete_pending"
            if os.path.exists(pending_photo_folder):
                raise OSError("A previous batch photo deletion is still pending")
            if os.path.exists(pending_csv_path):
                raise OSError("A previous batch deletion is still pending")
            if os.path.isdir(photo_folder):
                os.rename(photo_folder, pending_photo_folder)
            os.rename(path, pending_csv_path)
            if os.path.isdir(pending_photo_folder):
                shutil.rmtree(pending_photo_folder)
            os.remove(pending_csv_path)
        except Exception:
            if 'pending_csv_path' in locals() and os.path.exists(pending_csv_path) and not os.path.exists(path):
                try:
                    os.rename(pending_csv_path, path)
                except OSError:
                    pass
            if 'pending_photo_folder' in locals() and os.path.isdir(pending_photo_folder) \
                    and not os.path.isdir(get_photo_folder(course, batch)):
                try:
                    os.rename(pending_photo_folder, get_photo_folder(course, batch))
                except OSError:
                    pass
            app.logger.exception("Batch deletion failed")
            flash("Batch deletion failed; check that the safety backup and files are writable.", "error")
            return redirect(url_for("admin"))

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

    course = normalize_course(request.form.get("course", ""))
    batch = normalize_batch(request.form.get("batch", ""))

    # BUG FIX: create_empty_batch() -> get_photo_folder() raises ValueError
    # for a course that isn't UG/PG or a batch that doesn't match the
    # required YYYY_YYYY shape. That was previously unhandled here and
    # crashed the request with a 500 instead of a friendly flash message.
    try:
        result = create_empty_batch(course, batch)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("admin"))

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

    course = normalize_course(search_data.get("course", ""))
    batch = normalize_batch(search_data.get("batch", ""))

    # BUG FIX: search_type/keyword were previously read with bracket access
    # (search_data["search_type"]), which raises an unhandled 400/500 for any
    # request missing either field instead of failing gracefully.
    search_type = search_data.get("search_type", "").strip().lower()
    keyword = search_data.get("keyword", "").strip()

    if not search_type or not keyword:
        flash("Please provide a search type and keyword.", "error")
        return redirect(url_for("admin"))

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

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", regno):
        return "Register number may contain only letters, numbers, hyphens, and underscores."

    if not name:

        return "Student name is required."

    if len(name) > 120:
        return "Student name is too long."

    if (
        is_new
        and
        not dataframe[
            dataframe["RegNo"].astype(str).str.strip() == regno
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

    dob = form.get("DOB", "").strip()
    if dob:
        try:
            parsed_dob = pd.to_datetime(dob, format="%Y-%m-%d", errors="raise").date()
        except (TypeError, ValueError):
            return "Enter a valid date of birth."
        if parsed_dob > date.today():
            return "Date of birth cannot be in the future."

    return ""
# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":

    # DEPLOYMENT / SECURITY FIX:
    # - debug now defaults to OFF and is only enabled by explicitly setting
    #   FLASK_DEBUG=1 in the environment (was hardcoded to True, which is a
    #   remote-code-execution risk if this process is ever reachable
    #   publicly, via the Werkzeug interactive debugger).
    # - port now honors the PORT environment variable used by most hosting
    #   platforms (Render, Heroku, etc.), falling back to 5000 to preserve
    #   the existing local-development default.
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1"
    )
