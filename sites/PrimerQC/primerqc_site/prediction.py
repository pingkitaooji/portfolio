import math
import re
from functools import lru_cache
from pathlib import Path

try:
    import joblib
    import pandas as pd
except ImportError:
    joblib = None
    pd = None

try:
    import primer3
except ImportError:
    primer3 = None


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "modlebuild" / "best_primer_model.joblib"
MODEL_VERSION = "primerqc-trained-model-v1.0.0"
FALLBACK_MODEL_VERSION = "primerqc-primer3-py-fallback-v0.5.0"
MODEL_FEATURE_COLUMNS = [
    "F_gc_content",
    "F_gc_clamp",
    "R_gc_content",
    "R_gc_clamp",
    "F_tm",
    "R_tm",
    "tm_diff",
    "F_haripin",
    "R_haripin",
    "F_homodimer",
    "R_homodimer",
    "heterodimer",
    "end_stability",
    "F_repeat",
    "R_repeat",
    "F_len",
    "R_len",
    "len_diff",
    "avg_gc_content",
    "avg_tm",
    "max_hairpin",
    "max_homodimer",
    "max_repeat",
]


def predict_primer_pair(forward, reverse, amplicon_length):
    """Score one primer pair using Python feature extraction and demo model weights."""
    forward = sanitize_sequence(forward)
    reverse = sanitize_sequence(reverse)
    amplicon_length = _validate_amplicon_length(amplicon_length)
    _validate_inputs(forward, reverse)

    f = _primer_features(forward)
    r = _primer_features(reverse)
    tm_diff = abs(f["tm_celsius"] - r["tm_celsius"])
    pair_thermo = _pair_thermo_features(forward, reverse)
    hetero_dimer = pair_thermo["hetero_dimer_score"]
    three_prime_dimer = pair_thermo["three_prime_dimer_score"]
    avg_gc = (f["gc_percent"] + r["gc_percent"]) / 2
    avg_tm = (f["tm_celsius"] + r["tm_celsius"]) / 2
    max_self = max(f["self_complementarity"], r["self_complementarity"])
    max_hairpin = max(f["hairpin_proxy"], r["hairpin_proxy"])
    max_run_value = max(f["max_homopolymer"], r["max_homopolymer"])
    model_features = _model_feature_row(forward, reverse, f, r, pair_thermo)
    model_result = _predict_with_trained_model(model_features)

    if model_result["available"]:
        probability = model_result["probability_usable"]
        model_version = MODEL_VERSION
    else:
        probability = _fallback_probability(
            f,
            r,
            avg_gc,
            avg_tm,
            tm_diff,
            hetero_dimer,
            three_prime_dimer,
            max_self,
            max_hairpin,
            max_run_value,
            amplicon_length,
        )
        model_version = FALLBACK_MODEL_VERSION

    label = "PASS" if probability >= 0.72 else "REVIEW" if probability >= 0.45 else "FAIL"
    reasons = _prediction_reasons(tm_diff, hetero_dimer, three_prime_dimer, avg_gc, max_run_value, max_hairpin)

    return {
        "model_version": model_version,
        "model_note": "Prediction uses the trained best_primer_model.joblib artifact from the curated primer dataset when runtime dependencies are available; otherwise it falls back to primer3-py scoring logic.",
        "model": model_result,
        "input": {
            "forward_primer": forward,
            "reverse_primer": reverse,
            "amplicon_length_bp": amplicon_length,
        },
        "features": {
            "forward": f,
            "reverse": r,
            "pair": {
                "tm_difference_celsius": _round(tm_diff, 2),
                "average_gc_percent": _round(avg_gc, 1),
                "average_tm_celsius": _round(avg_tm, 2),
                "hetero_dimer_proxy": hetero_dimer,
                "three_prime_dimer_proxy": three_prime_dimer,
                "max_self_complementarity": max_self,
                "max_hairpin_proxy": max_hairpin,
                "max_homopolymer": max_run_value,
                "thermodynamics": pair_thermo,
                "model_input": model_features,
            },
        },
        "prediction": {
            "probability_usable": probability,
            "label": label,
            "reasons": reasons,
        },
    }


def sanitize_sequence(value):
    return re.sub(r"[^ACGT]", "", str(value or "").upper())


def _validate_inputs(forward, reverse):
    if len(forward) < 12 or len(reverse) < 12:
        raise ValueError("Forward / reverse primer 至少需要 12 bp。")
    if len(forward) > 35 or len(reverse) > 35:
        raise ValueError("Demo 模型建議輸入 35 bp 以內的 primer。")


def _validate_amplicon_length(value):
    try:
        length = int(value)
    except (TypeError, ValueError):
        raise ValueError("Amplicon length 需要是整數。") from None
    if length < 40 or length > 600:
        raise ValueError("Amplicon length 建議介於 40-600 bp。")
    return length


def _gc_percent(sequence):
    if not sequence:
        return 0
    gc = len([base for base in sequence if base in {"G", "C"}])
    return (gc / len(sequence)) * 100


