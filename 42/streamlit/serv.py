# server_echo.py
from flask import Flask, request
app = Flask(__name__)

@app.post("/ping")
def ping():
    print("BODY:", request.data)          # увидишь в консоли
    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)