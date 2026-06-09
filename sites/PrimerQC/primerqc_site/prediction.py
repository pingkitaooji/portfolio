import math
import re


DEMO_MODEL_VERSION = "primerqc-python-v0.4.0"


def predict_primer_pair(forward, reverse, amplicon_length):
    """Score one primer pair using Python feature extraction and demo model weights."""
    forward = sanitize_sequence(forward)
    reverse = sanitize_sequence(reverse)
    amplicon_length = _validate_amplicon_length(amplicon_length)
    _validate_inputs(forward, reverse)

    f = _primer_features(forward)
    r = _primer_features(reverse)
    tm_diff = abs(f["tm_celsius"] - r["tm_celsius"])
    hetero_dimer = _complement_score(forward, reverse)
    three_prime_dimer = _complement_score(forward[-8:], reverse[-8:])
    avg_gc = (f["gc_percent"] + r["gc_percent"]) / 2
    avg_tm = (f["tm_celsius"] + r["tm_celsius"]) / 2
    max_self = max(f["self_complementarity"], r["self_complementarity"])
    max_hairpin = max(f["hairpin_proxy"], r["hairpin_proxy"])
    max_run_value = max(f["max_homopolymer"], r["max_homopolymer"])

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

    probability = _round(_sigmoid(logit), 3)
    label = "PASS" if probability >= 0.72 else "REVIEW" if probability >= 0.45 else "FAIL"
    reasons = _prediction_reasons(tm_diff, hetero_dimer, three_prime_dimer, avg_gc, max_run_value, max_hairpin)

    return {
        "model_version": DEMO_MODEL_VERSION,
        "model_note": "Prediction is calculated by Django/Python from Primer3-style proxy features. The saved benchmark model can be wired in after adding sklearn/joblib runtime dependencies.",
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


def _primer_features(sequence):
    return {
        "sequence": sequence,
        "length": len(sequence),
        "gc_percent": _round(_gc_percent(sequence), 1),
        "tm_celsius": _round(_estimate_tm(sequence), 2),
        "three_prime_gc_percent": _round(_three_prime_gc(sequence), 1),
        "max_homopolymer": _max_run(sequence),
        "self_complementarity": _complement_score(sequence, sequence),
        "hairpin_proxy": _hairpin_proxy(sequence),
    }


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