def _estimate_tm(sequence):
    if not sequence:
        return 0
    if primer3 is not None:
        return primer3.calc_tm(sequence)
    gc = _gc_percent(sequence)
    length = len(sequence)
    if length < 14:
        a = sequence.count("A")
        t = sequence.count("T")
        g = sequence.count("G")
        c = sequence.count("C")
        return 2 * (a + t) + 4 * (g + c)
    return 64.9 + 41 * ((gc / 100) * length - 16.4) / length


def _reverse_complement(sequence):
    pair = {"A": "T", "T": "A", "C": "G", "G": "C"}
    return "".join(pair.get(base, "N") for base in reversed(sequence))


def _max_run(sequence):
    best = 0
    run = 0
    previous = ""
    for base in sequence:
        run = run + 1 if base == previous else 1
        previous = base
        best = max(best, run)
    return best


def _three_prime_gc(sequence):
    return _gc_percent(sequence[-5:])


def _gc_clamp(sequence):
    return sum(1 for base in sequence[-5:] if base in {"G", "C"})


def _complement_score(a, b):
    # Approximate dimer risk by finding the longest contiguous complement match.
    rc = _reverse_complement(b)
    best = 0
    for offset in range(-len(rc) + 1, len(a)):
        contiguous = 0
        local_best = 0
        for i, base in enumerate(a):
            j = i - offset
            if 0 <= j < len(rc) and base == rc[j]:
                contiguous += 1
                local_best = max(local_best, contiguous)
            else:
                contiguous = 0
        best = max(best, local_best)
    return best


