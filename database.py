import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "data" / "dispatchdesk.db"


def get_connection():
    """Open a connection to the DispatchDesk SQLite database."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_database():
    """Create the database tables if they do not exist."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS resources (
                resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL UNIQUE,
                resource_type TEXT NOT NULL,
                availability_status TEXT NOT NULL DEFAULT 'available'
                    CHECK (
                        availability_status IN (
                            'available',
                            'assigned',
                            'unavailable'
                        )
                    )
            );

            CREATE TABLE IF NOT EXISTS incidents (
                incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL
                    CHECK (
                        priority IN ('low', 'medium', 'high', 'critical')
                    ),
                location_label TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
                    CHECK (
                        status IN (
                            'new',
                            'assigned',
                            'in_progress',
                            'resolved',
                            'cancelled'
                        )
                    ),
                assigned_resource_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                FOREIGN KEY (assigned_resource_id)
                    REFERENCES resources(resource_id)
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                actor_label TEXT NOT NULL DEFAULT 'Demo Operator',
                event_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (incident_id)
                    REFERENCES incidents(incident_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_incidents_status
                ON incidents(status);

            CREATE INDEX IF NOT EXISTS idx_incidents_priority
                ON incidents(priority);

            CREATE INDEX IF NOT EXISTS idx_audit_incident
                ON audit_events(incident_id, event_at);
            """
        )


if __name__ == "__main__":
    initialise_database()
    print(f"Database initialised at: {DATABASE_PATH}")
