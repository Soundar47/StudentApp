/**
 * Safe updater for the existing Student Biodata Form.
 * It never calls FormApp.create(), SpreadsheetApp.create(), or addFileUploadItem().
 */
const STUDENT_FORM_ID = '1cABFlYjpqd6yKpn-cm0oUdtqT5BiwDueiUwIf2HHlJA';
const APPLY_LAYOUT = false; // Run inspectExistingStudentForm() first; then set true.
const UG_BATCHES = ['2026-2029', '2027-2030', '2028-2031'];
const PG_BATCHES = ['2026-2028', '2027-2029', '2028-2030'];

const FIELD_TYPES = {
  RegNo: FormApp.ItemType.TEXT,
  Name: FormApp.ItemType.TEXT,
  Course: FormApp.ItemType.LIST,
  Batch: FormApp.ItemType.LIST,
  DOB: FormApp.ItemType.DATE,
  Community: FormApp.ItemType.LIST,
  ParentName: FormApp.ItemType.TEXT,
  MotherName: FormApp.ItemType.TEXT,
  faOccupation: FormApp.ItemType.TEXT,
  moOccupation: FormApp.ItemType.TEXT,
  AnualIncome: FormApp.ItemType.TEXT,
  Address: FormApp.ItemType.PARAGRAPH_TEXT,
  Pincode: FormApp.ItemType.TEXT,
  Mobile: FormApp.ItemType.TEXT,
  FirstGraduate: FormApp.ItemType.MULTIPLE_CHOICE,
  BankName: FormApp.ItemType.TEXT,
  Branch: FormApp.ItemType.TEXT,
  BankAccount: FormApp.ItemType.TEXT,
  IFSC: FormApp.ItemType.TEXT,
  MICR: FormApp.ItemType.TEXT,
  Aadhar: FormApp.ItemType.TEXT,
  BloodGroup: FormApp.ItemType.LIST,
  UmisID: FormApp.ItemType.TEXT,
  EmisNo: FormApp.ItemType.TEXT,
  Email: FormApp.ItemType.TEXT
};
const ALTERNATE_FIELD_TYPES = {
  Course: [FormApp.ItemType.LIST, FormApp.ItemType.MULTIPLE_CHOICE],
  Batch: [FormApp.ItemType.LIST, FormApp.ItemType.MULTIPLE_CHOICE],
  Community: [FormApp.ItemType.LIST, FormApp.ItemType.MULTIPLE_CHOICE],
  BloodGroup: [FormApp.ItemType.LIST, FormApp.ItemType.MULTIPLE_CHOICE]
};

/** Read-only preflight. Run this first and review the execution log. */
function inspectExistingStudentForm() {
  const form = FormApp.openById(STUDENT_FORM_ID);
  Logger.log('Form ID (must remain unchanged): ' + form.getId());
  Logger.log('Published URL (must remain unchanged): ' + form.getPublishedUrl());
  Logger.log('Edit URL: ' + form.getEditUrl());
  Logger.log('Existing response Sheet destination ID: ' + form.getDestinationId());
  form.getItems().forEach(function(item, index) {
    Logger.log((index + 1) + ': id=' + item.getId() +
      ' type=' + item.getType() + ' title=' + item.getTitle());
  });
}

/**
 * Builds the requested sections only after the form passes a no-delete preflight.
 * This changes question order, Course choices, and Branching. It never deletes
 * questions, responses, the Form, or its existing spreadsheet destination.
 */
