DISCLAIMER = (
    "本報告為教學與作品集展示用之模擬結果，僅根據範例 SNP 資料與固定規則產生，"
    "不等同於臨床診斷、治療建議或用藥指示。實際醫療決策仍需由合格醫療專業人員，"
    "結合病史、家族史、檢驗數據、生活型態與臨床評估後判斷。"
)


ADVICE_RULES = {
    "cardiovascular": {
        "高": "建議安排心血管風險評估，追蹤血壓、血脂與血糖，並由醫師評估是否需要進一步檢查。",
        "中": "建議定期追蹤血壓與血脂，維持規律運動、均衡飲食，並與醫療人員討論個人風險因子。",
        "低": "目前模擬 SNP 訊號未顯示明顯升高，仍建議維持健康生活型態並依例行健檢追蹤。",
    },
    "type2_diabetes": {
        "高": "建議追蹤空腹血糖與 HbA1c，並由醫療人員評估飲食、體重管理與後續檢查需求。",
        "中": "建議注意體重、腰圍與飲食型態，定期追蹤血糖並搭配個人病史進行評估。",
        "低": "目前模擬 SNP 訊號未顯示明顯升高，仍建議維持規律運動與均衡飲食。",
    },
    "drug_metabolism": {
        "高": "若未來需要使用相關藥物，建議主動告知醫師此模擬結果，並由醫師評估是否需要藥物基因檢測或劑量調整。",
        "中": "建議用藥前與醫療人員討論藥物代謝差異，避免自行調整藥物劑量。",
        "低": "目前模擬 SNP 訊號未顯示明顯代謝風險，仍應依醫囑用藥並留意不良反應。",
    },
}

DEFAULT_ADVICE = "建議將本結果視為初步風險提示，並交由合格醫療專業人員搭配臨床資料解讀。"


PDF_ADVICE_RULES = {
    "cardiovascular": {
        "高": "Discuss cardiovascular follow-up with a clinician; monitor blood pressure, lipids, and glucose.",
        "中": "Review lifestyle and routine cardiovascular screening with clinical history.",
        "低": "Maintain routine health checks and heart-healthy habits.",
    },
    "type2_diabetes": {
        "高": "Consider fasting glucose and HbA1c follow-up with clinician review.",
        "中": "Monitor weight, diet, and glucose trends with clinical context.",
        "低": "Maintain exercise, balanced diet, and routine screening.",
    },
    "drug_metabolism": {
        "高": "Tell clinicians before related medications; pharmacogenetic review may be considered.",
        "中": "Discuss medication metabolism differences before changing any medication.",
        "低": "Use medication as prescribed and monitor adverse reactions.",
    },
}

PDF_DISCLAIMER = (
    "Disclaimer: This is a simulated demo report for portfolio and education only. "
    "It is not a diagnosis, treatment recommendation, or medication instruction. "
    "Clinical decisions require qualified professional review."
)


def build_medical_advice(risk_results):
    advice = []
    for risk in risk_results:
        risk_key = risk.get("key", "")
        level = risk.get("level", "")
        recommendation = ADVICE_RULES.get(risk_key, {}).get(level, DEFAULT_ADVICE)
        pdf_recommendation = PDF_ADVICE_RULES.get(risk_key, {}).get(level, "Review with a qualified clinician.")
        advice.append(
            {
                "risk_key": risk_key,
                "risk_name": risk.get("name", "風險項目"),
                "level": level,
                "recommendation": recommendation,
                "pdf_recommendation": pdf_recommendation,
            }
        )
    return advice
