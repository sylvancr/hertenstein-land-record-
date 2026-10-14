// Hertenstein readings: serves the phone form and saves each reading to Google.
// One row per reading goes to a Sheet, photos go to a Drive folder. Both are
// created on first use in the Drive of whoever deploys this script.
// Station links: <web app url>?s=S1 ... ?s=S10 fill in the station for the visitor.

const FOLDER_NAME = 'Hertenstein readings';
const SHEET_NAME = 'Hertenstein readings';
const NOTIFY = ''; // an address here gets one email per reading; '' keeps it quiet
const MAX_FILE_MB = 10;
const MAX_FILES = 6;

// Provisional; set real positions after the site walk (also kept in the Stations tab).
const STATIONS = [
  ['S1', 'Oak park'],
  ['S2', 'Best meadow'],
  ['S3', 'Hay meadow'],
  ['S4', 'Kitchen garden'],
  ['S5', 'Woodland edge'],
  ['S6', 'Hedge or orchard'],
  ['S7', 'Shore and landing'],
  ['S8', 'Wet ground'],
  ['S9', 'Night sky spot'],
  ['S10', 'Courtyard']
];

const TYPES = {
  birds: 'Five-minute bird count',
  pollinators: 'Ten-minute pollinator count',
  flowers: 'Flowers in bloom',
  lake: 'Lake',
  soil: 'Soil',
  night: 'Night',
  first: 'First of the year',
  weather: 'Weather',
  invasive: 'Invasive plant or pest',
  other: 'Anything else'
};

const HEADERS = [
  'Received', 'Observed', 'Station', 'Latitude', 'Longitude', 'Accuracy (m)',
  'Reading', 'Summary', 'Main number', 'Values (JSON)', 'Notes', 'Photos',
  'Photo sharing', 'Name', 'Experience', 'Confidence', 'Contact',
  'Reviewed', 'Review note'
];

function doGet(e) {
  const t = HtmlService.createTemplateFromFile('Index');
  const s = String((e && e.parameter && e.parameter.s) || '').toUpperCase();
  t.station = STATIONS.some(function (r) { return r[0] === s; }) ? s : '';
  t.stations = STATIONS;
  return t.evaluate()
    .setTitle('Readings · Stella Matutina, Hertenstein')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// Same as the form's Send, for testing with a JSON POST.
function doPost(e) {
  let result;
  try {
    result = submit(JSON.parse(e.postData.contents));
  } catch (err) {
    result = { ok: false, error: err.message };
  }
  return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
}

// Run once from the editor to create the folder and sheet and grant permissions.
function setup() {
  const folder = getFolder_();
  const sheet = getSheet_();
  Logger.log('Folder: ' + folder.getUrl());
  Logger.log('Sheet: ' + sheet.getParent().getUrl());
}

// Logs the ten station links once the script is deployed as a web app.
function stationLinks() {
  const url = ScriptApp.getService().getUrl();
  STATIONS.forEach(function (r) { Logger.log(r[0] + ' ' + r[1] + ': ' + url + '?s=' + r[0]); });
}

function submit(data) {
  data = data || {};
  if (data.website) return { ok: true }; // hidden field only bots fill in

  const type = String(data.type || '');
  if (!TYPES[type]) throw new Error('Choose a reading first.');
  const station = STATIONS.some(function (r) { return r[0] === data.station; }) ? data.station : 'Elsewhere';
  const values = cleanValues_(data.values);
  const notes = clean_(data.notes, 5000);
  const files = Array.isArray(data.files) ? data.files.slice(0, MAX_FILES) : [];
  if (!Object.keys(values).length && !notes && !files.length) {
    throw new Error('Add a reading, a note or a photo first.');
  }

  const observed = parseDate_(data.observed);
  const name = clean_(data.name, 200);
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  let links = [];
  try {
    const folder = getFolder_();
    const stamp = Utilities.formatDate(observed, 'Europe/Zurich', 'yyyy-MM-dd HH.mm');
    links = files.map(function (f, i) {
      const bytes = Utilities.base64Decode(String(f.data || ''));
      if (bytes.length > MAX_FILE_MB * 1024 * 1024) {
        throw new Error(clean_(f.name, 120) + ' is larger than ' + MAX_FILE_MB + ' MB.');
      }
      const fileName = [stamp, station, type, i + 1, clean_(f.name, 120)].join(' ');
      const blob = Utilities.newBlob(bytes, String(f.type || 'application/octet-stream'), fileName);
      return folder.createFile(blob).getUrl();
    });
    getSheet_().appendRow([
      new Date(), observed, station,
      num_(data.lat), num_(data.lon), num_(data.accuracy),
      TYPES[type], clean_(data.summary, 500), num_(data.main),
      JSON.stringify(values), notes, links.join('\n'),
      clean_(data.share, 60), name, clean_(data.experience, 40),
      clean_(data.confidence, 40), clean_(data.contact, 200), '', ''
    ]);
  } finally {
    lock.releaseLock();
  }

  if (NOTIFY) {
    MailApp.sendEmail(NOTIFY, 'Hertenstein reading: ' + TYPES[type] + ' at ' + station,
      clean_(data.summary, 500) + '\n\n' + (notes ? notes + '\n\n' : '') + links.join('\n'));
  }
  return { ok: true };
}

function getFolder_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('FOLDER_ID');
  if (id) {
    try { return DriveApp.getFolderById(id); } catch (e) { /* deleted: make a new one */ }
  }
  const folder = DriveApp.createFolder(FOLDER_NAME);
  props.setProperty('FOLDER_ID', folder.getId());
  return folder;
}

