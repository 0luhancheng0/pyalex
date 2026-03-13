"""
Visualization tools for experiment analysis.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from typing import Optional


def plot_calibration(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
    strategy: str = "uniform",
    title: str = "Calibration Plot",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Plot calibration curve (reliability diagram) for binary classifier.

    Parameters
    ----------
    y_true : np.ndarray
        True binary labels (0 or 1).
    y_prob : np.ndarray
        Predicted probabilities for the positive class.
    n_bins : int, default=10
        Number of bins for calibration curve.
    strategy : {'uniform', 'quantile'}, default='uniform'
        Strategy to define bin widths.
    title : str, default='Calibration Plot'
        Title for the plot.
    save_path : str, optional
        If provided, save figure to this path.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The generated figure.
    """
    # Compute calibration curve
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_true, y_prob, n_bins=n_bins, strategy=strategy
    )

    # Create plot
    fig, ax = plt.subplots(figsize=(8, 6))

    # Plot calibration curve
    ax.plot(
        mean_predicted_value,
        fraction_of_positives,
        "s-",
        label="Model",
        linewidth=2,
        markersize=8,
    )

    # Plot perfect calibration line
    ax.plot([0, 1], [0, 1], "k:", label="Perfectly calibrated", linewidth=2)

    # Set labels and title
    ax.set_xlabel("Mean Predicted Probability", fontsize=12)
    ax.set_ylabel("Fraction of Positives", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    # Set equal aspect ratio
    ax.set_aspect("equal", adjustable="box")

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

    return fig


def plot_error_stratification(
    error_rates: dict,
    x_labels: list,
    title: str = "Error Rate Stratification",
    xlabel: str = "Strata",
    ylabel: str = "Error Rate",
    save_path: Optional[str] = None,
    kind: str = "bar",
) -> plt.Figure:
    """
    Plot error rates across different strata.

    Parameters
    ----------
    error_rates : dict
        Dictionary mapping error type (e.g., 'FP', 'FN') to list of error rates.
    x_labels : list
        Labels for each stratum.
    title : str, default='Error Rate Stratification'
        Title for the plot.
    xlabel : str, default='Strata'
        Label for x-axis.
    ylabel : str, default='Error Rate'
        Label for y-axis.
    save_path : str, optional
        If provided, save figure to this path.
    kind : {'bar', 'line'}, default='bar'
        Type of plot.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The generated figure.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(x_labels))
    width = 0.8 / len(error_rates)  # width of bars

    for i, (error_type, rates) in enumerate(error_rates.items()):
        offset = width * i - width * (len(error_rates) - 1) / 2
        if kind == "bar":
            ax.bar(x + offset, rates, width, label=error_type, alpha=0.8)
        elif kind == "line":
            ax.plot(
                x + offset, rates, "o-", label=error_type, linewidth=2, markersize=6
            )

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

    return fig


def plot_feature_distribution_by_error(
    df: pd.DataFrame,
    feature_col: str,
    error_col: str = "error_type",
    title: Optional[str] = None,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Plot distribution of a feature stratified by error type.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing features and error labels.
    feature_col : str
        Column name of the feature to plot.
    error_col : str, default='error_type'
        Column name indicating error type (e.g., 'FP', 'FN', 'TN', 'TP').
    title : str, optional
        Title for the plot. If None, uses feature_col.
    save_path : str, optional
        If provided, save figure to this path.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The generated figure.
    """
    if title is None:
        title = f"Distribution of {feature_col} by Error Type"

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot histogram for each error type
    error_types = df[error_col].unique()
    for error_type in error_types:
        subset = df[df[error_col] == error_type][feature_col].dropna()
        ax.hist(subset, bins=30, alpha=0.5, label=error_type, density=True)

    ax.set_xlabel(feature_col, fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

    return fig
