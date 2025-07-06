import cv2
import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.signal import butter, sosfilt
from collections import deque

from leaser_control import ComSetting

prev_y_min, prev_y_max = None, None
adjust_threshold = 0.05
smoothing_factor = 0.95
"该程序为单次曝光测量，封装函数s_DSCA"
def update_y_axis(ax, filtered_y_data):
    global prev_y_min, prev_y_max

    if len(filtered_y_data) < 80:
        return

    recent_data = list(filtered_y_data)[-80:]
    y_min, y_max = min(recent_data), max(recent_data)
    margin = (y_max - y_min) * 1.3
    y_center = (y_max + y_min) / 2

    if prev_y_min is not None and prev_y_max is not None:
        min_change = abs(y_min - prev_y_min) / max(abs(prev_y_min), 1e-5)
        max_change = abs(y_max - prev_y_max) / max(abs(prev_y_max), 1e-5)

        if min_change < adjust_threshold and max_change < adjust_threshold:
            return

    if prev_y_min is not None and prev_y_max is not None:
        y_min = smoothing_factor * y_min + (1 - smoothing_factor) * prev_y_min
        y_max = smoothing_factor * y_max + (1 - smoothing_factor) * prev_y_max

    ax.set_ylim(y_min - margin, y_max + margin)
    prev_y_min, prev_y_max = y_min, y_max

def draw_roi(frame, roi_size=50):
    height, width, _ = frame.shape
    x1 = (width - roi_size) // 2
    y1 = (height - roi_size) // 2
    x2 = x1 + roi_size
    y2 = y1 + roi_size
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    return frame, (x1, y1, x2, y2)

def cac_k(roi_frame, sign):
    gray_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
    mean_i = np.mean(gray_roi)
    std_i = np.std(gray_roi)
    K = std_i / mean_i if mean_i != 0 else 0
    if sign == 0:
        return 1 / (K ** 2) if K != 0 else float('inf')
    elif sign == 1:
        return -K
    elif sign == 2:
        return K ** 2
    elif sign == 3:
        return -mean_i

def butter_bandpass_sos(lowcut, highcut, fs, order=2):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    sos = butter(order, [low, high], btype='band', output='sos')
    return sos

def bandpass_filter(data, lowcut, highcut, fs, order=2):
    sos = butter_bandpass_sos(lowcut, highcut, fs, order)
    return sosfilt(sos, data)

def s_DSCA(data_type=0, initial_power=50, camera_index=0, fps=60, size=496, roi_size=50):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("无法打开相机")
        return

    # 设置分辨率和帧率（有些相机型号可能不支持）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, size)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, size)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_EXPOSURE, -1)
    controller = ComSetting()
    port_name = "COM6"

    if controller.init_serial(port_name):
        # 打开激光器
        controller.send_data(controller.open_cmd)
        time.sleep(0.5)

    controller.set_power_state(initial_power)
    # 图形数据初始化
    x_data = deque(maxlen=500)
    y_data = deque(maxlen=500)

    fig, ax = plt.subplots()
    line, = ax.plot([], [], 'r-')
    ax.set_xlabel("fps(60/s)")
    ax.set_ylabel("-1/k^2")

    def update_plot(frame_num):
        ret, frame = cap.read()
        if not ret:
            return line,

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            plt.close(fig)
            cap.release()
            cv2.destroyAllWindows()
            return line,

        frame_with_roi, (x1, y1, x2, y2) = draw_roi(frame, roi_size=roi_size)
        roi_frame = frame[y1:y2, x1:x2]
        processing_value = cac_k(roi_frame, data_type)
        print(processing_value)

        x_data.append(len(x_data))
        y_data.append(processing_value)

        if len(y_data) > 60:
            filtered_y_data = bandpass_filter(list(y_data), 0.5, 3, fps, 2)
            filtered_y_data = deque(filtered_y_data, maxlen=500)
        else:
            filtered_y_data = y_data

        update_y_axis(ax, y_data)
        line.set_data(range(len(x_data)), y_data)
        ax.set_xlim(100, max(500, len(x_data)))

        cv2.imshow('Camera Feed', frame_with_roi)  # 可选显示摄像头画面

        return line,

    ani = FuncAnimation(fig, update_plot, blit=False, interval=1000/fps, save_count=500)
    plt.show()

if __name__ == "__main__":
    s_DSCA(data_type=0, initial_power=150, camera_index=0, fps=60, size=496, roi_size=100)
