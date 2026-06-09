import os
import sys
import cv2
import numpy as np
import base64
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Fix Windows Path issue for PosixPath
import pathlib
if os.name == "nt":
    pathlib.PosixPath = pathlib.WindowsPath

# Add current folder to path so we can import detector
sys.path.append(str(Path(__file__).resolve().parent))
from detector import ViolationEngine, USER_DATABASE, send_violation_email, build_violation_message

app = Flask(__name__)
# Enable CORS for all routes
CORS(app)

# Initialize and pre-load the models to speed up API responses
app_dir = Path(__file__).resolve().parent
print("Initializing Violation Detection Engine...")
engine = ViolationEngine(app_dir)
print("Loading Deep Learning Models (this can take a few moments)...")
engine.load_models()
print("Models loaded successfully. Starting API service...")

@app.route("/")
def home():
    # Render the drag-and-drop Web UI interface
    return render_template("index.html")

@app.route("/detect", methods=["POST"])
def detect():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided in the request field 'image'"}), 400
        
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Selected file is empty"}), 400
        
    try:
        # Read image bytes directly from memory without saving to disk
        img_bytes = file.read()
        np_img = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({"error": "Invalid or corrupted image format"}), 400
            
        # Get optional country query parameter (default to India)
        country = request.args.get("country", "India")
        mode = request.args.get("mode", "helmet")
        
        # Run inference using the shared ViolationEngine
        if mode == "plate":
            result = engine.analyze_plate(frame, country)
        else:
            result = engine.analyze(frame, country)
            
        # Check if the filename stem matches a user in USER_DATABASE to send email violation alerts
        filename = file.filename
        if filename:
            image_name = Path(filename).stem
            user = USER_DATABASE.get(image_name)
            if user:
                import time
                if mode == "plate":
                    if not result["plate_detected"] or not result["plate_valid"]:
                        try:
                            msg = "🚨 License Plate Violation Detected\n\n"
                            if not result["plate_detected"]:
                                msg += "❌ License Plate Not Detected\n"
                            elif not result["plate_valid"]:
                                msg += "⚠ Invalid License Plate Format\n"
                            msg += f"\nPlate: {result['plate_text'] if result['plate_text'] else 'Not detected'}"
                            msg += f"\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                            send_violation_email(
                                user["email"],
                                "License Plate Violation Alert 🚨",
                                msg
                            )
                        except Exception as email_err:
                            print(f"⚠️ Email sending failed: {email_err}")
                else: # helmet mode
                    if result["no_helmet_count"] > 0 or not result["plate_detected"]:
                        try:
                            message = build_violation_message(result)
                            send_violation_email(
                                user["email"],
                                "Traffic Violation Alert 🚨",
                                message
                            )
                        except Exception as email_err:
                            print(f"⚠️ Email sending failed: {email_err}")
        
        # Encode the annotated frame to JPEG base64 to render directly inside the web browser
        annotated_frame = result["annotated_frame"]
        _, buffer = cv2.imencode(".jpg", annotated_frame)
        annotated_b64 = base64.b64encode(buffer).decode("utf-8")
        
        return jsonify({
            "no_helmet_count": result.get("no_helmet_count", 0),
            "plate": result["plate_text"],
            "plate_valid": result["plate_valid"],
            "challan": result["challan"],
            "vehicle_details": result["vehicle_details"],
            "annotated_image": annotated_b64,
            "ocr_candidates": result.get("ocr_candidates", [])
        })
        
    except Exception as exc:
        print(f"API Error during detection: {exc}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(exc)}"}), 500

if __name__ == "__main__":
    # Bind to 0.0.0.0 and port 5000
    app.run(host="0.0.0.0", port=5000)
