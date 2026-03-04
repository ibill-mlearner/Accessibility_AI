from .routes import api_v1_bp


def _register_route_modules() -> None:
    """Import split route modules so their @api_v1_bp decorators execute."""
    # Early exit when modules are already loaded to avoid duplicate decorator work in reload paths.
    if getattr(api_v1_bp, "_split_routes_loaded", False):
        return

    # Need to change to explicit imports if I want anonymous functions
    from . import accessiblity_features
    from . import ai_interactions_routes
    from . import ai_model_catalog_routes
    from . import auth
    from . import chats
    from . import classes_file
    from . import messages
    from . import notes
    from . import system_prompts_routes

    setattr(api_v1_bp, "_split_routes_loaded", True)


_register_route_modules()

__all__ = ["api_v1_bp"]
