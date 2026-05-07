"""Shared logging helpers for HaruQuant agents."""

from __future__ import annotations

import logging


def get_agent_logger(agent_name: str) -> logging.Logger:
    return logging.getLogger(f"haruquant.agents.{agent_name}")


__all__ = ["get_agent_logger"]