function getSheet_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('SHEET_ID');
  if (id) {
    try { return SpreadsheetApp.openById(id).getSheetByName('Readings'); } catch (e) { /* deleted: make a new one */ }
  }
  const ss = SpreadsheetApp.create(SHEET_NAME);
  DriveApp.getFileById(ss.getId()).moveTo(getFolder_());
  const sheet = ss.getSheets()[0].setName('Readings');
  sheet.appendRow(HEADERS);
  sheet.setFrozenRows(1);
  const st = ss.insertSheet('Stations');
  st.appendRow(['Station', 'Habitat', 'Latitude', 'Longitude', 'Notes']);
  STATIONS.forEach(function (r) { st.appendRow([r[0], r[1], '', '', '']); });
  st.setFrozenRows(1);
  props.setProperty('SHEET_ID', ss.getId());
  return sheet;
}

// Keeps a flat object of short strings, numbers and lists of {name, count}.
function cleanValues_(v) {
  const out = {};
  if (!v || typeof v !== 'object') return out;
  Object.keys(v).slice(0, 40).forEach(function (k) {
    const key = String(k).replace(/[^a-zA-Z0-9_]/g, '').slice(0, 40);
    const val = v[k];
    if (!key || val === '' || val == null) return;
    if (Array.isArray(val)) {
      const rows = val.slice(0, 60).map(function (r) {
        return { name: clean_(r && r.name, 120), count: num_(r && r.count) };
      }).filter(function (r) { return r.name; });
      if (rows.length) out[key] = rows;
    } else if (typeof val === 'number' || typeof val === 'boolean') {
      out[key] = val;
    } else {
      out[key] = clean_(val, 1000);
    }
  });
  return out;
}

function parseDate_(s) {
  const d = new Date(String(s || ''));
  const now = new Date();
  // Accept up to a year back and a day ahead (clock drift); otherwise use now.
  if (isNaN(d) || d > new Date(now.getTime() + 864e5) || d < new Date(now.getTime() - 365 * 864e5)) return now;
  return d;
}

function num_(v) {
  const n = parseFloat(String(v == null ? '' : v).replace(',', '.'));
  return isFinite(n) ? n : '';
}

// Trims, caps length, and stops text being read as a spreadsheet formula.
function clean_(value, max) {
  let s = String(value == null ? '' : value).trim().slice(0, max);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}
