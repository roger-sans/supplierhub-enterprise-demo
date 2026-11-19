import {actionSpec, modalForm} from "./actions.js";
import {actors, button, dateLabel, departments, esc, icon, navItems, options, routeLink} from "./ui.js";
import * as views from "./views.js";

const main = document.querySelector("#content");
const sidebar = document.querySelector("#sidebar");
const topbar = document.querySelector("#topbar");
const modal = document.querySelector("#modal");
const notice = document.querySelector("#notice");
let actor = sessionStorage.getItem("supplierhub.role") || "buyer";
if (!actors[actor]) actor = "buyer";
let asOf = "";
let context = {};
let sequence = 0;
let activeSpec;
let noticeTimer;
let mobileMenu = false;

async function api(path, data, method="POST") {
  const response = await fetch(path, data === undefined ? {} : {
    method,headers:{"Content-Type":"application/json","X-Demo-Actor":actor},body:JSON.stringify(data),
  });
  if (!response.ok) {
    let detail;
    try {detail = (await response.json()).detail;} catch {detail = "";}
    if (Array.isArray(detail)) detail = detail.map(error=>error.loc.at(-1)+": "+error.msg).join(" · ");
    throw new Error(detail || "The workspace could not complete this request.");
  }
  return response.json();
}

function locationInfo() {
  const [location,search] = (window.location.hash.slice(1)||"overview").split("?");
  const [view,id,tab] = location.split("/");
  return {view,id,tab,params:new URLSearchParams(search)};
}

function selected() {
  return [...navItems.flatMap(([,items])=>items)].find(([key])=>key===(context.view==="supplier"?"suppliers":context.view));
}

function shell() {
  const [current,title] = selected() || ["overview","Overview"];
  sidebar.classList.toggle("expanded",mobileMenu);
  sidebar.innerHTML = `<a href="#overview" class="brand"><span>${icon("brand",26)}</span><div>SupplierHub<small>Governance workspace</small></div></a>
    <nav>${navItems.map(([segment,items])=>`<div class="nav-group"><div class="nav-heading">${segment}</div>
      ${items.map(([key,label,glyph])=>`<a class="nav-link ${current===key?"active":""}" href="#${key}" ${current===key?'aria-current="page"':""}>${icon(glyph,18)}<span>${label}</span></a>`).join("")}</div>`).join("")}</nav>
    <div class="sidebar-foot"><a href="/docs" target="_blank" rel="noopener" class="nav-link">${icon("file",18)}<span>API documentation</span>${icon("external",14)}</a>
    <div class="environment"><i></i><div><strong>Synthetic workspace</strong><small>Local demo data</small></div></div></div>`;
  topbar.innerHTML = `<div class="breadcrumbs"><button type="button" class="icon-btn mobile-toggle" aria-label="Toggle navigation" aria-expanded="${mobileMenu}" data-action="menu">${icon("menu",22)}</button>
    <span>Supplier workspace</span>${icon("chevron",14)}<strong>${title}</strong></div>
    <div class="toolbar"><span class="date-chip">${icon("calendar",16)} ${dateLabel(asOf)}</span>
    <label class="role-picker"><span class="role-icon" aria-hidden="true">${departments[actor].slice(0,2).toUpperCase()}</span>
    <span class="role-label"><span>Simulated role</span><select id="role-select" aria-label="Simulated role">${options(actors,actor)}</select></span>${icon("down",15)}</label></div>`;
}

