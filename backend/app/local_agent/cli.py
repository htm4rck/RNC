import argparse
import json
import os
import sys
from pathlib import Path

from app.local_agent.answers import configure_answers, load_answers
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
        ("inspect-job", "Diagnostica encabezados, botones y diálogos de una vacante."),
        ("inspect-application", "Inspecciona el paso visible de Easy Apply."),
        ("prepare-application", "Rellena contacto, selecciona un CV existente y avanza sin enviar."),
    ):
        action = commands.add_parser(command, help=help_text)
        action.add_argument("--url", help="URL del perfil o de la vacante en LinkedIn.")
        if command == "capture-profile":
            action.add_argument(
                "--no-scroll", action="store_true",
                help="Lee solo el contenido ya renderizado, sin desplazar la página.",
            )
        if command in {"inspect-application", "prepare-application"}:
            action.add_argument("--open", action="store_true", help="Abre Easy Apply con un clic.")
        if command == "prepare-application":
            action.add_argument("--answers-file", type=Path)
            action.add_argument("--dry-run", action="store_true", help="Planifica el paso actual sin modificarlo.")
            action.add_argument("--max-steps", type=int, default=8)
    configure = commands.add_parser("configure", help="Guarda respuestas verificadas en un archivo local privado.")
    configure.add_argument("--answers-file", type=Path)
    configure.add_argument("--email")
    configure.add_argument("--phone-country-code")
    configure.add_argument("--phone-number")
    configure.add_argument("--resume-name", help="Nombre exacto del CV ya cargado en LinkedIn.")
    configure.add_argument("--resume-job-keyword", action="append", help="Puesto al que se aplica ese CV; repetible.")
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
    if args.command == "configure":
        return configure_answers(
            args.answers_file or args.data_dir / "answers.json", email=args.email,
            phone_country_code=args.phone_country_code, phone_number=args.phone_number,
            resume_name=args.resume_name, resume_job_keywords=args.resume_job_keyword,
        )
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
        inspect_job,
        inspect_profile,
        read_job,
        read_profile,
    )

    kind = "profile" if args.command in {"capture-profile", "inspect-profile"} else "job"
    if args.url:
        linkedin_url(args.url, kind)  # Validate before connecting or touching any tab.
    answers = None
    if args.command == "prepare-application":
        answers = load_answers(args.answers_file or args.data_dir / "answers.json")
        if not 1 <= args.max_steps <= 20:
            raise ValueError("max_steps debe estar entre 1 y 20.")
    lock_dir = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / f"rcn-agent-{os.getuid()}"
    with connected_firefox(args.marionette_port, lock_dir) as driver:
        select_linkedin_tab(driver, kind, args.url)
        if args.command == "inspect-profile":
            return inspect_profile(driver)
        elif args.command == "inspect-job":
            return inspect_job(driver)
        elif args.command == "capture-profile":
            content = read_profile(driver, scroll=not args.no_scroll)
        elif args.command == "capture-job":
            content = read_job(driver)
        elif args.command == "prepare-application":
            from app.local_agent.applications import prepare_application

            kind = "application"
            content = prepare_application(
                driver, answers, open_dialog=args.open, dry_run=args.dry_run, max_steps=args.max_steps,
            )
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
