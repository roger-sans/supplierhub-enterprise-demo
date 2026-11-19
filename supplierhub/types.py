from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Country = Literal["BE", "DE", "ES", "FI", "FR", "GB", "IE", "NL", "PL", "PT", "SE"]
Currency = Literal["EUR", "GBP", "SEK"]
Category = Literal["Components", "Materials", "Packaging", "Industrial services", "Freight"]
Risk = Literal["low", "medium", "high"]
Segment = Literal["standard", "preferred", "strategic"]
Kind = Literal["supplier_profile", "financial_review", "capacity_check", "quality_certificate", "legal_clearance"]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=360)]
Registration = Annotated[str, StringConstraints(pattern=r"^DEMO-[A-Z0-9]{4,12}$")]
EvidenceRef = Annotated[str, StringConstraints(pattern=r"^DEMO-[A-Z0-9-]{4,28}$")]


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SupplierFields(StrictPayload):
    name: Title
    country: Country
    registration: Registration
    category: Category
    segment: Segment
    risk: Risk
    payment_days: int = Field(ge=0, le=180)
    currency: Currency


class Versioned(StrictPayload):
    revision: int = Field(ge=1)


class EditSupplier(SupplierFields, Versioned):
    reason: Reason


class Explanation(Versioned):
    reason: Reason


class Decision(Explanation):
    decision: Literal["approve", "return"]


class EvidenceInput(Versioned):
    kind: Kind
    title: Title
    ref: EvidenceRef
    valid_until: date


class IncidentInput(Versioned):
    title: Title
    kind: Literal["delivery", "quality", "financial", "compliance"]
    severity: Literal["minor", "major", "critical"]
    due_on: date


class AgreementInput(Versioned):
    title: Title
    ref: EvidenceRef
    starts_on: date
    ends_on: date
    annual_value: int = Field(gt=0, le=1_000_000_000)
    currency: Currency

    @model_validator(mode="after")
    def validate_window(self):
        if self.starts_on > self.ends_on:
            raise ValueError("Agreement end must be on or after its start.")
        return self


class AgreementDecision(Explanation):
    state: Literal["effective", "retired"]


class InitiativeInput(StrictPayload):
    supplier_id: str = Field(pattern=r"^SUP-[A-Z0-9]{3,12}$")
    title: Title
    item_family: Title
    target_on: date


class InitiativeMove(Explanation):
    stage: Literal["qualification", "commercial", "awarded", "closed"]


class SourceRecord(StrictPayload):
    external_key: Annotated[str, StringConstraints(pattern=r"^DEMO-[A-Z0-9-]{4,24}$")]
    name: Title
    country: Country
    registration: Registration
    category: Category


class SourceEnvelope(StrictPayload):
    version: Literal["1.0"]
    source: Literal["DEMO-ERP", "DEMO-CATALOG"]
    data_class: Literal["synthetic"]
    extracted_at: datetime
    records: list[SourceRecord] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_envelope(self):
        if self.extracted_at.utcoffset() is None:
            raise ValueError("Extraction time requires a timezone.")
        keys = {row.external_key for row in self.records}
        if len(keys) != len(self.records):
            raise ValueError("External keys must be unique within a batch.")
        return self


class ResolveIdentity(StrictPayload):
    action: Literal["link", "create", "dismiss"]
    supplier_id: str | None = Field(default=None, pattern=r"^SUP-[A-Z0-9]{3,12}$")
    reason: Reason

    @model_validator(mode="after")
    def validate_target(self):
        if (self.action == "link") != (self.supplier_id is not None):
            raise ValueError("Only linking requires a target supplier.")
        return self


class ProductRecord(StrictPayload):
    supplier_id: str = Field(pattern=r"^SUP-[A-Z0-9]{3,12}$")
    name: Title
    country: Country
    category: Category
    segment: Segment
    risk: Risk
    payment_days: int = Field(ge=0, le=180)
    currency: Currency


class ProductEnvelope(StrictPayload):
    version: Literal["1.0"]
    product: Literal["qualified-suppliers"]
    data_class: Literal["synthetic"]
    as_of: date
    records: list[ProductRecord]
