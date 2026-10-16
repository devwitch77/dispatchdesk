
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from incident_classifier import (
    CATEGORIES,
    EVALUATION_DATA,
    TRAINING_DATA,
    build_classifier,
)


def main():
    # The model is trained only on TRAINING_DATA.
    # EVALUATION_DATA remains held out.
    model = build_classifier()

    test_texts = [text for text, label in EVALUATION_DATA]
    test_labels = [label for text, label in EVALUATION_DATA]

    predictions = model.predict(test_texts)

    print("DISPATCHDESK NLP PROTOTYPE EVALUATION")
    print("=" * 48)
    print(f"Training examples:   {len(TRAINING_DATA)}")
    print(f"Evaluation examples: {len(test_texts)}")
    print(f"Accuracy: {accuracy_score(test_labels, predictions):.1%}")

    print("\nPer-category metrics:")
    print(
        classification_report(
            test_labels,
            predictions,
            labels=CATEGORIES,
            zero_division=0,
            digits=3,
        )
    )

    print("Confusion matrix (rows = actual, columns = predicted):")
    print(CATEGORIES)
    print(
        confusion_matrix(
            test_labels,
            predictions,
            labels=CATEGORIES,
        )
    )

    print("\nIndividual predictions:")
    for text, actual, predicted in zip(
        test_texts,
        test_labels,
        predictions,
    ):
        result = "PASS" if actual == predicted else "MISS"
        print(f"[{result}] Actual: {actual} | Predicted: {predicted}")
        print(f"       {text}")

    misses = sum(
        actual != predicted
        for actual, predicted in zip(test_labels, predictions)
    )

    print(f"\nMisclassified examples: {misses}/{len(test_texts)}")

    if misses:
        print(
            "Review the misses before changing the training data. "
            "Do not move evaluation examples into training and then "
            "reuse them as an independent test set."
        )


if __name__ == "__main__":
    main()
