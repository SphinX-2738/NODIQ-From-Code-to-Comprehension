from app.evaluation.harness import EvalQuestion, evaluate_retrieval, EvalReport


def make_mock_retrieval(fixed_results: list[dict]):
    """
    Create a fake retrieval function that always returns fixed results.
    This lets us test the evaluation logic without needing ChromaDB or Gemini.
    """
    def retrieval_fn(question: str, n_results: int = 5):
        return fixed_results
    return retrieval_fn


def test_perfect_retrieval():
    """When retrieval returns exactly the expected IDs, precision and recall are 1.0."""
    questions = [
        EvalQuestion(
            question="how does login work?",
            expected_ids=["myapp.auth.login"],
        )
    ]
    retrieval_fn = make_mock_retrieval([{"id": "myapp.auth.login"}])
    report = evaluate_retrieval(questions, retrieval_fn)

    assert report.results[0].precision == 1.0
    assert report.results[0].recall == 1.0
    assert report.results[0].found is True
    assert report.hit_rate == 1.0


def test_missed_retrieval():
    """When retrieval returns nothing relevant, precision and recall are 0."""
    questions = [
        EvalQuestion(
            question="how does login work?",
            expected_ids=["myapp.auth.login"],
        )
    ]
    retrieval_fn = make_mock_retrieval([{"id": "myapp.utils.helper"}])
    report = evaluate_retrieval(questions, retrieval_fn)

    assert report.results[0].precision == 0.0
    assert report.results[0].recall == 0.0
    assert report.results[0].found is False
    assert report.hit_rate == 0.0


def test_partial_retrieval():
    """When only some expected IDs are found, scores are between 0 and 1."""
    questions = [
        EvalQuestion(
            question="authentication functions",
            expected_ids=["myapp.auth.login", "myapp.auth.logout"],
        )
    ]
    retrieval_fn = make_mock_retrieval([
        {"id": "myapp.auth.login"},
        {"id": "myapp.utils.helper"},
    ])
    report = evaluate_retrieval(questions, retrieval_fn)

    assert report.results[0].recall == 0.5
    assert report.results[0].found is True


def test_average_metrics_across_questions():
    """Average precision and recall should be calculated across all questions."""
    questions = [
        EvalQuestion(question="q1", expected_ids=["id1"]),
        EvalQuestion(question="q2", expected_ids=["id2"]),
    ]
    retrieval_fn = make_mock_retrieval([{"id": "id1"}])
    report = evaluate_retrieval(questions, retrieval_fn)

    assert report.hit_rate == 0.5
    assert report.average_recall == 0.5


def test_empty_report():
    """An empty report should return 0 for all metrics, not crash."""
    report = EvalReport()
    assert report.average_precision == 0.0
    assert report.average_recall == 0.0
    assert report.hit_rate == 0.0