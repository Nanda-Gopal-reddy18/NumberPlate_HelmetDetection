import os
import sys
import cv2 as cv
from pathlib import Path

# Fix Windows Path issue for PosixPath
import pathlib
if os.name == "nt":
    pathlib.PosixPath = pathlib.WindowsPath

# Add HelmetDetection folder to path so we can import from it
sys.path.append(str(Path(__file__).resolve().parent / "HelmetDetection"))
from HelmetDetection import ViolationEngine

def main():
    base_dir = Path(__file__).resolve().parent
    app_dir = base_dir / "HelmetDetection"
    
    print("Loading Helmet Detection & Plate models...")
    engine = ViolationEngine(app_dir)
    engine.load_models()
    
    # Check if image path is passed as argument
    if len(sys.argv) > 1:
        image_paths = [Path(sys.argv[1])]
    else:
        bikes_dir = app_dir / "bikes"
        image_paths = sorted(
            list(bikes_dir.glob("*.jpg")) + 
            list(bikes_dir.glob("*.jpeg")) + 
            list(bikes_dir.glob("*.png")),
            key=lambda x: x.name
        )
        
    print(f"\nProcessing {len(image_paths)} image(s) for helmet violations...")
    print("-" * 90)
    print(f"{'Image Name':<15} | {'Riders':<8} | {'No-Helmet':<10} | {'Plate Number':<15} | {'Challan'}")
    print("-" * 90)
    
    for path in image_paths:
        frame = cv.imread(str(path))
        if frame is None:
            print(f"{path.name:<15} | Error reading image")
            continue
            
        # Analyze using the production-grade ViolationEngine
        result = engine.analyze(frame, "India")
        
        riders_count = len(result["riders"])
        no_helmet_count = result["no_helmet_count"]
        plate_text = result["plate_text"] if result["plate_text"] else "Not detected"
        
        challan = result["challan"]
        challan_str = f"{challan['fine_total']}" if challan else "None"
        
        print(f"{path.name:<15} | {riders_count:<8} | {no_helmet_count:<10} | {plate_text:<15} | {challan_str}")
        
    print("-" * 90)

if __name__ == "__main__":
    main()
