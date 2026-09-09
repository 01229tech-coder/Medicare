import os
import uuid

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from database import get_connection, create_tables, seed_medicines


app = Flask(__name__)
UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "pdf"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)
CORS(app)


# Create database tables when the backend starts
create_tables()
seed_medicines()

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================
# HOME
# ============================================

@app.route("/")
def home():
    return jsonify({
        "message": "MediCare Assistant Backend is Running",
        "status": "success"
    })


# ============================================
# HEALTH CHECK
# ============================================

@app.route("/api/health")
def health_check():
    return jsonify({
        "status": "Backend is healthy"
    })


# ============================================
# PATIENT LOGIN / VERIFICATION
# ============================================

@app.route("/api/register", methods=["POST"])
def register_patient():

    data = request.get_json()

    patient_name = data.get(
        "patient_name",
        ""
    ).strip()


    if not patient_name:

        return jsonify({
            "success": False,
            "message": "Patient name is required."
        }), 400


    connection = get_connection()
    cursor = connection.cursor()


    # Create patient temporarily without ID
    cursor.execute(
        """
        INSERT INTO patients (
            patient_name,
            verification_id
        )
        VALUES (?, ?)
        """,
        (
            patient_name,
            "TEMP"
        )
    )


    patient_id = cursor.lastrowid


    # Generate human-readable Patient ID
    generated_patient_id = (
        f"MC-{10000 + patient_id}"
    )


    cursor.execute(
        """
        UPDATE patients

        SET verification_id = ?

        WHERE id = ?
        """,
        (
            generated_patient_id,
            patient_id
        )
    )


    connection.commit()
    connection.close()


    return jsonify({

        "success": True,

        "message":
            "Registration successful.",

        "patient": {

            "id":
                patient_id,

            "name":
                patient_name,

            "patient_id":
                generated_patient_id

        }

    }), 201


# ============================================
# EXISTING PATIENT LOGIN
# ============================================

@app.route(
    "/api/login",
    methods=["POST"]
)
def login():

    data = request.get_json()


    patient_name = data.get(
        "patient_name",
        ""
    ).strip()


    patient_id = data.get(
        "patient_id",
        ""
    ).strip()


    if not patient_name or not patient_id:

        return jsonify({

            "success": False,

            "message":
                "Patient name and Patient ID are required."

        }), 400


    connection = get_connection()
    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *

        FROM patients

        WHERE verification_id = ?

          AND LOWER(patient_name)
              = LOWER(?)
        """,
        (
            patient_id,
            patient_name
        )
    )


    patient = cursor.fetchone()

    connection.close()


    if patient is None:

        return jsonify({

            "success": False,

            "message":
                "Invalid Patient ID or patient name."

        }), 401


    return jsonify({

        "success": True,

        "message":
            "Patient login successful.",

        "patient": {

            "id":
                patient["id"],

            "name":
                patient["patient_name"],

            "patient_id":
                patient["verification_id"],

            "verification_id":
                patient["verification_id"],

            "new_patient":
                False

        }

    })
    
    
# ============================================
# MEDICINE IDENTIFIER
# ============================================

@app.route("/api/medicine/<query>", methods=["GET"])
def identify_medicine(query):

    search_query = query.strip()


    if not search_query:
        return jsonify({
            "success": False,
            "message": "Medicine name or code is required."
        }), 400


    connection = get_connection()
    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM medicines
        WHERE UPPER(medicine_code) = UPPER(?)
        OR UPPER(medicine_name) LIKE UPPER(?)
        """,
        (
            search_query,
            f"%{search_query}%"
        )
    )


    medicine = cursor.fetchone()

    connection.close()


    if medicine is None:

        return jsonify({
            "success": False,
            "message": "No verified medicine match found."
        }), 404


    return jsonify({
        "success": True,

        "medicine": {
            "code": medicine["medicine_code"],
            "name": medicine["medicine_name"],
            "manufacturer": medicine["manufacturer"],
            "type": medicine["medicine_type"],
            "purpose": medicine["purpose"],
            "warning": medicine["warning"]
        }
    })


@app.route(
    "/api/upload-prescription",
    methods=["POST"]
)
def upload_prescription():

    # Get patient ID from form data
    patient_id = request.form.get(
        "patient_id",
        type=int
    )


    if not patient_id:

        return jsonify({
            "success": False,
            "message": "Patient ID is required."
        }), 400


    if "file" not in request.files:

        return jsonify({
            "success": False,
            "message": "No file was uploaded."
        }), 400


    file = request.files["file"]


    if file.filename == "":

        return jsonify({
            "success": False,
            "message": "No file selected."
        }), 400


    if not allowed_file(file.filename):

        return jsonify({
            "success": False,
            "message":
                "Only JPG, JPEG, PNG and PDF files are allowed."
        }), 400


    # Get file extension
    extension = file.filename.rsplit(
        ".",
        1
    )[1].lower()


    # Generate unique filename
    unique_filename = (
        f"{uuid.uuid4()}.{extension}"
    )


    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )


    # Save the actual file
    file.save(file_path)


    # Save file information in SQLite
    connection = get_connection()
    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO prescriptions (
            patient_id,
            original_filename,
            stored_filename,
            file_type
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            patient_id,
            file.filename,
            unique_filename,
            extension
        )
    )


    prescription_id = cursor.lastrowid

    connection.commit()
    connection.close()


    return jsonify({
        "success": True,

        "message":
            "Prescription uploaded and saved successfully.",

        "prescription": {

            "id":
                prescription_id,

            "patient_id":
                patient_id,

            "original_name":
                file.filename,

            "stored_name":
                unique_filename,

            "type":
                extension
        }
    })

