"""Logical expressions for OpenAlex API queries."""


class or_(dict):
    """Logical OR expression class."""

    pass


class _LogicalExpression:
    """Base class for logical expressions.

    Attributes
    ----------
    token : str
        Token representing the logical operation.
    value : any
        Value to be used in the logical expression.
    """

    token = None

    def __init__(self, value):
        self.value = value

    def __str__(self) -> str:
        return f"{self.token}{self.value}"


class not_(_LogicalExpression):
    """Logical NOT expression class."""

    token = "!"


class gt_(_LogicalExpression):
    """Logical greater than expression class."""

    token = ">"


class lt_(_LogicalExpression):
    """Logical less than expression class."""

    token = "<"
