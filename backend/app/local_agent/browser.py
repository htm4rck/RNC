from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from shutil import which
from socket import create_connection
from urllib.parse import urlsplit

from app.local_agent.urls import linkedin_url


def firefox_status(port: int = 2828) -> dict:
    driver = which("geckodriver")
    if driver is None and Path("/snap/bin/geckodriver").exists():
        driver = "/snap/bin/geckodriver"
    try:
        with create_connection(("127.0.0.1", port), timeout=1):
            listening = True
    except OSError:
        listening = False
    return {
        "firefox": which("firefox"),
        "geckodriver": driver,
        "host": "127.0.0.1",
        "marionette_port": port,
        "marionette_listening": listening,
        "ready": bool(driver and listening),
    }


@contextmanager
def connected_firefox(port: int, lock_dir: Path) -> Iterator:
    """Attach as Learnex does; never launch Firefox or load another browser profile."""
    import fcntl

    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.firefox.service import Service

    lock_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (lock_dir / f"firefox-{port}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Otro agente RNC está usando este Firefox.") from None
        status = firefox_status(port)
        if not status["marionette_listening"]:
            raise RuntimeError(
                f"Firefox no escucha en 127.0.0.1:{port}. Cierra Firefox por completo y "
                "ábrelo con firefox --marionette. Luego inicia sesión y abre LinkedIn."
            )
        if not status["geckodriver"]:
            raise RuntimeError("No se encontró geckodriver. Ejecuta rcn-agent doctor.")
        service = Service(
            executable_path=status["geckodriver"],
            service_args=["--connect-existing", "--marionette-port", str(port)],
        )
        try:
            driver = webdriver.Firefox(service=service)
        except WebDriverException as exc:
            raise RuntimeError(
                "No se pudo conectar a Firefox. Comprueba geckodriver y que Learnex u otro "
                "agente no esté conectado a Marionette."
            ) from exc
        try:
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(15)
            yield driver
        finally:
            # With --connect-existing geckodriver deletes the automation session,
            # without the force-quit flag used for browsers it launched itself.
            driver.quit()


def select_linkedin_tab(driver, kind: str, url: str | None = None) -> str:
    """Read an existing tab, or navigate an existing LinkedIn tab to the requested URL."""
    from selenium.common.exceptions import NoSuchWindowException
    from selenium.webdriver.support.ui import WebDriverWait

    target = linkedin_url(url, kind) if url else None
    original = driver.current_window_handle
    fallback = None
    handles = [original, *(handle for handle in driver.window_handles if handle != original)]
    for handle in handles:
        try:
            driver.switch_to.window(handle)
            current = driver.current_url
            parsed = urlsplit(current)
            if parsed.scheme != "https" or parsed.hostname not in {
                "linkedin.com", "www.linkedin.com"
            }:
                continue
            fallback = fallback or handle
            try:
                canonical = linkedin_url(current, kind)
            except ValueError:
                continue
            if target is None or target == canonical:
                break
        except NoSuchWindowException:
            continue
    else:
        if target and fallback:
            driver.switch_to.window(fallback)
            driver.get(target)
        else:
            driver.switch_to.window(original)
            raise RuntimeError(
                "Abre tu perfil de LinkedIn o una vacante /jobs/view/ en Firefox. "
                "También puedes indicar --url si ya tienes una pestaña de LinkedIn abierta."
            )
    WebDriverWait(driver, 15).until(
        lambda browser: browser.execute_script("return document.readyState") == "complete"
    )
    require_linkedin_page(driver, kind)
    if kind != "profile":
        WebDriverWait(driver, 15).until(
            lambda browser: browser.execute_script(
                "return [...document.querySelectorAll('main,[role=main]')]"
                ".some(e => e.getClientRects().length && e.innerText.trim())"
            )
        )
    return linkedin_url(driver.current_url, kind)


def require_linkedin_page(driver, kind: str) -> None:
    from selenium.webdriver.common.by import By

    try:
        linkedin_url(driver.current_url, kind)
    except ValueError:
        raise RuntimeError(
            "LinkedIn cambió de página. Revisa la sesión o cualquier verificación en Firefox."
        ) from None
    if driver.find_elements(
        By.CSS_SELECTOR,
        'input[type="password"], form[action*="login"], '
        'iframe[src*="captcha"], #captcha-internal',
    ):
        raise RuntimeError("Completa el inicio de sesión o la verificación en Firefox y repite.")
