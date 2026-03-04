"""Marshmallow schemas for API request validation and normalization."""

from __future__ import annotations

from typing import Any

from marshmallow import EXCLUDE, Schema, fields, pre_load, validate


class BaseAPISchema(Schema):
    """Base schema that ignores unknown fields for backward-compatible payloads."""

    class Meta:
        unknown = EXCLUDE


class ChatPayloadSchema(BaseAPISchema):
    class_id = fields.Integer(required=False, allow_none=True)
    user_id = fields.Integer(required=False, allow_none=True)
    title = fields.String(required=False, validate=validate.Length(min=1))
    model = fields.String(required=False, validate=validate.Length(min=1))
    started_at = fields.DateTime(required=False, allow_none=True)

    @pre_load
    def normalize_strings(
        self, 
        data: dict[str, Any], 
        **_: Any
    ) -> dict[str, Any]:
        payload = dict(data)
        for field in ("title", "model"):
            if field in payload and payload[field] is not None:
                payload[field] = str(payload[field]).strip()
        return payload


class MessagePayloadSchema(BaseAPISchema):
    chat_id = fields.Integer(required=False, allow_none=True)
    message_text = fields.String(required=True, validate=validate.Length(min=1))
    vote = fields.String(required=False, load_default="good", validate=validate.OneOf(["good", "bad"]))
    note = fields.String(required=False, load_default="no", validate=validate.OneOf(["yes", "no"]))
    help_intent = fields.String(required=True, validate=validate.Length(min=1))

    @pre_load
    def normalize_strings(
        self, 
        data: dict[str, Any], 
        **_: Any
    ) -> dict[str, Any]:
        payload = dict(data)

        #variable with litteral string for linting
        accom_ids = "selected_accommodations_id_system_prompts_ids"
        access_ids = "accommodations_id_system_prompts_id"
        if (accom_ids not in payload and access_ids in payload):
            payload[accom_ids] = payload[access_ids]

        for field in ("message_text", "help_intent", "vote", "note"):
            if field in payload and payload[field] is not None:
                payload[field] = str(payload[field]).strip()
        return payload


class PartialMessagePayloadSchema(MessagePayloadSchema):
    message_text = fields.String(required=False, validate=validate.Length(min=1))
    help_intent = fields.String(required=False, validate=validate.Length(min=1))


class ClassPayloadSchema(BaseAPISchema):
    name = fields.String(required=True, validate=validate.Length(min=1))
    description = fields.String(required=True, validate=validate.Length(min=1))
    instructor_id = fields.Integer(required=True)
    active = fields.Boolean(required=False, load_default=True)

    @pre_load
    def normalize_strings(
        self, 
        data: dict[str, Any], 
        **_: Any
    ) -> dict[str, Any]:
        payload = dict(data)
        for field in ("name", "description"):
            if field in payload and payload[field] is not None:
                payload[field] = str(payload[field]).strip()
        return payload


class PartialClassPayloadSchema(BaseAPISchema):
    name = fields.String(required=False, validate=validate.Length(min=1))
    description = fields.String(required=False, validate=validate.Length(min=1))
    instructor_id = fields.Integer(required=False)
    active = fields.Boolean(required=False)

    @pre_load
    def normalize_strings(
        self, 
        data: dict[str, Any], 
        **_: Any
    ) -> dict[str, Any]:
        payload = dict(data)
        for field in ("name", "description"):
            if field in payload and payload[field] is not None:
                payload[field] = str(payload[field]).strip()
        return payload


class FeaturePayloadSchema(BaseAPISchema):
    title = fields.String(required=True, validate=validate.Length(min=1))
    details = fields.String(required=False, allow_none=True, load_default="")
    active = fields.Boolean(required=False, load_default=True)

    @pre_load
    def normalize_feature_aliases(
        self, 
        data: dict[str, Any], 
        **_: Any
    ) -> dict[str, Any]:
        payload = dict(data)
        if "details" not in payload and "description" in payload:
            payload["details"] = payload["description"]
        if "active" not in payload and "enabled" in payload:
            payload["active"] = payload["enabled"]

        for field in ("title", "details"):
            if field in payload and payload[field] is not None:
                payload[field] = str(payload[field]).strip()
        return payload


class PartialFeaturePayloadSchema(BaseAPISchema):
    title = fields.String(required=False, validate=validate.Length(min=1))
    details = fields.String(required=False, allow_none=True)
    active = fields.Boolean(required=False)

    @pre_load
    def normalize_feature_aliases(
        self, 
        data: dict[str, Any], 
        **_: Any
    ) -> dict[str, Any]:
        payload = dict(data)
        if "details" not in payload and "description" in payload:
            payload["details"] = payload["description"]
        if "active" not in payload and "enabled" in payload:
            payload["active"] = payload["enabled"]

        for field in ("title", "details"):
            if field in payload and payload[field] is not None:
                payload[field] = str(payload[field]).strip()
        return payload

class AIInteractionPayloadSchema(BaseAPISchema):
    prompt = fields.String(required=False, allow_none=True)
    system_prompt = fields.String(required=False, allow_none=True)
    context = fields.Dict(keys=fields.String(), values=fields.Raw(), required=False, load_default=dict)
    rag = fields.Dict(keys=fields.String(), values=fields.Raw(), required=False, allow_none=True)
    conversation_id = fields.String(required=False, allow_none=True)
    chat_id = fields.Integer(required=False, allow_none=True)
    class_id = fields.Integer(required=False, allow_none=True)
    user_id = fields.Raw(required=False, allow_none=True)
    request_id = fields.String(required=False, allow_none=True)
    accommodations_id_system_prompts_id = fields.Integer(required=False, allow_none=True)
    selected_accommodations_id_system_prompts_ids = fields.List(fields.Integer(), required=False)
    messages = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()), required=False, load_default=list)

    @pre_load
    def normalize_strings(
        self, 
        data: dict[str, Any], 
        **_: Any
    ) -> dict[str, Any]:
        payload = dict(data)
        for field in ("prompt", "system_prompt", "conversation_id", "request_id"):
            if field in payload and payload[field] is not None:
                payload[field] = str(payload[field]).strip()
        return payload