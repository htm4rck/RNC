import re
from urllib.parse import parse_qs, urlsplit


def linkedin_url(value: str, kind: str) -> str:
    """Keep supported resources on LinkedIn and drop tracking parameters."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"linkedin.com", "www.linkedin.com"}
        or parsed.port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Se requiere una URL HTTPS de linkedin.com o www.linkedin.com.")
    if kind not in {"profile", "job"}:
        raise ValueError("Tipo de recurso LinkedIn desconocido.")
    if kind == "job" and parsed.path.rstrip("/") in {"/jobs/search", "/jobs/search-results"}:
        selected = parse_qs(parsed.query, keep_blank_values=True).get("currentJobId", [])
        if len(selected) != 1 or not re.fullmatch(r"[0-9]+", selected[0]):
            raise ValueError("Selecciona una vacante: la URL requiere un único currentJobId numérico.")
        return f"https://www.linkedin.com/jobs/view/{selected[0]}/"
    pattern = r"/in/([\w%-]+)/?" if kind == "profile" else r"/jobs/view/([0-9]+)/?"
    match = re.fullmatch(pattern, parsed.path)
    if not match:
        example = "/in/tu-perfil/" if kind == "profile" else "/jobs/view/123456789/"
        suffix = " o una búsqueda de empleos con currentJobId." if kind == "job" else "."
        raise ValueError(f"La URL debe tener la forma https://www.linkedin.com{example}{suffix}")
    prefix = "in" if kind == "profile" else "jobs/view"
    return f"https://www.linkedin.com/{prefix}/{match[1]}/"
