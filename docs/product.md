# Product case study

## Vision

Help regional buying teams make a defensible sourcing decision from one governed supplier record. Each team owns the evidence it can verify. The rest of the company can consume the resulting eligibility decision without reconstructing it from emails or spreadsheets.

The fictional network buys components, raw materials, packaging, freight and industrial services across several European markets. Buying needs an earlier view of candidates. Finance must verify trade terms and financial exposure. Operations must verify capacity and continuity. Quality needs current process evidence and the ability to stop supply selection when a critical exception opens. Legal needs targeted oversight of enhanced due diligence and commercial agreements. Analytics needs stable supplier keys and reusable measures.

## Discovery and decisions

The following scenario is an illustrative product exercise. It records the acceptance decisions a cross-functional team would make and links each one to a working product behavior.

| Stakeholder and decision | Conflict raised during discovery | Product decision and acceptance check |
| --- | --- | --- |
| Regional sourcing buyer, create and progress a candidate | A complete dossier at intake would delay visibility into new supply options | A supplier profile starts the review. Other evidence can arrive during review. An empty individual gate remains blocked. Try the Aster Vale case in the [walkthrough](walkthrough.md). |
| Procurement lead, own classification and award | Buyers want to award a candidate as soon as terms are negotiated | The buyer creates the case. Procurement owns its approval and the award. Award also needs a currently qualified supplier and a current effective agreement. |
| Finance controller, accept financial exposure | Finance wants risk visibility before commitments and consistent payment terms afterward | Finance owns its evidence and approval. Approved master-data edits reopen qualification. Downstream sees payment days and currency through the serving contract. |
| Operations planner, confirm capacity and continuity | Buyers want to use a strong score to override a capacity problem | Operations owns the capacity check and delivery remediation. Performance informs a case, while current evidence and risk determine eligibility. |
| Quality engineer, accept process evidence | A supplier previously approved can still present an expired certificate | Missing evidence blocks Quality. A critical incident suspends an approved case, and closing it starts a new review path. Expiry dynamically removes eligibility. |
| Legal reviewer, decide enhanced exposure | Universal Legal review would congest routine onboarding | Legal joins high-risk qualification and owns agreement activation and retirement. Low- and medium-risk qualification use four gates. |
| Data steward and Analytics engineer | Source identifiers collide across systems and source labels may differ | Match the synthetic registration within its country and review normalized-name candidates. Record the crosswalk and decision. Publish one versioned eligible row per stable supplier key. |

**Change control example.** A request to publish pending suppliers to make pipeline forecasts easier changes the eligibility contract. The Product Owner records the forecasting use case, asks Analytics to estimate consumer impact, and has Finance and Quality confirm the boundary. Use the sourcing pipeline for the current increment. Create a restricted candidate feed only if the separate accepted outcome justifies it, with its own consumer contract.

## Responsibilities

**R** performs the work, **A** accepts the outcome, **C** contributes, **I** receives the outcome. Roles here describe responsibility for the simulated process.

| Outcome | Product Owner | Buying | Procurement lead | Finance | Operations | Quality | Legal | Data steward | Engineering / Analytics |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Scope, sequencing and release acceptance | A/R | C | C | C | C | C | C | C | R |
| Register candidate and coordinate evidence | I | R | A | C | C | C | I | C | I |
| Review financial exposure | I | I | C | A/R | I | I | I | I | I |
| Review capacity and resolve delivery issues | I | I | C | I | A/R | C | I | I | I |
| Accept process evidence and resolve defects | I | I | C | I | C | A/R | I | I | I |
| Enhanced due diligence and agreement activation | I | C | C | C | I | C | A/R | I | I |
| Source identity resolution | I | C | C | C | I | I | I | A/R | C |
| Publish eligible supplier data product | C | I | A | C | C | C | C | R | R |

Buying owns the case and correspondence. Procurement is accountable for the Qualified Suppliers product, with the steward accountable for mappings and Analytics responsible for consumption feedback. Finance can use the projection to reconcile supplier classifications without accessing evidence references or decision text. A federated governance forum owns shared rules for contract naming, classification, changes and deprecation. The Procurement domain owns its supplier-specific definitions and support.

## Delivery and stakeholder cadence

