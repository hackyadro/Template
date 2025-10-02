from flask import Flask, jsonify
import state

app = Flask(__name__)

@app.route("/position", methods=["GET"])
def get_position():
    data = state.load_last_position()
    if not data:
        return jsonify({"status": "waiting", "message": "Нет данных о позиции"}), 200

    eq = data.get("environment_quality", {}) or {}
    return jsonify({
        "status": "ok",
        "position": {
            "x": data.get("x"),
            "y": data.get("y"),
            "accuracy": data.get("accuracy_estimate"),
            "quality": eq.get("quality"),
            "stability": eq.get("stability"),
            "anchors_used": data.get("anchors_used"),
        }
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)