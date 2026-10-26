"""User-provided application facts, stored locally and never included in reports."""

import json
import os
import tempfile
from pathlib import Path


class AnswersError(ValueError):
    """Invalid content in a user-provided configuration file."""


def empty_answers() -> dict:
    return {
        "contact": {"email": None, "phone_country_code": None, "phone_number": None},
        "resume": {"filename": None, "job_title_contains": ["arquitecto", "architect"]},
        "answers": {},
    }


def validate_answers(data: dict) -> dict:
    if not isinstance(data, dict):
        raise AnswersError("El archivo de respuestas debe contener un objeto JSON.")
    result = empty_answers()
    for section in result:
        if not isinstance(data.get(section, {}), dict):
            raise AnswersError(f"La sección {section} debe ser un objeto JSON.")
        result[section].update(data.get(section, {}))
    for key in ("email", "phone_country_code", "phone_number"):
        value = result["contact"][key]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"contact.{key} debe ser un texto no vacío o null.")
    filename = result["resume"]["filename"]
    if filename is not None and (not isinstance(filename, str) or not filename.strip()):
        raise ValueError("resume.filename debe ser un nombre de archivo o null.")
    keywords = result["resume"]["job_title_contains"]
    if not isinstance(keywords, list) or not keywords or any(
        not isinstance(word, str) or not word.strip() for word in keywords
    ):
        raise ValueError("resume.job_title_contains requiere palabras de puesto no vacías.")
    for label, answer in result["answers"].items():
        if not isinstance(label, str) or not label.strip() or not (
            answer is None or isinstance(answer, str | int | float | bool)
        ):
            raise ValueError("answers debe asociar etiquetas de preguntas a respuestas simples.")
    return result


def load_answers(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError("No existe el archivo de respuestas. Ejecuta rcn-agent configure primero.") from None
    except json.JSONDecodeError:
        raise ValueError("El archivo de respuestas no contiene JSON válido.") from None
    return validate_answers(data)


def configure_answers(path: Path, *, email=None, phone_country_code=None, phone_number=None,
                      resume_name=None, resume_job_keywords=None) -> dict:
    data = load_answers(path) if path.exists() else empty_answers()
    changed = []
    for key, value in {
        "email": email, "phone_country_code": phone_country_code, "phone_number": phone_number,
    }.items():
        if value is not None:
            data["contact"][key] = value
            changed.append("contact." + key)
    if resume_name is not None:
        data["resume"]["filename"] = resume_name
        changed.append("resume.filename")
    if resume_job_keywords:
        data["resume"]["job_title_contains"] = resume_job_keywords
        changed.append("resume.job_title_contains")
    if not changed:
        raise ValueError("Indica al menos un dato de contacto o un CV para configurar.")
    data = validate_answers(data)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8", delete=False) as file:
            temporary = Path(file.name)
            os.chmod(temporary, 0o600)
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return {"answers_file": str(path), "updated_fields": changed}
