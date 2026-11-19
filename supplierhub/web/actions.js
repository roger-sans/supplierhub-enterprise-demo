import {actors,categories,departments,esc,evidenceKinds,icon,options} from "./ui.js";

const supplierBase = "/api/suppliers";
const countries = ["BE","DE","ES","FI","FR","GB","IE","NL","PL","PT","SE"];
const currencies = ["EUR","GBP","SEK"];
const reason = {name:"reason",label:"Decision reason",type:"textarea",min:8,placeholder:"Explain the evidence or business reason",full:true};
const read = (name,label,value="",extra={}) => ({name,label,value,...extra});
const select = (name,label,choices,value="") => read(name,label,value,{choices});
const date = (name,label,value="") => read(name,label,value,{type:"date"});
const number = (name,label,value,minimum,maximum) => read(name,label,value,{type:"number",min:minimum,max:maximum});
const master = (row={}) => [
  read("name","Registered supplier name",row.name,{full:true,min:3}),select("country","Country",countries,row.country||"DE"),
  read("registration","Synthetic registration",row.registration,{pattern:"DEMO-[A-Z0-9]{4,12}",placeholder:"DEMO-X1234"}),
  select("category","Category",categories,row.category),select("segment","Segment",["standard","preferred","strategic"],row.segment),
  select("risk","Risk tier",["medium","low","high"],row.risk),number("payment_days","Payment days",row.payment_days??30,0,180),
  select("currency","Currency",currencies,row.currency),
];

function field(item) {
  const value = esc(item.value);
  let control;
  if (item.choices) control = `<select name="${item.name}" required>${options(item.choices,item.value)}</select>`;
  else if (item.type==="textarea") control = `<textarea name="${item.name}" rows="${item.rows||3}" minlength="${item.min||1}" maxlength="${item.max||360}" placeholder="${esc(item.placeholder)}" required>${value}</textarea>`;
  else control = `<input name="${item.name}" type="${item.type||"text"}" value="${value}" required
    ${item.pattern?`pattern="${esc(item.pattern)}"`:""}
    ${item.type==="number"?`min="${item.min}" max="${item.max}"`:`minlength="${item.min||1}" maxlength="120"`}
    placeholder="${esc(item.placeholder)}">`;
  return `<label class="form-field ${item.full?"form-full":""}"><span>${esc(item.label)}</span>${control}</label>`;
}

function decision(title,path,revision,defaults={},description="") {
  return {title,path,defaults:{revision,...defaults},fields:[reason],description};
}

function snapshot(asOf) {
  return JSON.stringify({
    version:"1.0",source:"DEMO-ERP",data_class:"synthetic",extracted_at:asOf+"T07:00:00Z",
    records:[{external_key:"DEMO-ERP-910",name:"Lark Hollow Ceramics",country:"IE",registration:"DEMO-R9910",category:"Materials"}],
  },null,2);
}

