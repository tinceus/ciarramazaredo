/**
 * Content Router: Apps Script Web App
 * ===================================
 * One deployment that reads and writes every post-mapping spreadsheet the
 * deploying account can edit. push_to_sheets.py is the client.
 *
 * Setup: Project Settings > Script Properties
 *   ROUTER_TOKEN          shared secret, same value as SHEET_ROUTER_TOKEN on the client
 *   DIAG_SPREADSHEET_ID   (optional) a spreadsheet to inspect with diagComments()
 *
 * OPS
 *   GET  ?token&spreadsheetId&sheet          -> { sheet, spreadsheet, rows }
 *   POST { token, spreadsheetId, sheet, op }
 *     writeCell         row, col, value
 *     updateRange       range, values
 *     appendRow         values
 *     clearRange        range
 *     deleteRow         row
 *     listSheets
 *     readNotes                              -> { ok, notes }
 *     readSheetFull                          -> { ok, rows, notes }
 *     writeNote         row, col, note
 *     writeCellWithNote row, col, value, note
 *     listComments      max                  -> { ok, driveVersion, comments }
 *     addComment        content, anchor
 *     deleteComment     commentId
 *
 * NOTE ON doGet: it returns NO "ok" field. The client does not require one.
 */

function token_() {
  const t = PropertiesService.getScriptProperties().getProperty("ROUTER_TOKEN");
  if (!t) throw new Error("ROUTER_TOKEN script property is not set");
  return t;
}

function doGet(e) {
  if (e.parameter.token !== token_()) return json({ error: "Unauthorized" });
  if (!e.parameter.spreadsheetId) return json({ error: "Missing spreadsheetId" });

  const ss = SpreadsheetApp.openById(e.parameter.spreadsheetId);
  const sheet = e.parameter.sheet ? ss.getSheetByName(e.parameter.sheet) : ss.getActiveSheet();
  if (!sheet) return json({ error: "Sheet not found: " + e.parameter.sheet });

  return json({
    sheet: sheet.getName(),
    spreadsheet: ss.getName(),
    rows: sheet.getDataRange().getValues()
  });
}

