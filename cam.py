iimport sys
import cv2
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QLineEdit, QHBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
import os
from datetime import datetime, timedelta
import concurrent.futures
from flask import Flask, render_template, Response
import threading

a = Flask(__name__, template_folder='templates')

class C(QWidget):
  def __init__(s):
    super().__init__()

    s.setWindowTitle("Camera App")
    s.resize(640, 520)

    s.i_l = QLabel(s)
    s.i_l.setAlignment(Qt.AlignCenter)
    s.i_l.setMinimumSize(640, 480)
    s.i_l.setScaledContents(True)

    s.s_s_b = QPushButton("Start Camera", s)
    s.s_s_b.clicked.connect(s.t_c)

    s.d_e = QLineEdit(s)
    s.d_e.setPlaceholderText("Enter directory path")

    s.b_b = QPushButton("Browse", s)
    s.b_b.clicked.connect(s.b_d)

    d_l = QHBoxLayout()
    d_l.addWidget(s.d_e)
    d_l.addWidget(s.b_b)

    l = QVBoxLayout(s)
    l.addWidget(s.i_l)
    l.addWidget(s.s_s_b)
    l.addLayout(d_l)

    s.c = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    s.t = QTimer(s)
    s.t.timeout.connect(s.u_f)
    s.c_r = False
    s.v_w = None
    s.m_d = cv2.createBackgroundSubtractorMOG2()
    s.r = False
    s.l_m_t = None
    s.z_f = 1.0

  def t_c(s):
    if not s.c_r:
      s.s_s_b.setText("Stop Camera")
      s.t.start(50)
      s.s_s()
    else:
      s.s_s_b.setText("Start Camera")
      s.t.stop()
      s.s_s()
    s.c_r = not s.c_r

  def s_s(s):
    d = s.d_e.text()
    if not d:
      QMessageBox.warning(s, "Warning", "Please enter a directory path.")
      return
    if not os.path.exists(d):
      QMessageBox.warning(s, "Warning", "Directory does not exist.")
      return

    n = datetime.now()
    t = n.strftime("%Y%m%d_%H%M%S")
    v_f = os.path.join(d, f"session_{t}.mp4")
    f_w = int(s.c.get(cv2.CAP_PROP_FRAME_WIDTH))
    f_h = int(s.c.get(cv2.CAP_PROP_FRAME_HEIGHT))
    f = 20
    c = cv2.VideoWriter_fourcc(*"mp4v")
    s.v_w = cv2.VideoWriter(v_f, c, f, (f_w, f_h))

  def s_s(s):
    if s.v_w is not None:
      s.v_w.release()
      s.v_w = None

  def u_f(s):
    r, f = s.c.read()
    if r:
      m = s.m_d.apply(f)
      m_d = cv2.countNonZero(m) > 0

      if m_d:
        if not s.r:
          s.s_s()
          s.r = True
          s.l_m_t = datetime.now()
      elif s.r and (datetime.now() - s.l_m_t) > timedelta(minutes=5):
        s.r = False
        s.s_s()

      if s.r:
        if s.v_w is not None:
          s.v_w.write(f)

      f = s.a_z(f)

      f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
      h, w, ch = f.shape
      b_p_l = ch * w
      i = QImage(f.data, w, h, b_p_l, QImage.Format_RGB888)
      p = QPixmap.fromImage(i)
      s.i_l.setPixmap(p)

  def a_z(s, f):
    h, w, _ = f.shape
    c = (w // 2, h // 2)
    z_w = int(w * s.z_f)
    z_h = int(h * s.z_f)
    t_l_x = c[0] - z_w // 2
    t_l_y = c[1] - z_h // 2
    b_r_x = t_l_x + z_w
    b_r_y = t_l_y + z_h
    z_f = f[t_l_y:b_r_y, t_l_x:b_r_x]
    return z_f

  def b_d(s):
    d = QFileDialog.getExistingDirectory(s, "Select Directory")
    if d:
      s.d_e.setText(d)

  def w_e(s, e):
    s.s_s()
    s.c.release()

def g_f():
    c = cv2.VideoCapture(0)
    while True:
        s, f = c.read()
        if not s:
            break
        else:
            r, b = cv2.imencode('.jpg', f)
            f = b.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + f + b'\r\n')

@a.route('/')
def index():
    return render_template('index.html')

@a.route('/video_feed')
def video_feed():
    return Response(g_f(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    t1 = threading.Thread(target=a.run, kwargs={'debug':False, 'port':8000})
    t1.start()
    m_a = QApplication(sys.argv)
    w = C()
    w.show()
    sys.exit(m_a.exec_())

