"""Shared cancellation helpers for long-running processing."""

from __future__ import annotations


class ProcessingCancelled(RuntimeError):
    """Raised when the user requests cancellation of a processing run."""


def raise_if_cancelled(cancel_event) -> None:
    """Raise :class:`ProcessingCancelled` when *cancel_event* has been set."""
    if cancel_event is not None and cancel_event.is_set():
        raise ProcessingCancelled("Verarbeitung wurde abgebrochen.")
