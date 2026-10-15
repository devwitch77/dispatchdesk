
import sqlite3

from database import get_connection, initialise_database


def seed_resources(connection):
    """Insert fictional resources if they do not already exist."""
    resources = [
        ("Team Alpha", "Response Team", "available"),
        ("Team Bravo", "Response Team", "assigned"),
        ("Support Unit 1", "Support Unit", "available"),
        ("Support Unit 2", "Support Unit", "unavailable"),
    ]

    connection.executemany(
        """
        INSERT OR IGNORE INTO resources
            (display_name, resource_type, availability_status)
        VALUES (?, ?, ?)
        """,
        resources,
    )


def seed_incidents(connection):
    """Insert fictional incidents if the database is empty."""
    existing_count = connection.execute(
        "SELECT COUNT(*) FROM incidents"
    ).fetchone()[0]

    if existing_count > 0:
        print("Incidents already exist; skipping sample incidents.")
        return

    incidents = [
        (
            "Road obstruction reported",
            "A fictional report of an obstruction on a local road.",
            "Traffic",
            "high",
            "Demo Zone A",
            "new",
        ),
        (
            "Streetlight outage",
            "Several streetlights are reported as not functioning.",
            "Infrastructure",
            "low",
            "Demo Zone B",
            "new",
        ),
        (
            "Minor vehicle collision",
            "A fictional report of a collision with no injuries specified.",
            "Traffic",
            "medium",
            "Demo Zone C",
            "assigned",
        ),
        (
            "Public assistance request",
            "A fictional request for general public assistance.",
            "Public Assistance",
            "medium",
            "Demo Zone D",
            "in_progress",
        ),
        (
            "Damaged road sign",
            "A damaged sign has been reported in a fictional area.",
            "Infrastructure",
            "low",
            "Demo Zone E",
            "resolved",
        ),
        (
            "Urgent safety concern",
            "A fictional report requiring prompt operator review.",
            "Public Safety",
            "critical",
            "Demo Zone F",
            "new",
        ),
    ]

    connection.executemany(
        """
        INSERT INTO incidents
            (title, description, category, priority, location_label, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        incidents,
    )


def main():
    initialise_database()

    with get_connection() as connection:
        seed_resources(connection)
        seed_incidents(connection)

    print("Sample data setup complete.")


if __name__ == "__main__":
    main()
