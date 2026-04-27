"""Marshmallow runtime validation schemas for API v1.

This module defines strict payload contracts for route inputs. Each schema encodes whether fields
are required, optional, nullable (`allow_none=True`), or have load defaults. In handoff terms,
this is the runtime contract guardrail that enforces "what shape is allowed" before route logic runs.
"""

from __future__ import annotations

from marshmallow import Schema, fields, EXCLUDE


class ChatPayloadSchema(Schema):
    class_id = fields.Int(required=False, allow_none=True)
    user_id = fields.Int(required=False, allow_none=True)
    title = fields.Str(required=False, allow_none=True)
    model = fields.Str(required=False, allow_none=True)
    active = fields.Bool(required=False, allow_none=True)
    started_at = fields.DateTime(required=False, allow_none=True)


class ClassPayloadSchema(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    instructor_id = fields.Int(required=True)
    active = fields.Bool(required=False, load_default=True)


class PartialClassPayloadSchema(Schema):
    name = fields.Str(required=False)
    description = fields.Str(required=False)
    instructor_id = fields.Int(required=False)
    active = fields.Bool(required=False)


class FeaturePayloadSchema(Schema):
    title = fields.Str(required=True)
    details = fields.Str(required=True)
    active = fields.Bool(required=False, load_default=True)
    displayable = fields.Bool(required=False, load_default=True)
    font_size_px = fields.Int(required=False, allow_none=True)
    font_family = fields.Str(required=False, allow_none=True)
    color_family = fields.Str(required=False, allow_none=True)


class PartialFeaturePayloadSchema(Schema):
    title = fields.Str(required=False)
    details = fields.Str(required=False)
    active = fields.Bool(required=False)
    displayable = fields.Bool(required=False)
    font_size_px = fields.Int(required=False, allow_none=True)
    font_family = fields.Str(required=False, allow_none=True)
    color_family = fields.Str(required=False, allow_none=True)


class MessagePayloadSchema(Schema):
    chat_id = fields.Int(required=False, allow_none=True)
    message_text = fields.Str(required=True)
    vote = fields.Str(required=False, allow_none=True)
    note = fields.Str(required=False, allow_none=True)
    help_intent = fields.Str(required=False, allow_none=True)


class PartialMessagePayloadSchema(Schema):
    message_text = fields.Str(required=False)
    vote = fields.Str(required=False, allow_none=True)
    note = fields.Str(required=False, allow_none=True)
    help_intent = fields.Str(required=False, allow_none=True)


class AIInteractionPayloadSchema(Schema):

    class Meta:
        unknown = EXCLUDE

    prompt = fields.Str(required=False, allow_none=True)
    system_prompt = fields.Str(required=False, allow_none=True)
    context = fields.Dict(required=False)
    conversation_id = fields.Str(required=False, allow_none=True)
    chat_id = fields.Int(required=False, allow_none=True)
    class_id = fields.Int(required=False, allow_none=True)
    user_id = fields.Raw(required=False, allow_none=True)
    messages = fields.List(fields.Dict(), required=False)
    provider = fields.Str(required=False, allow_none=True)
    model_id = fields.Str(required=False, allow_none=True)
    family_id = fields.Str(required=False, allow_none=True)
    provider_preference = fields.Str(required=False, allow_none=True)
    request_id = fields.Str(required=False, allow_none=True)
    accommodations_id_system_prompts_id = fields.Int(required=False, allow_none=True)
    selected_accommodations_id_system_prompts_ids = fields.List(
        fields.Int(), required=False
    )
    selected_accessibility_link_ids = fields.List(fields.Int(), required=False)
    use_user_feature_preferences = fields.Bool(required=False, load_default=False)


class AdminModelDownloadPayloadSchema(Schema):

    class Meta:
        unknown = EXCLUDE

    model_id = fields.Str(required=True)
