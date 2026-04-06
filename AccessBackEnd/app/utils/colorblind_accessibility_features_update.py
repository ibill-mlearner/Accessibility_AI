from __future__ import annotations

import json
from collections import defaultdict

from flask import Flask
from sqlalchemy import inspect

from ..extensions import db
from ..models import Accommodation

_COLORBLIND_FEATURE_SPECS_JSON = """
[
  {
    "title": "Color family: Protanopia-safe",
    "details": "standard; Use cyan/magenta-leaning contrasts and avoid red-dependent status indicators.",
    "active": true,
    "displayable": true,
    "color_family": "protanopia-safe"
  },
  {
    "title": "Color family: Deuteranopia-safe",
    "details": "standard; Use blue/orange emphasis with strong lightness contrast and avoid red/green-only status indicators.",
    "active": true,
    "displayable": true,
    "color_family": "deuteranopia-safe"
  },
  {
    "title": "Color family: Tritanopia-safe",
    "details": "standard; Use red/green contrasts with neutral backups and avoid blue/yellow-only distinctions.",
    "active": true,
    "displayable": true,
    "color_family": "tritanopia-safe"
  },
  {
    "title": "Color family: Achromatopsia-safe",
    "details": "standard; Use grayscale-friendly palettes with clear luminance contrast and non-color visual cues.",
    "active": true,
    "displayable": true,
    "color_family": "achromatopsia-safe"
  }
]
"""

_FONT_FAMILY_FEATURE_SPECS_JSON = """
[
  {
    "title": "Font family: OpenDyslexic",
    "details": "standard; Use OpenDyslexic-style typography to support dyslexia-friendly reading.",
    "active": true,
    "displayable": true,
    "font_family": "opendyslexic"
  },
  {
    "title": "Font family: Atkinson Hyperlegible",
    "details": "standard; Use Atkinson Hyperlegible to improve character distinction and readability.",
    "active": true,
    "displayable": true,
    "font_family": "atkinson"
  },
  {
    "title": "Font family: Arial",
    "details": "standard; Use Arial for a familiar sans-serif readability baseline.",
    "active": true,
    "displayable": true,
    "font_family": "arial"
  },
  {
    "title": "Font family: Verdana",
    "details": "standard; Use Verdana for wider letterforms and improved low-resolution legibility.",
    "active": true,
    "displayable": true,
    "font_family": "verdana"
  },
  {
    "title": "Font family: Monospace",
    "details": "standard; Use monospace for consistent character widths and code-friendly readability.",
    "active": true,
    "displayable": true,
    "font_family": "monospace"
  }
]
"""

_COLORBLIND_FEATURE_SPECS: tuple[dict[str, object], ...] = tuple(json.loads(_COLORBLIND_FEATURE_SPECS_JSON))
_FONT_FAMILY_FEATURE_SPECS: tuple[dict[str, object], ...] = tuple(json.loads(_FONT_FAMILY_FEATURE_SPECS_JSON))


def _sync_accommodation_specs(
    *,
    specs: tuple[dict[str, object], ...],
    key_field: str,
) -> bool:
    key_values = [str(item[key_field]) for item in specs]
    model_field = getattr(Accommodation, key_field)
    existing_rows = db.session.query(Accommodation).filter(model_field.in_(key_values)).all()
    existing_by_key: dict[str, list[Accommodation]] = defaultdict(list)
    existing_by_title = {row.title: row for row in existing_rows}
    for row in existing_rows:
        row_key = getattr(row, key_field)
        if row_key:
            existing_by_key[str(row_key)].append(row)

    has_changes = False
    for spec in specs:
        spec_key = str(spec[key_field])
        desired_title = str(spec["title"])
        matching_rows = existing_by_key.get(spec_key, [])
        row = next((candidate for candidate in matching_rows if candidate.title == desired_title), None)
        if row is None and matching_rows:
            row = matching_rows[0]
        if row is None:
            db.session.add(Accommodation(**spec))
            has_changes = True
            continue

        for field_name, desired_value in spec.items():
            if field_name == "title":
                conflicting_row = existing_by_title.get(str(desired_value))
                if conflicting_row is not None and conflicting_row.id != row.id:
                    continue
            if getattr(row, field_name) != desired_value:
                setattr(row, field_name, desired_value)
                if field_name == "title":
                    existing_by_title[str(desired_value)] = row
                has_changes = True

    return has_changes


def ensure_colorblind_accessibility_features(app: Flask) -> None:
    """Create/update baseline colorblind + font-family accommodation rows."""

    with app.app_context():
        if not inspect(db.engine).has_table("accommodations"):
            app.logger.info("Skipping accessibility feature family sync because accommodations table is not created yet.")
            return

        has_changes = False
        has_changes = _sync_accommodation_specs(specs=_COLORBLIND_FEATURE_SPECS, key_field="color_family") or has_changes
        has_changes = _sync_accommodation_specs(specs=_FONT_FAMILY_FEATURE_SPECS, key_field="font_family") or has_changes
        standardized_rows = (
            db.session.query(Accommodation)
            .filter(
                (Accommodation.color_family.isnot(None))
                | (Accommodation.font_family.isnot(None))
                | (Accommodation.font_size_px.isnot(None))
            )
            .all()
        )
        for row in standardized_rows:
            details = str(row.details or "").strip()
            if details.lower().startswith("standard;"):
                continue
            row.details = f"standard; {details}" if details else "standard;"
            has_changes = True

        if has_changes:
            db.session.commit()
            app.logger.info("Colorblind and font-family accessibility features synchronized.")
