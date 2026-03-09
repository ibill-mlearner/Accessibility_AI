from AccessBackEnd.app.helpers.ai_checker import AIInteractionEnvelope, AIInteractionMonolith


def test_monolith_normalize_and_check_compact_payload():
    monolith = AIInteractionMonolith()
    envelope = monolith.normalize(
        {
            "prompt": "Summarize this",
            "answer": "Done",
            "provider": "OpenAI",
            "model_id": "gpt-4o-mini",
            "confidence": 0.8,
            "notes": ["ok"],
            "meta": {"request_id": "abc"},
        }
    )

    assert isinstance(envelope, AIInteractionEnvelope)
    assert envelope.assistant_text == "Done"
    assert monolith.check(envelope)["assistant_has_text"] is True


def test_monolith_validate_and_mutate():
    monolith = AIInteractionMonolith()
    envelope = AIInteractionEnvelope(prompt="hello")

    monolith.validate(envelope)
    updated = monolith.mutate(envelope, {"assistant_text": "world", "meta": {"x": 1}})

    assert updated.assistant_text == "world"
    assert updated.meta["x"] == 1