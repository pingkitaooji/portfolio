import json
import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = Path(os.getenv("PRIMERQC_TRAINING_DATA", BASE_DIR / "confidential_training_dataset.csv"))
RESULT_JSON_PATH = BASE_DIR / "model_results.json"
RESULT_JS_PATH = BASE_DIR / "model_results.js"
MODEL_PATH = BASE_DIR / "best_primer_model.joblib"
RANDOM_STATE = 42


TARGET = "Panelchip_specificity"
POSITIVE_LABEL = "success"
DROP_COLUMNS = {"Primer_ID", "Name", "F_seq", "R_seq", TARGET}
MODEL_NAMES = {
    "hist_gradient_boosting": "Hist Gradient Boosting",
    "extra_trees": "Extra Trees",
    "logistic_regression": "Logistic Regression",
    "xgboost": "XGBoost",
    "random_forest": "Random Forest",
}


def main():
    df = pd.read_csv(DATA_PATH)
    prepared = add_sequence_features(df)
    feature_columns = [column for column in prepared.columns if column not in DROP_COLUMNS]
    X = prepared[feature_columns]
    y = prepared[TARGET].map({POSITIVE_LABEL: 1, "fail": 0})
    if y.isna().any():
        unknown = sorted(prepared.loc[y.isna(), TARGET].dropna().unique())
        raise ValueError(f"Unknown target labels: {unknown}")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    models = build_models(feature_columns)
    rows = []
    fitted_models = {}

    for model_key, pipeline in models.items():
        pipeline.fit(X_train, y_train)
        fitted_models[model_key] = pipeline
        y_pred = pipeline.predict(X_test)
        y_score = predict_score(pipeline, X_test)
        rows.append(evaluate_model(model_key, y_test, y_pred, y_score))

    rows = sorted(
        rows,
        key=lambda row: (
            row["metrics"]["f1_success"],
            row["metrics"]["roc_auc"],
            row["metrics"]["balanced_accuracy"],
        ),
        reverse=True,
    )
    best_key = rows[0]["model_key"]
    best_model = fitted_models[best_key]
    best_model.fit(X, y)
    joblib.dump({"model": best_model, "feature_columns": feature_columns}, MODEL_PATH)

    result = {
        "dataset": {
            "source_file": "confidential_training_dataset_redacted.csv",
            "row_count": int(len(df)),
            "feature_count": len(feature_columns),
            "train_count": int(len(X_train)),
            "test_count": int(len(X_test)),
            "positive_label": POSITIVE_LABEL,
            "class_distribution": {
                label: int(count)
                for label, count in df[TARGET].value_counts().to_dict().items()
            },
            "split": "stratified train_test_split",
            "test_size": 0.25,
            "random_state": RANDOM_STATE,
        },
        "feature_columns": feature_columns,
        "models": rows,
        "best_model": {
            "model_key": best_key,
            "display_name": MODEL_NAMES[best_key],
            "selection_rule": "highest F1(success), then ROC AUC, then balanced accuracy",
            "artifact": MODEL_PATH.name,
            "top_features": top_features(best_model, feature_columns, best_key),
        },
    }

    RESULT_JSON_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    RESULT_JS_PATH.write_text(
        "window.PRIMER_MODEL_RESULTS = "
        + json.dumps(result, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    print(json.dumps(result["best_model"], ensure_ascii=False, indent=2))
    print(f"Wrote {RESULT_JSON_PATH}")
    print(f"Wrote {RESULT_JS_PATH}")
    print(f"Wrote {MODEL_PATH}")


def add_sequence_features(df):
    output = df.copy()
    output["F_len"] = output["F_seq"].astype(str).str.len()
    output["R_len"] = output["R_seq"].astype(str).str.len()
    output["len_diff"] = (output["F_len"] - output["R_len"]).abs()
    output["avg_gc_content"] = (output["F_gc_content"] + output["R_gc_content"]) / 2
    output["avg_tm"] = (output["F_tm"] + output["R_tm"]) / 2
    output["max_hairpin"] = output[["F_haripin", "R_haripin"]].max(axis=1)
    output["max_homodimer"] = output[["F_homodimer", "R_homodimer"]].max(axis=1)
    output["max_repeat"] = output[["F_repeat", "R_repeat"]].max(axis=1)
    return output


def base_preprocessor(feature_columns, scale=False):
    steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        steps.append(("scaler", StandardScaler()))
    return ColumnTransformer(
        transformers=[("numeric", Pipeline(steps), feature_columns)],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def build_models(feature_columns):
    # The dataset is small, so the model settings are intentionally conservative.
    return {
        "hist_gradient_boosting": Pipeline(
            [
                ("preprocess", base_preprocessor(feature_columns)),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=0.06,
                        max_iter=180,
                        l2_regularization=0.08,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "extra_trees": Pipeline(
            [
                ("preprocess", base_preprocessor(feature_columns)),
                (
                    "model",
                    ExtraTreesClassifier(
                        n_estimators=350,
                        min_samples_leaf=3,
                        class_weight="balanced",
                        n_jobs=1,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "logistic_regression": Pipeline(
            [
                ("preprocess", base_preprocessor(feature_columns, scale=True)),
                (
                    "model",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=2000,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "xgboost": Pipeline(
            [
                ("preprocess", base_preprocessor(feature_columns)),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=160,
                        max_depth=3,
                        learning_rate=0.05,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        reg_lambda=1.2,
                        eval_metric="logloss",
                        n_jobs=1,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("preprocess", base_preprocessor(feature_columns)),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=350,
                        min_samples_leaf=3,
                        class_weight="balanced",
                        n_jobs=1,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }


def predict_score(pipeline, X):
    if hasattr(pipeline, "predict_proba"):
        return pipeline.predict_proba(X)[:, 1]
    if hasattr(pipeline, "decision_function"):
        scores = pipeline.decision_function(X)
        return 1 / (1 + np.exp(-scores))
    return pipeline.predict(X)


def evaluate_model(model_key, y_test, y_pred, y_score):
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_test, y_pred)), 4),
        "precision_success": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall_success": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1_success": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_score)), 4),
    }
    return {
        "model_key": model_key,
        "display_name": MODEL_NAMES[model_key],
        "metrics": metrics,
        "confusion_matrix": {
            "tn_fail": int(tn),
            "fp_fail_as_success": int(fp),
            "fn_success_as_fail": int(fn),
            "tp_success": int(tp),
        },
    }


def top_features(pipeline, feature_columns, model_key, limit=8):
    model = pipeline.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    elif hasattr(model, "coef_"):
        values = np.abs(model.coef_[0])
    else:
        return []
    ranked = sorted(zip(feature_columns, values), key=lambda pair: pair[1], reverse=True)
    return [
        {"feature": feature, "importance": round(float(importance), 5)}
        for feature, importance in ranked[:limit]
    ]


if __name__ == "__main__":
    main()
