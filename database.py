import sqlite3


DATABASE_NAME = "medicare.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    # Patient table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            verification_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add profile columns if they do not already exist
    try:
        cursor.execute(
            """
            ALTER TABLE patients
            ADD COLUMN email TEXT
            """
        )
    except:
        pass


    try:
        cursor.execute(
            """
            ALTER TABLE patients
            ADD COLUMN phone TEXT
            """
        )
    except:
        pass


    try:
        cursor.execute(
            """
            ALTER TABLE patients
            ADD COLUMN age INTEGER
            """
        )
    except:
        pass


    try:
        cursor.execute(
            """
            ALTER TABLE patients
            ADD COLUMN gender TEXT
            """
        )
    except:
        pass


    try:
        cursor.execute(
            """
            ALTER TABLE patients
            ADD COLUMN blood_group TEXT
            """
        )
    except:
        pass

    # Medicine table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_code TEXT UNIQUE NOT NULL,
            medicine_name TEXT NOT NULL,
            manufacturer TEXT,
            medicine_type TEXT,
            purpose TEXT,
            warning TEXT
        )
    """)
    
    # Prescription upload history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            patient_id INTEGER NOT NULL,

            original_filename TEXT NOT NULL,

            stored_filename TEXT NOT NULL,

            file_type TEXT,

            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (patient_id)
                REFERENCES patients (id)
        )
    """)

    connection.commit()
    connection.close()


def seed_medicines():
    medicines = [
        (
            "MED5001",
            "Metformin 500 mg",
            "Example Pharmaceutical Ltd.",
            "Tablet",
            "Blood sugar management",
            "Use only according to a healthcare professional's instructions."
        ),
        (
            "MED5002",
            "Amoxicillin 500 mg",
            "Example Pharma Ltd.",
            "Capsule",
            "Certain bacterial infections",
            "Antibiotic. Use only when prescribed."
        ),
        (
            "MED5003",
            "Pantoprazole 40 mg",
            "Example Pharma Ltd.",
            "Tablet",
            "Reduction of stomach acid",
            "Use according to prescription."
        ),
        (
            "MED5004",
            "Amlodipine 5 mg",
            "Example Pharma Ltd.",
            "Tablet",
            "Blood pressure management",
            "Do not change dose without medical advice."
        ),
        (
            "MED5005",
            "Cetirizine 10 mg",
            "Example Pharma Ltd.",
            "Tablet",
            "Allergy symptom relief",
            "May cause drowsiness in some people."
        )
    ]

    connection = get_connection()
    cursor = connection.cursor()

    for medicine in medicines:

        cursor.execute(
            """
            INSERT OR IGNORE INTO medicines (
                medicine_code,
                medicine_name,
                manufacturer,
                medicine_type,
                purpose,
                warning
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            medicine
        )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_tables()
    seed_medicines()

    print("Database created successfully.")
    print("Medicine database populated successfully.")