async function render() {
  const token = ++sequence;
  context = locationInfo();
  const next = context;
  shell();
  main.setAttribute("aria-busy","true");
  try {
    if (!asOf) asOf = (await api("/api/health")).as_of;
    let page;
    switch (next.view) {
      case "overview": page = views.overview(await api("/api/dashboard"),actor,next.params); break;
      case "suppliers": {
        const params = new URLSearchParams(next.params);
        params.set("limit","12");
        page = views.directory(await api("/api/suppliers?"+params),next.params,actor);
        break;
      }
      case "reviews": page = views.reviews(await api("/api/dashboard"),actor,next.params); break;
      case "supplier": {
        const tabs = ["qualification","evidence","agreements","incidents","lineage"];
        next.row = await api("/api/suppliers/"+encodeURIComponent(next.id));
        page = views.detail(next.row,tabs.includes(next.tab)?next.tab:tabs[0],actor,asOf);
        break;
      }
      case "sourcing":
        next.initiatives = await api("/api/sourcing");
        page = views.sourcing(next.initiatives,actor);
        break;
      case "scorecards": page = views.scorecards(await api("/api/scorecards")); break;
      case "identity": {
        const batches = await api("/api/identity/batches");
        const id = next.id || batches[0]?.id;
        next.batch = id ? await api("/api/identity/batches/"+encodeURIComponent(id)) : null;
        page = views.identity(batches,next.batch,actor);
        break;
      }
      case "products": {
        const [health,product] = await Promise.all([api("/api/data-health"),api("/api/v1/products/qualified-suppliers")]);
        page = views.products(health,product);
        break;
      }
      case "audit": page = views.audit(await api("/api/audit")); break;
      default: page = `<div class="error-screen"><h1>Page unavailable</h1>${routeLink("overview","Return to overview")}</div>`;
    }
    if (token !== sequence) return;
    main.innerHTML = page;
    shell();
    document.title = (main.querySelector("h1")?.textContent||"Workspace") + " · SupplierHub";
  } catch (error) {
    if (token !== sequence) return;
    main.innerHTML = `<div class="error-screen"><h1>Workspace unavailable</h1><p>${esc(error.message)}</p>${button("retry","Try again")}</div>`;
  } finally {
    if (token===sequence) main.setAttribute("aria-busy","false");
  }
}

function flash(text) {
  clearTimeout(noticeTimer);
  notice.textContent = text;
  notice.classList.add("visible");
  noticeTimer = setTimeout(()=>notice.classList.remove("visible"),3500);
}

document.addEventListener("click", async event => {
  const target = event.target.closest("[data-action]");
  if (!target) {
    if (event.target.closest(".skip")) {
      event.preventDefault();
      main.focus();
    }
    if (event.target.closest(".nav-link")) mobileMenu = false;
    return;
  }
  const {action,id} = target.dataset;
  if (action==="menu") {
    mobileMenu = !mobileMenu;
    shell();
    topbar.querySelector(".mobile-toggle").focus();
    return;
  }
  if (action==="close-modal") {modal.close();return;}
  if (action==="retry") {render();return;}
  target.disabled = true;
  try {
    activeSpec = await actionSpec(action,id,context,actor,asOf,api);
    if (!activeSpec) return;
    modal.innerHTML = modalForm(activeSpec,actor);
    modal.showModal();
    modal.querySelector(".form-field input, .form-field select, textarea")?.focus();
  } catch (error) {
    flash(error.message);
  } finally {
    target.disabled = false;
  }
});

document.addEventListener("change", event => {
  if (event.target.id !== "role-select") return;
  actor = event.target.value;
  sessionStorage.setItem("supplierhub.role",actor);
  render().then(()=>document.querySelector("#role-select")?.focus());
});

document.addEventListener("submit", async event => {
  event.preventDefault();
  if (event.target.id==="directory-filters") {
    const filters = new URLSearchParams([...new FormData(event.target)].filter(([,value])=>value.trim()));
    const target = "#suppliers"+(filters.size?"?"+filters:"");
    if (window.location.hash===target) render();
    else window.location.hash = target;
    return;
  }
  if (event.target.id!=="action-form" || !activeSpec) return;
  const submit = event.target.querySelector('[type="submit"]');
  const errorBox = modal.querySelector("#form-error");
  errorBox.hidden = true;
  submit.disabled = true;
  const spec = activeSpec;
  try {
    const data = {...spec.defaults};
    for (const [name,value] of new FormData(event.target)) {
      data[name] = event.target.elements.namedItem(name).type === "number" ? Number(value) : value;
    }
    const payload = spec.prepare ? spec.prepare(data) : data;
    const result = await api(spec.path,payload,spec.method);
    modal.close();
    flash("Changes saved.");
    const next = spec.next?.(result);
    if (next && window.location.hash !== "#"+next) window.location.hash = next;
    else await render();
  } catch (error) {
    errorBox.textContent = error instanceof SyntaxError ? "Enter a valid JSON envelope." : error.message;
    errorBox.hidden = false;
  } finally {
    submit.disabled = false;
  }
});

window.addEventListener("hashchange",()=> {
  mobileMenu = false;
  window.scrollTo(0,0);
  render().then(()=>main.focus({preventScroll:true}));
});
render();
