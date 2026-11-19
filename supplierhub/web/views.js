import {actors, avatar, badge, button, categories, dateLabel, departments, empty, esc, evidenceKinds, heading, icon, money, num, options, panel, pct, pretty, routeLink, stages, supplierLink, table} from "./ui.js";

const addSupplier = actor => ["buyer","steward"].includes(actor) ? button("create-supplier","New supplier",{css:"btn primary",glyph:"plus"}) : "";
const progress = gates => {
  const completed = gates.filter(gate => gate.status === "approved").length;
  return `<span class="gate-progress" aria-label="${completed} of ${gates.length} gates approved">${gates.map(gate=>`<i class="${gate.status==="approved"?"complete":""}"></i>`).join("")}<small>${completed}/${gates.length}</small></span>`;
};
function trendPlot(trend) {
  if (!trend.length) return empty("No delivery observations in this period.");
  const baseline = Math.max(0, Math.floor(Math.min(...trend.map(row=>row.pct))/10)*10-10);
  const middle = (100+baseline)/2;
  const position = value => 100*(value-baseline)/(100-baseline);
  const bars = trend.map(row=>{
    const month = new Intl.DateTimeFormat("en-GB",{month:"short",timeZone:"UTC"}).format(new Date(row.period));
    return `<div class="plot-column"><div class="plot-track"><div class="plot-bar" style="--bar:${position(row.pct)}%;" title="${month}: ${pct(row.pct)}, ${num(row.deliveries)} deliveries"></div></div><span>${month}</span></div>`;
  }).join("");
  return `<div class="plot" role="img" aria-label="${esc(trend.map(row=>dateLabel(row.period)+": "+pct(row.pct)).join(", "))}">
    <div class="plot-scale"><span>100%</span><span>${middle}%</span><span>${baseline}%</span></div>
    <div class="plot-area"><div class="plot-grid"><i></i><i></i><i></i></div><div class="plot-bars">${bars}</div></div>
  </div>`;
}

export function overview(data, actor, params) {
  if (params.get("view")==="renewals") {
    return `<div class="back-link">${routeLink("overview","Supplier overview","subtle-link","left")}</div>`+
      heading("Upcoming renewals","Effective agreements expiring in the next 45 days.")+
      panel("Renewal calendar",table(["Supplier","Agreement","Expires","Annual value"],data.renewals.map(row=>[
        supplierLink(row.supplier_id,row.supplier_name),
        routeLink("supplier/"+row.supplier_id+"/agreements",row.ref),
        dateLabel(row.ends_on),money(row.annual_value,row.currency),
      ]),"No agreements expire in the next 45 days."));
  }
  const metrics = [
    ["users","Suppliers", data.supplier_count, "In the governed master", "suppliers", "green"],
    ["shield","Qualified", data.qualified_count, "Eligible for downstream use", "products", "green"],
    ["clock","In review", data.review_count, "Awaiting a decision", "reviews", "amber"],
    ["calendar","Renewals due", data.renewals.length, "Next 45 days", "overview?view=renewals", "indigo"],
  ];
  const metricsHTML = metrics.map(([glyph,label,value,help,path,tone])=>
    `<a href="#${path}" class="metric"><div class="metric-top"><span class="metric-icon ${tone}">${icon(glyph,18)}</span>${icon("chevron",16)}</div><strong>${num(value)}</strong><div class="metric-label">${label}</div><small>${help}</small></a>`).join("");
  const exceptions = [
    ...data.blockers.map(row=>[row,"alert","Critical incident",row.due_on,"red"]),
    ...data.renewals.slice(0,3).map(row=>[row,"calendar","Agreement renewal",row.ends_on,"amber"]),
  ];
  const exceptionHTML = exceptions.length ? `<div class="exceptions">${exceptions.map(([item,glyph,label,due,tone])=>
    `<a href="#supplier/${esc(item.supplier_id)}/${glyph==="alert"?"incidents":"agreements"}"><span class="exception-icon ${tone}">${icon(glyph,17)}</span><span><strong>${esc(item.supplier_name)}</strong><small>${label} · ${dateLabel(due)}</small></span>${icon("chevron",16)}</a>`).join("")}</div>` : empty("No critical incidents or upcoming renewals.");
  const latest = data.trend.at(-1)?.pct;
  return heading("Supplier overview","Track qualification, supply performance and upcoming decisions.",addSupplier(actor))+
    `<div class="metric-grid">${metricsHTML}</div><div class="dashboard-grid">
      ${panel("On-time delivery",`<div class="trend-number"><strong>${pct(latest)}</strong><span>latest completed month</span></div>${trendPlot(data.trend)}`,
         {sub:"Weighted by delivery volume across suppliers",action:routeLink("scorecards","Performance","subtle-link","right")})}
      ${panel("Attention needed",exceptionHTML,{sub:"Critical incidents and agreement renewals"})}
    </div>`+
    panel("Approval queue",table(["Supplier","Risk","Gates approved","Pending teams"],data.reviews.slice(0,5).map(row=>[
      supplierLink(row.id,row.name,row.category),badge(row.risk),progress(row.gates),
      `<span class="muted">${row.gates.filter(gate=>gate.status==="pending").map(gate=>departments[gate.role]).join(", ")}</span>`,
    ]),"No reviews are open."),{sub:"Open qualification cases, highest risk first",action:routeLink("reviews","Open approval desk","subtle-link","right")});
}

