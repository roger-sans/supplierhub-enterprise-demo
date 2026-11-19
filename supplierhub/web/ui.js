const paths = {
  brand: '<path d="M4 7.2 12 3l8 4.2v9.6L12 21l-8-4.2z"/><path d="m4 7.2 8 4.4 8-4.4M12 11.6V21m-4-15.9 8 4.3v3.5"/>',
  overview: '<rect x="3" y="3" width="7" height="8" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="3" y="15" width="7" height="6" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.9M15 3.1a4 4 0 0 1 0 7.8"/><circle cx="9" cy="7" r="4"/>',
  shield: '<path d="M12 22s7-3 7-9V5l-7-3-7 3v8c0 6 7 9 7 9Z"/><path d="m9 12 2 2 4-4"/>',
  board: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16m6-16v16M6 8v3m6-3v6m6-6v2"/>',
  chart: '<path d="M3 3v18h18M8 16v-4m5 4V7m5 9v-7"/>',
  identity: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8" cy="10" r="2"/><path d="M5.5 16a2.5 2.5 0 0 1 5 0m3.5-6h4m-4 4h4"/>',
  data: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  audit: '<path d="M8 4H5v17h14V4h-3m-8 0a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2H8Zm0 7h8m-8 5h6"/>',
  chevron: '<path d="m9 18 6-6-6-6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  right: '<path d="M4 12h15m-6-6 6 6-6 6"/>',
  left: '<path d="M20 12H5m6-6-6 6 6 6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  file: '<path d="M6 3h8l4 4v14H6zm8 0v5h4M9 12h6m-6 4h6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  alert: '<path d="M12 3 2.7 20h18.6L12 3Zm0 6v4m0 3h.01"/>',
  search: '<circle cx="10.5" cy="10.5" r="6"/><path d="m16 16 4 4"/>',
  external: '<path d="M13 4h7v7m0-7-9 9m6 1v6H4V7h6"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  upload: '<path d="M12 16V4m-4 4 4-4 4 4M4 16v4h16v-4"/>',
};
export const icon = (name, size = 19) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.file}</svg>`;
export const esc = (val = "") => String(val ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[char]);
export const pretty = (val = "") => ({"in_review":"In review","changes_requested":"Changes requested","not_started":"Not started","already_linked":"Already linked","DEMO-ERP":"Demo ERP","DEMO-CATALOG":"Demo catalog"}[val] || String(val).replaceAll("_"," ").replace(/^./, char => char.toUpperCase()));
export const badge = (value, label = pretty(value)) => `<span class="badge badge-${esc(value)}">${esc(label)}</span>`;
export const dateLabel = val => val ? new Intl.DateTimeFormat("en-GB", {day:"numeric",month:"short",year:"numeric",timeZone:"UTC"}).format(new Date(val)) : "—";
export const pct = val => val == null ? "—" : `${Number(val).toFixed(1)}%`;
export const num = val => new Intl.NumberFormat("en-GB").format(val);
export const money = (amount, currency) => new Intl.NumberFormat("en-GB",{style:"currency",currency,maximumFractionDigits:0}).format(amount);
export const actors = {buyer:"Sourcing buyer",procurement:"Procurement lead",finance:"Finance controller",operations:"Operations planner",quality:"Quality engineer",legal:"Legal reviewer",steward:"Data steward"};
export const departments = {buyer:"Buying",procurement:"Procurement",finance:"Finance",operations:"Operations",quality:"Quality",legal:"Legal",steward:"Data Governance"};
export const categories = ["Components","Materials","Packaging","Industrial services","Freight"];
export const evidenceKinds = {supplier_profile:"Supplier profile",financial_review:"Financial review",capacity_check:"Capacity check",quality_certificate:"Quality certificate",legal_clearance:"Legal clearance"};
export const stages = ["discovery","qualification","commercial","awarded","closed"];
export const routeLink = (path,label,css="text-link",arrow="") => `<a class="${css}" href="#${esc(path)}">${esc(label)}${arrow ? icon(arrow, 15) : ""}</a>`;
export const button = (action,label,{id="",css="btn",glyph=""}={}) => `<button type="button" class="${css}" data-action="${esc(action)}" data-id="${esc(id)}">${glyph ? icon(glyph, 16) : ""}${esc(label)}</button>`;
export const empty = message => `<div class="empty">${esc(message)}</div>`;
export const avatar = name => `<span class="supplier-mark" aria-hidden="true">${esc(name.split(/\s+/).slice(0,2).map(word=>word[0]).join(""))}</span>`;
export const supplierLink = (id,name,meta="") => `<a href="#supplier/${esc(id)}" class="supplier-link">${avatar(name)}<span><strong>${esc(name)}</strong>${meta ? `<small>${esc(meta)}</small>` : ""}</span></a>`;
export const heading = (title, description, action="") => `<div class="page-head"><div><h1>${esc(title)}</h1><p>${esc(description)}</p></div>${action}</div>`;
export const panel = (title, content, {sub="",action="",css=""}={}) => `<section class="panel ${css}"><div class="panel-head"><div><h2>${esc(title)}</h2>${sub ? `<p>${esc(sub)}</p>` : ""}</div>${action}</div>${content}</section>`;
export const table = (headers,rows,emptyText="No records match this view.") => rows.length ? `<div class="table-wrap"><table><thead><tr>${headers.map(head=>`<th scope="col">${esc(head)}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map((cell,index)=>`<td data-column="${esc(headers[index])}">${cell}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : empty(emptyText);
export const options = (values, selected="") => Object.entries(Array.isArray(values) ? Object.fromEntries(values.map(value=>[value,pretty(value)])) : values).map(([key,label])=>`<option value="${esc(key)}"${key===selected?" selected":""}>${esc(label)}</option>`).join("");
export const navItems = [
  ["Workspace", [["overview","Overview","overview"],["suppliers","Suppliers","users"],["reviews","Approval desk","shield"],["sourcing","Sourcing pipeline","board"]]],
  ["Data & governance", [["scorecards","Performance","chart"],["identity","Identity reconciliation","identity"],["products","Data products","data"],["audit","Audit trail","audit"]]],
];
