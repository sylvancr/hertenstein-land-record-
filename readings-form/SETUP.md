# Hertenstein readings form: setup

Same set-up as the summer reflections page. The form runs on Google Apps Script with no login
for visitors. Each reading becomes a row in a Sheet called "Hertenstein readings" (tab Readings,
plus a Stations tab), and photos land in a Drive folder of the same name, both in your
stella.earth Drive. No emails by default; put an address in `NOTIFY` at the top of Code.gs if
you want one per reading.

## Steps (about five minutes)

1. Go to script.google.com, signed in as your stella.earth account. **New project.** Name it
   "Hertenstein readings".
2. In `Code.gs`, replace everything with the contents of `Code.gs` from this folder.
3. **+ (Add a file) → HTML**, name it `Index` (no extension), and paste in `Index.html` from
   this folder.
4. **Project settings (gear) → Show "appsscript.json"**, then replace that file's contents
   with `appsscript.json` from this folder.
5. Choose `setup` in the function menu and press **Run**. Allow the permissions (Drive,
   Sheets). The log shows links to the new folder and sheet.
6. **Deploy → New deployment → type: Web app.** Execute as: **Me**. Who has access:
   **Anyone**. Deploy and copy the URL ending in `/exec`.
7. Choose `stationLinks` in the function menu and press **Run**. The log lists one link per
   station (`…/exec?s=S1` to `?s=S10`). Each one becomes a QR code on its post. The plain
   link without `?s=` works too and asks the visitor where they are.

## After changes

Edit, then **Deploy → Manage deployments → edit (pencil) → Version: New version**. The link
and the QR codes stay the same.

## Good to know

- Station names are provisional. After the site walk, change `STATIONS` near the top of
  Code.gs and fill in latitude and longitude in the Stations tab.
- Photos over 3 MB are scaled down on the phone before sending, so readings go through on a
  weak signal. Up to 6 photos per reading.
- "Use my location" depends on the phone and browser allowing it inside Google's page. If it
  doesn't work, the station is enough.
- The Reviewed and Review note columns are for the weekly look-over. Mark doubtful rows rather
  than deleting them.
- Values for each reading are kept as JSON in one column, with a plain summary and a main
  number beside it for quick charts.
