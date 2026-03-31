from flask import jsonify
from flask_login import current_user, login_required

from .routes import (
    BadRequestError,
    _read_json_object,
    _require_record,
    _serialize_record,
    _validate_payload,
    api_v1_bp,
    db,
)
from ...schemas.validation import FeaturePayloadSchema, PartialFeaturePayloadSchema
from ...models import Accommodation, UserAccessibilityFeature
from ...utils.api_checker import _apply_feature_mutations


def _load_user_preference_map(user_id: int) -> dict[int, bool]:
    rows = (
        db.session.query(UserAccessibilityFeature)
        .filter(UserAccessibilityFeature.user_id == int(user_id))
        .all()
    )
    return {int(row.accommodation_id): bool(row.enabled) for row in rows}


def _serialize_feature_with_preference(feature: Accommodation, preference_map: dict[int, bool]) -> dict:
    payload = _serialize_record("feature", feature)
    payload["enabled"] = bool(preference_map.get(int(feature.id), False))
    payload["active"] = bool(payload.get("active", True))
    return payload


@api_v1_bp.get("/features")
@login_required
def list_features():
    features = db.session.query(Accommodation).order_by(Accommodation.id.asc()).all()
    preference_map = _load_user_preference_map(int(current_user.id))
    return jsonify([_serialize_feature_with_preference(feature, preference_map) for feature in features]), 200


@api_v1_bp.post("/features")
@login_required
def create_feature():
    payload = _validate_payload(_read_json_object(), FeaturePayloadSchema())
    feature = Accommodation(
        title=payload['title'],
        details=payload['details'],
        active=payload['active'],
        displayable=payload["displayable"],
    )
    if not feature.title:
        raise BadRequestError("title is required")
    db.session.add(feature)
    db.session.commit()
    return jsonify(_serialize_record("feature", feature)), 201


@api_v1_bp.get("/features/<int:feature_id>")
@login_required
def get_feature(feature_id: int):
    feature = _require_record("feature", Accommodation, feature_id)
    return jsonify(_serialize_record("feature", feature)), 200


@api_v1_bp.put("/features/<int:feature_id>")
@api_v1_bp.patch("/features/<int:feature_id>")
@login_required
def update_feature(feature_id: int):
    feature = _require_record("feature", Accommodation, feature_id)
    payload = _validate_payload(_read_json_object(), PartialFeaturePayloadSchema())
    _apply_feature_mutations(feature, payload)
    db.session.commit()
    return jsonify(_serialize_record("feature", feature)), 200


@api_v1_bp.delete("/features/<int:feature_id>")
@login_required
def delete_feature(feature_id: int):
    feature = _require_record("feature", Accommodation, feature_id)
    response_payload = _serialize_record("feature", feature)
    db.session.delete(feature)
    db.session.commit()
    return jsonify(response_payload), 200


@api_v1_bp.get('/features/preferences')
@login_required
def list_current_user_feature_preferences():
    preference_map = _load_user_preference_map(int(current_user.id))
    features = db.session.query(Accommodation).order_by(Accommodation.id.asc()).all()
    payload = [
        {
            "accommodation_id": int(feature.id),
            "enabled": bool(preference_map.get(int(feature.id), False)),
        }
        for feature in features
    ]
    return jsonify(payload), 200


@api_v1_bp.patch('/features/preferences/<int:feature_id>')
@login_required
def update_current_user_feature_preference(feature_id: int):
    _require_record("feature", Accommodation, feature_id)
    payload = _read_json_object()
    if "enabled" not in payload:
        raise BadRequestError("enabled is required")

    enabled = bool(payload.get("enabled"))
    user_id = int(current_user.id)
    preference = (
        db.session.query(UserAccessibilityFeature)
        .filter(
            UserAccessibilityFeature.user_id == user_id,
            UserAccessibilityFeature.accommodation_id == int(feature_id),
        )
        .one_or_none()
    )
    if preference is None:
        preference = UserAccessibilityFeature(
            user_id=user_id,
            accommodation_id=int(feature_id),
            enabled=enabled,
        )
        db.session.add(preference)
    else:
        preference.enabled = enabled

    db.session.commit()
    return jsonify({"accommodation_id": int(feature_id), "enabled": enabled}), 200


@api_v1_bp.put('/features/preferences')
@login_required
def replace_current_user_feature_preferences():
    payload = _read_json_object()
    preferences = payload.get("preferences")
    if not isinstance(preferences, list):
        raise BadRequestError("preferences must be a list")

    user_id = int(current_user.id)
    desired_map: dict[int, bool] = {}
    for item in preferences:
        if not isinstance(item, dict):
            continue
        feature_id = item.get("accommodation_id")
        try:
            normalized_id = int(feature_id)
        except (TypeError, ValueError):
            continue
        _require_record("feature", Accommodation, normalized_id)
        desired_map[normalized_id] = bool(item.get("enabled"))

    existing = (
        db.session.query(UserAccessibilityFeature)
        .filter(UserAccessibilityFeature.user_id == user_id)
        .all()
    )
    existing_map = {int(row.accommodation_id): row for row in existing}

    for feature_id, enabled in desired_map.items():
        row = existing_map.get(feature_id)
        if row is None:
            db.session.add(
                UserAccessibilityFeature(
                    user_id=user_id,
                    accommodation_id=feature_id,
                    enabled=enabled,
                )
            )
        else:
            row.enabled = enabled

    db.session.commit()
    return jsonify([
        {"accommodation_id": feature_id, "enabled": enabled}
        for feature_id, enabled in sorted(desired_map.items())
    ]), 200
