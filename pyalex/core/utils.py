"""Utility functions for PyAlex."""

from urllib.parse import quote_plus


def invert_abstract(inv_index):
    """Invert OpenAlex abstract index.

    Parameters
    ----------
    inv_index : dict
        Inverted index of the abstract.

    Returns
    -------
    str
        Inverted abstract.
    """
    if inv_index is not None:
        l_inv = [(w, p) for w, pos in inv_index.items() for p in pos]
        return " ".join(map(lambda x: x[0], sorted(l_inv, key=lambda x: x[1])))


def quote_oa_value(v):
    """Prepare a value for the OpenAlex API.

    Applies URL encoding to strings and converts booleans to lowercase strings.

    Parameters
    ----------
    v : any
        Value to be prepared.

    Returns
    -------
    any
        Prepared value.
    """
    from pyalex.core.expressions import _LogicalExpression
    
    # workaround for bug https://groups.google.com/u/1/g/openalex-users/c/t46RWnzZaXc
    if isinstance(v, bool):
        return str(v).lower()

    if isinstance(v, _LogicalExpression) and isinstance(v.value, str):
        v.value = quote_plus(v.value)
        return v

    if isinstance(v, str):
        return quote_plus(v)

    return v
