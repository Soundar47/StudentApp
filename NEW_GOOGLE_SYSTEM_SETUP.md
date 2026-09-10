# New Google Form System Setup

This procedure is isolated from the legacy Form, Sheet, submissions, and Drive folder. Do not paste credentials into chat or commit them.

## 1. Provision new resources

1. Open [script.google.com](https://script.google.com/) while signed into the Google account that owns the new resources.
2. Create a new standalone Apps Script project. Do not reuse the legacy Apps Script project.
3. Paste `google-apps-script/NewStudentRegistrationSetup.gs` into the project and save it.
4. Run `provisionNewStudentSystem` and approve the normal Google authorization prompts.
5. Copy the six values from the execution log into a private local note. The script creates a new Form, Spreadsheet, `Responses` tab, and `Student Photos NEW` folder, shares the Sheet and folder with the existing service account as Editor, and installs the Form submit trigger.

The script does not create a File Upload item because FormApp does not support that operation.

## 2. Add the Photo question manually

Open the new Form edit URL from the execution log and add one question titled exactly `Photo`:

- Question type: File upload
- Allow only images
- Maximum number of files: 1
- Required: Yes

Do not add or import any old questions or responses. Confirm the response destination is the new spreadsheet and that its response tab is named `Responses`.

## 3. Configure Flask for the new resources

In the active PowerShell terminal, set only the new IDs. The credential path remains the existing private file:

```powershell
$env:GOOGLE_CREDENTIALS_FILE = 'secrets/google-service-account.json'
$env:GOOGLE_SHEET_ID = '<NEW_SPREADSHEET_ID>'
$env:GOOGLE_PHOTO_FOLDER_ID = '<NEW_PHOTO_FOLDER_ID>'
$env:GOOGLE_SHEET_RANGE = 'Responses'
```

Use the project virtual environment when running diagnostics or Flask:

```powershell
.\.venv\Scripts\python.exe google_api_diagnostic.py
```

The diagnostic separately reports service-account authentication, Sheets API, Drive API, new spreadsheet access, and new photo folder access. It rejects the known legacy Sheet IDs and does not print credentials.

For a persistent deployment, set the same variables in the deployment environment. Do not hardcode the IDs into credential files or private keys.

## 4. One-record test

Use exactly one new Form submission:

- `RegNo`: `TEST1001`
- `Name`: `Test Student`
- `Course`: `PG`
- `Batch`: a batch with an existing local CSV, such as `2027-2029`
- Complete the remaining required fields with test values
- Upload one test JPG or PNG as `Photo`

Then run the Flask Google import once. Verify the new `Responses` tab contains one response, the new Drive folder contains the copied photo, and Flask reports one new record. Do not run the importer against the legacy Sheet and do not submit or import old responses.

The existing batch/CSV creation workflow is intentionally unchanged in this first test.
