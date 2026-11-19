"""Regenerate JSON Schema files from the API request and response models."""
import json
from pathlib import Path

from supplierhub.types import ProductEnvelope, SourceEnvelope

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {"supplier-source": SourceEnvelope, "qualified-suppliers": ProductEnvelope}


def schema(name, model):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:supplierhub:contracts:{name}:1.0",
        **model.model_json_schema(),
    }


if __name__ == "__main__":
    for name, model in CONTRACTS.items():
        (ROOT / "contracts" / f"{name}.v1.schema.json").write_text(json.dumps(schema(name, model), indent=2) + "\n")
