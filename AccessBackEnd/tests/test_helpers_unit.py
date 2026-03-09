from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from ..app.api.errors import BadRequestError
from ..app.helpers.auth_helpers import AuthHelpers
from ..app.helpers.route_helpers import (
    _deserialize_payload,
    _parse_int_field,
    _parse_optional_datetime,
    _parse_required_date,
    _serialize_record,
)


def test_normalize_auth_email_trims_and_lowercases():
    assert AuthHelpers._normalize_auth_email("  STUDENT@Example.com  ") == "student@example.com"
    assert AuthHelpers._normalize_auth_email(None) == ""


def test_resolve_session_timetolive_honors_timedelta(app):
    with app.app_context():
        app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=5)
        assert AuthHelpers._resolve_session_timetolive() == timedelta(minutes=5)


def test_resolve_session_timetolive_converts_numeric_minutes(app):
    with app.app_context():
        app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 7
        assert AuthHelpers._resolve_session_timetolive() == timedelta(minutes=7)


def test_resolve_session_timetolive_uses_default_when_not_configured(app):
    with app.app_context():
        app.config["JWT_ACCESS_TOKEN_EXPIRES"] = "unexpected"
        assert AuthHelpers._resolve_session_timetolive() == timedelta(minutes=30)


def test_resolved_allowed_actions_for_known_and_unknown_roles():
    assert AuthHelpers._resolved_allowed_actions("admin") == [
        "users:read",
        "users:write",
        "classes:read",
        "classes:write",
        "classes:delete",
    ]
    assert AuthHelpers._resolved_allowed_actions("instructor") == [
        "classes:read",
        "classes:write",
        "students:read",
    ]
    assert AuthHelpers._resolved_allowed_actions("student") == [
        "classes:read",
        "profile:read",
        "profile:write",
    ]
    assert AuthHelpers._resolved_allowed_actions("unknown") == ["profile:read"]


def test_as_utc_normalizes_naive_and_aware_values():
    naive = datetime(2026, 1, 1, 12, 30, 0)
    aware = datetime(2026, 1, 1, 12, 30, 0, tzinfo=UTC)

    assert AuthHelpers._as_utc(None) is None
    assert AuthHelpers._as_utc(naive).tzinfo == UTC
    assert AuthHelpers._as_utc(aware) == aware


def test_deserialize_payload_maps_api_fields_to_model_fields():
    payload = {"class": 4, "user": 9, "title": "chat title"}

    assert _deserialize_payload("chat", payload) == {
        "class_id": 4,
        "user_id": 9,
        "title": "chat title",
    }


def test_parse_optional_datetime_accepts_iso_and_datetime_objects():
    parsed = _parse_optional_datetime("2026-02-02T10:15:00Z")
    assert parsed == datetime(2026, 2, 2, 10, 15, tzinfo=UTC)

    already_datetime = datetime(2026, 2, 2, 10, 15, tzinfo=UTC)
    assert _parse_optional_datetime(already_datetime) == already_datetime
    assert _parse_optional_datetime("") is None


def test_parse_optional_datetime_rejects_non_iso_values():
    with pytest.raises(BadRequestError, match="started_at must be an ISO-8601 datetime"):
        _parse_optional_datetime("not-a-datetime")


def test_parse_required_date_supports_date_and_iso_string():
    assert _parse_required_date("2026-03-05", field_name="deadline") == date(2026, 3, 5)
    assert _parse_required_date(date(2026, 3, 6), field_name="deadline") == date(2026, 3, 6)


def test_parse_required_date_raises_for_invalid_values():
    with pytest.raises(BadRequestError, match="deadline must be YYYY-MM-DD"):
        _parse_required_date("03-05-2026", field_name="deadline")


def test_parse_int_field_handles_required_optional_and_invalid_values():
    assert _parse_int_field(" 42 ", field_name="class_id") == 42
    assert _parse_int_field(None, field_name="class_id") is None

    with pytest.raises(BadRequestError, match="class_id is required"):
        _parse_int_field("", field_name="class_id", required=True)

    with pytest.raises(BadRequestError, match="class_id must be an integer"):
        _parse_int_field("abc", field_name="class_id")


def test_serialize_record_for_note_resource_includes_alias_fields():
    record = SimpleNamespace(
        id=11,
        class_id=4,
        chat_id=8,
        noted_on=date(2026, 1, 15),
        content="Reminder",
    )

    assert _serialize_record("note", record) == {
        "id": 11,
        "class": 4,
        "class_id": 4,
        "chat": 8,
        "chat_id": 8,
        "date": "2026-01-15",
        "noted_on": "2026-01-15",
        "content": "Reminder",
    }