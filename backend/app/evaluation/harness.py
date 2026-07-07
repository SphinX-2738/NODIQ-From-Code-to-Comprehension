from dataclasses import dataclass, field


@dataclass
class EvalQuestion:
    """
    A single evaluation question with its expected answer.

    question: what a user might ask
    expected_ids: the OKF record IDs we expect to appear in retrieval results
    notes: optional explanation of why these are the correct answers
    """
    question: str
    expected_ids: list[str]
    notes: str = ""


@dataclass
class RetrievalResult:
    """Result of evaluating one question against the retrieval system."""
    question: str
    expected_ids: list[str]
    retrieved_ids: list[str]
    precision: float
    recall: float
    found: bool  # True if at least one expected ID was retrieved


@dataclass
class EvalReport:
    """Full evaluation report across all questions."""
    results: list[RetrievalResult] = field(default_factory=list)

    @property
    def average_precision(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.precision for r in self.results) / len(self.results)

    @property
    def average_recall(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.recall for r in self.results) / len(self.results)

    @property
    def hit_rate(self) -> float:
        """Percentage of questions where at least one correct answer was found."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.found) / len(self.results)

    def print_report(self) -> None:
        print("\n" + "=" * 60)
        print("NODIQ EVALUATION REPORT")
        print("=" * 60)
        for r in self.results:
            status = "✓" if r.found else "✗"
            print(f"\n{status} {r.question}")
            print(f"  Expected : {r.expected_ids}")
            print(f"  Retrieved: {r.retrieved_ids}")
            print(f"  Precision: {r.precision:.2f} | Recall: {r.recall:.2f}")
        print("\n" + "-" * 60)
        print(f"Average Precision : {self.average_precision:.2f}")
        print(f"Average Recall    : {self.average_recall:.2f}")
        print(f"Hit Rate          : {self.hit_rate:.2%}")
        print("=" * 60 + "\n")


def evaluate_retrieval(
    questions: list[EvalQuestion],
    retrieval_fn,
    n_results: int = 5,
) -> EvalReport:
    """
    Run evaluation against a list of questions.

    retrieval_fn: a callable that takes a question string and returns
                  a list of dicts with an 'id' key — exactly what
                  query_collection() returns from our pipeline.

    This function doesn't care how retrieval works internally —
    it just calls retrieval_fn and checks whether the right IDs
    came back. This makes it reusable across different retrieval
    strategies (vector-only, graph-only, hybrid).
    """
    report = EvalReport()

    for eval_q in questions:
        results = retrieval_fn(eval_q.question, n_results)
        retrieved_ids = [r["id"] for r in results]

        expected_set = set(eval_q.expected_ids)
        retrieved_set = set(retrieved_ids)

        hits = expected_set & retrieved_set

        precision = len(hits) / len(retrieved_set) if retrieved_set else 0.0
        recall = len(hits) / len(expected_set) if expected_set else 0.0
        found = len(hits) > 0

        report.results.append(RetrievalResult(
            question=eval_q.question,
            expected_ids=eval_q.expected_ids,
            retrieved_ids=retrieved_ids,
            precision=precision,
            recall=recall,
            found=found,
        ))

    return report