
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline


CATEGORIES = [
    "Traffic",
    "Infrastructure",
    "Public Assistance",
    "Public Safety",
]

# Prototype review threshold only.
# Logistic regression scores are NOT calibrated probabilities.
REVIEW_SCORE_THRESHOLD = 0.45


# Fictional development data only.
# Keep evaluation examples separate from this training data.
TRAINING_DATA = [
    # Traffic
    ("A car has broken down in the middle of the road", "Traffic"),
    ("There is a major traffic jam near the intersection", "Traffic"),
    ("Two vehicles have collided at the junction", "Traffic"),
    ("Traffic lights are causing congestion on the main road", "Traffic"),
    ("A vehicle is blocking the entrance to the parking area", "Traffic"),
    ("Road traffic is moving very slowly after an accident", "Traffic"),
    ("Several cars are backed up behind a stalled vehicle", "Traffic"),
    ("A long queue of vehicles is forming near the roundabout", "Traffic"),
    ("Cars cannot move because the junction is congested", "Traffic"),
    ("A lorry has stopped and is blocking a traffic lane", "Traffic"),
    ("Vehicles are queuing because of a minor road collision", "Traffic"),
    ("Heavy congestion is affecting the road outside the station", "Traffic"),
    ("A car collision has blocked a lane near Al Hisn", "Traffic"),
    ("Several vehicles are stuck in traffic near Al Reem Island", "Traffic"),
    ("A broken-down taxi is causing delays on the Corniche", "Traffic"),
    ("A vehicle has stalled near Al Zahiyah and traffic is building up", "Traffic"),

    # Infrastructure
    ("A streetlight has stopped working", "Infrastructure"),
    ("There is a large pothole in the road", "Infrastructure"),
    ("A water pipe has burst and water is flooding the street", "Infrastructure"),
    ("A traffic signal pole appears to be damaged", "Infrastructure"),
    ("There is a power outage affecting several buildings", "Infrastructure"),
    ("A broken manhole cover is exposed on the pavement", "Infrastructure"),
    ("A public drainage pipe is leaking onto the pavement", "Infrastructure"),
    ("Several street lamps are not turning on at night", "Infrastructure"),
    ("A section of pavement has collapsed", "Infrastructure"),
    ("A damaged road sign needs to be repaired", "Infrastructure"),
    ("A utility cabinet has been damaged beside the road", "Infrastructure"),
    ("The public water supply has stopped in this block", "Infrastructure"),
    ("A streetlight is not working near Al Khalidiyah", "Infrastructure"),
    ("A damaged pavement needs repair on Al Reem Island", "Infrastructure"),
    ("Water is leaking from a pipe near Al Hisn", "Infrastructure"),
    ("A road sign has fallen near the Abu Dhabi Corniche", "Infrastructure"),

    # Public Safety
    ("Smoke is coming from a building", "Public Safety"),
    ("There is a fire in a residential building", "Public Safety"),
    ("A person is behaving aggressively and threatening others", "Public Safety"),
    ("Someone has reported a suspicious unattended package", "Public Safety"),
    ("There is a strong smell of gas inside the building", "Public Safety"),
    ("A fight has broken out in a public area", "Public Safety"),
    ("Flames can be seen inside an office building", "Public Safety"),
    ("A person is threatening passersby in the street", "Public Safety"),
    ("An unattended bag has raised a security concern", "Public Safety"),
    ("People report smoke coming from a warehouse", "Public Safety"),
    ("A violent altercation has started outside a shop", "Public Safety"),
    ("A possible gas leak has been reported indoors", "Public Safety"),
    ("Smoke is coming from a building near Al Zahiyah", "Public Safety"),
    ("A person is threatening members of the public near Al Hisn", "Public Safety"),
    ("A suspicious unattended package was found on Al Reem Island", "Public Safety"),
    ("People report a possible fire near the Abu Dhabi Corniche", "Public Safety"),

    # Public Assistance
    ("An elderly person needs help getting home", "Public Assistance"),
    ("A resident needs assistance accessing a public service", "Public Assistance"),
    ("A visitor is lost and needs directions", "Public Assistance"),
    ("Someone requires help contacting their family", "Public Assistance"),
    ("A person needs assistance with a non-emergency request", "Public Assistance"),
    ("A resident is requesting information about local services", "Public Assistance"),
    ("A tourist needs directions to the nearest public office", "Public Assistance"),
    ("A resident wants help completing a service request", "Public Assistance"),
    ("A visitor is unsure where to find the information desk", "Public Assistance"),
    ("Someone needs assistance finding a community centre", "Public Assistance"),
    ("A member of the public is asking about service opening hours", "Public Assistance"),
    ("A resident needs guidance on a routine administrative matter", "Public Assistance"),
    ("A visitor is lost near Al Hisn and needs directions", "Public Assistance"),
    ("A resident needs help finding a public service on Al Reem Island", "Public Assistance"),
    ("A tourist needs directions near the Abu Dhabi Corniche", "Public Assistance"),
    ("Someone needs information about a government service in Al Zahiyah", "Public Assistance"),
]


