"""Customer-level Welch intervals. Currency sums/variance never use binary floats."""

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from fractions import Fraction


def decimal(value, places=6):
    with localcontext() as ctx:
        ctx.prec = 70
        value = Fraction(value)
        return format(
            Decimal(value.numerator) / Decimal(value.denominator), f".{places}f"
        )


def variance(values):
    n = len(values)
    if n < 2:
        return None
    return (sum(v * v for v in values) - sum(values) ** 2 / n) / (n - 1)


def welch_interval(treatment, control, confidence_bps=9500, comparisons=1):
    """Exact rational variance; SciPy handles only dimensionless t quantiles.

    Zero observed variance cannot establish a zero-width population interval.
    Sample-size, timing, coverage and contamination gates belong to the caller.
    """
    treatment, control = [list(map(Fraction, v)) for v in (treatment, control)]
    if min(len(treatment), len(control)) < 2:
        return None
    vx, vy = variance(treatment) / len(treatment), variance(control) / len(control)
    se2 = vx + vy
    if not se2:
        return None
    df = se2**2 / (vx**2 / (len(treatment) - 1) + vy**2 / (len(control) - 1))
    alpha = Fraction(10000 - confidence_bps, 10000 * comparisons)
    from scipy.stats import t

    critical = Decimal(str(t.ppf(float(1 - alpha / 2), float(df))))
    difference = sum(treatment) / len(treatment) - sum(control) / len(control)
    with localcontext() as ctx:
        ctx.prec = 70
        se = (Decimal(se2.numerator) / Decimal(se2.denominator)).sqrt()
        center = Decimal(difference.numerator) / Decimal(difference.denominator)
        half = critical * se
        return {
            "lower_minor": str((center - half).to_integral_value(rounding=ROUND_FLOOR)),
            "upper_minor": str(
                (center + half).to_integral_value(rounding=ROUND_CEILING)
            ),
            "standard_error_minor": str(se),
            "degrees_of_freedom": decimal(df),
            "family_confidence_bps": confidence_bps,
            "comparisons": comparisons,
            "method": "welch_bonferroni_v1",
        }
