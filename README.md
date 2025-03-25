# Video Collection API

## Project Overview

This project is a Flask-based backend API deployed on Vercel Cloud that facilitates the collection of video datasets from remote participants. The system was specifically designed to overcome geographical challenges in gathering posture data for pose estimation research.

The API allows participants to easily upload videos along with corresponding motion sensor data (gyroscope and accelerometer), which are then stored securely on the server. The collected dataset was successfully used to analyze posture patterns for a pose estimation project.

## Key Features

- **Secure Video & Sensor Data Collection**: Upload MP4 videos with corresponding JSON sensor data
- **Authentication**: API endpoints protected with token-based authentication
- **Dataset Management**: Download individual datasets or all collected datasets as ZIP archives
- **Debugging and Maintenance**: Endpoints for listing available datasets and system diagnostics

## API Endpoints

### Upload Endpoint
```
POST /upload
```
Accepts video (MP4) and JSON data files. JSON files should contain gyroscope and accelerometer data.

### Download Endpoints
```
GET /download/<timestamp>
GET /all
GET /download_all
GET /all_stream
```
These endpoints allow downloading individual datasets by timestamp or all datasets as a ZIP archive. The `/all_stream` endpoint is optimized for streaming large collections.

### Management Endpoints
```
GET /list
GET /debug
GET /delete_all
```
List available datasets, debug file structure, or delete all datasets.

## Authentication

All endpoints (except for upload) require authentication using a Bearer token in the Authorization header:
```
Authorization: Bearer <API_SECRET_TOKEN>
```

## Project Success

The API successfully facilitated the collection of 90 videos from participants, capturing various posture patterns. These videos were then analyzed as part of a pose estimation research project.

## Deployment

The application is configured to deploy on Vercel using the included Procfile:
```
web: gunicorn app:app --timeout 1000 --bind 0.0.0.0:$PORT
```

## Environment Variables

The application requires the following environment variable:
- `API_SECRET_TOKEN`: Secret token for API authentication

## Technical Details

### Dependencies
- Flask
- Flask-CORS
- gunicorn
- python-dotenv

### Data Structure
- Videos are stored in the `uploads/videos` directory
- JSON data is stored in the `uploads/json_data` directory
- Each file is timestamped to maintain association between video and sensor data

## Security Considerations

- The API uses bearer token authentication
- Filenames are sanitized to prevent path traversal attacks
- File types are verified before storage
- Directories are checked for write permissions on startup

---

This project demonstrates how cloud-based APIs can help overcome geographical limitations in research data collection, enabling collaborative projects despite physical distance constraints.
