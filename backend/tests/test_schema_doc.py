"""SCHEMA.md must describe every model and field (every schema change updates it)."""

import re
from pathlib import Path

import pytest
from django.apps import apps

DOC = (Path(__file__).resolve().parent.parent / "SCHEMA.md").read_text()
OUR_APPS = ("accounts", "centres", "counsellors", "queue", "messaging")


def _section(model_name):
    match = re.search(rf"^### {model_name} \(`[^`]+`\)\n(.*?)(?=^### |^## )", DOC, flags=re.M | re.S)
    return match.group(1) if match else None


@pytest.mark.parametrize(
    "model", [m for m in apps.get_models() if m._meta.app_label in OUR_APPS], ids=lambda m: m.__name__
)
def test_schema_doc_covers_model_fields(model):
    section = _section(model.__name__)
    assert section is not None, f"SCHEMA.md has no section for {model.__name__}"
    missing = [f.name for f in model._meta.concrete_fields if f"| `{f.name}` |" not in section]
    assert not missing, f"SCHEMA.md {model.__name__} is missing fields {missing}"
    for constraint in model._meta.constraints:
        assert f"`{constraint.name}`" in section, constraint.name