- The Product Owner maintains one ranked queue in GitHub Issues once the repository is provisioned. Capture each request as a consumer decision, trade-off, dependency and acceptance test. Use the [ranked backlog](backlog.json) to initialize the milestones and issues.
- Run two-week iterations. Refine mid-iteration with Buying, a rotating reviewer and Engineering. Engineering sizes items and documents uncertainty as a spike. Planning selects a vertical outcome and identifies the accepting business role.
- A 30-minute review alternates between reviewing an actual decision in the app and inspecting the resulting downstream record. Stakeholders in different time zones get the same recorded scenario and 48 hours for asynchronous comments. Decisions use explicit dates and a UTC timestamp in the audit trail.
- The Product Owner records scope changes on the issue and updates milestone forecasts when a dependency shifts. Business owners accept their scenarios. The release decision requires agreed regression evidence and a recorded owner for known risks.
- **Definition of Ready** requires a named consumer and decision, data grain and authority, a measurable acceptance check, identified dependencies and an agreed policy when a gate or contract changes.
- **Definition of Done** requires passing acceptance and negative cases, documented state transitions, persisted audit evidence, validated contracts, browser review, release notes and sign-off examples for the applicable roles. The [release record](release.md) distinguishes local checks and future deployment gates.

## Adoption and value

Start with one Buying cell and its four reviewers. Use a fictional case in a 20-minute session, then repeat with an enhanced review and steward reconciliation. Keep an escalation route to the Product Owner during the pilot. After two iterations, ask another buying cell to repeat the workflow without coaching. Publish line-by-line product semantics to an Analytics consumer before a second-domain rollout.

| Measure | Definition | Proposed pilot target / evidence |
| --- | --- | --- |
| Qualification lead time | Median elapsed time from `review.submitted` to the last gate approval for qualified cases | Establish baseline in week 1, then aim for ≤ 5 working days. Audit timestamps support derivation. |
| First-pass quality | Share of submitted cycles completed without a return | ≥ 80% after two iterations. Audit history records return and resubmission. |
| Ownership adoption | Number of required departments with at least one weekly decision, divided by assigned departments | ≥ 80% in the pilot. Aggregate decision events by role. |
| Eligibility integrity | Published rows meeting current gate and incident policy | 100% for every load. Verified in service and contract tests. |
| Consumer availability | Observation snapshot age and scorecard coverage at the minimum bases | ≤ 35 days old. Monitor coverage weekly and investigate missing sources. |
| Exceptions | Pending identity records and approved records held for evidence | Owners review open items at each weekly triage. Both counts are visible in Data products. |

The targets are proposals. The application reports synthetic observations and coverage. Operational lead time, pilot adoption and commercial impact require a real rollout and a baseline.

## Roadmap

| Milestone | Outcome and release decision | Expected acceptance |
| --- | --- | --- |
| **1.0.0 · Governed qualification** | Ship supplier master, evidence, decisions, risk, sourcing and versioned reporting as one local increment | Run Aster Vale to publication, reconcile a candidate, suspend a supplier, and prove warehouse score parity. |
| **1.1 · Reviewer reliability** | Reduce missed handoffs and validate identity controls for a pilot | Review aging alerts with Operations. Complete SSO and scheduling spikes before committing the pilot. |
| **2.0 · Federated rollout** | Add an approved ERP source and Snowflake delivery path after access and policy reviews | Steward can replay/reconcile a bounded source batch. A second consumer accepts its migration contract. |

| Risk or debt | Current mitigation | Next validation |
| --- | --- | --- |
| Wrong legal merge | Exact registration required for linking, name candidate triage and stable identities | Evaluate legitimate duplicate registrations and a reversible merge process in a restricted pilot |
| Approval backlogs | Role-specific queue and visible outstanding gates | Measure aging and validate reviewer coverage before enabling reminders |
| Accidental eligibility drift | Runtime check against effective evidence, critical incidents and persisted approvals | Add scheduled consumer reconciliation and freshness ownership |
| Simulated decision rights | Loopback-only launch and synthetic data | Validate authenticated identities, access boundaries and secure evidence retention |
| Warehouse execution uncertainty | Match tested SQL models against local exports | Run delegated role, stage, load, rollback and monitoring in an isolated Snowflake account |
| SQLite write serialization | Local transactions enforce a single commit path and preserve audit consistency | Benchmark PostgreSQL concurrency if adoption requires multiple writers or service replicas |

Codex supported implementation and validation. A delivery team can use Copilot or Claude Code for reviewable test scaffolding or SQL alternatives with synthetic fixtures. Engineering owns verification, and the stakeholder named on the issue owns acceptance. The application has no runtime AI dependency.
