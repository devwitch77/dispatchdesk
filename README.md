# DispatchDesk

**A simulated incident dispatch and operations dashboard built with Python.**

DispatchDesk is a portfolio project that demonstrates incident management, resource allocation, database-backed workflows, text classification, and geospatial visualization in an Abu Dhabi-inspired operational setting.

> **Disclaimer:** DispatchDesk is a software prototype for demonstration and educational purposes. Its incidents, fleet units, and unit positions are simulated. It is not connected to real emergency services and must not be used for actual emergency response.

## Features

- **Incident management** — Create incidents, review reports, and update their lifecycle status.
- **Priority-based operations** — Organize incidents by Critical, High, Medium, and Low priority, with older incidents prioritized within each level.
- **Resource assignment** — Assign available simulated response units to incidents and track fleet availability.
- **Assignment safeguards** — Prevent assignment of unavailable units or assignment to closed incidents, and release resources when appropriate.
- **Audit history** — Record incident creation, status changes, and resource assignments.
- **Operational handover** — Review unresolved incidents, highlight critical and unassigned work, and export handover data as CSV.
- **Interactive map** — Explore incident clusters and simulated fleet positions on a map, inspect selected items, and filter incidents and resources.
- **NLP category suggestions** — Suggest one of four incident categories from a text description, with a low-confidence warning for uncertain predictions.

## Technology stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Streamlit | Interactive web application |
| SQLite | Persistent incident, location, resource, and audit data |
| pandas | Data handling and presentation |
| scikit-learn | Text classification |
| TF-IDF | Word- and character-level text features |
| Logistic Regression | Incident category prediction |
| PyDeck | Interactive geospatial visualization |

Pinned Python dependencies are listed in `requirements.txt`.

## Project structure

```text
dispatchdesk/
├── app.py
├── database.py
├── incident_classifier.py
├── evaluate_classifier.py
├── seed_data.py
├── requirements.txt
├── data/
│   └── dispatchdesk.db       # Local database; generated at runtime
└── README.md
```

The local database and virtual environment are development artifacts and should not be committed to version control.

## Getting started

### Requirements

- Python installed on your system
- PowerShell on Windows, or an equivalent terminal
- Git (optional, for cloning and version control)

### 1. Open the project directory

```powershell
cd C:\Users\Youssef\dispatchdesk
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, follow the Python environment setup guidance for your system or activate the environment using a supported terminal.

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Start DispatchDesk

```powershell
streamlit run app.py
```

Streamlit will display a local URL in the terminal. Open that URL in your browser to use the dashboard.

The application initializes its database when it starts. Keep the local database file if you want to preserve your development incidents and audit history.

## How it works

### Incident lifecycle

DispatchDesk stores incident details including title, description, category, priority, location, status, assigned resource, and timestamps.

The workflow supports statuses such as New, Assigned, In Progress, Resolved, and Cancelled. Closed incidents cannot receive new resource assignments. Resolution and cancellation also trigger resource-release logic.

### Resource management

The database tracks simulated units, their identifiers, resource types, availability, and coordinates. Assignment operations update incident and resource records and write corresponding audit events.

### Database layer

`database.py` contains the SQLite connection and database operations. It handles initialization, incident creation, status changes, resource assignments, location and resource retrieval, and operational handover queries.

### Incident classification

`incident_classifier.py` implements a text-classification prototype using word-level and character-level TF-IDF features with Logistic Regression.

The classifier suggests a category:

- Traffic
- Infrastructure
- Public Assistance
- Public Safety

Category prediction is separate from operational priority. The model does not determine whether an incident is Critical, High, Medium, or Low; priority remains an operational decision.

### Evaluation

Run the classifier evaluation with:

```powershell
python evaluate_classifier.py
```

The current authored evaluation set contains 24 examples, with six examples per category. The latest recorded run achieved 100% accuracy on that set.

**Interpretation:** This result verifies performance on the current evaluation examples only. The dataset is small and hand-authored, so the score should not be interpreted as evidence of equivalent accuracy on unseen real-world incident reports. Broader testing with independently collected and labelled data is needed.

## Data and mapping notes

The map uses geographic coordinates associated with named Abu Dhabi areas. These are approximate area reference points, not verified incident addresses.

Fleet positions represent simulated locations. The map's incident clusters are visual groupings of nearby approximate coordinates; they do not represent verified incidents at an exact address.

No live emergency-service feeds, GPS tracking, or real-time dispatch integrations are used.

## Testing and reliability

The following checks have been run during development:

- Python compilation checks for the application, database, classifier, and evaluation modules.
- Classifier evaluation on the authored 24-example evaluation set.
- SQLite integrity check and foreign-key validation.
- Operational checks for duplicate unit identifiers, coordinate validity, missing resource references, multiple active assignments, and fleet availability consistency.
- Incident lifecycle and resource assignment logic review.

These are development checks, not a comprehensive automated test suite. The classifier and operational workflows require broader testing before any production use.

To run the available checks:

```powershell
python -m py_compile app.py database.py incident_classifier.py evaluate_classifier.py
python evaluate_classifier.py
```

## Limitations and future improvements

Potential next steps include:

- Automated unit and integration tests for incident lifecycle and resource assignment.
- Larger, independently labelled classifier datasets and more robust evaluation.
- Improved handling of ambiguous or out-of-category reports.
- More detailed location validation and geospatial behavior.
- Additional architecture documentation and screenshots.
- Deployment and configuration guidance for a demonstration environment.

## Project status

DispatchDesk is an actively developed portfolio prototype intended to demonstrate practical software engineering, database-backed workflows, NLP, and geospatial data presentation.

---
