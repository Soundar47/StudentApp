/**
 * Provision a completely new Student Registration Form system.
 * Run provisionNewStudentSystem() once from a new Apps Script project.
 * This script never opens, edits, or imports from legacy resources.
 * File Upload questions cannot be created by FormApp and must be added manually.
 */
const NEW_FORM_TITLE = 'Student Registration NEW';
const NEW_SHEET_TITLE = 'Student Registration Responses NEW';
const NEW_SHEET_TAB = 'Responses';
const NEW_PHOTO_FOLDER_TITLE = 'Student Photos NEW';
const SERVICE_ACCOUNT_EMAIL = 'student-management-api@student-506314.iam.gserviceaccount.com';

const FIELD_DEFINITIONS = [
  ['RegNo', 'text'],
  ['Name', 'text'],
  ['Course', 'list'],
  ['Batch', 'text'],
  ['DOB', 'date'],
  ['Community', 'list'],
  ['ParentName', 'text'],
  ['MotherName', 'text'],
  ['faOccupation', 'text'],
  ['moOccupation', 'text'],
  ['Address', 'paragraph'],
  ['Pincode', 'text'],
  ['Mobile', 'text'],
  ['FirstGraduate', 'choice'],
  ['AnualIncome', 'text'],
  ['BankName', 'text'],
  ['Branch', 'text'],
  ['BankAccount', 'text'],
  ['IFSC', 'text'],
  ['MICR', 'text'],
  ['Aadhar', 'text'],
  ['BloodGroup', 'list'],
  ['UmisID', 'text'],
  ['EmisNo', 'text'],
  ['EmisID', 'text'],
  ['Email', 'text']
];

function provisionNewStudentSystem() {
  const photoFolder = DriveApp.createFolder(NEW_PHOTO_FOLDER_TITLE);
  photoFolder.addEditor(SERVICE_ACCOUNT_EMAIL);

  const spreadsheet = SpreadsheetApp.create(NEW_SHEET_TITLE);
  spreadsheet.getSheets()[0].setName(NEW_SHEET_TAB);
  DriveApp.getFileById(spreadsheet.getId()).addEditor(SERVICE_ACCOUNT_EMAIL);

  const form = FormApp.create(NEW_FORM_TITLE);
  addSupportedQuestions(form);
  form.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheet.getId());
  ScriptApp.newTrigger('handleNewStudentSubmit')
    .forForm(form)
    .onFormSubmit()
    .create();

  PropertiesService.getScriptProperties().setProperties({
    NEW_FORM_ID: form.getId(),
    NEW_SHEET_ID: spreadsheet.getId(),
    NEW_PHOTO_FOLDER_ID: photoFolder.getId()
  });

  Logger.log(JSON.stringify({
    formUrl: form.getPublishedUrl(),
    formId: form.getId(),
    spreadsheetUrl: spreadsheet.getUrl(),
    spreadsheetId: spreadsheet.getId(),
    photoFolderUrl: photoFolder.getUrl(),
    photoFolderId: photoFolder.getId(),
    nextStep: 'Manually add Photo as File upload, Images only, max 1, Required.'
  }, null, 2));
}

function addSupportedQuestions(form) {
  FIELD_DEFINITIONS.forEach(function(definition) {
    const title = definition[0];
    const type = definition[1];
    let item;
    if (type === 'paragraph') item = form.addParagraphTextItem();
    else if (type === 'date') item = form.addDateItem();
    else if (type === 'list') item = form.addListItem();
    else if (type === 'choice') item = form.addMultipleChoiceItem();
    else item = form.addTextItem();
    item.setTitle(title).setRequired(true);
    if (title === 'Course') item.setChoiceValues(['UG', 'PG']);
    if (title === 'Community') item.setChoiceValues(['General', 'BC', 'MBC', 'SC', 'ST', 'Other']);
    if (title === 'FirstGraduate') item.setChoiceValues(['Yes', 'No']);
    if (title === 'BloodGroup') item.setChoiceValues(['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']);
  });
}

function handleNewStudentSubmit(event) {
  const properties = PropertiesService.getScriptProperties();
  const folderId = properties.getProperty('NEW_PHOTO_FOLDER_ID');
  const sheetId = properties.getProperty('NEW_SHEET_ID');
  if (!folderId || !sheetId) throw new Error('New system properties are not configured.');

  const answers = {};
  event.response.getItemResponses().forEach(function(itemResponse) {
    answers[itemResponse.getItem().getTitle()] = itemResponse.getResponse();
  });
  const fileIds = Array.isArray(answers.Photo) ? answers.Photo : [answers.Photo];
  const sourceFileId = fileIds.filter(String)[0];
  if (!sourceFileId) throw new Error('Photo upload response did not contain a Drive file ID.');

  const folder = DriveApp.getFolderById(folderId);
  const sourceFile = DriveApp.getFileById(sourceFileId);
  const copyName = String(answers.RegNo || 'student') + ' - ' + String(answers.Name || 'photo');
  const copiedFile = sourceFile.makeCopy(copyName, folder);

  const sheet = SpreadsheetApp.openById(sheetId).getSheetByName(NEW_SHEET_TAB);
  const values = sheet.getDataRange().getValues();
  const headers = values[0].map(String);
  const responseTimestamp = event.response.getTimestamp().getTime();
  let rowNumber = values.length;
  for (let index = values.length - 1; index > 0; index -= 1) {
    const cell = values[index][0];
    if (cell instanceof Date && cell.getTime() === responseTimestamp) {
      rowNumber = index + 1;
      break;
    }
  }
  const photoColumn = headers.indexOf('Photo') + 1;
  if (photoColumn > 0) {
    sheet.getRange(rowNumber, photoColumn).setValue(copiedFile.getUrl());
  }
  Logger.log('Processed new submission for ' + answers.RegNo + '; copied Drive file ' + copiedFile.getId());
}
