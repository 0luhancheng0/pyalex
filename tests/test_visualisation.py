import numpy as np
import pytest
import matplotlib.pyplot as plt
from experiments.visualisation import plot_calibration

def test_plot_calibration_single():
    """Test plot_calibration with a single probability array."""
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.4, 0.35, 0.8])
    
    fig = plot_calibration(y_true, y_prob, n_bins=2)
    
    assert isinstance(fig, plt.Figure)
    plt.close(fig)

def test_plot_calibration_dict():
    """Test plot_calibration with a dictionary of probabilities (new functionality)."""
    y_true = np.array([0, 0, 1, 1])
    y_probs = {
        "Strategy A": np.array([0.1, 0.4, 0.35, 0.8]),
        "Strategy B": np.array([0.2, 0.3, 0.6, 0.9])
    }
    
    # This should work after the update
    fig = plot_calibration(y_true, y_probs, n_bins=2)
    
    assert isinstance(fig, plt.Figure)
    
    # Check if multiple lines are plotted (one for each strategy + one for perfect calibration)
    ax = fig.get_axes()[0]
    lines = ax.get_lines()
    assert len(lines) == 3  # Strategy A, Strategy B, Perfect calibration
    
    plt.close(fig)

def test_plot_calibration_invalid_input():
    """Test plot_calibration with invalid input."""
    y_true = np.array([0, 0, 1, 1])
    y_prob = "not an array"
    
    with pytest.raises(TypeError):
        plot_calibration(y_true, y_prob)
