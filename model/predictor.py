from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

category_model = joblib.load(BASE_DIR / "category_model.joblib")
urgency_model = joblib.load(BASE_DIR / "urgency_model.joblib")
secondary_detector = joblib.load(BASE_DIR / "secondary_detector.joblib")
secondary_label_model = joblib.load(BASE_DIR / "secondary_label_model.joblib")


TEAM_MAP = {
    "payment_refund": "Payments & Refunds",
    "ride_trip_issue": "Ride Operations",
    "lost_item": "Lost & Found",
    "order_missing_wrong": "Food Operations",
    "delivery_delay": "Delivery Operations",
    "food_quality": "Restaurant Quality",
    "account_promo": "Account Services",
    "safety_conduct": "Trust & Safety",
    "app_technical": "Tech Support",
    "general_inquiry": "Front-line Support",
    "spam_irrelevant": "Auto-close / Spam Filter",
}


def build_text(channel, subject, text):
    subject = subject or ""
    text = text or ""

    return f"__CHANNEL_{channel} {subject} {text}"


def build_secondary_text(channel, subject, text, primary):
    subject = subject or ""
    text = text or ""

    return (
        f"__PRIMARY_{primary} "
        f"__CHANNEL_{channel} "
        f"{subject} {text}"
    )


def predict_ticket(channel, subject, text):
    model_text = build_text(channel, subject, text)

    primary = str(category_model.predict([model_text])[0])

    urgent = bool(urgency_model.predict([model_text])[0])

    has_secondary = bool(
        secondary_detector.predict([model_text])[0]
    )

    secondary = None

    if has_secondary and primary != "spam_irrelevant":
        secondary_text = build_secondary_text(
            channel,
            subject,
            text,
            primary
        )

        secondary = str(
            secondary_label_model.predict([secondary_text])[0]
        )

        if secondary == primary:
            secondary = None

    if primary == "spam_irrelevant":
        secondary = None
        urgent = False

    team = TEAM_MAP[primary]

    decision_scores = category_model.decision_function([model_text])

    scores = decision_scores[0]

    exp_scores = pd.Series(scores).apply(lambda x: pow(2.718281828, x))
    probabilities = exp_scores / exp_scores.sum()

    confidence = float(probabilities.max())

    confidence = round(
        max(0.0, min(1.0, confidence)),
        4
    )

    return {
        "category": primary,
        "secondary_category": secondary,
        "team": team,
        "is_urgent": urgent,
        "confidence": confidence,
        "model_version": "v1.0"
    }