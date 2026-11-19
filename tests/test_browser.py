from playwright.sync_api import expect


def route(page, base, path, heading):
    page.goto(base + "/#" + path)
    expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()


def role(page, value):
    page.get_by_role("combobox", name="Simulated role").select_option(value)
    expect(page.locator("main")).to_have_attribute("aria-busy", "false")


def reason(page, value="Reviewed the fictional operating evidence for this decision."):
    page.get_by_label("Decision reason").fill(value)


def test_qualification_change_through_browser(page, live_url):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    route(page, live_url, "overview", "Supplier overview")
    page.get_by_role("link", name="Approval desk", exact=True).click()
    page.get_by_role("row", name="Aster Vale", exact=False).get_by_role("link", name="Review case").click()
    expect(page.get_by_role("heading", name="Aster Vale Components")).to_be_visible()
    role(page, "quality")
    page.get_by_role("button", name="Approve", exact=True).click()
    reason(page)
    page.get_by_role("button", name="Confirm", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("current evidence")
    page.get_by_role("button", name="Cancel", exact=True).click()
    page.get_by_role("link", name="Evidence", exact=True).click()
    page.get_by_role("button", name="Register evidence", exact=True).click()
    page.get_by_label("Title", exact=True).fill("Quality continuity certificate")
    page.get_by_label("Synthetic reference").fill("DEMO-WEB-QUALITY")
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_text("Quality continuity certificate", exact=True)).to_be_visible()
    page.get_by_role("link", name="Qualification", exact=True).click()
    for actor in ["quality", "operations", "finance"]:
        role(page, actor)
        page.get_by_role("button", name="Approve", exact=True).click()
        reason(page)
        page.get_by_role("button", name="Confirm", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_hidden()
    expect(page.get_by_text("Eligible for downstream use", exact=True)).to_be_visible()
    page.get_by_role("link", name="Data products", exact=True).click()
    expect(page.get_by_role("link", name="Aster Vale Components", exact=False)).to_be_visible()
    with page.expect_download() as download:
        page.get_by_role("link", name="Download JSON").click()
    assert download.value.suggested_filename == "qualified-suppliers-v1.json"
    assert errors == []


def test_steward_reconciles_registration_and_reloads(page, live_url):
    route(page, live_url, "identity", "Identity reconciliation")
    role(page, "steward")
    pending = page.get_by_role("row", name="Aster Vale Components Ltd", exact=False)
    pending.get_by_role("button", name="Resolve", exact=True).click()
    page.get_by_label("Disposition").select_option("link")
    reason(page, "The source and master registration match exactly.")
    page.get_by_role("button", name="Confirm", exact=True).click()
    expect(pending.get_by_text("Linked", exact=True)).to_be_visible()
    page.reload()
    expect(pending.get_by_text("Linked", exact=True)).to_be_visible()
    pending.get_by_role("link", name="Aster Vale Components", exact=True).click()
    page.get_by_role("link", name="Lineage & audit", exact=True).click()
    expect(page.get_by_text("DEMO-CAT-201", exact=True)).to_be_visible()


def test_mobile_navigation_filters_and_supplier_creation(page, live_url):
    page.set_viewport_size({"width": 390, "height": 844})
    route(page, live_url, "overview", "Supplier overview")
    assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
    page.get_by_role("button", name="Toggle navigation").click()
    page.get_by_role("link", name="Suppliers", exact=True).click()
    expect(page.get_by_role("heading", name="Supplier directory")).to_be_visible()
    page.get_by_role("searchbox", name="Search suppliers").fill("nordlume")
    page.get_by_role("button", name="Apply filters").click()
    expect(page.get_by_role("link", name="Nordlume Precision", exact=False)).to_be_visible()
    expect(page.get_by_role("link", name="Aster Vale Components", exact=False)).to_have_count(0)
    page.get_by_role("button", name="New supplier", exact=True).click()
    page.get_by_label("Registered supplier name").fill("Longfen Sample Logistics")
    page.get_by_label("Synthetic registration").fill("DEMO-E2E3")
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("heading", name="Longfen Sample Logistics")).to_be_visible()
    expect(page.get_by_text("Held from downstream publication", exact=True)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth === innerWidth")


def test_critical_incident_suspends_from_supplier_record(page, live_url):
    route(page, live_url, "supplier/SUP-005/incidents", "Rillcrest Motion")
    expect(page.get_by_text("Eligible for downstream use", exact=True)).to_be_visible()
    role(page, "quality")
    page.get_by_role("button", name="Open incident").click()
    page.get_by_label("Incident title").fill("Urgent fixture inspection")
    page.get_by_label("Severity").select_option("critical")
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_text("Held from downstream publication")).to_be_visible()
    page.get_by_role("button", name="Close incident").click()
    reason(page, "Containment confirmed; initiate a new qualification cycle.")
    page.get_by_role("button", name="Confirm").click()
    expect(page.get_by_text("Closed", exact=True)).to_be_visible()
    expect(page.get_by_text("Suspended", exact=True)).to_be_visible()
    page.get_by_role("link", name="Qualification", exact=True).click()
    role(page, "buyer")
    expect(page.get_by_role("button", name="Submit for review")).to_be_visible()
