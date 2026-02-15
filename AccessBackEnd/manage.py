import argparse
import os

from app import create_app
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
    parser.add_argument("--ai-endpoint", help="Live AI endpoint URL (used when --ai-provider=live_agent)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--init-db", action="store_true", help="Initialize database tables before starting the server")
    return parser


def _apply_runtime_overrides(args: argparse.Namespace) -> None:
    if args.config:
        os.environ["APP_CONFIG"] = args.config
    if args.ai_provider:
        os.environ["AI_PROVIDER"] = "live_agent" if args.ai_provider == "live_agent" else "mock_json"
    if args.ai_endpoint:
        os.environ["AI_LIVE_ENDPOINT"] = args.ai_endpoint


def _create_runtime_app():
    parser = _build_parser()
    args, _ = parser.parse_known_args()
    _apply_runtime_overrides(args)
    return create_app(), args


app, runtime_args = _create_runtime_app()

if runtime_args.init_db:
    init_flask_database(app)


@app.shell_context_processor
def _shell_context():
    return {"db": db}


if __name__ == "__main__":
    app.run(host=runtime_args.host, port=runtime_args.port)