def _hairpin_proxy(sequence):
    # This lightweight proxy searches for short reverse-complement stems.
    best = 0
    for stem in range(4, min(8, len(sequence) // 2) + 1):
        for i in range(0, len(sequence) - stem * 2 - 2):
            left = sequence[i : i + stem]
            for loop in range(3, 9):
                right_start = i + stem + loop
                right = sequence[right_start : right_start + stem]
                if len(right) == stem and left == _reverse_complement(right):
                    best = max(best, stem)
    return best


def _thermo_result_to_dict(result):
    return {
        "structure_found": bool(result.structure_found),
        "tm_celsius": _round(result.tm, 2),
        "dg_kcal_per_mol": _round(result.dg / 1000, 2),
        "dh_kcal_per_mol": _round(result.dh / 1000, 2),
        "ds_cal_per_k_mol": _round(result.ds, 2),
    }


def _thermo_risk_score(result):
    if not result.structure_found:
        return 0
    return _round(abs(min(result.dg, 0)) / 1000, 2)


def _primer3_thermo(sequence):
    if primer3 is None:
        return None
    hairpin = primer3.calc_hairpin(sequence)
    homodimer = primer3.calc_homodimer(sequence)
    return {
        "source": "primer3-py",
        "hairpin": _thermo_result_to_dict(hairpin),
        "homodimer": _thermo_result_to_dict(homodimer),
        "hairpin_score": _thermo_risk_score(hairpin),
        "homodimer_score": _thermo_risk_score(homodimer),
    }


def _pair_thermo_features(forward, reverse):
    if primer3 is None:
        return {
            "source": "python-proxy-fallback",
            "hetero_dimer_score": _complement_score(forward, reverse),
            "three_prime_dimer_score": _complement_score(forward[-8:], reverse[-8:]),
            "end_stability_score": _complement_score(forward[-5:], reverse[-5:]),
        }

    heterodimer = primer3.calc_heterodimer(forward, reverse)
    three_prime_dimer = primer3.calc_heterodimer(forward[-8:], reverse[-8:])
    end_stability = primer3.calc_end_stability(forward, reverse)
    return {
        "source": "primer3-py",
        "heterodimer": _thermo_result_to_dict(heterodimer),
        "three_prime_heterodimer": _thermo_result_to_dict(three_prime_dimer),
        "end_stability": _thermo_result_to_dict(end_stability),
        "hetero_dimer_score": _thermo_risk_score(heterodimer),
        "three_prime_dimer_score": _thermo_risk_score(three_prime_dimer),
        "end_stability_score": _thermo_risk_score(end_stability),
    }


def _primer_features(sequence):
    thermo = _primer3_thermo(sequence)
    if thermo is None:
        hairpin_score = _hairpin_proxy(sequence)
        self_score = _complement_score(sequence, sequence)
        source = "python-proxy-fallback"
    else:
        hairpin_score = thermo["hairpin_score"]
        self_score = thermo["homodimer_score"]
        source = "primer3-py"

    return {
        "sequence": sequence,
        "length": len(sequence),
        "gc_percent": _round(_gc_percent(sequence), 1),
        "tm_celsius": _round(_estimate_tm(sequence), 2),
        "three_prime_gc_percent": _round(_three_prime_gc(sequence), 1),
        "gc_clamp": _gc_clamp(sequence),
        "max_homopolymer": _max_run(sequence),
        "self_complementarity": self_score,
        "hairpin_proxy": hairpin_score,
        "thermo_source": source,
        "thermodynamics": thermo,
    }


@lru_cache(maxsize=1)
def _load_trained_model():
    if joblib is None or pd is None:
        return None
    if not MODEL_PATH.exists():
        return None
    try:
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def _model_feature_row(forward, reverse, f, r, pair_thermo):
    tm_diff = abs(f["tm_celsius"] - r["tm_celsius"])
    avg_gc = (f["gc_percent"] + r["gc_percent"]) / 2
    avg_tm = (f["tm_celsius"] + r["tm_celsius"]) / 2
    max_hairpin = max(f["hairpin_proxy"], r["hairpin_proxy"])
    max_homodimer = max(f["self_complementarity"], r["self_complementarity"])
    max_repeat = max(f["max_homopolymer"], r["max_homopolymer"])

    return {
        "F_gc_content": f["gc_percent"],
        "F_gc_clamp": f["gc_clamp"],
        "R_gc_content": r["gc_percent"],
        "R_gc_clamp": r["gc_clamp"],
        "F_tm": f["tm_celsius"],
        "R_tm": r["tm_celsius"],
        "tm_diff": _round(tm_diff, 2),
        "F_haripin": f["hairpin_proxy"],
        "R_haripin": r["hairpin_proxy"],
        "F_homodimer": f["self_complementarity"],
        "R_homodimer": r["self_complementarity"],
        "heterodimer": pair_thermo["hetero_dimer_score"],
        "end_stability": pair_thermo["end_stability_score"],
        "F_repeat": f["max_homopolymer"],
        "R_repeat": r["max_homopolymer"],
        "F_len": len(forward),
        "R_len": len(reverse),
        "len_diff": abs(len(forward) - len(reverse)),
        "avg_gc_content": _round(avg_gc, 1),
        "avg_tm": _round(avg_tm, 2),
        "max_hairpin": max_hairpin,
        "max_homodimer": max_homodimer,
        "max_repeat": max_repeat,
    }


def _predict_with_trained_model(model_features):
    artifact = _load_trained_model()
    if artifact is None:
        return {
            "available": False,
            "source": "fallback",
            "artifact": str(MODEL_PATH),
            "reason": "best_primer_model.joblib or runtime dependencies are unavailable.",
        }

    model = artifact["model"]
    feature_columns = artifact.get("feature_columns", MODEL_FEATURE_COLUMNS)
    row = {column: model_features[column] for column in feature_columns}
    frame = pd.DataFrame([row], columns=feature_columns)

    if hasattr(model, "predict_proba"):
        probability = float(model.predict_proba(frame)[0][1])
    elif hasattr(model, "decision_function"):
        score = float(model.decision_function(frame)[0])
        probability = _sigmoid(score)
    else:
        probability = float(model.predict(frame)[0])

    return {
        "available": True,
        "source": "best_primer_model.joblib",
        "display_name": "Logistic Regression",
        "artifact": str(MODEL_PATH),
        "feature_columns": feature_columns,
        "probability_usable": _round(probability, 3),
    }


def _fallback_probability(
    f,
    r,
    avg_gc,
    avg_tm,
    tm_diff,
    hetero_dimer,
    three_prime_dimer,
    max_self,
    max_hairpin,
    max_run_value,
    amplicon_length,
):
    logit = 2.1
    logit -= _penalty_window(f["length"], 18, 25, 0.22)
    logit -= _penalty_window(r["length"], 18, 25, 0.22)
    logit -= _penalty_window(avg_gc, 40, 60, 0.035)
    logit -= _penalty_window(avg_tm, 58, 65, 0.08)
    logit -= max(0, tm_diff - 2.5) * 0.32
    logit -= max(0, hetero_dimer - 5) * 0.36
    logit -= max(0, three_prime_dimer - 3) * 0.52
    logit -= max(0, max_self - 5) * 0.22
    logit -= max(0, max_hairpin - 4) * 0.42
    logit -= max(0, max_run_value - 4) * 0.35
    logit -= _penalty_window(amplicon_length, 70, 250, 0.006)
    return _round(_sigmoid(logit), 3)


def _prediction_reasons(tm_diff, hetero_dimer, three_prime_dimer, avg_gc, max_run_value, max_hairpin):
    # Return human-readable drivers for the final PASS / REVIEW / FAIL label.
    reasons = []
    if tm_diff > 2.5:
        reasons.append("Forward / reverse Tm difference is high")
    if hetero_dimer > 5:
        reasons.append("Pair complementarity suggests dimer risk")
    if three_prime_dimer > 3:
        reasons.append("3-prime complementarity is elevated")
    if avg_gc < 40 or avg_gc > 60:
        reasons.append("Average GC is outside the preferred window")
    if max_run_value > 4:
        reasons.append("Homopolymer run may reduce specificity")
    if max_hairpin > 4:
        reasons.append("Hairpin proxy score is high")
    if not reasons:
        reasons.append("Thermal balance and structural proxy features are within demo limits")
    return reasons


def _penalty_window(value, min_value, max_value, weight):
    if value < min_value:
        return (min_value - value) * weight
    if value > max_value:
        return (value - max_value) * weight
    return 0


def _sigmoid(x):
    return 1 / (1 + math.exp(-x))


def _round(value, digits=2):
    return round(float(value), digits)
