import os
import sys
import cv2
import torch
import easyocr
from pathlib import Path

# Fix Windows Path issue for PosixPath
import pathlib
if os.name == "nt":
    pathlib.PosixPath = pathlib.WindowsPath

def sanitize_plate_text(text: str) -> str:
    import re
    return re.sub(r"[^A-Z0-9]", "", text.upper())

def main():
    base_dir = Path(__file__).resolve().parent
    
    print("Loading models...")
    model_path = base_dir / "NumberPlate" / "model" / "best.pt"
    yolo_repo = base_dir / "NumberPlate" / "yolov5"
    
    if not model_path.exists() or not yolo_repo.exists():
        print("Error: Could not find model or YOLOv5 repository")
        sys.exit(1)
        
    model = torch.hub.load(str(yolo_repo), "custom", path=str(model_path), source="local")
    model.conf = 0.35
    model.iou = 0.45
    
    reader = easyocr.Reader(["en"], gpu=False)
    
    # Check if a specific image path is passed
    if len(sys.argv) > 1:
        image_paths = [Path(sys.argv[1])]
    else:
        # Default to all images in NP_Images
        images_dir = base_dir / "NumberPlate" / "NP_Images"
        image_paths = sorted(
            list(images_dir.glob("*.jpg")) + 
            list(images_dir.glob("*.jpeg")) + 
            list(images_dir.glob("*.png")),
            key=lambda x: x.name
        )
        
    print(f"\nProcessing {len(image_paths)} image(s)...")
    print("-" * 60)
    print(f"{'Image Name':<20} | {'Detected Plate':<18} | {'Confidence'}")
    print("-" * 60)
    
    for path in image_paths:
        frame = cv2.imread(str(path))
        if frame is None:
            print(f"{path.name:<20} | Error: Unable to read image")
            continue
            
        results = model(frame)
        out = results.pandas().xyxy[0]
        if out is None or len(out) == 0:
            print(f"{path.name:<20} | No plate detected    | -")
            continue
            
        out = out.sort_values("confidence", ascending=False)
        top = out.iloc[0]
        xmin, ymin, xmax, ymax = int(top["xmin"]), int(top["ymin"]), int(top["xmax"]), int(top["ymax"])
        det_conf = float(top["confidence"])
        
        # Extract ROI with margin
        margin_x = max(2, int((xmax - xmin) * 0.08))
        margin_y = max(2, int((ymax - ymin) * 0.2))
        x1 = max(0, xmin - margin_x)
        y1 = max(0, ymin - margin_y)
        x2 = min(frame.shape[1], xmax + margin_x)
        y2 = min(frame.shape[0], ymax + margin_y)
        roi = frame[y1:y2, x1:x2]
        
        # Read text using easyocr
        ocr_result = reader.readtext(roi, detail=1, paragraph=False, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        if not ocr_result:
            print(f"{path.name:<20} | OCR failed           | {det_conf:.2f} (det)")
            continue
            
        # Find candidate with highest confidence
        best_ocr = sorted(ocr_result, key=lambda x: x[2], reverse=True)[0]
        cleaned = sanitize_plate_text(best_ocr[1])
        print(f"{path.name:<20} | {cleaned:<18} | {best_ocr[2]:.2f}")
        
    print("-" * 60)

if __name__ == "__main__":
    main()
