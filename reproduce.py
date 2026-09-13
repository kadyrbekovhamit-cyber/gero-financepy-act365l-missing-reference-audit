#!/usr/bin/env python3
"""Reproduce FinancePy Act/365L's omitted-reference-end failure."""

import argparse
from datetime import date
import importlib.metadata
import json
from math import isclose

import financepy
from financepy.utils.date import Date
from financepy.utils.day_count import DayCount, DayCountTypes
from financepy.utils.frequency import FrequencyTypes


def independent_actual_days(start, end):
    """Actual calendar days using only Python's standard library."""

    return (date(*end) - date(*start)).days


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-released-failure", action="store_true")
    args = parser.parse_args()

    day_count = DayCount(DayCountTypes.ACT_365L)
    start = Date(1, 12, 2023)
    end = Date(1, 3, 2024)

    implicit_result = None
    implicit_exception = None
    try:
        implicit_result = day_count.year_frac(
            start,
            end,
            freq_type=FrequencyTypes.ANNUAL,
        )
    except Exception as exc:  # The released version reaches this path.
        implicit_exception = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    explicit_result = day_count.year_frac(
        start,
        end,
        end,
        FrequencyTypes.ANNUAL,
    )

    # Preserve the separate accrued-fraction semantics: this interval itself
    # does not reach February 29, but its explicit coupon period does.
    accrued_result = day_count.year_frac(
        Date(1, 3, 2023),
        Date(1, 12, 2023),
        Date(1, 3, 2024),
        FrequencyTypes.ANNUAL,
    )

    actual_days = independent_actual_days((2023, 12, 1), (2024, 3, 1))
    oracle = (actual_days / 366.0, float(actual_days), 366)

    try:
        financepy_version = importlib.metadata.version("financepy")
    except importlib.metadata.PackageNotFoundError:
        financepy_version = financepy.__version__

    record = {
        "financepy": financepy_version,
        "synthetic_interval": ["2023-12-01", "2024-03-01"],
        "implicit_dt3_result": implicit_result,
        "implicit_dt3_exception": implicit_exception,
        "explicit_dt3_result": explicit_result,
        "independent_oracle": oracle,
        "explicit_later_coupon_control": accrued_result,
        "synthetic_inputs": True,
    }
    print(json.dumps(record, indent=2))

    if actual_days != 91:
        raise SystemExit("independent day count did not equal 91")
    if explicit_result[1:] != oracle[1:] or not isclose(
        explicit_result[0], oracle[0], rel_tol=0.0, abs_tol=1e-15
    ):
        raise SystemExit("explicit period-end result did not match oracle")
    if accrued_result != (275.0 / 366.0, 275.0, 366):
        raise SystemExit("explicit coupon-period semantics changed")

    if args.expect_released_failure:
        if implicit_exception is None:
            raise SystemExit("expected the released omitted-dt3 call to fail")
        if implicit_exception["type"] != "AttributeError":
            raise SystemExit("released call failed with an unexpected exception")
    else:
        if implicit_exception is not None:
            raise SystemExit("omitted-dt3 call still fails")
        if implicit_result != explicit_result:
            raise SystemExit("omitted dt3 did not fall back to dt2")


if __name__ == "__main__":
    main()