# Held-out evaluation examples.
# Do not add these examples to TRAINING_DATA.
EVALUATION_DATA = [
    # Traffic
    ("Vehicles are barely moving due to a queue on the highway", "Traffic"),
    ("A broken-down van is holding up traffic", "Traffic"),
    ("A collision has caused a backup at the roundabout", "Traffic"),
    ("Cars are stuck in a long line approaching the bridge", "Traffic"),
    ("car collison at Al Hisn", "Traffic"),
    ("A stalled vehicle is causing delays near Al Reem Island", "Traffic"),

    # Infrastructure
    ("A burst main is sending water across the sidewalk", "Infrastructure"),
    ("The lamp beside the pedestrian crossing is out", "Infrastructure"),
    ("A deep hole has appeared in the road surface", "Infrastructure"),
    ("Power has failed across several nearby buildings", "Infrastructure"),
    ("street light not working near Al Reem Island", "Infrastructure"),
    ("A water pipe is leaking near Al Zahiyah", "Infrastructure"),

    # Public Safety
    ("Flames and thick smoke are visible at a warehouse", "Public Safety"),
    ("A person is threatening people outside a supermarket", "Public Safety"),
    ("A suspicious package has been left unattended in a lobby", "Public Safety"),
    ("Building occupants report a possible gas leak", "Public Safety"),
    ("Smoke is coming from a building near Al Hisn", "Public Safety"),
    ("A fight has broken out in a public area", "Public Safety"),

    # Public Assistance
    ("A visitor cannot find the correct government department", "Public Assistance"),
    ("Someone needs directions to a nearby community facility", "Public Assistance"),
    ("A resident is asking how to access a routine municipal service", "Public Assistance"),
    ("A person needs help locating a public information counter", "Public Assistance"),
    ("tourist is lost near the Corniche and needs directions", "Public Assistance"),
    ("Someone needs information about local public services", "Public Assistance"),
]


def build_classifier():
    """Train the classifier using fictional training examples only."""
    texts = [text for text, label in TRAINING_DATA]
    labels = [label for text, label in TRAINING_DATA]

    features = FeatureUnion([
        (
            "word_features",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                strip_accents="unicode",
                sublinear_tf=True,
            ),
        ),
        (
            "character_features",
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                lowercase=True,
                strip_accents="unicode",
                sublinear_tf=True,
            ),
        ),
    ])

    model = Pipeline([
        ("features", features),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                random_state=42,
            ),
        ),
    ])

    model.fit(texts, labels)
    return model


# Train once when this module is imported.
classifier = build_classifier()


def suggest_category(description: str) -> dict:
    """Suggest an incident category and flag low-scoring predictions."""
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Please enter an incident description.")

    cleaned_description = " ".join(description.split())

    probabilities = classifier.predict_proba([cleaned_description])[0]
    best_index = probabilities.argmax()
    score = float(probabilities[best_index])

    return {
        "category": classifier.classes_[best_index],
        "confidence": score,
        "needs_review": score < REVIEW_SCORE_THRESHOLD,
    }


if __name__ == "__main__":
    examples = [
        "Several cars are backed up because a vehicle broke down",
        "car collison at Al Hisn",
        "street light not working near Al Reem Island",
        "Smoke is coming from a building",
        "A visitor needs directions to a public office",
        "Fire at a shopping mall",
    ]

    for description in examples:
        result = suggest_category(description)
        print(f"\nReport: {description}")
        print(f"Suggested category: {result['category']}")
        print(f"Model score: {result['confidence']:.1%}")
        print(f"Needs extra review: {result['needs_review']}")
