import argparse

from app import create_app, build_ai_service
from app.db import init_flask_database
from app.extensions import db


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Accessibility AI backend")
    parser.add_argument("--config", choices=["development", "testing", "production"], help="Application config profile")
    parser.add_argument(
        "--ai-provider",
        choices=["mock_json", "live_agent"],
        help="AI provider mode. Use mock JSON for local testing or live agent endpoint.",
    )
    parser.add_argument("--ai-endpoint", help="Live AI endpoint URL (required when --ai-provider=live_agent)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--init-db", action="store_true", help="Initialize database tables before starting the server")
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.ai_provider == "live_agent" and not args.ai_endpoint:
        raise SystemExit("--ai-endpoint is required when --ai-provider=live_agent")


def build_runtime_app(args: argparse.Namespace):
    _validate_args(args)

    app = create_app(args.config)

    if args.ai_provider:
        app.config["AI_PROVIDER"] = args.ai_provider
    if args.ai_endpoint:
        app.config["AI_LIVE_ENDPOINT"] = args.ai_endpoint

    # Rebuild service with runtime overrides from parsed args.
    app.extensions["ai_service"] = build_ai_service(app)

    if args.init_db:
        init_flask_database(app)

    return app


app = create_app()


@app.shell_context_processor
def _shell_context():
    return {"db": db}


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    runtime_app = build_runtime_app(args)
    runtime_app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
