# @api_v1_bp.get("/features")
# @login_required
# def list_features():
#     features = db.session.query(Accommodation).order_by(Accommodation.id.asc()).all()
#     return jsonify([_serialize_record("feature", feature) for feature in features]), 200
#
#
# @api_v1_bp.post("/features")
# @login_required
# def create_feature():
#     payload = _read_json_object()
#     feature = Accommodation(
#         title=str(payload.get("title") or "").strip(),
#         details=str(payload.get("details") or payload.get("description") or "").strip(),
#         active=bool(payload.get("active", payload.get("enabled", True))),
#     )
#     if not feature.title:
#         raise BadRequestError("title is required")
#     db.session.add(feature)
#     db.session.commit()
#     return jsonify(_serialize_record("feature", feature)), 201
#
#
# @api_v1_bp.get("/features/<int:feature_id>")
# @login_required
# def get_feature(feature_id: int):
#     feature = _require_record("feature", Accommodation, feature_id)
#     return jsonify(_serialize_record("feature", feature)), 200
#
#
# @api_v1_bp.put("/features/<int:feature_id>")
# @api_v1_bp.patch("/features/<int:feature_id>")
# @login_required
# def update_feature(feature_id: int):
#     feature = _require_record("feature", Accommodation, feature_id)
#     payload = _read_json_object()
#     _apply_feature_mutations(feature, payload)
#     db.session.commit()
#     return jsonify(_serialize_record("feature", feature)), 200
#
#
# @api_v1_bp.delete("/features/<int:feature_id>")
# @login_required
# def delete_feature(feature_id: int):
#     feature = _require_record("feature", Accommodation, feature_id)
#     response_payload = _serialize_record("feature", feature)
#     db.session.delete(feature)
#     db.session.commit()
#     return jsonify(response_payload), 200

# def _apply_feature_mutations(feature: Accommodation, payload: dict[str, Any]) -> None:
#     field_aliases = {"description": "details", "enabled": "active"}
#     for field in ("title", "details", "active", "description", "enabled"):
#         if field in payload:
#             setattr(feature, field_aliases.get(field, field), payload[field])
#
