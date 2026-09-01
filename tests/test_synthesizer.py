"""Regression coverage for MacroSynthesizer.falsify()."""

from unittest.mock import MagicMock

from agent.synthesizer import MacroSynthesizer


def _make_synthesizer_with_mock_client():
    synth = MacroSynthesizer.__new__(MacroSynthesizer)
    synth.client = MagicMock()
    synth.thesis_history = []
    return synth


def test_falsify_requests_enough_tokens_to_avoid_truncation():
    """A max_tokens too low silently truncates Claude's JSON mid-string,
    which json.loads() then fails to parse -- and the exception handler
    swallows that into the deterministic fallback with no visible error.
    This regression-locks the token budget so that bug can't quietly
    come back."""
    synth = _make_synthesizer_with_mock_client()
    block = MagicMock(type="text", text='{"confidence_adjustment": -0.05}')
    synth.client.messages.create.return_value = MagicMock(content=[block])

    synth.falsify(
        thesis={"thesis": "t", "confidence_overall": 0.6},
        market_state={"equity_vol": {"atm_iv": 0.2}},
        disagreement={"score": 80, "primary": {"id": "x"}},
    )

    _, kwargs = synth.client.messages.create.call_args
    assert kwargs["max_tokens"] >= 2000, (
        "falsify() max_tokens dropped back below a safe margin; a long, "
        "genuine Claude critique can get cut off mid-JSON and silently "
        "fall back to the deterministic default instead of erroring loudly."
    )


def test_falsify_falls_back_cleanly_on_unparseable_response():
    synth = _make_synthesizer_with_mock_client()
    block = MagicMock(type="text", text='{"confidence_adjustment": -0.05')  # truncated, invalid JSON
    synth.client.messages.create.return_value = MagicMock(content=[block])

    result = synth.falsify(
        thesis={"thesis": "t", "confidence_overall": 0.6},
        market_state={},
        disagreement={"score": 80, "primary": {"id": "x"}},
    )

    assert result["source"] == "deterministic-fallback"
    assert "Claude review unavailable" in result["note"]
