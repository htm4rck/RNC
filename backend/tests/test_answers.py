import json

import pytest

from app.local_agent.answers import configure_answers, empty_answers, load_answers, validate_answers
from app.local_agent.cli import main


def test_configuration_is_private_and_preserves_existing_answers(tmp_path):
    path = tmp_path / "private/answers.json"
    result = configure_answers(path, email="person@example.test", phone_country_code="+51",
                               phone_number="000123456", resume_name="CV_Architect.pdf")
    assert "person@example.test" not in json.dumps(result)
    assert "000123456" not in json.dumps(result)
    assert path.stat().st_mode & 0o777 == 0o600
    data = load_answers(path)
    assert data["contact"]["phone_number"] == "000123456"
    data["answers"]["Years of experience?"] = "5"
    path.write_text(json.dumps(data), encoding="utf-8")
    configure_answers(path, email="updated@example.test")
    updated = load_answers(path)
    assert updated["answers"]["Years of experience?"] == "5"
    assert updated["resume"]["filename"] == "CV_Architect.pdf"
    assert updated["contact"]["phone_number"] == "000123456"


@pytest.mark.parametrize("data", [[], {"contact": []}, {"contact": {"email": 1}},
                                  {"resume": {"job_title_contains": []}}, {"answers": {"Question": {}}}])
def test_invalid_configuration_is_rejected(data):
    with pytest.raises(ValueError):
        validate_answers(data)


def test_empty_configuration_does_not_invent_contact_details():
    assert all(value is None for value in empty_answers()["contact"].values())
    assert empty_answers()["resume"]["filename"] is None


def test_cli_configures_answers_without_connecting_to_firefox(tmp_path, capsys):
    assert main(["--data-dir", str(tmp_path), "configure", "--email", "person@example.test"]) == 0
    output = capsys.readouterr().out
    assert "person@example.test" not in output
    assert load_answers(tmp_path / "answers.json")["contact"]["email"] == "person@example.test"


def test_invalid_json_error_does_not_echo_private_file_content(tmp_path):
    path = tmp_path / "answers.json"
    path.write_text('{"email":"private@example.test",broken}', encoding="utf-8")
    with pytest.raises(ValueError, match="JSON válido") as error:
        load_answers(path)
    assert "private@example.test" not in str(error.value)
