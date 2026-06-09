import math
import statistics


CYCLE_COUNT = 40
CYCLES = list(range(1, CYCLE_COUNT + 1))


def analyze_signals(signals):
    """Run the full qPCR Cq calling pipeline for one 40-cycle signal."""
    values = _validate_signals(signals)
    fit = _fit_sigmoid(CYCLES, values)
    cq = _second_derivative_max_cycle(fit)
    ir = ((fit["top"] - fit["bottom"]) * fit["k"]) / 4
    predictions = [_sigmoid(cycle, fit) for cycle in CYCLES]
    r2 = _calculate_r2(values, predictions)
    corrected = [value - fit["bottom"] for value in values]
    residuals = [value - predictions[index] for index, value in enumerate(values)]
    qc = _evaluate_qc(values, fit, r2, cq, ir, residuals)
    reportable_cq = cq if qc["overall"] != "FAIL" and math.isfinite(cq) else None

    return {
        **fit,
        "signals": [_round(value, 4) for value in values],
        "predictions": [_round(value, 4) for value in predictions],
        "corrected": [_round(value, 4) for value in corrected],
        "residuals": [_round(value, 4) for value in residuals],
        "cq": _round(cq, 6),
        "reportableCq": None if reportable_cq is None else _round(reportable_cq, 6),
        "cqMaxSlope": _round(fit["x0"], 6),
        "ir": _round(ir, 6),
        "r2": _round(r2, 6),
        "qc": qc,
        "instrumentOutput": _instrument_output(fit, cq, reportable_cq, ir, r2, qc),
    }


def _validate_signals(signals):
    if not isinstance(signals, list) or len(signals) != CYCLE_COUNT:
        raise ValueError(f"請提供剛好 {CYCLE_COUNT} 個螢光訊號。")
    values = []
    for signal in signals:
        try:
            value = float(signal)
        except (TypeError, ValueError):
            raise ValueError("每一點都需要是 0-100 的數值。") from None
        if not math.isfinite(value) or value < 0 or value > 100:
            raise ValueError("每一點都需要是 0-100 的數值。")
        values.append(value)
    return values


def _fit_sigmoid(x_values, y_values):
    # Use a small bounded coordinate search so the demo stays dependency-free.
    first_window = y_values[:8]
    last_window = y_values[-8:]
    bottom_guess = _percentile(first_window, 0.25)
    top_guess = max(_percentile(last_window, 0.75), bottom_guess + 8)
    half = bottom_guess + (top_guess - bottom_guess) / 2
    x0_guess = _estimate_crossing(x_values, y_values, half) or 24
    slope_guess = _estimate_local_slope(x_values, y_values, x0_guess)
    k_guess = _clamp((4 * max(slope_guess, 0.1)) / max(top_guess - bottom_guess, 1), 0.08, 1.2)

    best = _normalize_params(
        {
            "bottom": bottom_guess,
            "top": top_guess,
            "k": k_guess,
            "x0": x0_guess,
        }
    )
    best_error = _sse(x_values, y_values, best)
    steps = {"bottom": 8, "top": 8, "k": 0.18, "x0": 4}

    for _ in range(26):
        improved = False
        for key in ["bottom", "top", "k", "x0"]:
            for direction in [-1, 1]:
                candidate = _normalize_params({**best, key: best[key] + steps[key] * direction})
                error = _sse(x_values, y_values, candidate)
                if error < best_error:
                    best = candidate
                    best_error = error
                    improved = True
        if not improved:
            steps = {key: value * 0.62 for key, value in steps.items()}

    return {**{key: _round(value, 8) for key, value in best.items()}, "sse": _round(best_error, 8)}


def _normalize_params(params):
    bottom = _clamp(params["bottom"], -10, 95)
    top = _clamp(params["top"], bottom + 1, 120)
    if top <= bottom:
        top = bottom + 1
    return {
        "bottom": bottom,
        "top": top,
        "k": _clamp(params["k"], 0.015, 2.2),
        "x0": _clamp(params["x0"], 1, 40),
    }


def _sigmoid(x, params):
    return params["bottom"] + (params["top"] - params["bottom"]) / (
        1 + math.exp(-params["k"] * (x - params["x0"]))
    )


def _second_derivative_max_cycle(params):
    # For a 4PL sigmoid, the second-derivative peak occurs at this fixed fraction.
    p = (3 - math.sqrt(3)) / 6
    return params["x0"] + math.log(p / (1 - p)) / params["k"]


def _calculate_r2(actual, predicted):
    mean = sum(actual) / len(actual)
    total = sum((value - mean) ** 2 for value in actual)
    residual = sum((value - predicted[index]) ** 2 for index, value in enumerate(actual))
    if total == 0:
        return 0
    return _clamp(1 - residual / total, -1, 1)


