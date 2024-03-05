import sys
import cv2
import threading
from flask import Flask, render_template, Response
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QLineEdit, QHBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt, QSize, QThread
import os
from datetime import datetime, timedelta
from cam import app

class FlaskThread(QThread):
    def __init__(self):
        super().__init__()

    def run(self):
        app = Flask(__name__)

        camera = cv2.VideoCapture(0)

        def generate_frames():
            while True:
                success, frame = camera.read()
                if not success:
                    break
                else:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        @app.route('/')
        def index():
            return render_template('index.html')

        @app.route('/video_feed')
        def video_feed():
            return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

        app.run(debug=True)  # Run Flask app


class CameraApp(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the UI
        self.setWindowTitle("Camera App")
        self.resize(640, 520)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)  # Align image to center
        self.image_label.setMinimumSize(640, 480)  # Set minimum size for label
        self.image_label.setScaledContents(True)  # Allow image to scale with label size

        self.start_stop_button = QPushButton("Start Camera", self)
        self.start_stop_button.clicked.connect(self.toggle_camera)

        self.directory_edit = QLineEdit(self)
        self.directory_edit.setPlaceholderText("Enter directory path")

        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.browse_directory)

        directory_layout = QHBoxLayout()
        directory_layout.addWidget(self.directory_edit)
        directory_layout.addWidget(self.browse_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)
        layout.addWidget(self.start_stop_button)
        layout.addLayout(directory_layout)

        # Set up the camera
        self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.camera_running = False

        # Initialize video writer
        self.video_writer = None

        # Initialize motion detector
        self.motion_detector = cv2.createBackgroundSubtractorMOG2()

        # Variables for motion detection and recording
        self.recording = False
        self.last_motion_time = None

        # Variables for zoom functionality
        self.zoom_factor = 1.0

    def toggle_camera(self):
        if not self.camera_running:
            self.start_stop_button.setText("Stop Camera")
            self.timer.start(50)  # Update frame every 50 milliseconds
            self.start_session()
        else:
            self.start_stop_button.setText("Start Camera")
            self.timer.stop()
            self.stop_session()
        self.camera_running = not self.camera_running

    def start_session(self):
        directory = self.directory_edit.text()
        if not directory:
            QMessageBox.warning(self, "Warning", "Please enter a directory path.")
            return
        if not os.path.exists(directory):
            QMessageBox.warning(self, "Warning", "Directory does not exist.")
            return

        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        video_file = os.path.join(directory, f"session_{timestamp}.mp4")
        frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 20  # Frames per second
        codec = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(video_file, codec, fps, (frame_width, frame_height))

    def stop_session(self):
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None

    def update_frame(self):
        ret, frame = self.camera.read()
        if ret:
            # Apply motion detection
            fg_mask = self.motion_detector.apply(frame)

            # Check if motion is detected
            motion_detected = cv2.countNonZero(fg_mask) > 0

            if motion_detected:
                if not self.recording:
                    self.start_session()
                    self.recording = True
                    self.last_motion_time = datetime.now()
            elif self.recording and (datetime.now() - self.last_motion_time) > timedelta(minutes=5):
                self.recording = False
                self.stop_session()

            if self.recording:
                # Write frame to video file
                if self.video_writer is not None:
                    self.video_writer.write(frame)

            # Apply zoom
            frame = self.apply_zoom(frame)

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert frame to RGB
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)
            self.image_label.setPixmap(pixmap)

    def apply_zoom(self, frame):
        h, w, _ = frame.shape
        center = (w // 2, h // 2)
        zoomed_width = int(w * self.zoom_factor)
        zoomed_height = int(h * self.zoom_factor)
        top_left_x = center[0] - zoomed_width // 2
        top_left_y = center[1] - zoomed_height // 2
        bottom_right_x = top_left_x + zoomed_width
        bottom_right_y = top_left_y + zoomed_height
        zoomed_frame = frame[top_left_y:bottom_right_y, top_left_x:bottom_right_x]
        return zoomed_frame

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.directory_edit.setText(directory)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            # Scrolling up (zoom in)
            self.zoom_factor += 0.1
        else:
            # Scrolling down (zoom out)
            self.zoom_factor -= 0.1
            if self.zoom_factor < 0.1:
                self.zoom_factor = 0.1

    def closeEvent(self, event):
        self.stop_session()
        self.camera.release()

def main():
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()

    flask_thread = FlaskThread()
    flask_thread.start()

    sys.exit(app.exec_())

if __name__ == "__main__":
    app.run(debug=True)
    main()
