from flask import Blueprint, jsonify

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    # TODO: US-04: Implement user registration
    # Assigned to: @nidhipoojamrutha20
    # Steps:
    # 1. Parse JSON body (username, email, password)
    # 2. Validate input and check if user already exists
    # 3. Hash password and save user record to database
    return jsonify({"message": "Registration endpoint ready for US-04 implementation"}), 501

@auth_bp.route("/login", methods=["POST"])
def login():
    # TODO: US-05: Implement user login
    # Assigned to: @gaganraghavan
    # Steps:
    # 1. Parse JSON body (username, password)
    # 2. Verify user credentials against database
    # 3. Establish user session or generate auth token
    return jsonify({"message": "Login endpoint ready for US-05 implementation"}), 501

@auth_bp.route("/logout", methods=["POST"])
def logout():
    # TODO: US-06: Implement logout and session management
    # Assigned to: @aryannang123
    return jsonify({"message": "Logout endpoint ready for US-06 implementation"}), 501
