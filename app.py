from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import os
import re
import json
from datetime import datetime
import zipfile
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

# Secret token to authenticate API requests
API_SECRET_TOKEN = os.environ.get("API_SECRET_TOKEN")

if not API_SECRET_TOKEN:
    raise ValueError("API_SECRET_TOKEN environment variable is not set!")

# Utility function to sanitize filenames
def sanitize_filename(filename):
    """
    Replace invalid characters in the filename with underscores.
    """
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", filename)


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Directory to save uploads
UPLOAD_FOLDER = os.path.join(os.environ.get("HOME", "/tmp"), "uploads")
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, "videos")
JSON_FOLDER = os.path.join(UPLOAD_FOLDER, "json_data")

# Ensure directories exist
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(JSON_FOLDER, exist_ok=True)

if not os.access(VIDEO_FOLDER, os.W_OK) or not os.access(JSON_FOLDER, os.W_OK):
    raise PermissionError("Upload directories are not writable.")



def require_auth(func):
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token or token != f"Bearer {API_SECRET_TOKEN}":
            return jsonify({"message": "Unauthorized"}), 403
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Endpoint to upload video and JSON data files.
    """
    if "video" not in request.files or "json" not in request.files:
        return jsonify({"message": "Video and JSON data are required"}), 400

    video = request.files["video"]
    json_data_file = request.files["json"]

    # Check if the video file is an actual file object
    if video.filename == "":
        return jsonify({"message": "No video file uploaded"}), 400

    if json_data_file.filename == "":
        return jsonify({"message": "No JSON file uploaded"}), 400

    if video.mimetype != "video/mp4":
        return jsonify({"message": "Video must be an MP4 file"}), 400

    if json_data_file.mimetype != "application/json":
        return jsonify({"message": "JSON data must be a .json file"}), 400

    # Sanitize filenames and add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    video_filename = sanitize_filename(video.filename)
    if not video_filename.lower().endswith(".mp4"):
        video_filename = os.path.splitext(video_filename)[0] + ".mp4"
    video_filename = f"{timestamp}-{video_filename}"

    json_filename = sanitize_filename(json_data_file.filename)
    json_filename = f"{timestamp}-{json_filename}"

    # File paths
    video_path = os.path.join(VIDEO_FOLDER, video_filename)
    json_path = os.path.join(JSON_FOLDER, json_filename)

    try:
        # Save files to designated directories
        os.makedirs(VIDEO_FOLDER, exist_ok=True)
        os.makedirs(JSON_FOLDER, exist_ok=True)

        video.save(video_path)
        json_data_file.save(json_path)

        # Read and parse the JSON file
        with open(json_path, "r") as f:
            json_data = json.load(f)

        # Construct response data
        response_data = {
            "video": os.path.relpath(video_path, UPLOAD_FOLDER),
            "gyroscopeData": json_data.get("gyroscopeData", []),
            "accelerometerData": json_data.get("accelerometerData", []),
        }
        
        print(f"Uploaded video: {video_filename}")
        print(f"Uploaded JSON: {json_filename}")
        # path
        print(f"Video path: {video_path}")
        print(f"JSON path: {json_path}")

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/download/<timestamp>", methods=["GET"])
@require_auth
def download_dataset(timestamp):
    """
    Endpoint to download video and JSON data as a dataset based on timestamp.
    """
    try:
        # Construct file paths
        video_filename = f"{timestamp}.mp4"
        json_filename = f"{timestamp}.json"
        video_path = os.path.join(VIDEO_FOLDER, video_filename)
        json_path = os.path.join(JSON_FOLDER, json_filename)

        # Validate file existence
        if not os.path.exists(video_path):
            return jsonify({"message": f"Video file {video_filename} not found"}), 404
        if not os.path.exists(json_path):
            return jsonify({"message": f"JSON file {json_filename} not found"}), 404

        # Create a ZIP archive in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            zip_file.write(video_path, arcname=video_filename)
            zip_file.write(json_path, arcname=json_filename)

        zip_buffer.seek(0)  # Move to the beginning of the buffer

        # Return the ZIP file as a downloadable response
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{timestamp}_dataset.zip",
        )

    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@app.route("/all", methods=["GET"])
@require_auth
def download_all():
    try:
        # Create a ZIP buffer
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            # Add all video files to a "videos" folder in the ZIP
            for video_filename in os.listdir(VIDEO_FOLDER):
                if video_filename.endswith(".mp4"):
                    video_path = os.path.join(VIDEO_FOLDER, video_filename)
                    zip_file.write(video_path, arcname=os.path.join("videos", video_filename))

            # Add all JSON files to a "json_data" folder in the ZIP
            for json_filename in os.listdir(JSON_FOLDER):
                if json_filename.endswith(".json"):
                    json_path = os.path.join(JSON_FOLDER, json_filename)
                    zip_file.write(json_path, arcname=os.path.join("json_data", json_filename))

        # Move the ZIP buffer to the beginning
        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="all_datasets_separated.zip",
        )
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/list", methods=["GET"])
@require_auth
def list_datasets():
    """
    Endpoint to list available datasets.
    """
    datasets = []
    for filename in os.listdir(VIDEO_FOLDER):
        if filename.endswith(".mp4"):
            timestamp = os.path.splitext(filename)[0]
            datasets.append(timestamp)

    return jsonify(datasets), 200


@app.route("/download_all", methods=["GET"])
@require_auth
def download_all_datasets():
    try:
        print(f"Video Folder: {os.listdir(VIDEO_FOLDER)}")
        print(f"JSON Folder: {os.listdir(JSON_FOLDER)}")
        zip_buffer = BytesIO()
        missing_files = []

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for video_filename in os.listdir(VIDEO_FOLDER):
                if video_filename.endswith(".mp4"):
                    timestamp = "-".join(video_filename.split("-")[:2])
                    video_path = os.path.join(VIDEO_FOLDER, video_filename)

                    matching_json_files = [
                        f
                        for f in os.listdir(JSON_FOLDER)
                        if timestamp in f and f.endswith(".json")
                    ]

                    if not matching_json_files:
                        missing_files.append(f"{timestamp}/Missing JSON")
                        continue

                    json_filename = matching_json_files[0]
                    json_path = os.path.join(JSON_FOLDER, json_filename)

                    folder_name = timestamp
                    zip_file.write(
                        video_path, arcname=os.path.join(folder_name, video_filename)
                    )
                    zip_file.write(
                        json_path, arcname=os.path.join(folder_name, json_filename)
                    )

        zip_buffer.seek(0)
        if missing_files:
            print(f"Missing JSON files: {missing_files}")

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="all_datasets.zip",
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500




@app.route("/debug", methods=["GET"])
@require_auth
def debug_files():
    return jsonify(
        {
            "videos": (
                os.listdir(VIDEO_FOLDER) if os.path.exists(VIDEO_FOLDER) else "Missing"
            ),
            "json_data": (
                os.listdir(JSON_FOLDER) if os.path.exists(JSON_FOLDER) else "Missing"
            ),
        }
    )
    
    
@app.route("/delete_all", methods=["GET"])
@require_auth
def delete_all():
    try:
        for filename in os.listdir(VIDEO_FOLDER):
            if filename.endswith(".mp4"):
                timestamp = os.path.splitext(filename)[0]
                video_path = os.path.join(VIDEO_FOLDER, filename)
                json_filename = f"{timestamp}.json"
                json_path = os.path.join(JSON_FOLDER, json_filename)

                if os.path.exists(video_path):
                    os.remove(video_path)
                if os.path.exists(json_path):
                    os.remove(json_path)

        return jsonify({"message": "All datasets deleted"}), 200
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
    
@app.route("/all_stream", methods=["GET"])
@require_auth
def download_all_stream():
    def generate_zip():
        with zipfile.ZipFile("temp.zip", "w") as zip_file:
            # Add your files one by one
            for video_filename in os.listdir(VIDEO_FOLDER):
                if video_filename.endswith(".mp4"):
                    video_path = os.path.join(VIDEO_FOLDER, video_filename)
                    zip_file.write(video_path, arcname=os.path.join("videos", video_filename))
            # etc. for JSON files

        # Read the temp.zip file in chunks
        with open("temp.zip", "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk

    return Response(generate_zip(), mimetype="application/zip",
                    headers={
                        'Content-Disposition': 'attachment; filename=all_datasets_streamed.zip'
                    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
