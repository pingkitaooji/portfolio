import random
import time

from .prediction import predict_primer_pair


DEMO_PROFILES = [
    {
        "status": "pass",
        "note": "Demo: balanced GC and primer length",
        "gc_range": (0.3, 0.52),
        "length_range": (18, 25),
        "amplicon_range": (80, 220),
        "risk": "pass-borderline",
        "target_score": (0.72, 0.9),
    },
    {
        "status": "fail",
        "note": "Demo: AT-rich primer pair with low predicted usability",
        "gc_range": (0.05, 0.28),
        "length_range": (18, 24),
        "amplicon_range": (70, 180),
        "risk": "at-rich",
        "target_score": (0.0, 0.44),
    },
    {
        "status": "review",
        "note": "Demo: borderline primer pair for review",
        "gc_range": (0.24, 0.46),
        "length_range": (18, 26),
        "amplicon_range": (120, 320),
        "risk": "borderline",
        "target_score": (0.45, 0.71),
    },
    {
        "status": "untested",
        "note": "Demo: exploratory primer pair",
        "gc_range": (0.18, 0.68),
        "length_range": (18, 27),
        "amplicon_range": (90, 360),
        "risk": "balanced",
        "target_score": (0.1, 0.9),
    },
]


def create_demo_primer_pair():
    profile = random.choice(DEMO_PROFILES)
    return _create_scored_demo(profile)


def _create_scored_demo(profile, attempts=80):
    low, high = profile["target_score"]
    midpoint = (low + high) / 2
    best_demo = None
    best_distance = float("inf")

    for _attempt in range(attempts):
        demo = _create_demo_candidate(profile)
        score = predict_primer_pair(demo["forward"], demo["reverse"], demo["ampliconLength"])["prediction"][
            "probability_usable"
        ]
        demo["expectedScore"] = score
        if low <= score <= high:
            return demo

        distance = abs(score - midpoint)
        if distance < best_distance:
            best_demo = demo
            best_distance = distance

    return best_demo


def _create_demo_candidate(profile):
    f_length = random.randint(*profile["length_range"])
    r_length = random.randint(*profile["length_range"])
    f_gc = random.uniform(*profile["gc_range"])
    r_gc = random.uniform(*profile["gc_range"])

    forward = _generate_primer(f_length, f_gc)
    reverse = _generate_primer(r_length, r_gc)

    if profile["risk"] == "dimer":
        shared_stem = _reverse_complement(forward[-random.randint(4, 6) :])
        reverse = f"{reverse[: max(0, len(reverse) - len(shared_stem))]}{shared_stem}"
    elif profile["risk"] == "pass-borderline":
        if random.random() < 0.6:
            forward = _soften_gc_clamp(forward)
    elif profile["risk"] == "at-rich":
        forward = _soften_gc_clamp(forward)
        reverse = _soften_gc_clamp(reverse)
    elif profile["risk"] == "borderline":
        if random.random() < 0.5:
            forward = _soften_gc_clamp(forward)
        else:
            reverse = f"{reverse[: max(0, len(reverse) - 4)]}{_reverse_complement(forward[-4:])}"
    elif profile["risk"] == "gc-rich":
        forward = f"{forward[:-3]}{random.choice(['GCG', 'CCG', 'GGC'])}"
        reverse = f"{reverse[:-3]}{random.choice(['CGC', 'GCC', 'CGG'])}"

    return {
        "assayId": f"PRIMER-DEMO-{str(int(time.time() * 1000))[-6:]}-{random.randint(10, 99)}",
        "ampliconLength": random.randint(*profile["amplicon_range"]),
        "forward": forward,
        "reverse": reverse,
        "status": profile["status"],
        "note": profile["note"],
    }


def _generate_primer(length, target_gc):
    for _attempt in range(40):
        sequence = "".join(_random_base(target_gc) for _index in range(length - 1))
        sequence = f"{sequence}{random.choice(['G', 'C'])}"
        if not _has_long_run(sequence):
            return sequence
    return "".join(_random_base(target_gc) for _index in range(length))


def _random_base(target_gc):
    if random.random() < target_gc:
        return random.choice(["G", "C"])
    return random.choice(["A", "T"])


def _has_long_run(sequence, limit=4):
    run = 0
    previous = ""
    for base in sequence:
        run = run + 1 if base == previous else 1
        previous = base
        if run > limit:
            return True
    return False


def _reverse_complement(sequence):
    pairs = {"A": "T", "C": "G", "G": "C", "T": "A"}
    return "".join(pairs[base] for base in reversed(sequence))


def _soften_gc_clamp(sequence):
    return f"{sequence[:-3]}{random.choice(['ATA', 'TAT', 'AAT', 'TTA'])}"
