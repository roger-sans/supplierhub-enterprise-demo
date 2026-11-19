# Product review walkthrough

The business date is 1 November 2026. Start from a fresh database for the counts and states below. Each perspective is selected with **Simulated role** in the header.

## A case from evidence gap to qualified data product

1. Open **Approval desk** and select **Review case** for **Aster Vale Components** (`SUP-001`). Procurement has already approved. Finance, Operations and Quality are pending. Quality has an expired certificate.
2. Choose **Quality engineer**. Attempt to approve with a decision reason such as “Verified the controlled process declaration.” The service reports missing current evidence. Cancel the dialog.
3. Open **Evidence**, register a **Quality certificate** with title “Renewed process declaration”, reference `DEMO-EV-NEW1` and validity after 1 November 2026. Return to **Qualification** and approve the Quality gate with a reason.
4. Switch to **Operations planner** and approve the capacity gate. Switch to **Finance controller** and approve the final open gate. The record becomes eligible. **Data products** now lists Aster Vale Components in the versioned JSON.
5. Switch to **Quality engineer**, open **Incidents** and add a **critical** **quality** incident with a future remediation due date. The record is suspended and leaves the published product. Close the incident with a reason. It remains suspended until the **Sourcing buyer** submits a new review and all required gates approve.
6. In **Lineage & audit**, expand an approval or incident entry. Inspect the actor, reason and state transition.

## Enhanced approval and sourcing award

- Open **Kestrel Arc Materials**. Its high-risk case includes Legal. The case can open while other functions collect evidence. It qualifies only once all five roles approve. Each role can add only its own evidence.
- On an approved supplier, propose a commercial agreement as **Sourcing buyer**, then switch to **Legal reviewer** to activate it. Create a sourcing initiative and move it through qualification and commercial stages. Switch to **Procurement lead** to award. The service checks current qualification and an effective agreement on the business date.

## Governed source reconciliation

1. Select **Data steward** and open **Identity reconciliation**. The seeded catalog batch includes an exact registration match, a name-only match and a new supplier.
2. Resolve **Aster Vale Components Ltd** by linking its matching country and registration to **Aster Vale Components**. Open supplier lineage to confirm the binding. Master name and risk remain under domain control.
3. Dismiss **Nordlume-Precision** with a reason after observing the different registration. The name candidate cannot be linked or used to create a duplicate from that batch. Resolve **West Ember Textiles** as a new draft; qualification remains a separate workflow.
4. Stage a new snapshot using the sample in the dialog. Re-stage it and observe the same batch ID. Open **Audit trail** to inspect both import and resolution decisions.

## Discussion prompts

- Which role can stop a sourcing award, and what conditions restore eligibility?
- What would change if Finance needed early pipeline data for forecasts?
- If scorecards show 98% delivery with a base of 10 observations, what should the app display?
- What would you require before enabling a second source or warehouse-backed consumer?
