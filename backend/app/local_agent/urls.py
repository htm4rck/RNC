import re
from urllib.parse import urlsplit


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
    pattern = r"/in/([\w%-]+)/?" if kind == "profile" else r"/jobs/view/(\d+)/?"
    match = re.fullmatch(pattern, parsed.path)
    if not match:
        example = "/in/tu-perfil/" if kind == "profile" else "/jobs/view/123456789/"
        raise ValueError(f"La URL debe tener la forma https://www.linkedin.com{example}")
    prefix = "in" if kind == "profile" else "jobs/view"
    return f"https://www.linkedin.com/{prefix}/{match[1]}/"