export async function actionSpec(action,id,context,actor,asOf,api) {
  const row = context.row;
  const root = row ? supplierBase+"/"+row.id : "";
  const rev = row?.revision;
  const tomorrow = new Date(asOf);
  tomorrow.setUTCDate(tomorrow.getUTCDate()+30);
  const future = tomorrow.toISOString().slice(0,10);
  const evidenceRef = read("ref","Synthetic reference","",{placeholder:"DEMO-REF-0001"});
  switch (action) {
    case "create-supplier": return {title:"New supplier",path:supplierBase,fields:master(),next:result=>"supplier/"+result.id};
    case "edit-supplier": return {title:"Edit master data",path:root,method:"PATCH",defaults:{revision:rev},
      fields:[...master(row),reason],description:row.state==="approved"?"Saving changes requires a new qualification review.":""};
    case "submit-review": return decision("Submit for review",root+"/submit",rev,{},"Submit the current master and supplier profile to the assigned teams.");
    case "approve-review": return decision("Approve "+departments[actor]+" gate",root+"/decisions",rev,{decision:"approve"},"The service checks current evidence and critical incidents before recording this approval.");
    case "return-review": return decision("Return for changes",root+"/decisions",rev,{decision:"return"},"This closes the current review cycle and returns it to Buying.");
    case "add-evidence": {
      const permitted = {buyer:["supplier_profile"],procurement:["supplier_profile"],finance:["financial_review"],operations:["capacity_check"],quality:["quality_certificate"],legal:["legal_clearance"]}[actor] || [];
      return {title:"Register evidence",path:root+"/evidence",defaults:{revision:rev},fields:[
        select("kind","Evidence type",Object.fromEntries(permitted.map(kind=>[kind,evidenceKinds[kind]]))),
        read("title","Title","",{min:3,full:true}),evidenceRef,date("valid_until","Valid until",future),
      ],description:"Register the metadata for a fictional document."};
    }
    case "add-incident": {
      const kinds = {finance:["financial"],operations:["delivery"],quality:["quality"],legal:["compliance"]}[actor] || ["delivery","quality","financial","compliance"];
      return {title:"Open incident",path:root+"/incidents",defaults:{revision:rev},fields:[
        read("title","Incident title","",{min:3,full:true}),select("kind","Risk type",kinds),select("severity","Severity",["major","minor","critical"]),
        date("due_on","Remediation due",future),
      ],description:"Severity and type determine the response. A critical incident suspends an approved supplier or an open review."};
    }
    case "close-incident": return decision("Close incident",root+"/incidents/"+id+"/close",rev,{},"Record the containment or remediation evidence.");
    case "add-agreement": return {title:"Propose agreement",path:root+"/agreements",defaults:{revision:rev},fields:[
      read("title","Agreement title","",{min:3,full:true}),evidenceRef,select("currency","Currency",currencies,row.currency),
      date("starts_on","Effective from",asOf),date("ends_on","Expires on",future),number("annual_value","Annual value",10000,1,1000000000),
    ],description:"Legal reviews proposed agreements."};
    case "activate-agreement": return decision("Activate agreement",root+"/agreements/"+id+"/decisions",rev,{state:"effective"});
    case "retire-agreement": return decision("Retire agreement",root+"/agreements/"+id+"/decisions",rev,{state:"retired"});
    case "add-initiative": {
      const suppliers = (await api(supplierBase+"?limit=200")).rows;
      return {title:"New sourcing initiative",path:"/api/sourcing",fields:[
        select("supplier_id","Candidate supplier",Object.fromEntries(suppliers.map(item=>[item.id,item.name]))),
        read("item_family","Item or service family","",{min:3}),read("title","Initiative title","",{min:3,full:true}),
        date("target_on","Target date",future),
      ]};
    }
    case "move-initiative": {
      const initiative = context.initiatives.find(item=>item.id===id);
      const next = {discovery:"qualification",qualification:"commercial",commercial:"awarded"}[initiative.stage];
      const choices = [...(next && (next!=="awarded"||actor==="procurement")?[next]:[]),"closed"];
      return {title:"Update sourcing stage",path:"/api/sourcing/"+id+"/move",defaults:{revision:initiative.revision},
        description:next==="awarded"?"Award requires Procurement, a qualified supplier and a current effective agreement.":"",
        fields:[select("stage","Move to",choices),reason]};
    }
    case "stage-batch": return {title:"Stage synthetic snapshot",path:"/api/identity/batches",fields:[
      read("payload","Source contract JSON",snapshot(asOf),{type:"textarea",max:160000,rows:13,full:true}),
    ],description:"The version 1.0 contract admits up to 50 records. Staging never changes supplier master data.",
    prepare:data=>JSON.parse(data.payload),next:result=>"identity/"+result.id};
    case "resolve-identity": {
      const item = context.batch.rows.find(entry=>entry.external_key===id);
      const match = item.candidates.filter(candidate=>candidate.country===item.record.country && candidate.registration===item.record.registration);
      const dispositions = [...(match.length?["link"]:[]),...(!item.candidates.length?["create"]:[]),"dismiss"];
      return {title:"Resolve "+item.record.name,path:"/api/identity/batches/"+context.batch.id+"/rows/"+id+"/resolve",
        description:"A matching country and registration are required to link. Uncertain matches can be dismissed with a reason.",
        fields:[select("action","Disposition",dispositions),
          ...(match.length ? [select("supplier_id","Canonical match",Object.fromEntries(match.map(candidate=>[candidate.id,candidate.name])))] : []),reason],
        prepare:data=>{if(data.action!=="link") delete data.supplier_id; return data;}};
    }
    default: return null;
  }
}

export function modalForm(spec,actor) {
  return `<form id="action-form"><div class="dialog-head"><div><h2 id="dialog-title">${esc(spec.title)}</h2>
    <p>Acting as ${esc(actors[actor])}</p></div><button type="button" class="icon-btn" data-action="close-modal" aria-label="Close dialog">${icon("close",21)}</button></div>
    <div class="dialog-body">${spec.description?`<p class="form-help">${esc(spec.description)}</p>`:""}
    <div class="form-grid">${spec.fields.map(field).join("")}</div><p id="form-error" role="alert" hidden></p></div>
    <div class="dialog-footer"><button type="button" class="btn" data-action="close-modal">Cancel</button><button type="submit" class="btn primary">Save decision</button></div></form>`
    .replace("Save decision", spec.fields.includes(reason) ? (spec.title.startsWith("Edit")?"Save changes":"Confirm") : "Save");
}
