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

def create_incident(
    title,
    description,
    category,
    priority,
    location_label,
):
    """Create a new incident and return its generated ID."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO incidents (
                title,
                description,
                category,
                priority,
                location_label
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                title.strip(),
                description.strip(),
                category,
                priority,
                location_label.strip(),
            ),
        )

        return cursor.lastrowid



def update_incident_status(incident_id, new_status):
    """Update an incident status and safely release its resource when closed."""

    allowed_statuses = {
        "new",
        "in_progress",
        "resolved",
        "cancelled",
    }

    if new_status not in allowed_statuses:
        raise ValueError("Invalid incident status.")

    with get_connection() as connection:
        incident = connection.execute(
            """
            SELECT status, assigned_resource_id
            FROM incidents
            WHERE incident_id = ?
            """,
            (incident_id,),
        ).fetchone()

        if incident is None:
            raise ValueError("Incident not found.")

        old_status = incident["status"]

        if old_status == new_status:
            return False

        # Closed incidents cannot be reopened through this workflow.
        if old_status in {"resolved", "cancelled"}:
            raise ValueError(
                "This incident is closed and cannot be reopened."
            )

        resource_id = incident["assigned_resource_id"]

        # Update the incident and clear its assignment if it is closing.
        connection.execute(
            """
            UPDATE incidents
            SET status = ?,
                assigned_resource_id = CASE
                    WHEN ? IN ('resolved', 'cancelled') THEN NULL
                    ELSE assigned_resource_id
                END,
                updated_at = CURRENT_TIMESTAMP,
                resolved_at = CASE
                    WHEN ? = 'resolved' THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END
            WHERE incident_id = ?
            """,
            (new_status, new_status, new_status, incident_id),
        )

        connection.execute(
            """
            INSERT INTO audit_events (
                incident_id,
                event_type,
                old_value,
                new_value
            )
            VALUES (?, 'status_changed', ?, ?)
            """,
            (incident_id, old_status, new_status),
        )

        # Release the resource when an incident is closed.
        if new_status in {"resolved", "cancelled"}:
            if resource_id is not None:
                resource = connection.execute(
                    """
                    SELECT display_name
                    FROM resources
                    WHERE resource_id = ?
                    """,
                    (resource_id,),
                ).fetchone()

                connection.execute(
                    """
                    INSERT INTO audit_events (
                        incident_id,
                        event_type,
                        old_value,
                        new_value
                    )
                    VALUES (?, 'resource_released', ?, ?)
                    """,
                    (
                        incident_id,
                        resource["display_name"] if resource else "Unknown",
                        "Unassigned",
                    ),
                )

                other_active_incidents = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM incidents
                    WHERE assigned_resource_id = ?
                      AND incident_id != ?
                      AND status NOT IN ('resolved', 'cancelled')
                    """,
                    (resource_id, incident_id),
                ).fetchone()[0]

                if other_active_incidents == 0:
                    connection.execute(
                        """
                        UPDATE resources
                        SET availability_status = 'available'
                        WHERE resource_id = ?
                        """,
                        (resource_id,),
                    )

    return True





def assign_incident_resource(incident_id, resource_id):
    """Assign an available resource and record the assignment."""

    with get_connection() as connection:
        incident = connection.execute(
            """
            SELECT incident_id, status, assigned_resource_id
            FROM incidents
            WHERE incident_id = ?
            """,
            (incident_id,),
        ).fetchone()

        if incident is None:
            raise ValueError("Incident not found.")

        resource = connection.execute(
            """
            SELECT resource_id, display_name, availability_status
            FROM resources
            WHERE resource_id = ?
            """,
            (resource_id,),
        ).fetchone()

        if resource is None:
            raise ValueError("Resource not found.")

        if incident["status"] in ("resolved", "cancelled"):
            raise ValueError(
                "Cannot assign a resource to a closed incident."
            )

        old_resource_id = incident["assigned_resource_id"]

        if old_resource_id == resource_id:
            return False

        if resource["availability_status"] != "available":
            raise ValueError(
                "This resource is not available. Choose another resource."
            )

        old_resource = None

        if old_resource_id is not None:
            old_resource = connection.execute(
                """
                SELECT display_name
                FROM resources
                WHERE resource_id = ?
                """,
                (old_resource_id,),
            ).fetchone()

        old_resource_name = (
            old_resource["display_name"]
            if old_resource
            else "Unassigned"
        )

        old_status = incident["status"]
        new_status = (
            "assigned" if old_status == "new" else old_status
        )

        connection.execute(
            """
            UPDATE incidents
            SET assigned_resource_id = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE incident_id = ?
            """,
            (resource_id, new_status, incident_id),
        )

        connection.execute(
            """
            UPDATE resources
            SET availability_status = 'assigned'
            WHERE resource_id = ?
            """,
            (resource_id,),
        )

        # Release the previous resource if nothing else uses it.
        if old_resource_id is not None:
            other_assignments = connection.execute(
                """
                SELECT COUNT(*)
                FROM incidents
                WHERE assigned_resource_id = ?
                  AND incident_id != ?
                  AND status NOT IN ('resolved', 'cancelled')
                """,
                (old_resource_id, incident_id),
            ).fetchone()[0]

            if other_assignments == 0:
                connection.execute(
                    """
                    UPDATE resources
                    SET availability_status = 'available'
                    WHERE resource_id = ?
                    """,
                    (old_resource_id,),
                )

        connection.execute(
            """
            INSERT INTO audit_events (
                incident_id,
                event_type,
                old_value,
                new_value
            )
            VALUES (?, 'resource_assigned', ?, ?)
            """,
            (
                incident_id,
                old_resource_name,
                resource["display_name"],
            ),
        )

        # Record a status change separately if assignment changed it.
        if old_status != new_status:
            connection.execute(
                """
                INSERT INTO audit_events (
                    incident_id,
                    event_type,
                    old_value,
                    new_value
                )
                VALUES (?, 'status_changed', ?, ?)
                """,
                (incident_id, old_status, new_status),
            )

    return True




def get_handover_incidents():
    """Return unresolved incidents for a shift handover report."""

    with get_connection() as connection:
        incidents = connection.execute(
            """
            SELECT
                incidents.incident_id,
                incidents.title,
                incidents.description,
                incidents.category,
                incidents.priority,
                incidents.location_label,
                incidents.status,
                incidents.created_at,
                incidents.updated_at,
                resources.display_name AS assigned_resource
            FROM incidents
            LEFT JOIN resources
                ON incidents.assigned_resource_id =
                   resources.resource_id
            WHERE incidents.status IN (
                'new',
                'assigned',
                'in_progress'
            )
            ORDER BY
                CASE incidents.priority
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END,
                incidents.created_at ASC
            """
        ).fetchall()

    return [dict(incident) for incident in incidents]



if __name__ == "__main__":
    initialise_database()
    print(f"Database initialised at: {DATABASE_PATH}")
