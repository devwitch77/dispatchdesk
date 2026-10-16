
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from incident_classifier import (
    CATEGORIES,
    EVALUATION_DATA,
    build_classifier,
)


def main():
    # build_classifier() trains only on TRAINING_DATA.
    model = build_classifier()

    test_texts = [text for text, label in EVALUATION_DATA]
    test_labels = [label for text, label in EVALUATION_DATA]

    predictions = model.predict(test_texts)

    print("DISPATCHDESK NLP PROTOTYPE EVALUATION")
    print("=" * 45)
    print(f"Training examples:  {48}")
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
    print(confusion_matrix(
        test_labels,
        predictions,
        labels=CATEGORIES,
    ))

    print("\nIndividual predictions:")
    for text, actual, predicted in zip(
        test_texts, test_labels, predictions
    ):
        result = "PASS" if actual == predicted else "MISS"
        print(f"[{result}] Actual: {actual} | Predicted: {predicted}")
        print(f"       {text}")


if __name__ == "__main__":
    main()
