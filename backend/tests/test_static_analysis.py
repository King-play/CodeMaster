from app.static_analysis import analyze_code


def test_python_syntax_error_is_reported() -> None:
    issues = analyze_code("def broken(:\n    pass", "python", "broken.py")

    assert issues
    assert issues[0].type == "syntax_error"
    assert issues[0].severity == "critical"


def test_sql_concatenation_is_reported() -> None:
    issues = analyze_code(
        'query = "SELECT * FROM users WHERE id = " + user_id',
        "python",
        "repo.py",
    )

    assert any(issue.type == "sql_injection_risk" for issue in issues)


def test_external_analyzers_can_be_disabled() -> None:
    class SettingsStub:
        codemate_enable_external_analyzers = False

    issues = analyze_code("eval('1 + 1')", "python", "sample.py", SettingsStub())

    assert any(issue.type == "dangerous_dynamic_execution" for issue in issues)
    assert all(issue.source != "pylint" for issue in issues)
