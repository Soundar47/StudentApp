"""Sanitized, read-only diagnostic for the new Google Form system."""
import json
import os
import sys
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
LEGACY_SHEET_ID = "153RHUhM2Kms340iFLhQrY-KkC7mMmuecTUFNvyqe-Y8"
LEGACY_DEFAULT_FOLDER_ID = "1nib4js7EkrszgAU-vtRl-TD0ZtviZhNz"


def classify_error(error):
    status = getattr(getattr(error, "resp", None), "status", None)
    text = str(error).lower()
    if status == 401:
        return "401 authentication problem"
    if status == 403:
        if "accessnotconfigured" in text or "has not been used" in text:
            return "403 API is not enabled for the service-account project"
        return "403 permission problem"
    if status == 404:
        return "404 resource is missing or inaccessible"
    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return "timeout/OSError network problem"
    if "timeout" in text or "timed out" in text or "connection" in text:
        return "timeout/OSError network problem"
    if "malformed" in text or "private key" in text or "service account" in text:
        return "invalid service-account credentials"
    if status is not None:
        return f"Google API error (HTTP {status})"
    return "Google API error"


def check(name, callback):
    try:
        callback()
        return {"name": name, "status": "PASS"}
    except Exception as error:
        return {"name": name, "status": "FAIL", "reason": classify_error(error)}


def main():
    credential_path = os.environ.get("GOOGLE_CREDENTIALS_FILE", "secrets/google-service-account.json")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    folder_id = os.environ.get("GOOGLE_PHOTO_FOLDER_ID", "").strip()
    result = {"checks": [], "service_account_email": ""}
    if not sheet_id or sheet_id == LEGACY_SHEET_ID:
        result["checks"].append({"name": "new spreadsheet configuration", "status": "FAIL", "reason": "new GOOGLE_SHEET_ID is required"})
    if not folder_id or folder_id == LEGACY_DEFAULT_FOLDER_ID:
        result["checks"].append({"name": "new photo folder configuration", "status": "FAIL", "reason": "new GOOGLE_PHOTO_FOLDER_ID is required"})
    if any(item["status"] == "FAIL" for item in result["checks"]):
        print(json.dumps(result, indent=2))
        return 1

    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        credentials = service_account.Credentials.from_service_account_file(
            credential_path,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        credentials.refresh(Request())
        result["service_account_email"] = credentials.service_account_email
        result["checks"].append({"name": "service account authentication", "status": "PASS"})
    except Exception as error:
        result["checks"].append({"name": "service account authentication", "status": "FAIL", "reason": classify_error(error)})
        print(json.dumps(result, indent=2))
        return 1

    sheets = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
    result["checks"].append(check("Google Sheets API", lambda: sheets.spreadsheets().get(spreadsheetId=sheet_id, fields="spreadsheetId").execute()))
    result["checks"].append(check("Google Drive API", lambda: drive.files().list(pageSize=1, fields="files(id)").execute()))
    result["checks"].append(check("new spreadsheet access", lambda: sheets.spreadsheets().get(spreadsheetId=sheet_id, fields="spreadsheetId,properties(title)").execute()))

    def check_folder():
        folder = drive.files().get(fileId=folder_id, fields="id,name,mimeType", supportsAllDrives=True).execute()
        if folder.get("mimeType") != "application/vnd.google-apps.folder":
            raise ValueError("configured resource is not a folder")

    result["checks"].append(check("new photo folder access", check_folder))
    print(json.dumps(result, indent=2))
    return 0 if all(item["status"] == "PASS" for item in result["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