export function directory(data, params, actor) {
  const match = key => params.get(key) || "";
  const offset = Number(match("offset"));
  const limit = 12;
  function page(value,label) {
    const next = new URLSearchParams(params);
    next.set("offset",value);
    return routeLink("suppliers?"+next,label,"btn");
  }
  return heading("Supplier directory","Find governed supplier records and manage qualification.",addSupplier(actor))+
    `<form id="directory-filters" class="filters">
      <label class="search-field">${icon("search",17)}<input name="q" type="search" aria-label="Search suppliers" placeholder="Search name, ID or registration" value="${esc(match("q"))}"></label>
      <select name="state" aria-label="Lifecycle status"><option value="">All statuses</option>${options(["approved","in_review","changes_requested","draft","suspended"],match("state"))}</select>
      <select name="category" aria-label="Category"><option value="">All categories</option>${options(categories,match("category"))}</select>
      <select name="risk" aria-label="Risk"><option value="">All risk tiers</option>${options(["low","medium","high"],match("risk"))}</select>
      <button class="btn" type="submit">Apply filters</button>
      ${[...params.keys()].some(key=>key!=="offset")?routeLink("suppliers","Clear filters","subtle-link"):""}
    </form>`+panel("Suppliers",table(["Supplier","Country","Segment","Risk","Lifecycle"],data.rows.map(row=>[
      supplierLink(row.id,row.name,row.id+" · "+row.category),esc(row.country),esc(pretty(row.segment)),badge(row.risk),badge(row.state),
    ]))+ `<div class="pagination"><span>${data.total ? `${offset+1}–${offset+data.rows.length} of ${num(data.total)}` : "0 suppliers"}</span><div>${offset>0?page(Math.max(0,offset-limit),"Previous"):""}${offset+limit<data.total?page(offset+limit,"Next"):""}</div></div>`,{css:"directory-panel"});
}

export function reviews(data, actor, params) {
  const mine = params.get("queue") === "mine";
  const rows = data.reviews.filter(row=>!mine || row.gates.some(gate=>gate.role===actor && gate.status==="pending"));
  return heading("Approval desk","Coordinate independent decisions before a supplier can qualify.")+
    `<div class="tabs" aria-label="Approval queue filter">${routeLink("reviews","All open cases",mine?"":"selected")}${routeLink("reviews?queue=mine","My pending gates",mine?"selected":"")}</div>`+
    panel(mine ? "Pending for "+actors[actor] : "Cases in review",table(["Supplier","Risk","Progress","Evidence gaps","Action"],rows.map(row=>[
      supplierLink(row.id,row.name,row.id+" · "+row.category),badge(row.risk),progress(row.gates),
      esc(row.gates.filter(gate=>!gate.evidence).map(gate=>departments[gate.role]).join(", ") || "Complete"),
      routeLink("supplier/"+row.id+"/qualification","Review case","text-link","right"),
    ]),"No pending cases for this view."),{sub:"Legal joins enhanced reviews for high-risk suppliers."});
}

