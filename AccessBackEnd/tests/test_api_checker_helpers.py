from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from marshmallow import Schema, fields

from AccessBackEnd.app.api.errors import BadRequestError
from AccessBackEnd.app.utils.api_checker import ApiMonolithHelper


class _ChatSchema(Schema):
    class_id = fields.Integer(required=True)
    title = fields.String(required=True)


def test_monolith_deserialize_maps_aliases():
    payload = {"class": 5, "user": 2, "title": "hello"}
    assert ApiMonolithHelper.deserialize("chat", payload) == {
        "class_id": 5,
        "user_id": 2,
        "title": "hello",
    }


def test_monolith_validate_raises_bad_request_for_schema_errors():
    with pytest.raises(BadRequestError, match="request validation failed"):
        ApiMonolithHelper.validate({"title": "missing class"}, _ChatSchema())


def test_monolith_datetime_int_and_date_parsers_cover_valid_and_invalid_inputs():
    assert ApiMonolithHelper.parse_optional_datetime("2026-02-02T10:15:00Z") == datetime(2026, 2, 2, 10, 15, tzinfo=UTC)
    assert ApiMonolithHelper.parse_int(" 7 ", "class_id") == 7
    assert ApiMonolithHelper.parse_required_date("2026-05-01", "deadline") == date(2026, 5, 1)

    with pytest.raises(BadRequestError, match="started_at must be an ISO-8601 datetime"):
        ApiMonolithHelper.parse_optional_datetime("nope")
    with pytest.raises(BadRequestError, match="deadline must be YYYY-MM-DD"):
        ApiMonolithHelper.parse_required_date("05/01/2026", "deadline")
    with pytest.raises(BadRequestError, match="class_id must be an integer"):
        ApiMonolithHelper.parse_int("x", "class_id")


def test_monolith_serialize_and_apply_updates():
    record = SimpleNamespace(
        id=11,
        class_id=4,
        user_id=3,
        title="Old",
        model="model-x",
        started_at=datetime(2026, 3, 2, 8, 0, tzinfo=UTC),
        content="note",
        chat_id=9,
        noted_on=date(2026, 3, 2),
    )

    serialized = ApiMonolithHelper.serialize("chat", record)
    assert serialized["class_id"] == 4
    assert serialized["start"] == "2026-03-02T08:00:00+00:00"

    changed = ApiMonolithHelper.apply_updates(record, {"title": "New", "model": "model-y"}, {"title", "model"})
    assert set(changed) == {"title", "model"}
    assert record.title == "New"
    assert record.model == "model-y"