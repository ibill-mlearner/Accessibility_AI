from flask import jsonify
from flask_login import login_required

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
from ...models import Accommodation
from ...utils.api_checker import _apply_feature_mutations


@api_v1_bp.get("/features")
@login_required
def list_features():
    features = db.session.query(Accommodation).order_by(Accommodation.id.asc()).all()
    return jsonify([_serialize_record("feature", feature) for feature in features]), 200


@api_v1_bp.post("/features")
@login_required
def create_feature():
    payload = _validate_payload(_read_json_object(), FeaturePayloadSchema())
    feature = Accommodation(
        title=payload['title'],
        details=payload['details'],
        active=payload['active'],
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

