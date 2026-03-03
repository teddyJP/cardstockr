"""
Stub script for nightly model training.

In v1, this will:
1. Pull cleaned daily median price series per (card_id, grade bucket).
2. Fit a simple time-series model (e.g., ETS/Holt-Winters) for each.
3. Generate forecast paths and uncertainty bands (p10/p50/p90).
4. Store forecasts and metrics in dedicated tables or as artifacts.
"""


def main() -> None:
    # TODO: Implement:
    # - Time series extraction
    # - Model training (statsmodels / scikit-learn)
    # - Forecast storage
    print("train_models.py is a placeholder. Implement training logic here.")


if __name__ == "__main__":
    main()

