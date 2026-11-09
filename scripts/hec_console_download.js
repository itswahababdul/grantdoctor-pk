// Paste this whole thing into the Console tab (F12 -> Console) while on https://research.hec.gov.pk/ , press Enter.
// It runs inside YOUR browser on the public HEC pages, downloads everything, and saves ONE file: hec_data.json
// Then attach hec_data.json in the chat. Nothing else to do. (If Chrome asks, type: allow pasting)
(async () => {
  const B = "/hec-rnd-rest/rest/rga/";
  const out = { batches: null, rejected: {}, approved: {}, errors: [] };
  const get = async (u) => { const r = await fetch(u, { headers: { Accept: "application/json, text/plain, */*" } });
    if (!r.ok) throw new Error(u + " -> " + r.status); return r.json(); };
  const listOf = (o) => { let best = []; const st = [o]; while (st.length) { const x = st.pop();
    if (Array.isArray(x)) { if (x.length && typeof x[0] === "object" && x.length > best.length) best = x; st.push(...x.slice(0, 3)); }
    else if (x && typeof x === "object") st.push(...Object.values(x)); } return best; };
  try { out.batches = await get(B + "getAllRgaBatch"); } catch (e) { out.errors.push(String(e)); }
  const bl = out.batches ? listOf(out.batches) : [];
  const idKey = bl.length ? (bl[0].value !== undefined ? "value" : Object.keys(bl[0]).find(k => /^id$|batchid/i.test(k)) || Object.keys(bl[0])[0]) : null;
  let ids = bl.length ? bl.map(b => b[idKey]) : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  console.log("batch ids:", ids);
  const approvedNames = ["getApprovedProjectInformation", "getApprovedProjects", "getApprovedProjectsInformation", "getApprovedProjectList", "getApprovedProjectInformationByBatch", "getAllApprovedProjects"];
  let approvedName = null;
  for (const id of ids) {
    try { out.rejected[id] = await get(B + "getRejectedProjectInformation/" + id); console.log("rejected", id, listOf(out.rejected[id]).length); }
    catch (e) { out.errors.push(String(e)); }
    if (!approvedName) for (const n of approvedNames) { try { out.approved[id] = await get(B + n + "/" + id); approvedName = n; break; } catch (e) {} }
    else try { out.approved[id] = await get(B + approvedName + "/" + id); } catch (e) { out.errors.push(String(e)); }
    if (out.approved[id]) console.log("approved", id, listOf(out.approved[id]).length);
    await new Promise(r => setTimeout(r, 1500));
  }
  out.approvedEndpoint = approvedName;
  const blob = new Blob([JSON.stringify(out)], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "hec_data.json"; a.click();
  console.log("DONE. errors:", out.errors, "approved endpoint:", approvedName);
})();
