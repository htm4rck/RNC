import argparse
import json
import os
import sys
from pathlib import Path

from app.local_agent.browser import connected_firefox, firefox_status, select_linkedin_tab
from app.local_agent.store import STATUSES, LocalStore
from app.local_agent.urls import linkedin_url


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="RNC: agente local de carrera con Firefox.")
    result.add_argument(
        "--data-dir", type=Path,
        default=Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "rcn",
        help="Directorio de capturas y seguimiento local.",
    )
    result.add_argument("--marionette-port", type=int, default=2828)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Diagnóstico sin controlar pestañas.")
    for command, help_text in (
        ("capture-profile", "Captura el perfil visible."),
        ("inspect-profile", "Diagnostica los encabezados del perfil sin guardar una captura."),
        ("capture-job", "Captura una vacante visible."),
        ("inspect-application", "Inspecciona el paso visible de Easy Apply."),
    ):
        action = commands.add_parser(command, help=help_text)
        action.add_argument("--url", help="URL del perfil o de la vacante en LinkedIn.")
        if command == "capture-profile":
            action.add_argument(
                "--no-scroll", action="store_true",
                help="Lee solo el contenido ya renderizado, sin desplazar la página.",
            )
        if command == "inspect-application":
            action.add_argument("--open", action="store_true", help="Abre Easy Apply con un clic.")
    track = commands.add_parser("track", help="Registra manualmente el estado de una candidatura.")
    track.add_argument("--job-url", required=True)
    track.add_argument("--status", choices=STATUSES, required=True)
    track.add_argument("--notes", default=None)
    listing = commands.add_parser("applications", help="Lista candidaturas locales.")
    listing.add_argument("--status", choices=STATUSES)
    return result


def run(args: argparse.Namespace) -> dict | list:
    if not 1 <= args.marionette_port <= 65535:
        raise ValueError("El puerto Marionette debe estar entre 1 y 65535.")
    if args.command == "doctor":
        return firefox_status(args.marionette_port)
    if args.command == "applications":
        with LocalStore(args.data_dir) as store:
            return store.applications(args.status)
    if args.command == "track":
        url = linkedin_url(args.job_url, "job")
        with LocalStore(args.data_dir) as store:
            return store.track(url, args.status, args.notes)

    # Browser dependencies are optional; doctor and the tracker work without Selenium.
    from app.local_agent.linkedin import (
        inspect_application,
        inspect_profile,
        read_job,
        read_profile,
    )

    kind = "profile" if args.command in {"capture-profile", "inspect-profile"} else "job"
    if args.url:
        linkedin_url(args.url, kind)  # Validate before connecting or touching any tab.
    lock_dir = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / f"rcn-agent-{os.getuid()}"
    with connected_firefox(args.marionette_port, lock_dir) as driver:
        select_linkedin_tab(driver, kind, args.url)
        if args.command == "inspect-profile":
            return inspect_profile(driver)
        elif args.command == "capture-profile":
            content = read_profile(driver, scroll=not args.no_scroll)
        elif args.command == "capture-job":
            content = read_job(driver)
        else:
            kind = "application"
            content = inspect_application(driver, args.open)
        with LocalStore(args.data_dir) as store:
            return store.snapshot(kind, content)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        output = run(args)
    except ModuleNotFoundError as exc:
        print(
            f"Falta {exc.name}. Instala el agente: pip install '.[browser]' desde backend/.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Selenium failures may contain page content; don't dump its traceback or a DOM.
        if type(exc).__module__.startswith("selenium."):
            print(
                "Error de Firefox. Revisa la pestaña y ejecuta doctor antes de repetir.",
                file=sys.stderr,
            )
            return 1
        raise
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
