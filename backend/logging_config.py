"""Central rich-based logging setup for the backend.

Call :func:`setup_logging` once near your program's entry point. Everywhere
else just use the stdlib as usual::

    import logging

    log = logging.getLogger(__name__)
    log.info("hello")

The handler is attached to the root logger, so every module logger created via
``logging.getLogger(__name__)`` inherits the rich formatting automatically. Each
line shows the time, the log level and the module name (the logger name),
colourised by rich's ``RichHandler``.

This module is intentionally **not** named ``logging.py``: ``backend/`` is the
import root, so a module called ``logging`` there would shadow the standard
library and break ``import logging`` everywhere.
"""

import logging
import os

from rich.logging import RichHandler

# Guard so repeated setup_logging() calls (e.g. tests, re-imports) don't stack
# multiple handlers on the root logger.
_CONFIGURED = False


def setup_logging(level: int | str | None = None) -> None:
    """Configures the root logger to emit rich-formatted records.

    Args:
        level: Minimum level to emit. Accepts a logging level int
            (``logging.DEBUG``) or its name (``"DEBUG"``). Defaults to the
            ``LOG_LEVEL`` environment variable, or ``INFO`` if unset.

    Idempotent: calling it more than once is a no-op after the first call.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")

    handler = RichHandler(
        rich_tracebacks=True,  # render exceptions with rich's coloured traceback
        markup=True,  # allow [bold red]...[/] markup in log messages
        show_time=True,  # the timestamp column
        show_level=True,  # the colourised LEVEL column
        show_path=False,  # we put the module in the format string instead
        log_time_format="[%X]",  # wall-clock time, e.g. [14:53:07]
    )

    logging.basicConfig(
        level=level,
        # RichHandler renders time and level itself; the message we hand it is
        # just "<module>: <text>" so the logger name is visible and highlighted.
        format="%(name)s: %(message)s",
        datefmt="[%X]",
        handlers=[handler],
        force=True,  # replace any handlers a library installed before us
    )

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper: ensure logging is set up, then return the logger.

    Lets callers do ``from logging_config import get_logger`` without having to
    remember the one-time ``setup_logging()`` call. Plain
    ``logging.getLogger(__name__)`` works just as well once setup ran.
    """
    setup_logging()
    return logging.getLogger(name)
