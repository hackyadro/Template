from flask import Flask, jsonify
import state

app = Flask(__name__)

@app.route("/position", methods=["GET"])
def get_position():
    if state.last_position is None:
        return jsonify({"status": "waiting", "message": "Нет данных о позиции"}), 200
    return jsonify({
        "status": "ok",
        "position": {
            "x": state.last_position["x"],
            "y": state.last_position["y"],
            "accuracy": state.last_position["accuracy_estimate"],
            "quality": state.last_position["environment_quality"]["quality"],
            "stability": state.last_position["environment_quality"]["stability"],
            "anchors_used": state.last_position["anchors_used"],
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)