# ============================================
# PRESCRIPTION HISTORY
# ============================================

@app.route(
    "/api/history/<int:patient_id>",
    methods=["GET"]
)
def get_prescription_history(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            original_filename,
            stored_filename,
            file_type,
            uploaded_at

        FROM prescriptions

        WHERE patient_id = ?

        ORDER BY uploaded_at DESC
        """,
        (patient_id,)
    )

    rows = cursor.fetchall()

    connection.close()

    history = []

    for row in rows:

        history.append({
            "id": row["id"],
            "original_name": row["original_filename"],
            "stored_name": row["stored_filename"],
            "type": row["file_type"],
            "uploaded_at": row["uploaded_at"]
        })

    return jsonify({
        "success": True,
        "history": history
    })


@app.route(
    "/api/prescription-file/<filename>",
    methods=["GET"]
)
def get_prescription_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


@app.route(
    "/api/prescription/<int:prescription_id>",
    methods=["DELETE"]
)
def delete_prescription(prescription_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT stored_filename
        FROM prescriptions
        WHERE id = ?
        """,
        (prescription_id,)
    )

    prescription = cursor.fetchone()

    if prescription is None:

        connection.close()

        return jsonify({
            "success": False,
            "message": "Prescription not found."
        }), 404

    stored_filename = prescription["stored_filename"]

    cursor.execute(
        """
        DELETE FROM prescriptions
        WHERE id = ?
        """,
        (prescription_id,)
    )

    connection.commit()
    connection.close()


    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        stored_filename
    )

    if os.path.exists(file_path):

        os.remove(file_path)


    return jsonify({
        "success": True,
        "message":
            "Prescription deleted successfully."
    })


@app.route(
    "/api/medicines/search",
    methods=["GET"]
)
def search_medicines():

    query = request.args.get(
        "q",
        ""
    ).strip()


    if not query:

        return jsonify({
            "success": False,
            "message": "Search query is required."
        }), 400


    connection = get_connection()
    cursor = connection.cursor()


    search_query = f"%{query}%"


    cursor.execute(
        """
        SELECT
            id,
            medicine_code,
            medicine_name,
            manufacturer,
            medicine_type,
            purpose,
            warning

        FROM medicines

        WHERE LOWER(medicine_name) LIKE LOWER(?)
           OR LOWER(medicine_code) LIKE LOWER(?)

        ORDER BY medicine_name
        """,
        (
            search_query,
            search_query
        )
    )


    rows = cursor.fetchall()

    connection.close()


    medicines = []


    for row in rows:

        medicines.append({

            "id":
                row["id"],

            "name":
                row["medicine_name"],

            "code":
                row["medicine_code"],

            "manufacturer":
                row["manufacturer"],

            "type":
                row["medicine_type"],

            "purpose":
                row["purpose"],

            "warning":
                row["warning"]
        })


    return jsonify({

        "success": True,

        "count":
            len(medicines),

        "medicines":
            medicines
    })

@app.route(
    "/api/patient/<int:patient_id>",
    methods=["GET"]
)
def get_patient_profile(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            patient_name,
            verification_id,
            email,
            phone,
            age,
            gender,
            blood_group
        FROM patients
        WHERE id = ?
        """,
        (patient_id,)
    )

    patient = cursor.fetchone()

    connection.close()

    if patient is None:

        return jsonify({
            "success": False,
            "message": "Patient not found."
        }), 404


    return jsonify({
        "success": True,
        "patient": {
            "id": patient["id"],
            "name": patient["patient_name"],
            "verification_id": patient["verification_id"],
            "email": patient["email"],
            "phone": patient["phone"],
            "age": patient["age"],
            "gender": patient["gender"],
            "blood_group": patient["blood_group"]
        }
    })

@app.route(
    "/api/patient/<int:patient_id>",
    methods=["PUT"]
)
def update_patient_profile(patient_id):

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No profile data received."
        }), 400


    connection = get_connection()
    cursor = connection.cursor()


    # Check whether patient exists
    cursor.execute(
        """
        SELECT id
        FROM patients
        WHERE id = ?
        """,
        (patient_id,)
    )

    patient = cursor.fetchone()


    if patient is None:

        connection.close()

        return jsonify({
            "success": False,
            "message": "Patient not found."
        }), 404


    # Get profile information
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    age = data.get("age")
    gender = data.get("gender", "").strip()
    blood_group = data.get(
        "blood_group",
        ""
    ).strip()


    # Convert age to integer if provided
    if age == "":
        age = None

    elif age is not None:

        try:
            age = int(age)

        except (ValueError, TypeError):

            connection.close()

            return jsonify({
                "success": False,
                "message": "Age must be a valid number."
            }), 400


    cursor.execute(
        """
        UPDATE patients

        SET
            email = ?,
            phone = ?,
            age = ?,
            gender = ?,
            blood_group = ?

        WHERE id = ?
        """,
        (
            email,
            phone,
            age,
            gender,
            blood_group,
            patient_id
        )
    )


    connection.commit()
    connection.close()


    return jsonify({
        "success": True,
        "message":
            "Patient profile updated successfully."
    })

# ============================================
# START SERVER
# ============================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )