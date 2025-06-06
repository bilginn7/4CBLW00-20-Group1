import pandas as pd
import xgboost as xgb


def predict_month_range(model: xgb.XGBRegressor(), X_template: pd.DataFrame, start_year: int,
                        start_month: int, end_year: int, end_month: int, lsoa_col: str = "LSOA code") -> pd.DataFrame:
    """Predict a span of future months in one call.

    :param xgboost.XGBRegressor model: A fitted **XGBoost** regressor whose :py:meth:`~xgboost.XGBRegressor.predict`
                                       method will be used to generate forecasts.
    :param pandas.DataFrame X_template: A dataframe that contains **at least** the latest observation for every
                                        LSOA you wish to forecast. All feature engineering required by the model
                                        should already be present.
    :param int start_year: Calendar year of the first month to forecast (e.g. ``2025``).
    :param int start_month: Calendar month of the first month to forecast (``1``–``12``).
    :param int end_year: Calendar year of the **final** month to forecast (inclusive).
    :param int end_month: Calendar month of the **final** month to forecast (``1``–``12``, inclusive).
    :param str lsoa_col: Name of the column holding LSOA codes in *both* ``X_template`` and the
                         returned dataframe. Defaults to ``"LSOA code"``.

    :raises ValueError: If the end date precedes the start date (i.e. the pair
                        ``(end_year, end_month)`` is earlier than ``(start_year, start_month)``).

    :returns: A dataframe with one row per **LSOA–month** combination,
              containing:

              * ``LSOA_code`` – the LSOA identifier
              * ``year`` – forecast year
              * ``month`` – forecast month
              * ``prediction`` – model output for that LSOA-month
    :rtype: pandas.DataFrame
    """
    # sanity-check
    if (end_year, end_month) < (start_year, start_month):
        raise ValueError("`end_year/end_month` must be after `start_year/start_month`")

    # total number of months to iterate (inclusive range)
    n_months = (end_year - start_year) * 12 + (end_month - start_month) + 1

    # keep a copy so we don’t mutate the original template
    X_template = X_template.copy()
    X_template[lsoa_col] = X_template[lsoa_col].astype("category")

    all_results = []

    for i in range(n_months):
        # convert “i months after the start date” into YYYY-MM
        target_year = start_year + ((start_month - 1 + i) // 12)
        target_month = ((start_month - 1 + i) % 12) + 1

        # build the feature frame for this month
        month_rows = []
        for lsoa in X_template[lsoa_col].unique():
            row = X_template[X_template[lsoa_col] == lsoa].iloc[-1].copy()
            row["year"] = target_year
            row["month"] = target_month
            month_rows.append(row)

        month_df = pd.DataFrame(month_rows)
        month_df[lsoa_col] = month_df[lsoa_col].astype("category")

        # run the forecast
        preds = model.predict(month_df)

        # collect results
        all_results.append(pd.DataFrame({
            "LSOA_code": month_df[lsoa_col],
            "year": target_year,
            "month": target_month,
            "prediction": preds
        }))

    return pd.concat(all_results, ignore_index=True)

if __name__ == "__main__":
    loaded_model = xgb.XGBRegressor()
    loaded_model.load_model('final_xgboost_model.json')
    X_test = pd.read_parquet('../data/X_test.parquet')

    combined_results = predict_month_range(
        model=loaded_model,
        X_template=X_test,
        start_year=2025,
        start_month=3,  # March 2025
        end_year=2025,
        end_month=8  # August 2025
    )

    print(combined_results.head())