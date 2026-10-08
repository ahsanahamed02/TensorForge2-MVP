from pathlib import Path
import joblib
import pandas as pd

from sklearn.metrics import accuracy_score, f1_score

from model.train_category_v3 import build_text as build_text_v3
from model.train_category_v8 import build_text as build_text_v8


ROOT = Path(__file__).resolve().parents[1]

VAL_PATH = ROOT / "data" / "validation.csv"

V3_MODEL_PATH = ROOT / "model" / "category_model_v3.joblib"
V8_MODEL_PATH = ROOT / "model" / "category_model_v8.joblib"


def load_model(path):
    obj = joblib.load(path)

    if isinstance(obj, dict) and "pipeline" in obj:
        return obj["pipeline"]

    return obj


def main():
    print("=" * 72)
    print("RouteIQ V3 vs V8 Fair Audit")
    print("=" * 72)

    val = pd.read_csv(VAL_PATH)

    y_true = val["category"].astype(str)

    # IMPORTANT:
    # Each model gets its own original preprocessing.
    X_v3 = build_text_v3(val.copy())
    X_v8 = val.apply(build_text_v8, axis=1)

    v3 = load_model(V3_MODEL_PATH)
    v8 = load_model(V8_MODEL_PATH)

    print("Running V3 with V3 preprocessing...")
    pred_v3 = v3.predict(X_v3)

    print("Running V8 with V8 preprocessing...")
    pred_v8 = v8.predict(X_v8)

    acc_v3 = accuracy_score(y_true, pred_v3)
    acc_v8 = accuracy_score(y_true, pred_v8)

    macro_v3 = f1_score(y_true, pred_v3, average="macro")
    macro_v8 = f1_score(y_true, pred_v8, average="macro")

    print()
    print("=" * 72)
    print("OVERALL")
    print("=" * 72)

    print(f"V3 Accuracy : {acc_v3:.4%}")
    print(f"V8 Accuracy : {acc_v8:.4%}")
    print(f"Change      : {acc_v8 - acc_v3:+.4%}")

    print()
    print(f"V3 Macro F1 : {macro_v3:.6f}")
    print(f"V8 Macro F1 : {macro_v8:.6f}")
    print(f"Change      : {macro_v8 - macro_v3:+.6f}")

    audit = val.copy()

    audit["pred_v3"] = pred_v3
    audit["pred_v8"] = pred_v8

    v3_correct = audit["pred_v3"] == audit["category"]
    v8_correct = audit["pred_v8"] == audit["category"]

    fixed = (~v3_correct) & v8_correct
    broken = v3_correct & (~v8_correct)

    both_correct = v3_correct & v8_correct
    both_wrong = (~v3_correct) & (~v8_correct)

    print()
    print("=" * 72)
    print("CHANGE ANALYSIS")
    print("=" * 72)

    print(f"V3 wrong -> V8 correct : {fixed.sum()}")
    print(f"V3 correct -> V8 wrong : {broken.sum()}")
    print(f"Both correct           : {both_correct.sum()}")
    print(f"Both wrong             : {both_wrong.sum()}")
    print(f"Net improvement        : {fixed.sum() - broken.sum()}")

    print()
    print("=" * 72)
    print("LANGUAGE-WISE ACCURACY")
    print("=" * 72)

    rows = []

    for language, group in audit.groupby("language"):
        true = group["category"]

        v3_acc = accuracy_score(
            true,
            group["pred_v3"],
        )

        v8_acc = accuracy_score(
            true,
            group["pred_v8"],
        )

        rows.append(
            {
                "language": language,
                "count": len(group),
                "v3": v3_acc,
                "v8": v8_acc,
                "change": v8_acc - v3_acc,
            }
        )

    lang_df = pd.DataFrame(rows)
    lang_df = lang_df.sort_values(
        "change",
        ascending=False,
    )

    print(
        lang_df.to_string(
            index=False,
            formatters={
                "v3": lambda x: f"{x:.2%}",
                "v8": lambda x: f"{x:.2%}",
                "change": lambda x: f"{x:+.2%}",
            },
        )
    )

    print()
    print("=" * 72)
    print("CATEGORY-WISE RECALL")
    print("=" * 72)

    rows = []

    for category, group in audit.groupby("category"):
        true = group["category"]

        v3_acc = accuracy_score(
            true,
            group["pred_v3"],
        )

        v8_acc = accuracy_score(
            true,
            group["pred_v8"],
        )

        rows.append(
            {
                "category": category,
                "count": len(group),
                "v3": v3_acc,
                "v8": v8_acc,
                "change": v8_acc - v3_acc,
            }
        )

    cat_df = pd.DataFrame(rows)
    cat_df = cat_df.sort_values(
        "change",
        ascending=False,
    )

    print(
        cat_df.to_string(
            index=False,
            formatters={
                "v3": lambda x: f"{x:.2%}",
                "v8": lambda x: f"{x:.2%}",
                "change": lambda x: f"{x:+.2%}",
            },
        )
    )

    print()
    print("=" * 72)
    print("REGRESSIONS")
    print("V3 CORRECT -> V8 WRONG")
    print("=" * 72)

    regressions = audit[broken][
        [
            "ticket_id",
            "language",
            "category",
            "pred_v3",
            "pred_v8",
            "subject",
            "text",
        ]
    ]

    print(f"Regression count: {len(regressions)}")

    if len(regressions) > 0:
        print()
        print(regressions.head(15).to_string(index=False))

    print()
    print("=" * 72)
    print("FIXES")
    print("V3 WRONG -> V8 CORRECT")
    print("=" * 72)

    fixes = audit[fixed][
        [
            "ticket_id",
            "language",
            "category",
            "pred_v3",
            "pred_v8",
            "subject",
            "text",
        ]
    ]

    print(f"Fix count: {len(fixes)}")

    if len(fixes) > 0:
        print()
        print(fixes.head(15).to_string(index=False))

    output = ROOT / "model" / "v8_audit.csv"

    audit.to_csv(
        output,
        index=False,
    )

    print()
    print("=" * 72)
    print("AUDIT COMPLETE")
    print("=" * 72)

    print(f"Saved: {output}")


if __name__ == "__main__":
    main()