"""Helpers for loading parser-tuning rules from local JSON config."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from automation.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_parser_rules() -> dict[str, Any]:
    """Load parser rules from configured JSON file."""
    if not settings.parser_rules_enabled:
        return {}

    path = Path(settings.parser_rules_file)
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
        logger.warning("Failed to load parser rules from %s: %s", path, exc)
        return {}

    if not isinstance(payload, dict):
        logger.warning("Parser rules file must contain a JSON object: %s", path)
        return {}

    return payload


def get_parser_rule_section(name: str) -> dict[str, Any]:
    """Return one parser section from parser rules."""
    data = load_parser_rules().get(name, {})
    return data if isinstance(data, dict) else {}