function facts(row) {
  const details = [["Supplier identity",row.id],["Business registration",row.registration],["Category",row.category],["Region",row.region],["Segment",pretty(row.segment)],["Payment terms",row.payment_days+" days"],["Currency",row.currency],["Accountable desk",actors[row.owner]]];
  return `<dl class="facts">${details.map(([label,value])=>`<div><dt>${label}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>`;
}

function qualification(row, actor) {
  const headline = row.state==="in_review" ? "Review cycle "+row.cycle : "Qualification requirements";
  const primary = actor==="buyer" && ["draft","changes_requested","suspended"].includes(row.state) ?
    button("submit-review","Submit for review",{css:"btn primary",glyph:"right"}) : "";
  return panel(headline, `<div class="gates">${row.gates.map(gate=>{
    const action = row.state==="in_review" && gate.status==="pending" && gate.role===actor ?
      button("return-review","Return",{css:"btn small"})+button("approve-review","Approve",{css:"btn primary small"}) : "";
    return `<div class="gate"><div class="gate-mark">${icon(gate.status==="approved"?"check":"shield",18)}</div><div class="gate-detail">
      <strong>${departments[gate.role]}</strong>
      <span>${esc(evidenceKinds[gate.kind])} · ${gate.evidence?`Valid to ${dateLabel(gate.evidence.valid_until)}`:"Current evidence required"}</span>
      ${gate.reason ? `<small>${esc(gate.reason)}</small>` : ""}</div>
      <div class="row-actions">${badge(gate.status)}${action}</div></div>`;
  }).join("")}</div>`,{sub:row.risk==="high"?"Enhanced due diligence requires Legal review.":"Each department owns its evidence and decision.",action:primary});
}

export function detail(row, tab, actor, asOf) {
  const canEdit = ["buyer","steward"].includes(actor) && row.state!=="in_review";
  const tabs = [["qualification","Qualification"],["evidence","Evidence"],["agreements","Agreements"],["incidents","Incidents"],["lineage","Lineage & audit"]];
  const bar = `<div class="tabs" aria-label="Supplier record sections">${tabs.map(([key,label])=> routeLink("supplier/"+row.id+"/"+key,label,tab===key?"selected":"")).join("")}</div>`;
  let main = "";
  if (tab==="qualification") main = qualification(row,actor)+panel("Master data",facts(row));
  if (tab==="evidence") main = panel("Evidence register",table(["Evidence","Reference","Owner","Valid until","Status"],row.evidence.map(item=>[
    `<strong>${esc(item.title)}</strong><small class="cell-meta">${esc(evidenceKinds[item.kind])}</small>`,
    esc(item.ref),esc(departments[item.created_by]),dateLabel(item.valid_until),badge(item.valid_until>=asOf?"current":"expired"),
  ])),{action:actor==="steward"?"":button("add-evidence","Register evidence",{css:"btn primary",glyph:"plus"}),sub:"Reference metadata for fictional documents."});
  if (tab==="agreements") main = panel("Commercial agreements",table(["Agreement","Window","Annual value","State","Actions"],row.agreements.map(item=>[
    `<strong>${esc(item.title)}</strong><small class="cell-meta">${esc(item.ref)}</small>`,
    `${dateLabel(item.starts_on)} – ${dateLabel(item.ends_on)}`,money(item.annual_value,item.currency),
    badge(item.state==="effective"&&item.ends_on<asOf?"expired":item.state),
    actor==="legal"&&item.state!=="retired" ? `<span class="row-actions">${item.state==="proposed" ? button("activate-agreement","Activate",{id:item.id,css:"btn small"}) : ""}${button("retire-agreement","Retire",{id:item.id,css:"btn small"})}</span>` : "—",
  ])),{action:["buyer","procurement"].includes(actor)?button("add-agreement","Propose agreement",{css:"btn primary",glyph:"plus"}):"",sub:"Legal owns activation and retirement."});
  if (tab==="incidents") main = panel("Risk and incident register",table(["Incident","Severity","Owner","Due","Status","Actions"],row.incidents.map(item=>[
    `<strong>${esc(item.title)}</strong><small class="cell-meta">${esc(item.resolution || pretty(item.kind))}</small>`,
    badge(item.severity),esc(departments[item.owner]),dateLabel(item.due_on),badge(item.state),
    item.owner===actor&&item.state==="open"?button("close-incident","Close incident",{id:item.id,css:"btn small"}):"—",
  ])),{action:!["steward"].includes(actor)?button("add-incident","Open incident",{css:"btn primary",glyph:"plus"}):"",sub:"Open critical incidents block eligibility and suspend active reviews."});
  if (tab==="lineage") main = panel("Source identities",table(["Namespace","Source key","Batch reference","Linked"],row.source_links.map(link=>[
    esc(link.source),esc(link.external_key),esc(link.batch_id),dateLabel(link.linked_at),
  ]),"No source identity is linked."))+auditPanel(row.audit);
  return `<div class="back-link">${routeLink("suppliers","Supplier directory","subtle-link","left")}</div>
    <div class="page-head supplier-head"><div class="record-title">${avatar(row.name)}<div><h1>${esc(row.name)}</h1><p>${esc(row.id)} · ${esc(row.category)} · ${esc(row.region)}</p></div></div>
    ${canEdit?button("edit-supplier","Edit master data"): ""}</div>
    <div class="record-summary">${badge(row.state)}${badge(row.risk,pretty(row.risk)+" risk")}
    ${badge(row.qualified?"current":"held",row.qualified?"Eligible for downstream use":"Held from downstream publication")}
    <span class="summary-score">Performance score <strong>${row.scorecard.score ?? "—"}</strong></span></div>
    ${bar}<div class="stack">${main}</div>`;
}

export function sourcing(rows, actor) {
  const manager = ["buyer","procurement"].includes(actor);
  return heading("Sourcing pipeline","Move candidate supply options from discovery to commercial award.",
    manager?button("add-initiative","New initiative",{css:"btn primary",glyph:"plus"}):"")+
    `<div class="board">${stages.map(stage=>{
      const column = rows.filter(row=>row.stage===stage);
      return `<section class="board-lane"><h2>${pretty(stage)} <span>${column.length}</span></h2>
        ${column.map(row=>`<article class="board-card"><strong>${esc(row.title)}</strong>
        ${routeLink("supplier/"+row.supplier_id,row.supplier_name,"subtle-link")}
        <small>${icon("calendar",13)} ${dateLabel(row.target_on)}</small>
        ${manager&&stage!=="closed"?button("move-initiative","Update stage",{id:row.id,css:"btn small"}):""}</article>`).join("") || empty("No initiatives")}</section>`;
    }).join("")}</div>`;
}

export function scorecards(data) {
  const covered = data.rows.filter(row=>row.score!=null).length;
  const metric = (row,key,base) => `<strong>${pct(row[key])}</strong><small class="cell-meta">${row[base]!=null?`n = ${num(row[base])}`:"No observations"}</small>`;
  const end = new Date(data.end_exclusive);
  end.setUTCDate(end.getUTCDate()-1);
  return heading("Supplier performance","Compare delivery, inspection quality and compliance using source counts.")+
    panel("Rolling scorecards",table(["Supplier","Delivery · 50%","Quality · 30%","Compliance · 20%","Composite / 100"],data.rows.map(row=>[
      supplierLink(row.supplier_id,row.name,row.category),metric(row,"delivery_pct","delivery_base"),
      metric(row,"quality_pct","quality_base"),metric(row,"compliance_pct","compliance_base"),
      row.score==null ? badge("held","Insufficient evidence") : `<strong class="score">${row.score.toFixed(1)}</strong>`,
    ])),{sub:`${dateLabel(data.start)} – ${dateLabel(end)} · ${covered} of ${data.rows.length} suppliers scored. Minimum bases: 20 deliveries, 20 inspections, 3 checks.`});
}

export function identity(batches, current, actor) {
  const pending = current?.rows.filter(row=>row.disposition==="pending").length ?? 0;
  const rows = current?.rows.map(entry=>[
    `<strong>${esc(entry.record.name)}</strong><small class="cell-meta">${esc(entry.external_key+" · "+entry.record.country+" · "+entry.record.registration)}</small>`,
    entry.candidates.length?entry.candidates.map(candidate=>`<div class="candidate">${routeLink("supplier/"+candidate.id,candidate.name)}<small>${esc(candidate.match)}</small></div>`).join(""):"No candidate",
    badge(entry.disposition),
    actor==="steward"&&entry.disposition==="pending" ? button("resolve-identity","Resolve",{id:entry.external_key,css:"btn small"}) : entry.reason ? esc(entry.reason) : "—",
  ]) || [];
  return heading("Identity reconciliation","Stage a synthetic source snapshot, resolve candidates and preserve source lineage.",
    actor==="steward"?button("stage-batch","Stage snapshot",{css:"btn primary",glyph:"upload"}):"")+
    `<div class="stack">${current?panel("Source review",table(["Source record","Canonical candidates","Disposition","Resolution"],rows),{
      sub:`${current.source} · extracted ${dateLabel(current.extracted_at)} · ${pending} unresolved`,
    }):""}
    ${panel("Import batches",table(["Batch","Source","Extracted","Records","Pending"],batches.map(item=>[
      routeLink("identity/"+item.id,item.id,"text-link"),esc(item.source),dateLabel(item.extracted_at),num(item.records),num(item.pending),
    ])))}</div>`;
}

export function products(health, data) {
  return heading("Data products","Inspect eligibility, data quality and the versioned handoff to downstream consumers.")+
    `<div class="metric-grid compact-metrics">
      <div class="metric"><div class="metric-label">Published suppliers</div><strong>${data.records.length}</strong><small>Qualified Suppliers v1.0</small></div>
      <div class="metric"><div class="metric-label">Scorecard coverage</div><strong>${health.scored_suppliers}/${health.total_suppliers}</strong><small>Minimum sample sizes met</small></div>
      <div class="metric"><div class="metric-label">Observation age</div><strong>${health.observation_age_days ?? "—"} <span>days</span></strong><small>Freshness target ≤ ${health.observation_freshness_target_days} days</small></div>
      <div class="metric"><div class="metric-label">Identity exceptions</div><strong>${health.pending_source_rows}</strong><small>Unresolved source records</small></div>
    </div>
    <div class="stack">
    ${panel("Qualified Suppliers",table(["Supplier","Country","Category","Segment","Payment days"],data.records.map(row=>[
      supplierLink(row.supplier_id,row.name,row.supplier_id),esc(row.country),esc(row.category),esc(pretty(row.segment)),num(row.payment_days),
    ])),{sub:"Owner: Procurement Data · Grain: one eligible supplier · Consumers: Buying, Finance and Analytics",action:`<a href="/api/v1/products/qualified-suppliers" class="btn" download="qualified-suppliers-v1.json">${icon("data",16)} Download JSON</a>`})}
    ${panel("Quality exceptions",health.approved_held.length?`<div class="exceptions">${health.approved_held.map(id=>`<a href="#supplier/${esc(id)}"><span class="exception-icon amber">${icon("alert",17)}</span><span><strong>${esc(id)}</strong><small>Approved history · held for evidence or risk</small></span>${icon("chevron",16)}</a>`).join("")}</div>`:empty("All previously approved suppliers remain eligible."))}
    </div>`;
}

export function auditPanel(rows) {
  return panel("Decision history",table(["Recorded","Actor","Event","Record","Change"],rows.map(row=>{
    const why = row.after?.reason || row.after?.resolution || "";
    return [dateLabel(row.occurred_at),esc(actors[row.actor] || pretty(row.actor)),
      `<strong>${esc(row.action.replaceAll("."," · "))}</strong>`,row.supplier_id?routeLink("supplier/"+row.supplier_id+"/lineage",row.entity_id):esc(row.entity_id),
      `<details><summary>${why?esc(why):"View change"}</summary><pre>${esc(JSON.stringify({before:row.before,after:row.after},null,2))}</pre></details>`];
  }),"No supplier events yet."),{sub:"Latest recorded events, with decision reasons and before/after values."});
}

export function audit(rows) {
  return heading("Audit trail","Trace who changed a supplier, what changed and the reason for each decision.")+auditPanel(rows);
}
