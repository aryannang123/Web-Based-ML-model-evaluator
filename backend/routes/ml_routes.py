from flask import Blueprint, jsonify

ml_bp = Blueprint("ml", __name__, url_prefix="/api/ml")

@ml_bp.route("/algorithms", methods=["GET"])
def get_algorithms():
    # TODO: US-17: Implement ML algorithm selection
    # Assigned to: @gaganraghavan
    # Return available classification and regression models
    return jsonify({
        "classification": ["logistic_regression", "decision_tree", "random_forest", "knn"],
        "regression": ["linear_regression", "decision_tree", "random_forest", "knn"]
    }), 200

@ml_bp.route("/train", methods=["POST"])
def train_model():
    # TODO: US-18: Implement model training
    # Assigned to: @aryannang123
    # Steps:
    # 1. Parse target_column, algorithm, split_ratio
    # 2. Invoke preprocessor and train model
    # 3. Call US-19 evaluation and save model weights
    return jsonify({"message": "Model training endpoint ready for US-18 implementation"}), 501

@ml_bp.route("/evaluate", methods=["POST"])
def evaluate_model():
    # TODO: US-19: Implement model evaluation and visualization
    # Assigned to: @abhishekdeene-eng
    # Compute accuracy, F1, RMSE, R2, and confusion matrix
    return jsonify({"message": "Model evaluation endpoint ready for US-19 implementation"}), 501
