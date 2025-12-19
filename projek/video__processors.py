import cv2
import tkinter as tk
from tkinter import filedialog
from threading import Thread
import numpy as np
import time
import os

# ======================
# Helper: Overlay Logo
# ======================
def overlay_logo(frame, logo, x, y):
    if logo is None:
        return frame

    lh, lw = logo.shape[:2]
    fh, fw = frame.shape[:2]

    if x + lw > fw or y + lh > fh:
        return frame

    # PNG dengan alpha
    if logo.shape[2] == 4:
        b, g, r, a = cv2.split(logo)
        overlay = cv2.merge((b, g, r))
        mask = a / 255.0

        for c in range(3):
            frame[y:y+lh, x:x+lw, c] = (
                mask * overlay[:, :, c] +
                (1 - mask) * frame[y:y+lh, x:x+lw, c]
            ).astype("uint8")
    else:
        frame[y:y+lh, x:x+lw] = logo

    return frame


# ======================
# Tkinter UI
# ======================
class VideoProcessorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Processor UI - TPM2025")
        self.root.geometry("420x520")
        self.root.resizable(False, False)

        # State
        self.source = 0
        self.cap = None
        self.running = False

        self.enable_gray = tk.BooleanVar()
        self.enable_blur = tk.BooleanVar()
        self.enable_text = tk.BooleanVar()
        self.enable_logo = tk.BooleanVar()
        self.flip_mode = tk.StringVar(value="None")
        self.blur_ksize = tk.IntVar(value=9)

        # Load logo.png (satu folder dengan file ini)
        self.logo = None
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            self.logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)

        self.build_ui()

    def build_ui(self):
        tk.Label(self.root, text="🎥 Video Processor",
                 font=("Arial", 16, "bold")).pack(pady=10)

        # Source
        src = tk.LabelFrame(self.root, text="Sumber Video")
        src.pack(fill="x", padx=10, pady=5)

        tk.Button(src, text="Gunakan Webcam",
                  command=self.use_webcam).pack(fill="x", pady=3)
        tk.Button(src, text="Pilih File Video",
                  command=self.open_file).pack(fill="x", pady=3)

        # Effects
        eff = tk.LabelFrame(self.root, text="Efek")
        eff.pack(fill="x", padx=10, pady=5)

        tk.Checkbutton(eff, text="Grayscale",
                       variable=self.enable_gray).pack(anchor="w")
        tk.Checkbutton(eff, text="Blur",
                       variable=self.enable_blur).pack(anchor="w")

        tk.Scale(eff, from_=1, to=49, resolution=2,
                 orient="horizontal",
                 label="Blur Kernel (ganjil)",
                 variable=self.blur_ksize).pack(fill="x")

        tk.Checkbutton(eff, text="Text Watermark",
                       variable=self.enable_text).pack(anchor="w")
        tk.Checkbutton(eff, text="Logo Overlay",
                       variable=self.enable_logo).pack(anchor="w")

        # Flip
        flip = tk.LabelFrame(self.root, text="Flip")
        flip.pack(fill="x", padx=10, pady=5)

        for m in ["None", "Horizontal", "Vertical"]:
            tk.Radiobutton(flip, text=m,
                           value=m,
                           variable=self.flip_mode).pack(anchor="w")

        # Control
        ctrl = tk.LabelFrame(self.root, text="Kontrol")
        ctrl.pack(fill="x", padx=10, pady=10)

        tk.Button(ctrl, text="▶ Start", bg="#4CAF50",
                  fg="white", command=self.start).pack(fill="x", pady=3)
        tk.Button(ctrl, text="⏹ Stop", bg="#f44336",
                  fg="white", command=self.stop).pack(fill="x", pady=3)

        self.status = tk.Label(self.root,
                               text="Status: Idle",
                               fg="blue")
        self.status.pack(pady=5)

    def use_webcam(self):
        self.source = 0
        self.status.config(text="Status: Webcam dipilih")

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video", "*.mp4 *.avi *.mkv")]
        )
        if path:
            self.source = path
            self.status.config(text="Status: File dipilih")

    def start(self):
        if self.running:
            return
        self.running = True
        self.status.config(text="Status: Running")
        Thread(target=self.process_video, daemon=True).start()

    def stop(self):
        self.running = False
        self.status.config(text="Status: Stopped")

    def process_video(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            self.status.config(text="Gagal membuka video")
            self.running = False
            return

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            out = frame.copy()

            # Flip
            if self.flip_mode.get() == "Horizontal":
                out = cv2.flip(out, 1)
            elif self.flip_mode.get() == "Vertical":
                out = cv2.flip(out, 0)

            # Grayscale
            if self.enable_gray.get():
                g = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
                out = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)

            # Blur
            if self.enable_blur.get():
                k = self.blur_ksize.get()
                if k % 2 == 0:
                    k += 1
                out = cv2.GaussianBlur(out, (k, k), 0)

            # Text watermark
            if self.enable_text.get():
                cv2.putText(out,
                            "TPM2025 - Akhmad Fitriannor",
                            (10, out.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (255, 255, 255), 2)

            # Logo overlay
            if self.enable_logo.get() and self.logo is not None:
                h, w = out.shape[:2]
                logo_h = int(h * 0.15)
                ratio = logo_h / self.logo.shape[0]
                logo_w = int(self.logo.shape[1] * ratio)
                logo = cv2.resize(self.logo, (logo_w, logo_h))

                x = w - logo_w - 10
                y = 10
                out = overlay_logo(out, logo, x, y)

            cv2.imshow("Video Processor UI", out)
            if cv2.waitKey(1) & 0xFF == 27:
                break

        self.cap.release()
        cv2.destroyAllWindows()
        self.running = False
        self.status.config(text="Status: Idle")


# ======================
# Main
# ======================
if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessorUI(root)
    root.mainloop()
