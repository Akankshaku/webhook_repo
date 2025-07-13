import os, datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
events = db[os.getenv("COLLECTION")]

def format_doc(event_type, payload):
    author = payload.get("sender", {}).get("login", "unknown")
    now = datetime.datetime.utcnow()
    doc = {"type": event_type, "author": author, "timestamp": now}

    if event_type == "push":
        doc["to_branch"] = payload["ref"].split("/")[-1]
    elif event_type == "pull_request":
        pr = payload["pull_request"]
        doc["from_branch"] = pr["head"]["ref"]
        doc["to_branch"] = pr["base"]["ref"]
        if payload.get("action") == "closed" and pr.get("merged"):
            event_type = "merge"
            doc["type"] = "merge"
    return doc

@app.route("/webhook", methods=["POST"])
def webhook():
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    payload = request.get_json()
    doc = format_doc(event_type, payload)
    events.insert_one(doc)
    return {"status": "ok"}, 200

@app.route("/events/latest", methods=["GET"])
def latest_events():
    docs = events.find().sort("timestamp", -1).limit(20)
    return jsonify([{
        "type": d["type"],
        "author": d["author"],
        "to_branch": d.get("to_branch"),
        "from_branch": d.get("from_branch"),
        "timestamp": d["timestamp"].isoformat() + "Z"
    } for d in docs])

@app.route("/")
def home():
    return app.send_static_file("index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)

