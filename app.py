import os
from datetime import datetime, timezone
import certifi
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app, origins=[
    "https://www.flashawayfentanyl.org",
    "https://flashawayfentanyl.org",
    "http://localhost:3000",
    "http://127.0.0.1:5500"
])

MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=10000) if MONGO_URI else None
db = client["flash_away_fentanyl"] if client else None
stories_collection = db["stories"] if db is not None else None


@app.get("/health")
def health_check():
    return jsonify({"status": "ok", "database_configured": stories_collection is not None}), 200


@app.get("/api/stories")
def get_stories():
    if stories_collection is None:
        return jsonify({"stories": [], "warning": "MONGO_URI not configured yet"}), 200
    docs = list(stories_collection.find({"status": "approved"}, {"_id": 0}).sort("created_at", -1))
    return jsonify({"stories": docs}), 200


@app.post("/api/stories")
def create_story():
    if stories_collection is None:
        return jsonify({"error": "Database not configured on server."}), 500

    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    author = (payload.get("author") or "").strip()
    category = (payload.get("category") or "Family & Community Impact").strip()
    body = (payload.get("body") or "").strip()

    if not title or not author or not body:
        return jsonify({"error": "Title, author, and story text are required."}), 400

    if len(title) > 160 or len(author) > 120 or len(body) > 10000:
        return jsonify({"error": "One or more fields exceed the maximum allowed length."}), 400

    story = {
        "title": title,
        "author": author,
        "category": category,
        "body": body,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    stories_collection.insert_one(story)
    return jsonify({"message": "Story submitted and awaiting review."}), 201


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
