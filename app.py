from ultralytics import YOLO
import time
import numpy as np
import subprocess
import cv2
from flask import Flask, render_template, request, Response, session, redirect, url_for, send_file

from flask_socketio import SocketIO
import yt_dlp as youtube_dl
#from gps_step import on_message
import threading



model_object_detection = YOLO("yolov8x.pt")

app = Flask(__name__)
process  = None
location = None

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='threading')
stop_flag = False

class VideoStreaming(object):
    def __init__(self):
        super(VideoStreaming, self).__init__()
        print ("*********************************Video Streaming******************************")
        #self.VIDEO = cv2.VideoCapture(0)
        # self.VIDEO.set(10, 200)
        self._preview = False
        self._flipH = False
        self._detect = False
        self._model = False
        self._confidence = 75.0

    @property
    def confidence(self):
        return self._confidence

    @confidence.setter
    def confidence(self, value):
        self._confidence = int(value)

    @property
    def preview(self):
        return self._preview

    @preview.setter
    def preview(self, value):
        self._preview = bool(value)

    @property
    def flipH(self):
        return self._flipH

    @flipH.setter
    def flipH(self, value):
        self._flipH = bool(value)

    @property
    def detect(self):
        return self._detect

    @detect.setter
    def detect(self, value):
        self._detect = bool(value)


    def show(self, url):
        print(url)
        self._preview = False
        self._flipH = False
        self._detect = False

        self._confidence = 75.0
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best",
            "forceurl": True,
        }
        # Create a youtube-dl object
        ydl = youtube_dl.YoutubeDL(ydl_opts)

        # Extract the video URL
        info = ydl.extract_info(url, download=False)
        url = info["url"]

        cap = cv2.VideoCapture(0)
        while True:
            if self._preview:
                if stop_flag:
                    print("Process Stopped")
                    return

                grabbed, frame = cap.read()
                if not grabbed:
                    break
                if self.flipH:
                    frame = cv2.flip(frame, 1)
                if self.detect:
                    print(self._confidence)

                    # frame = cv2.cvtColor(snap, cv2.COLOR_BGR2RGB)
                    # frame = cv2.resize(frame, (500,500
                    # ))
                    # Detect objects
                    results = model_object_detection.predict(frame, conf=self._confidence/100)

                    frame, labels = results[0].plot()
                    list_labels = []
                    # labels_confidences
                    for label in labels:
                        confidence = label.split(" ")[-1]
                        label = (label.split(" "))[:-1]
                        label = " ".join(label)
                        list_labels.append(label)
                        list_labels.append(confidence)
                        socketio.emit('label', list_labels)
                # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frame = cv2.imencode(".jpg", frame)[1].tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                snap = np.zeros((
                    1000,
                    1000
                ), np.uint8)
                label = "Streaming Off"
                H, W = snap.shape
                font = cv2.FONT_HERSHEY_PLAIN
                color = (255, 255, 255)
                cv2.putText(snap, label, (W//2 - 100, H//2),
                            font, 2, color, 2)
                frame = cv2.imencode(".jpg", snap)[1].tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# check_settings()
VIDEO = VideoStreaming()

"""
@app.route('/', methods=['GET', 'POST'])
def homepage():
    return render_template('hompage.html')  """


@app.route('/', methods=['GET', 'POST'])
def index():
    print("index")
    global stop_flag
    stop_flag = False
    if request.method == 'POST':
        print("Index post request")
        url = request.form['url']
        print("index: ", url)
        session['url'] = url
        return redirect(url_for('index'))
    return render_template('index.html')

# def start_gps():
#     from gps_step import on_message
#     on_message.process_gps_data(socketio)

# @app.route('/start-gps')
# def start_gps_route():
#     thread = threading.Thread(target=start_gps)
#     thread.daemon = True
#     thread.start()
#     return "GPS started!"

@app.route('/video_feed')
def video_feed():
    url = session.get('url', None)
    print("video feed: ", url)
    if url is None:
        return redirect(url_for('index'))
    return Response(VIDEO.show(url), mimetype='multipart/x-mixed-replace; boundary=frame')

# * Button requests
@app.route("/request_preview_switch")
def request_preview_switch():
    VIDEO.preview = not VIDEO.preview
    print("*"*10, VIDEO.preview)
    return "nothing"

@app.route("/request_flipH_switch")
def request_flipH_switch():
    VIDEO.flipH = not VIDEO.flipH
    print("*"*10, VIDEO.flipH)
    return "nothing"

@app.route("/request_run_model_switch")
def request_run_model_switch():
    VIDEO.detect = not VIDEO.detect
    print("*"*10, VIDEO.detect)
    return "nothing"


@app.route('/update_slider_value', methods=['POST'])
def update_slider_value():
    slider_value = request.form['sliderValue']
    VIDEO.confidence = slider_value
    return 'OK'

@app.route('/stop_process')
def stop_process():
    print("Process stop Request")
    global stop_flag
    stop_flag = True
    return 'Process Stop Request'

@socketio.on('connect')
def test_connect():
    print('Connected')

@app.route('/run-script')
def run_script():
    global process
    if process is None or process.poll() is not None:  # Not running
        process = subprocess.Popen(['python', 'web_socket.py'])
        while True:
            continue

        
    else:
        return "Script is already running."

@app.route('/stop-script')
def stop_script():
    global process
    if process is not None:
        process.terminate()
        process = None
        return "Script stopped."
    else:
        return "No script is running."
    

@app.route('/get-plot')
def get_plot():
    return send_file('plot.png', mimetype='image/png')

# @app.route('/gps-output')
# def gps_output():
#     # Execute gps_step.py and capture its output
#     try:
#         output = subprocess.check_output(['python', 'gps_step.py'], text=True)
#         return output
#     except subprocess.CalledProcessError as e:
#         return "An error occurred while retrieving GPS data."


# @app.route('/gps')
# def gps():
#     global location
#     if location is None or location.poll() is not None:  # Not running
#         location = subprocess.Popen(['python', 'gps_step.py'])
#         while True:
#             continue

        
#     else:
#         return "Script is already running."

if __name__ == "__main__":
    socketio.run(app, debug=True)
