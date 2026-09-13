# FinancePy Act/365L fails without an optional reference-period end

Independent numerical audit by Xamit Kadirbekov / GERO Research, 13 September 2026.

`DayCount.year_frac()` documents two supported modes: an ordinary calculation
between `dt1` and `dt2`, where `dt3` is `None`, and a bond-accrual calculation
where `dt3` is the next coupon date. In the annual `ACT_365L` branch, however,
the implementation compares February 29 with `dt3` even when `dt3` is `None`.

The smallest released reproducer is:

```python
DayCount(DayCountTypes.ACT_365L).year_frac(
    Date(1, 12, 2023),
    Date(1, 3, 2024),
    freq_type=FrequencyTypes.ANNUAL,
)
```

FinancePy **1.0.1**, the latest distribution available from PyPI at the time
of this audit, raises:

```text
AttributeError: 'NoneType' object has no attribute 'excel_dt'
```

Supplying `dt3=dt2` returns the expected full-period result:

```text
(0.24863387978142076, 91.0, 366)
```

The same defect is present at upstream commit
`2b9227fea9d832c4033421d6cd53a54316414fca`, whose project metadata reports
version 1.1.2.

## Why the fallback is `dt2`

For an ordinary two-date calculation, `dt2` is the period end. For an accrued
fraction, a separately supplied `dt3` remains the reference/coupon-period end.
This is consistent with the method's own API documentation and preserves the
existing three-date semantics.

For annual Act/365L, the denominator is 366 when February 29 lies in the
relevant period and 365 otherwise. OpenGamma Strata likewise determines the
annual denominator using the period end (next coupon date). The independent
control in `reproduce.py` counts 91 actual days and applies a 366 denominator.

## Reproduce the released result

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reproduce.py --expect-released-failure
```

The program exits successfully only if all of these controls hold:

- the ordinary two-date call reproduces the released exception;
- the same interval with `dt3=dt2` returns `91/366`;
- the result agrees with an independent standard-library date calculation;
- an explicit later coupon end still controls the accrued-fraction denominator.

## Correction and validation

The minimal correction assigns `dt2` to `dt3` only when no reference-period
end was supplied. It is submitted as
[FinancePy PR #259](https://github.com/domokane/FinancePy/pull/259), commit
`a93243c4982dc77432d3405d478c34998e0f04a6`.

Local validation:

- focused day-count file: 11 tests passed;
- complete unit suite: 959 tests passed, with four pre-existing LSMC
  `RankWarning` messages;
- restoring the previous `None` handling reproduces the exception;
- explicit `dt3` behaviour is covered separately to prevent a semantic
  regression;
- both official upstream workflows completed successfully after submission.

Bounded GitHub searches for `ACT_365L`, `ACT/365L`, `day_count dt3`, and
`leap denominator` found no prior FinancePy issue or pull request for this
failure. This is not a worldwide novelty or priority guarantee.

The dates are synthetic. This report establishes a library-level day-count
failure; it does not establish use by a financial institution, a customer
loss, or a production deployment.

## Sources

- [FinancePy 1.0.1 on PyPI](https://pypi.org/project/financepy/1.0.1/)
- [Current tagged FinancePy implementation](https://github.com/domokane/FinancePy/blob/V1.1.2/financepy/utils/day_count.py)
- [FinancePy correction PR #259](https://github.com/domokane/FinancePy/pull/259)
- [OpenGamma Strata Act/365L documentation](https://strata.opengamma.io/day_counts/)
- [OpenGamma Strata implementation](https://github.com/OpenGamma/Strata/blob/main/modules/basics/src/main/java/com/opengamma/strata/basics/date/StandardDayCounts.java)
- [ISDA response reproducing the Act/365L period-end definition](https://www.isda.org/a/HAxgE/ISDA-Response-to-ROC-CDEv3-Consultation-103122.pdf)

The reproducer and report are supplied under GPL-3.0-or-later; see `LICENSE`.
