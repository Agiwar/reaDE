"""Base exceptions."""


class ReadeError(Exception):
    """Root of the reaDE exception hierarchy.

    Every feature module raises a module-specific subclass of this error.
    Raw driver or library exceptions never cross a module boundary; they
    are mapped into this hierarchy at the implementation layer, so callers
    can catch ``ReadeError`` for any reaDE failure or a subclass for a
    module-specific one.
    """
