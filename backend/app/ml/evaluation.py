from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def probabilities(model: Any, features: Any) -> np.ndarray:
    values = model.predict_proba(features)
    if values.shape[1] == 1:
        learned_class = int(model.classes_[0])
        return np.ones(len(features)) if learned_class == 1 else np.zeros(len(features))
    positive_index = list(model.classes_).index(1)
    return values[:, positive_index]


def select_f1_threshold(target: list[int], scores: np.ndarray) -> float:
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in np.linspace(0.05, 0.95, 181):
        value = f1_score(target, scores >= threshold, zero_division=0)
        if value > best_f1:
            best_f1 = value
            best_threshold = float(threshold)
    return round(best_threshold, 4)


def evaluate_scores(
    target: list[int],
    scores: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    labels = (scores >= threshold).astype(int)
    matrix = confusion_matrix(target, labels, labels=[0, 1]).tolist()
    roc_auc = float(roc_auc_score(target, scores)) if len(set(target)) > 1 else None
    pr_auc = (
        float(average_precision_score(target, scores))
        if len(set(target)) > 1
        else None
    )
    return {
        "accuracy": round(float(accuracy_score(target, labels)), 6),
        "precision": round(float(precision_score(target, labels, zero_division=0)), 6),
        "recall": round(float(recall_score(target, labels, zero_division=0)), 6),
        "f1": round(float(f1_score(target, labels, zero_division=0)), 6),
        "roc_auc": round(roc_auc, 6) if roc_auc is not None else None,
        "pr_auc": round(pr_auc, 6) if pr_auc is not None else None,
        "brier_score": round(float(brier_score_loss(target, scores)), 6),
        "confusion_matrix": matrix,
        "threshold": threshold,
    }


def evaluate_model(model: Any, features: Any, target: list[int], threshold: float) -> dict[str, Any]:
    return evaluate_scores(target, probabilities(model, features), threshold)


def choose_model(metrics: dict[str, dict[str, Any]]) -> tuple[str, str]:
    logistic = metrics["logistic_regression"]
    forest = metrics["random_forest"]
    logistic_pr = logistic["pr_auc"] or 0.0
    forest_pr = forest["pr_auc"] or 0.0
    if abs(logistic_pr - forest_pr) <= 0.02:
        return (
            "logistic_regression",
            "PR-AUC differs by at most 0.02; Logistic Regression is preferred for interpretability",
        )
    if logistic_pr > forest_pr:
        return "logistic_regression", "Logistic Regression has the highest validation PR-AUC"
    return "random_forest", "Random Forest has the highest validation PR-AUC"
