from app.evaluation.harness import EvalQuestion

# These are questions we'd expect a Nodiq user to ask,
# paired with the exact OKF IDs we expect retrieval to surface.
# We'll expand this as the project grows.
SAMPLE_QUESTIONS = [
    EvalQuestion(
        question="how does user authentication work?",
        expected_ids=["myapp.auth.UserAuth.login"],
        notes="Login method is the entry point for authentication",
    ),
    EvalQuestion(
        question="what validates a user password?",
        expected_ids=["myapp.auth.validate_password"],
        notes="validate_password is the direct password checking function",
    ),
    EvalQuestion(
        question="show me the calculator class",
        expected_ids=["myapp.calc.Calculator"],
        notes="Direct class lookup by name",
    ),
    EvalQuestion(
        question="how do I multiply two numbers?",
        expected_ids=["myapp.calc.Calculator.multiply"],
        notes="multiply method on Calculator handles this",
    ),
]