function doPost(e) {
  let body;
  try { body = JSON.parse(e.postData.contents); }
  catch (_) { return json({ error: "Invalid JSON" }); }

  if (body.token !== token_()) return json({ error: "Unauthorized" });
  if (!body.spreadsheetId) return json({ error: "Missing spreadsheetId" });

  const ss = SpreadsheetApp.openById(body.spreadsheetId);
  const sheet = body.sheet ? ss.getSheetByName(body.sheet) : ss.getActiveSheet();
  if (!sheet) return json({ error: "Sheet not found: " + body.sheet });

  const op = body.op;
  try {
    if (op === "writeCell")   { sheet.getRange(body.row, body.col).setValue(body.value); return json({ ok: true }); }
    if (op === "updateRange") { sheet.getRange(body.range).setValues(body.values);        return json({ ok: true, range: body.range, count: body.values.length }); }
    if (op === "appendRow")   { sheet.appendRow(body.values);                              return json({ ok: true }); }
    if (op === "clearRange")  { sheet.getRange(body.range).clearContent();                return json({ ok: true }); }
    if (op === "deleteRow")   { sheet.deleteRow(body.row);                                return json({ ok: true }); }
    if (op === "listSheets")  { return json({ ok: true, sheets: ss.getSheets().map(s => s.getName()) }); }

    // ---- NOTE SUPPORT ----
    if (op === "readNotes")     { return json({ ok: true, notes: sheet.getDataRange().getNotes() }); }
    if (op === "readSheetFull") {
      const r = sheet.getDataRange();
      return json({ ok: true, rows: r.getValues(), notes: r.getNotes() });
    }
    if (op === "writeNote")     {
      sheet.getRange(body.row, body.col).setNote(body.note == null ? "" : String(body.note));
      return json({ ok: true });
    }
    if (op === "writeCellWithNote") {
      const c = sheet.getRange(body.row, body.col);
      if ("value" in body) c.setValue(body.value);
      if ("note"  in body) c.setNote(body.note == null ? "" : String(body.note));
      return json({ ok: true });
    }

    // ---- COMMENT SUPPORT ----
    // Sheets COMMENTS are not notes. They live in Drive, not in the Sheet, so
    // SpreadsheetApp cannot touch them. These ops use the advanced Drive service,
    // which must be enabled in the editor: Services + > Drive API > Add.
    // Anchors are undocumented for Sheets, so we never invent one: listComments
    // reads the anchors the file already has and addComment reuses that shape.

    if (op === "listComments") {
      const out = driveListComments_(body.spreadsheetId, body.max || 50);
      return json({ ok: true, driveVersion: out.v, comments: out.items });
    }

    if (op === "addComment") {
      if (!body.content) return json({ error: "addComment needs content" });
      try {
        let created;
        if (typeof Drive.Comments.create === "function") {          // Drive v3
          created = Drive.Comments.create(
            { content: String(body.content), anchor: body.anchor || undefined },
            body.spreadsheetId, { fields: "id,anchor,content" });
        } else {                                                     // Drive v2
          created = Drive.Comments.insert(
            { content: String(body.content), anchor: body.anchor || undefined },
            body.spreadsheetId);
        }
        return json({ ok: true, commentId: created.id || created.commentId, anchor: created.anchor });
      } catch (err) {
        return json({ error: "addComment failed", detail: err.toString() });
      }
    }

    if (op === "deleteComment") {
      if (!body.commentId) return json({ error: "deleteComment needs commentId" });
      try {
        if (typeof Drive.Comments.remove === "function") Drive.Comments.remove(body.spreadsheetId, body.commentId);
        else Drive.Comments.delete(body.spreadsheetId, body.commentId);
        return json({ ok: true, deleted: body.commentId });
      } catch (err) {
        return json({ error: "deleteComment failed", detail: err.toString() });
      }
    }

    return json({ error: "Unknown op: " + op });
  } catch (err) {
    return json({ error: err.toString() });
  }
}

/**
 * Read comments through whichever Drive advanced-service version is enabled.
 * Returns { v: "v3"|"v2"|"none", items: [...] }. Never throws.
 */
function driveListComments_(fileId, max) {
  if (typeof Drive === "undefined" || !Drive.Comments) {
    return { v: "none", items: [{ error: "Drive advanced service is not enabled. Editor > Services + > Drive API > Add." }] };
  }
  try {
    const res = Drive.Comments.list(fileId, {
      fields: "comments(id,content,anchor,resolved,author/displayName,quotedFileContent)",
      pageSize: max, includeDeleted: false
    });
    return { v: "v3", items: (res.comments || []).map(function (c) {
      return { id: c.id, content: c.content, anchor: c.anchor, resolved: c.resolved,
               author: c.author && c.author.displayName,
               quoted: c.quotedFileContent && c.quotedFileContent.value };
    })};
  } catch (e3) {
    try {
      const res2 = Drive.Comments.list(fileId, { maxResults: max });
      return { v: "v2", items: (res2.items || []).map(function (c) {
        return { id: c.commentId, content: c.content, anchor: c.anchor, resolved: c.status === "resolved",
                 author: c.author && c.author.displayName, quoted: c.context && c.context.value };
      })};
    } catch (e2) {
      return { v: "none", items: [{ error: "v3: " + e3 + " | v2: " + e2 }] };
    }
  }
}

/**
 * Run once from the editor (Run > diagComments) to learn the anchor format a
 * file already uses. Reads DIAG_SPREADSHEET_ID from Script Properties.
 */
function diagComments() {
  const id = PropertiesService.getScriptProperties().getProperty("DIAG_SPREADSHEET_ID");
  if (!id) throw new Error("Set the DIAG_SPREADSHEET_ID script property first");
  const out = driveListComments_(id, 15);
  Logger.log("Drive version in use: " + out.v);
  Logger.log(JSON.stringify(out.items, null, 2));
}

function json(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
