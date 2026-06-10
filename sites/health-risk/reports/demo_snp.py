import random
from datetime import datetime

from django.core.files.base import ContentFile

from .models import SNPRecord
from .risk_calculator import RISK_RULES, calculate_and_store_risk
from .snp_parser import update_snp_checks


GENOTYPES = ["AA", "AC", "AG", "AT", "CC", "CG", "CT", "GG", "GT", "TT"]


def create_demo_snp_record(user=None):
    nonce = random.randint(1000, 9999)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    record = SNPRecord(created_by=user)
    content = build_random_demo_snp_csv()
    record.data_file.save(
        f"demo_snp_{timestamp}_{nonce}.csv",
        ContentFile(content.encode("utf-8")),
        save=True,
    )
    update_snp_checks(record)
    calculate_and_store_risk(record)
    return record


def build_random_demo_snp_csv(extra_count=18):
    rows = [
        ["rsid", "chromosome", "position", "genotype"],
        ["PC", "control", "0", "PASS"],
        ["NC", "control", "0", "PASS"],
    ]
    rows.extend(random_risk_rule_rows())
    rows.extend(random_background_rows(extra_count))
    return "\n".join(",".join(map(str, row)) for row in rows) + "\n"


def random_risk_rule_rows():
    rows = []
    for rule in RISK_RULES.values():
        for snp_id, config in rule["snps"].items():
            genotype = random_rule_genotype(config["risk_genotypes"])
            rows.append(
                [
                    snp_id,
                    random.randint(1, 22),
                    random.randint(1_000_000, 240_000_000),
                    genotype,
                ]
            )
    random.shuffle(rows)
    return rows


def random_rule_genotype(risk_genotypes):
    if random.random() < 0.55:
        return random.choice(risk_genotypes)
    neutral = [genotype for genotype in GENOTYPES if genotype not in risk_genotypes]
    return random.choice(neutral)


def random_background_rows(count):
    used = set(RISK_RULES_SNP_IDS)
    rows = []
    while len(rows) < count:
        snp_id = f"rs{random.randint(1_000_000, 99_999_999)}"
        if snp_id in used:
            continue
        used.add(snp_id)
        rows.append(
            [
                snp_id,
                random.randint(1, 22),
                random.randint(1_000_000, 240_000_000),
                random.choice(GENOTYPES),
            ]
        )
    return rows


RISK_RULES_SNP_IDS = {
    snp_id
    for rule in RISK_RULES.values()
    for snp_id in rule["snps"].keys()
}
