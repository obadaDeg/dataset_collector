from flask import Flask, request, jsonify, send_file
import os
import re
import json
from datetime import datetime
import zipfile
from io import BytesIO


# Utility function to sanitize filenames
def sanitize_filename(filename):
    """
    Replace invalid characters in the filename with underscores.
    """
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", filename)


app = Flask(__name__)

# Directory to save uploads
UPLOAD_FOLDER = os.path.abspath("./uploads")
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, "videos")
JSON_FOLDER = os.path.join(UPLOAD_FOLDER, "json_data")

# Ensure directories exist
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(JSON_FOLDER, exist_ok=True)


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

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/download/<timestamp>", methods=["GET"])
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


@app.route("/list", methods=["GET"])
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
def download_all_datasets():
    """
    Endpoint to download all datasets (videos and their corresponding JSON files) as a single ZIP archive.
    """
    try:
        zip_buffer = BytesIO()
        missing_files = []  # Track datasets missing JSON files

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            # Iterate through all video files
            for video_filename in os.listdir(VIDEO_FOLDER):
                if video_filename.endswith(".mp4"):
                    # Extract the timestamp from the video filename
                    timestamp = "-".join(video_filename.split("-")[:2])
                    video_path = os.path.join(VIDEO_FOLDER, video_filename)

                    # Find the matching JSON file
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

                    # Add files to the ZIP
                    folder_name = timestamp
                    zip_file.write(
                        video_path, arcname=os.path.join(folder_name, video_filename)
                    )
                    zip_file.write(
                        json_path, arcname=os.path.join(folder_name, json_filename)
                    )

        zip_buffer.seek(0)  # Reset the buffer position to the start

        if missing_files:
            print(f"Missing JSON files: {missing_files}")

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="all_datasets.zip",
        )

    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
