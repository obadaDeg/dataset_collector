from flask import Flask, request, jsonify
import os
import re


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

@app.route("/", methods=["GET"])
def hello_world():
    return "Hello, World!"

@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Endpoint to upload video and JSON data files.
    """
    print(request.files)  # Debug: Print the incoming files

    # Validate presence of required files
    if "video" not in request.files or "json" not in request.files:
        print("Video and JSON data are required")
        return jsonify({"message": "Video and JSON data are required"}), 400

    video = request.files["video"]
    json_data = request.files["json"]

    print(video)  # Debug: Print video file details
    print(json_data)  # Debug: Print JSON file details

    # Validate MIME types
    if video.mimetype != "video/mp4":
        return jsonify({"message": "Video must be an MP4 file"}), 400

    if json_data.mimetype != "application/json":
        return jsonify({"message": "JSON data must be a .json file"}), 400

    # Assign sanitized filenames and enforce .mp4 extension for video
    video_filename = sanitize_filename(video.filename)
    json_filename = sanitize_filename(json_data.filename)

    # Ensure the video filename ends with .mp4
    if not video_filename.lower().endswith(".mp4"):
        video_filename = os.path.splitext(video_filename)[0] + ".mp4"

    # Assign file paths
    video_path = os.path.join(VIDEO_FOLDER, video_filename)
    json_path = os.path.join(JSON_FOLDER, json_filename)

    # Ensure unique filenames
    video_path = _generate_unique_filename(video_path)
    json_path = _generate_unique_filename(json_path)

    # Confirm directories exist
    os.makedirs(VIDEO_FOLDER, exist_ok=True)
    os.makedirs(JSON_FOLDER, exist_ok=True)

    try:
        # Save files
        print(f"Saving video to {video_path}")
        video.save(video_path)
        print(f"Saving JSON to {json_path}")
        json_data.save(json_path)
    except Exception as e:
        print(f"Error saving files: {str(e)}")
        return jsonify({"message": f"Error saving files: {str(e)}"}), 500

    return (
        jsonify(
            {
                "message": "Files uploaded successfully",
                "video_path": video_path,
                "json_path": json_path,
            }
        ),
        200,
    )


def _generate_unique_filename(file_path):
    """
    Generate a unique filename if the file already exists.
    """
    base, ext = os.path.splitext(file_path)
    counter = 1
    while os.path.exists(file_path):
        file_path = f"{base}_{counter}{ext}"
        counter += 1
    return file_path


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
