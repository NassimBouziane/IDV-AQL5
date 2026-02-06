"""Main entry point for ThrottleX."""

import uvicorn

from throttlex.config import get_settings


def main() -> None:
    """Run the ThrottleX server."""
    settings = get_settings()

    uvicorn.run(
        "throttlex.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=False,  # We handle logging ourselves
    )


if __name__ == "__main__":
    main()
