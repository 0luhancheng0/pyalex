"""Query building utilities for OpenAlex API."""

from pyalex.core.expressions import or_
from pyalex.core.utils import quote_oa_value


def flatten_kv(d, prefix=None, logical="+"):
    """Flatten a dictionary into a key-value string for the OpenAlex API.

    Parameters
    ----------
    d : dict
        Dictionary to be flattened.
    prefix : str, optional
        Prefix for the keys.
    logical : str, optional
        Logical operator to join values.

    Returns
    -------
    str
        Flattened key-value string.
    """
    if prefix is None and not isinstance(d, dict):
        raise ValueError("prefix should be set if d is not a dict")

    if isinstance(d, dict):
        logical_subd = "|" if isinstance(d, or_) else logical

        t = []
        for k, v in d.items():
            x = flatten_kv(
                v, prefix=f"{prefix}.{k}" if prefix else f"{k}", logical=logical_subd
            )
            t.append(x)

        return ",".join(t)
    elif isinstance(d, list):
        if logical == "+":
            # For filter conditions on the same field, each should be separate
            # e.g., publication_year:>2018,publication_year:<2021
            return ",".join([f"{prefix}:{quote_oa_value(i)}" for i in d])
        else:
            # For OR conditions, join with the logical operator
            list_str = logical.join([f"{quote_oa_value(i)}" for i in d])
            return f"{prefix}:{list_str}"
    else:
        return f"{prefix}:{quote_oa_value(d)}"


def params_merge(params, add_params):
    """Merge additional parameters into existing parameters.

    Parameters
    ----------
    params : dict
        Existing parameters.
    add_params : dict
        Additional parameters to be merged.
    """
    for k in add_params.keys():
        if (
            k in params
            and isinstance(params[k], dict)
            and isinstance(add_params[k], dict)
        ):
            params_merge(params[k], add_params[k])
        elif (
            k in params
            and not isinstance(params[k], list)
            and isinstance(add_params[k], list)
        ):
            # example: params="a" and add_params=["b", "c"]
            params[k] = [params[k]] + add_params[k]
        elif (
            k in params
            and isinstance(params[k], list)
            and not isinstance(add_params[k], list)
        ):
            # example: params=["b", "c"] and add_params="a"
            params[k] = params[k] + [add_params[k]]
        elif k in params:
            params[k] = [params[k], add_params[k]]
        else:
            params[k] = add_params[k]


def wrap_values_nested_dict(d, func):
    """Apply a function to all values in a nested dictionary.

    Parameters
    ----------
    d : dict
        Nested dictionary.
    func : function
        Function to apply to the values.

    Returns
    -------
    dict
        Dictionary with the function applied to the values.
    """
    for k, v in d.items():
        if isinstance(v, dict):
            d[k] = wrap_values_nested_dict(v, func)
        elif isinstance(v, list):
            d[k] = [func(i) for i in v]
        else:
            d[k] = func(v)

    return d