def _sse(x_values, y_values, params):
    return sum((value - _sigmoid(x_values[index], params)) ** 2 for index, value in enumerate(y_values))


def _estimate_crossing(x_values, y_values, target):
    for index in range(1, len(y_values)):
        previous = y_values[index - 1]
        current = y_values[index]
        if (previous <= target <= current) or (previous >= target >= current):
            span = current - previous
            if span == 0:
                return x_values[index]
            ratio = (target - previous) / span
            return x_values[index - 1] + ratio * (x_values[index] - x_values[index - 1])
    return None


def _estimate_local_slope(x_values, y_values, center):
    index = int(_clamp(round(center) - 1, 1, len(y_values) - 2))
    return max(0.01, (y_values[index + 1] - y_values[index - 1]) / (x_values[index + 1] - x_values[index - 1]))


def _percentile(values, p):
    sorted_values = sorted(values)
    index = _clamp((len(sorted_values) - 1) * p, 0, len(sorted_values) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (index - lower)


def _evaluate_qc(signals, fit, r2, cq, ir, residuals):
    # QC checks mimic the kind of guards an instrument-side caller would need.
    amplitude = fit["top"] - fit["bottom"]
    baseline_noise = statistics.pstdev(signals[:10])
    residual_rmse = math.sqrt(sum(value**2 for value in residuals) / len(residuals))
    plateau_delta = abs(signals[-1] - signals[-5])
    saturated_points = len([value for value in signals if value >= 98])
    checks = [
        _qc_check("amplification", "Amplification signal", f"{_round(amplitude, 2):.2f} RFU", "PASS" if amplitude >= 35 else "WARN" if amplitude >= 18 else "FAIL"),
        _qc_check("r2", "Fit quality R²", f"{_round(r2, 4):.4f}", "PASS" if r2 >= 0.985 else "WARN" if r2 >= 0.94 else "FAIL"),
        _qc_check("noise", "Baseline noise", f"{_round(baseline_noise, 2):.2f} RFU", "PASS" if baseline_noise <= 3 else "WARN" if baseline_noise <= 6 else "FAIL"),
        _qc_check("cq_range", "Cq range", f"{_round(cq, 2):.2f}" if math.isfinite(cq) else "N/A", "PASS" if math.isfinite(cq) and 8 <= cq <= 36 else "WARN" if math.isfinite(cq) and cq <= 39 else "FAIL"),
        _qc_check("plateau", "Plateau stability", f"{_round(plateau_delta, 2):.2f} RFU", "PASS" if plateau_delta <= 4.5 else "WARN" if plateau_delta <= 8 else "FAIL"),
        _qc_check("saturation", "Saturation guard", f"{saturated_points} points", "PASS" if saturated_points <= 2 else "WARN" if saturated_points <= 5 else "FAIL"),
        _qc_check("ir", "Initial rate / max slope", f"{_round(ir, 3):.3f}", "PASS" if ir >= 3 else "WARN" if ir >= 1.2 else "FAIL"),
        _qc_check("rmse", "Residual RMSE", f"{_round(residual_rmse, 2):.2f} RFU", "PASS" if residual_rmse <= 4 else "WARN" if residual_rmse <= 7 else "FAIL"),
    ]
    has_fail = any(check["status"] == "FAIL" for check in checks)
    has_warn = any(check["status"] == "WARN" for check in checks)
    return {
        "overall": "FAIL" if has_fail else "WARN" if has_warn else "PASS",
        "confidence": "Low" if has_fail else "Medium" if has_warn else "High",
        "checks": checks,
    }


def _qc_check(key, name, value, status):
    return {"key": key, "name": name, "value": value, "status": status}


def _instrument_output(fit, cq, reportable_cq, ir, r2, qc):
    return {
        "sample_id": "DEMO-QPCR-001",
        "algorithm": "Python 4PL sigmoid bounded-refinement",
        "algorithm_version": "cqcalling-python-v0.3.0",
        "cycle_count": 40,
        "input_range": "0-100 RFU",
        "cq_value": None if reportable_cq is None else _round(reportable_cq, 3),
        "raw_cq_estimate": _round(cq, 3),
        "cq_method": "second_derivative_maximum",
        "inflection_cycle": _round(fit["x0"], 3),
        "ir": _round(ir, 4),
        "r_squared": _round(r2, 5),
        "qc": qc["overall"],
        "confidence": qc["confidence"],
        "fit_parameters": {
            "bottom": _round(fit["bottom"], 4),
            "top": _round(fit["top"], 4),
            "k": _round(fit["k"], 6),
            "x0": _round(fit["x0"], 4),
        },
        "qc_checks": {check["key"]: check["status"] for check in qc["checks"]},
    }


def _clamp(value, min_value, max_value):
    return min(max_value, max(min_value, value))


def _round(value, digits=2):
    return round(float(value), digits)
