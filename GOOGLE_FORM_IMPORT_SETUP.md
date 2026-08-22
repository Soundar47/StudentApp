# Existing Google Form Import Setup

This project updates and imports from the existing Form ID `1cABFlYjpqd6yKpn-cm0oUdtqT5BiwDueiUwIf2HHlJA`. It does not create a Form, a response Sheet, or a new public URL.

## Safely update the existing Form

1. Open the existing Apps Script project that has permission to edit the Form, then replace its `Code.gs` with [google-apps-script/Code.gs](google-apps-script/Code.gs).
2. Run `inspectExistingStudentForm`. It is read-only: it logs the Form ID, existing published URL, linked Sheet destination ID, and every question's type/title.
3. Review the log. The updater stops before changing anything if it sees an existing page/section, duplicate managed titles, a title it cannot safely manage, or an incompatible question type. This avoids blindly deleting or replacing Form questions.
4. Confirm the `UG_BATCHES` and `PG_BATCHES` lists in the script match your real batch CSVs. Set `APPLY_LAYOUT = true` only after the inspection succeeds.
5. Run `updateExistingStudentForm`. It reuses compatible questions, adds only missing fields and the second `Batch` question for the PG branch, and changes Course choices to `UG` / `PG`.
6. Open the same Form edit URL. In the final **Student Photo** section, manually add a question titled exactly `Photo`: **File upload**, **Images only**, **maximum 1 file**, and **Required**. Apps Script cannot create File Upload questions.

The update never calls `FormApp.create`, `SpreadsheetApp.create`, or `addFileUploadItem`; it also never deletes questions, Form responses, or the existing response Sheet destination. It changes question order and branching only after the explicit `APPLY_LAYOUT` opt-in.

To verify the old Form URL still works, compare the URL logged by `inspectExistingStudentForm` or `updateExistingStudentForm` with the existing URL, then open it in an incognito/private browser window. The Form ID and public URL remain the same.

## Google Cloud and Flask configuration

1. In Google Cloud Console, select/create a project and enable **Google Sheets API** and **Google Drive API**.
2. Create a service account and store its JSON key privately, e.g. `secrets/google-service-account.json`; never commit it.
3. Share the existing Form response Sheet and the Drive upload folder with the service-account email as **Viewer**.
4. Copy `.env.example` to `.env`, then set `GOOGLE_CREDENTIALS_FILE`, `GOOGLE_SHEET_ID` (the linked response Sheet ID), and `GOOGLE_SHEET_RANGE`.
5. Install dependencies with `pip install -r requirements.txt`.

## Import behavior and test

- Flask maps `UG + 2026-2029` to `data/ug/2026_2029.csv` and maps photos to `static/photos/ug/2026_2029/`.
- It matches students by RegNo inside that exact Course/Batch CSV, updates only Form fields, and preserves all academic columns and rows.
- A missing target CSV is reported and never created during import. CSV `Photo` stores only the filename.
- The local ignored `google_import_log.json` prevents completed Sheet response rows being imported repeatedly.

Before live use, make a backup in the existing Backup & Restore page, submit one UG and one PG test response with an image, click **Import Google Form Responses** as admin, and verify the Course/Batch summary, the nested photo path, and unchanged marks/attendance/result columns. Run import again without new submissions to confirm no duplicate student rows are created.