function updateExistingStudentForm() {
  if (!APPLY_LAYOUT) {
    throw new Error('Safety stop: run inspectExistingStudentForm(), review its log, then set APPLY_LAYOUT = true.');
  }

  const form = FormApp.openById(STUDENT_FORM_ID);
  const existing = indexItemsByTitle(form);
  assertSafeToReorganize(form, existing);

  const fields = {};
  Object.keys(FIELD_TYPES).forEach(function(title) {
    fields[title] = existing[title] || addField(form, title, FIELD_TYPES[title]);
  });

  // Reuse one existing Batch item for UG; add only the second branch Batch item.
  const ugBatch = fields.Batch;
  choiceItem(ugBatch).setChoiceValues(UG_BATCHES).setRequired(true);
  const pgBatch = form.addListItem().setTitle('Batch').setChoiceValues(PG_BATCHES).setRequired(true);

  configureChoices(fields);

  const personalHeader = form.addSectionHeaderItem().setTitle('Personal Details');
  const ugSection = form.addPageBreakItem().setTitle('UG Batch Selection');
  const pgSection = form.addPageBreakItem().setTitle('PG Batch Selection');
  const studentSection = form.addPageBreakItem().setTitle('Student Personal Details');
  const familySection = form.addPageBreakItem().setTitle('Family Details');
  const addressSection = form.addPageBreakItem().setTitle('Address & Contact Details');
  const academicSection = form.addPageBreakItem().setTitle('Academic Details');
  const bankSection = form.addPageBreakItem().setTitle('Bank Details');
  const otherSection = form.addPageBreakItem().setTitle('Other Details');
  const photoSection = form.addPageBreakItem().setTitle('Student Photo');
  form.addSectionHeaderItem().setTitle('Photo upload').setHelpText(
    'Manually add a question titled Photo: File upload, images only, maximum 1 file, required.'
  );

  ugSection.setGoToPage(studentSection);
  pgSection.setGoToPage(studentSection);
  const courseChoices = choiceItem(fields.Course);
  courseChoices.setChoices([
    courseChoices.createChoice('UG', ugSection),
    courseChoices.createChoice('PG', pgSection)
  ]).setRequired(true);

  const layout = [
    personalHeader, fields.RegNo, fields.Name, fields.Course,
    ugSection, ugBatch,
    pgSection, pgBatch,
    studentSection, fields.DOB, fields.Community,
    familySection, fields.ParentName, fields.MotherName, fields.faOccupation, fields.moOccupation, fields.AnualIncome,
    addressSection, fields.Address, fields.Pincode, fields.Mobile, fields.Email,
    academicSection, fields.FirstGraduate, fields.UmisID, fields.EmisNo,
    bankSection, fields.BankName, fields.Branch, fields.BankAccount, fields.IFSC, fields.MICR,
    otherSection, fields.Aadhar, fields.BloodGroup,
    photoSection
  ];
  layout.forEach(function(item, index) { form.moveItem(item, index); });

  Logger.log('Updated existing Form ID: ' + form.getId());
  Logger.log('Published URL remains: ' + form.getPublishedUrl());
  Logger.log('Existing response Sheet destination remains: ' + form.getDestinationId());
  Logger.log('Next: manually add the required Photo File upload question below Student Photo.');
}

function indexItemsByTitle(form) {
  const indexed = {};
  form.getItems().forEach(function(item) {
    const title = item.getTitle().trim();
    if (title && !indexed[title]) indexed[title] = item;
  });
  return indexed;
}

function assertSafeToReorganize(form, existing) {
  const duplicateTitles = {};
  form.getItems().forEach(function(item) {
    const title = item.getTitle().trim();
    if (title) duplicateTitles[title] = (duplicateTitles[title] || 0) + 1;
    if (item.getType() === FormApp.ItemType.PAGE_BREAK) {
      throw new Error('Safety stop: existing section "' + title + '" was found. Review it manually before restructuring.');
    }
    if (title && !FIELD_TYPES[title] && title !== 'Photo') {
      throw new Error('Safety stop: unmanaged existing item "' + title +
        '" was found. No changes were made, so it can be reviewed safely.');
    }
  });
  Object.keys(FIELD_TYPES).forEach(function(title) {
    if (duplicateTitles[title] > 1) {
      throw new Error('Safety stop: duplicate existing question title "' + title + '". No changes were made.');
    }
    const permittedTypes = ALTERNATE_FIELD_TYPES[title] || [FIELD_TYPES[title]];
    if (existing[title] && permittedTypes.indexOf(existing[title].getType()) === -1) {
      throw new Error('Safety stop: "' + title + '" has type ' + existing[title].getType() +
        ', but this layout requires ' + FIELD_TYPES[title] + '. No question was replaced.');
    }
  });
}

function addField(form, title, type) {
  let item;
  if (type === FormApp.ItemType.TEXT) item = form.addTextItem();
  else if (type === FormApp.ItemType.PARAGRAPH_TEXT) item = form.addParagraphTextItem();
  else if (type === FormApp.ItemType.DATE) item = form.addDateItem();
  else if (type === FormApp.ItemType.LIST) item = form.addListItem();
  else item = form.addMultipleChoiceItem();
  item.setTitle(title);
  return item;
}

function choiceItem(item) {
  return item.getType() === FormApp.ItemType.LIST
    ? item.asListItem()
    : item.asMultipleChoiceItem();
}

function configureChoices(fields) {
  choiceItem(fields.Community).setChoiceValues(['General', 'BC', 'MBC', 'SC', 'ST', 'Other']);
  fields.FirstGraduate.asMultipleChoiceItem().setChoiceValues(['Yes', 'No']);
  choiceItem(fields.BloodGroup).setChoiceValues(['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']);
  fields.RegNo.asTextItem().setRequired(true);
  fields.Name.asTextItem().setRequired(true);
}
