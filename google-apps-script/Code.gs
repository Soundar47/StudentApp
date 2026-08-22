/**
 * Creates the biodata Form and links responses to a new Spreadsheet.
 * Run once, then add the Photo File Upload item manually in the Form editor.
 */
function createStudentBiodataForm() {
  const form = FormApp.create('Student Biodata Collection');
  form.setDescription('Submit or update student biodata. Use the existing register number for updates.');

  form.addTextItem().setTitle('RegNo').setRequired(true);
  form.addTextItem().setTitle('Name').setRequired(true);
  form.addListItem().setTitle('Course').setChoiceValues(['UG', 'PG']).setRequired(true);
  form.addTextItem().setTitle('Batch').setRequired(true);
  form.addDateItem().setTitle('DOB');
  form.addListItem().setTitle('Community').setChoiceValues([
    'General', 'BC', 'MBC', 'SC', 'ST', 'Other'
  ]);
  form.addTextItem().setTitle('ParentName');
  form.addTextItem().setTitle('MotherName');
  form.addTextItem().setTitle('faOccupation');
  form.addTextItem().setTitle('moOccupation');
  form.addTextItem().setTitle('AnualIncome');
  form.addParagraphTextItem().setTitle('Address');
  form.addTextItem().setTitle('Pincode');
  form.addTextItem().setTitle('Mobile');
  form.addMultipleChoiceItem().setTitle('FirstGraduate').setChoiceValues(['Yes', 'No']);
  form.addTextItem().setTitle('BankName');
  form.addTextItem().setTitle('Branch');
  form.addTextItem().setTitle('BankAccount');
  form.addTextItem().setTitle('IFSC');
  form.addTextItem().setTitle('MICR');
  form.addTextItem().setTitle('Aadhar');
  form.addListItem().setTitle('BloodGroup').setChoiceValues([
    'A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'
  ]);
  form.addTextItem().setTitle('UmisID');
  form.addTextItem().setTitle('EmisNo');
  form.addTextItem().setTitle('Email');

  const responseSheet = SpreadsheetApp.create('Student Biodata Form Responses');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, responseSheet.getId());

  Logger.log('Form edit URL: ' + form.getEditUrl());
  Logger.log('Form published URL: ' + form.getPublishedUrl());
  Logger.log('Spreadsheet URL: ' + responseSheet.getUrl());
  Logger.log('Next: open the Form edit URL, add a File upload question titled Photo, make it required, images only, max 1 file.');
}
