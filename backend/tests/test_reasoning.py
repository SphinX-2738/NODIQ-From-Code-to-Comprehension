from unittest.mock import MagicMock, patch
from app.reasoning.graph import (
    check_confidence,
    clarify_query,
    synthesize_answer,
    ReasoningState,
    CONFIDENCE_THRESHOLD,
)


def make_state(**kwargs) -> ReasoningState:
    """Helper to create a ReasoningState with sensible defaults."""
    defaults = {
        "question": "how does login work?",
        "retrieved_context": [],
        "confidence": 0.0,
        "answer": "",
        "cited_ids": [],
        "needs_clarification": False,
        "retry_count": 0,
    }
    defaults.update(kwargs)
    return defaults


def test_check_confidence_high_score_goes_to_synthesize():
    """High confidence should route directly to synthesize_answer."""
    state = make_state(confidence=0.9)
    assert check_confidence(state) == "synthesize_answer"


def test_check_confidence_low_score_goes_to_clarify():
    """Low confidence on first attempt should route to clarify_query."""
    state = make_state(confidence=0.1, retry_count=0)
    assert check_confidence(state) == "clarify_query"


def test_check_confidence_low_score_after_retry_goes_to_synthesize():
    """After one retry, even low confidence should go to synthesize_answer."""
    state = make_state(confidence=0.1, retry_count=1)
    assert check_confidence(state) == "synthesize_answer"


def test_check_confidence_exactly_at_threshold():
    """Score exactly at threshold should go to synthesize_answer."""
    state = make_state(confidence=CONFIDENCE_THRESHOLD)
    assert check_confidence(state) == "synthesize_answer"


def test_clarify_query_rephrases_question():
    """clarify_query should update the question and increment retry_count."""
    state = make_state(question="login stuff", retry_count=0)

    mock_response = MagicMock()
    mock_response.content = "How is user authentication implemented in Python?"

    with patch("app.reasoning.graph.llm") as mock_llm:
        mock_llm.invoke.return_value = mock_response
        updated = clarify_query(state)

    assert updated["question"] == "How is user authentication implemented in Python?"
    assert updated["retry_count"] == 1
    assert updated["needs_clarification"] is True


def test_synthesize_answer_with_no_context():
    """When there's no retrieved context, answer should say so clearly."""
    state = make_state(retrieved_context=[])
    updated = synthesize_answer(state)
    assert "could not find" in updated["answer"].lower()
    assert updated["cited_ids"] == []


def test_synthesize_answer_calls_llm():
    """When context exists, synthesize_answer should call the LLM."""
    state = make_state(
        retrieved_context=[{
            "id": "myapp.auth.login",
            "document": "function: login\nfile: auth.py",
            "score": 0.9,
        }]
    )

    mock_response = MagicMock()
    mock_response.content = "The login function [myapp.auth.login] handles authentication."

    with patch("app.reasoning.graph.llm") as mock_llm:
        mock_llm.invoke.return_value = mock_response
        updated = synthesize_answer(state)

    assert "login" in updated["answer"].lower()
    assert "myapp.auth.login" in updated["cited_ids"]