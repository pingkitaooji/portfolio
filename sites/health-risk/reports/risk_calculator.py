from .models import RiskAssessment
from .snp_parser import inspect_snp_file


RISK_RULES = {
    "cardiovascular": {
        "name": "心血管風險",
        "snps": {
            "rs1333049": {"risk_genotypes": ["GG", "CG"], "weight": 18},
            "rs4977574": {"risk_genotypes": ["GG", "AG"], "weight": 14},
            "rs602633": {"risk_genotypes": ["CC", "CT"], "weight": 10},
        },
    },
    "type2_diabetes": {
        "name": "第二型糖尿病風險",
        "snps": {
            "rs7903146": {"risk_genotypes": ["TT", "CT"], "weight": 20},
            "rs1801282": {"risk_genotypes": ["CC", "CG"], "weight": 12},
            "rs5219": {"risk_genotypes": ["TT", "CT"], "weight": 10},
        },
    },
    "drug_metabolism": {
        "name": "藥物代謝注意事項",
        "snps": {
            "rs4244285": {"risk_genotypes": ["AA", "AG"], "weight": 22},
            "rs4986893": {"risk_genotypes": ["AA", "AG"], "weight": 16},
            "rs1799853": {"risk_genotypes": ["TT", "CT"], "weight": 12},
        },
    },
}


def calculate_and_store_risk(snp_record):
    # Persist calculated risk so reports can reuse the same deterministic result.
    results = calculate_risk_results(snp_record)
    assessment, _ = RiskAssessment.objects.update_or_create(
        snp_record=snp_record,
        defaults={
            "overall_risk_score": overall_score(results),
            "risk_results": results,
        },
    )
    return assessment


def calculate_risk_results(snp_record):
    # Map parsed genotypes onto a small demo rule set for portfolio purposes.
    inspection = inspect_snp_file(snp_record.data_file)
    genotype_map = {
        row["snp_id"].lower(): normalize_genotype(row.get("genotype", ""))
        for row in inspection["snp_rows"]
    }

    results = []
    for rule_key, rule in RISK_RULES.items():
        matched = []
        score = 0
        for snp_id, snp_rule in rule["snps"].items():
            genotype = genotype_map.get(snp_id.lower(), "")
            if not genotype:
                continue
            is_risk = genotype in snp_rule["risk_genotypes"]
            if is_risk:
                score += snp_rule["weight"]
            matched.append(
                {
                    "snp_id": snp_id,
                    "genotype": genotype,
                    "effect": "risk" if is_risk else "neutral",
                    "weight": snp_rule["weight"] if is_risk else 0,
                }
            )

        results.append(
            {
                "key": rule_key,
                "name": rule["name"],
                "score": min(score, 100),
                "level": risk_level(score),
                "note": risk_note(score, matched),
                "matched_snps": matched,
            }
        )
    return results


def normalize_genotype(value):
    return "".join(sorted(str(value).strip().upper().replace("/", "").replace("|", "")))


def risk_level(score):
    if score >= 35:
        return "高"
    if score >= 18:
        return "中"
    return "低"


def risk_note(score, matched):
    risk_hits = [item for item in matched if item["effect"] == "risk"]
    if score >= 35:
        return f"偵測到 {len(risk_hits)} 個模擬風險位點，建議進一步諮詢。"
    if score >= 18:
        return f"偵測到 {len(risk_hits)} 個模擬風險位點，建議搭配病史評估。"
    return "目前未見明顯升高訊號。"


def overall_score(results):
    if not results:
        return 0
    return round(sum(item["score"] for item in results) / len(results))
