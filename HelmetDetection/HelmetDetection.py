import os
import sys
import pathlib
from pathlib import Path
import cv2 as cv
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict, List, Optional, Tuple

# Fix Windows Path issue for PosixPath
if os.name == "nt":
    pathlib.PosixPath = pathlib.WindowsPath

# Add current folder to path so we can import detector
sys.path.append(str(Path(__file__).resolve().parent))

from detector import (
    ViolationEngine,
    Detection,
    first_existing_path,
    clip_box,
    box_area,
    intersection_area,
    box_iou,
    flatten_indices,
    wrapped_lines,
    draw_text_label,
    sanitize_plate_text,
    coerce_by_pattern,
    normalize_india_plate,
    normalize_plate,
    send_violation_email,
    build_violation_message,
    ensure_pkg_resources_available,
    CHALLAN_RULES,
    USER_DATABASE
)

class HelmetDetectionApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Helmet and Number Plate Enforcement")
        self.root.geometry("1320x900")
        self.root.minsize(1160, 780)
        self.root.configure(bg="#eaf0f8")

        self.app_dir = Path(__file__).resolve().parent
        self.engine = ViolationEngine(self.app_dir)

        self.selected_image: Optional[Path] = None
        self.preview_photo = None

        self.country_var = tk.StringVar(value="India")
        self.status_var = tk.StringVar(value="Ready")
        self.image_var = tk.StringVar(value="No image selected")

        self._build_styles()
        self._build_ui()

    def _build_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Header.TLabel", font=("Segoe UI", 23, "bold"), foreground="#0b1220", background="#eaf0f8")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 10), foreground="#334155", background="#eaf0f8")
        style.configure("Card.TFrame", background="#ffffff", relief="flat", borderwidth=1)
        style.configure("CardTitle.TLabel", font=("Segoe UI", 12, "bold"), foreground="#111827", background="#ffffff")
        style.configure("CardBody.TLabel", font=("Segoe UI", 10), foreground="#1f2937", background="#ffffff")
        style.configure("TSeparator", background="#d1d9e6")
        style.configure("TCombobox", fieldbackground="#f8fafc", background="#f8fafc", arrowsize=16)
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            foreground="#ffffff",
            background="#0b5fff",
            borderwidth=0,
            focuscolor="#0b5fff",
            padding=(10, 8),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#004ed0"), ("pressed", "#003aa3")],
            foreground=[("disabled", "#cbd5e1"), ("!disabled", "#ffffff")],
        )

    def _build_ui(self) -> None:
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=1)

        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)

        header = ttk.Frame(self.root, style="Card.TFrame", padding=(24, 18))
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(header, text="Helmet Violation and Plate Intelligence", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="rider-helmet validation, vehicle details, and country-based challan summary.",
            style="SubHeader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        controls = ttk.Frame(self.root, style="Card.TFrame", padding=18)
        controls.grid(row=1, column=0, sticky="nsew", padx=(14, 8), pady=(0, 8))
        controls.grid_columnconfigure(0, weight=1)

        ttk.Label(controls, text="Controls", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))

        ttk.Label(controls, text="Country", style="CardBody.TLabel").grid(row=1, column=0, sticky="w")
        country_combo = ttk.Combobox(
            controls,
            textvariable=self.country_var,
            values=list(CHALLAN_RULES.keys()),
            state="readonly",
            width=26,
        )
        country_combo.grid(row=2, column=0, sticky="ew", pady=(4, 10))

        ttk.Button(controls, text="Load Models", command=self.load_models, style="Primary.TButton").grid(
            row=3, column=0, sticky="ew", pady=4
        )
        ttk.Button(controls, text="Select Image", command=self.select_image).grid(row=4, column=0, sticky="ew", pady=4)
        ttk.Button(controls, text="Analyze", command=self.analyze_image, style="Primary.TButton").grid(
            row=5, column=0, sticky="ew", pady=4
        )
        ttk.Button(controls, text="Clear", command=self.clear_results).grid(row=6, column=0, sticky="ew", pady=4)

        ttk.Separator(controls, orient="horizontal").grid(row=7, column=0, sticky="ew", pady=10)

        ttk.Label(controls, text="Selected Image", style="CardBody.TLabel").grid(row=8, column=0, sticky="w")
        ttk.Label(controls, textvariable=self.image_var, style="CardBody.TLabel", wraplength=260).grid(
            row=9, column=0, sticky="w", pady=(4, 10)
        )

        ttk.Label(controls, text="Status", style="CardBody.TLabel").grid(row=10, column=0, sticky="w")
        ttk.Label(controls, textvariable=self.status_var, style="CardBody.TLabel", wraplength=260).grid(
            row=11, column=0, sticky="w", pady=(4, 0)
        )

        preview_card = ttk.Frame(self.root, style="Card.TFrame", padding=18)
        preview_card.grid(row=1, column=1, sticky="nsew", padx=(8, 14), pady=(0, 8))
        preview_card.grid_rowconfigure(1, weight=1)
        preview_card.grid_columnconfigure(0, weight=1)

        ttk.Label(preview_card, text="Detection Preview", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.preview_label = tk.Label(
            preview_card,
            anchor="center",
            bg="#020617",
            fg="#94a3b8",
            text="No preview",
            font=("Segoe UI", 13, "bold"),
            bd=0,
            highlightthickness=0,
        )
        self.preview_label.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        log_card = ttk.Frame(self.root, style="Card.TFrame", padding=18)
        log_card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=14, pady=(0, 14))
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        ttk.Label(log_card, text="Workflow Output", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.log_text = ScrolledText(
            log_card,
            height=12,
            font=("Consolas", 10),
            bg="#020617",
            fg="#e5e7eb",
            insertbackground="white",
            borderwidth=0,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.log_text.configure(state="disabled")

    def set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.root.update_idletasks()

    def log(self, text: str, clear: bool = False) -> None:
        self.log_text.configure(state="normal")
        if clear:
            self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def load_models(self) -> None:
        try:
            self.set_status("Loading models. This may take a minute on first run...")
            start = time.time()
            self.engine.load_models()
            elapsed = time.time() - start
            self.set_status(f"Models loaded in {elapsed:.1f}s")
            self.log("Models loaded successfully.", clear=False)
            for key, value in self.engine.last_loaded_paths.items():
                self.log(f"  {key}: {value}")
            print("RIDER LABELS:", self.engine.rider_labels)
            print("HELMET LABELS:", self.engine.helmet_labels)
        except Exception as exc:
            self.set_status("Model loading failed")
            messagebox.showerror("Model Load Error", str(exc))

    def select_image(self) -> None:
        start_dir = self.app_dir / "bikes"
        path = filedialog.askopenfilename(
            initialdir=str(start_dir if start_dir.exists() else self.app_dir),
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*")],
        )
        if not path:
            return

        self.selected_image = Path(path)
        self.image_var.set(str(self.selected_image))
        self.set_status("Image selected")

        frame = cv.imread(str(self.selected_image))
        if frame is not None:
            self.show_preview(frame)
            self.log(f"Selected image: {self.selected_image}", clear=False)

    def show_preview(self, frame: np.ndarray) -> None:
        rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)

        self.preview_label.update_idletasks()

        container_w = self.preview_label.winfo_width()
        container_h = self.preview_label.winfo_height()

        if container_w < 100 or container_h < 100:
            container_w, container_h = 900, 500

        image.thumbnail((container_w - 20, container_h - 20), Image.Resampling.LANCZOS)

        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_photo, text="")

    def analyze_image(self) -> None:
        if self.selected_image is None:
            messagebox.showwarning("Input Required", "Select an image first.")
            return

        frame = cv.imread(str(self.selected_image))
        if frame is None:
            messagebox.showerror("Input Error", "Unable to read selected image.")
            return

        try:
            self.set_status("Running detection workflow...")
            start = time.time()
            result = self.engine.analyze(frame, self.country_var.get())
            
            image_name = self.selected_image.stem

            user = USER_DATABASE.get(image_name)
            
            challan = result.get("challan")
            if challan:
                print(f"\n✅ CHALLAN GENERATED: {challan}")

            if user:
                if result["no_helmet_count"] > 0 or not result["plate_detected"]:
                    try:
                        message = build_violation_message(result)
                        success = send_violation_email(
                            user["email"],
                            "Traffic Violation Alert 🚨",
                            message
                        )
                        if success:
                            messagebox.showinfo(
                                "Email Sent",
                                f"Email successfully sent to:\n{user['email']}"
                            )
                    except Exception as email_err:
                        print(f"⚠️  Email sending failed (continuing): {email_err}")
                        
            elapsed = time.time() - start

            self.show_preview(result["annotated_frame"])
            self.render_report(result, elapsed)
            self.set_status(f"Analysis complete in {elapsed:.2f}s")
        except Exception as exc:
            self.set_status("Analysis failed")
            print(f"❌ Analysis error: {exc}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Analysis Error", str(exc))

    def render_report(self, result: Dict[str, object], elapsed: float) -> None:
        self.log("", clear=True)
        self.log(f"Image: {self.selected_image}")
        self.log(f"Country: {self.country_var.get()}")
        self.log(f"Execution time: {elapsed:.2f} sec")
        self.log("-" * 70)

        rider_count = len(result["riders"])
        helmeted_count = len(result["helmeted_riders"])
        no_helmet_count = result["no_helmet_count"]
        person_count = len(result["persons"])
        bike_count = len(result["bikes"])

        self.log(f"Persons detected: {person_count}")
        self.log(f"Bikes detected: {bike_count}")
        self.log(f"Riders detected: {rider_count}")
        self.log(f"Riders with helmet: {helmeted_count}")
        self.log(f"No-helmet violations: {no_helmet_count}")
        if rider_count == 0 and (person_count > 0 or bike_count > 0):
            self.log("Note: Person/bike detected but rider pairing was weak in this frame.")

        if result["plate_detected"]:
            plate_line = result["plate_text"] if result["plate_text"] else "Detected, OCR uncertain"
            self.log(f"Plate detection: {plate_line}")
            self.log(f"Plate confidence score: {result['plate_score']:.2f}")
            self.log(f"Plate format valid: {'Yes' if result['plate_valid'] else 'No'}")
        else:
            self.log("Plate detection: Not found")

        self.log("-" * 70)
        self.log("Vehicle Details")
        details = result["vehicle_details"]
        for key in [
            "country",
            "plate_number",
            "vehicle_type",
            "plate_valid",
            "registration_region",
            "owner_name",
            "vehicle_make",
            "vehicle_model",
            "fuel_type",
        ]:
            self.log(f"  {key}: {details.get(key, 'Unknown')}")

        self.log("-" * 70)
        challan = result["challan"]
        if challan:
            self.log("=" * 70)
            self.log("🚨 CHALLAN GENERATED (Violation Confirmed)")
            self.log("=" * 70)
            self.log(f"  offense: {challan['offense']}")
            self.log(f"  offender_count: {challan['offender_count']}")
            self.log(f"  fine_unit: {challan['fine_unit']}")
            self.log(f"  fine_total: {challan['fine_total']}")
            self.log(f"  plate_number: {challan['plate_number']}")
            self.log(f"  timestamp: {challan['timestamp']}")
            self.log(f"  notes: {challan['notes']}")
            self.log("=" * 70)
        else:
            self.log("❌ Challan: Not generated (no no-helmet violations found)")

        candidates = result["ocr_candidates"]
        if candidates:
            self.log("-" * 70)
            self.log("Top OCR candidates")
            for text, conf in candidates:
                self.log(f"  {text}: {conf:.2f}")

    def clear_results(self) -> None:
        self.selected_image = None
        self.image_var.set("No image selected")
        self.status_var.set("Ready")
        self.preview_label.configure(image="", text="No preview")
        self.preview_photo = None
        self.log("", clear=True)

def main() -> None:
    root = tk.Tk()
    app = HelmetDetectionApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
