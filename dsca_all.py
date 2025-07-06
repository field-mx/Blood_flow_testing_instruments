import cv2
import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.signal import butter, sosfilt
from collections import deque

from leaser_control import ComSetting

"该程序用于单曝光测量测试程序，直接输出波形，自动调整y轴范围，封装函数s_DSCA_all"
prev_y_min, prev_y_max = [None]*4, [None]*4
adjust_threshold = 0.05
smoothing_factor = 0.95

def update_y_axis(ax, filtered_y_data, idx):
    global prev_y_min, prev_y_max

    if len(filtered_y_data) < 80:
        return

    recent_data = list(filtered_y_data)[-80:]
    y_min, y_max = min(recent_data), max(recent_data)
    margin = (y_max - y_min) * 1.3
    y_center = (y_max + y_min) / 2

    if prev_y_min[idx] is not None and prev_y_max[idx] is not None:
        min_change = abs(y_min - prev_y_min[idx]) / max(abs(prev_y_min[idx]), 1e-5)
        max_change = abs(y_max - prev_y_max[idx]) / max(abs(prev_y_max[idx]), 1e-5)

        if min_change < adjust_threshold and max_change < adjust_threshold:
            return

    if prev_y_min[idx] is not None and prev_y_max[idx] is not None:
        y_min = smoothing_factor * y_min + (1 - smoothing_factor) * prev_y_min[idx]
        y_max = smoothing_factor * y_max + (1 - smoothing_factor) * prev_y_max[idx]

    ax.set_ylim(y_min - margin, y_max + margin)
    prev_y_min[idx], prev_y_max[idx] = y_min, y_max

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
        return -1 / (K ** 2) if K != 0 else float('inf')
    elif sign == 1:
        return -1/mean_i
    elif sign == 2:
        return -1/mean_i-1/(12*(mean_i ** 2))
    elif sign == 3:
        return -1/((K ** 2) + 1/mean_i + 1/(12*(mean_i ** 2)))

def butter_bandpass_sos(lowcut, highcut, fs, order=2):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    sos = butter(order, [low, high], btype='band', output='sos')
    return sos

def bandpass_filter(data, lowcut, highcut, fs, order=2):
    sos = butter_bandpass_sos(lowcut, highcut, fs, order)
    return sosfilt(sos, data)

def s_DSCA_all(initial_power=50, camera_index=0, fps=60, size=496, roi_size=50):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("无法打开相机")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, size)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, size)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_EXPOSURE, -4)

    controller = ComSetting()
    port_name = "COM6"
    if controller.init_serial(port_name):
        controller.send_data(controller.open_cmd)
        time.sleep(0.5)
    controller.set_power_state(initial_power)

    x_data = [deque(maxlen=500) for _ in range(4)]
    y_data = [deque(maxlen=500) for _ in range(4)]

    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    axs = axs.flatten()
    lines = []
    labels = ["Initial blood flow index", "shot noise", "total noise", "Quantization noise"]
    # 自定义每个图的Y轴范围
    custom_y_ranges = [
        (-110, -40),  # 图1的y轴范围
        (-0.0099, -0.0087),  # 图2的y轴范围
        (-0.0099, -0.0087),  # 图3的y轴范围
        (-0.101, -0.0094)  # 图4的y轴范围
    ]
    for i in range(4):
        axs[i].set_ylim(custom_y_ranges[i])  # 固定Y轴范围

    for i in range(4):
        lines.append(axs[i].plot([], [], 'r-')[0])
        axs[i].set_title(labels[i])
        axs[i].set_xlabel("Frame")
        axs[i].set_ylabel("Value")

    def update_plot(frame_num):
        ret, frame = cap.read()
        if not ret:
            return lines

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            plt.close(fig)
            cap.release()
            cv2.destroyAllWindows()
            return lines

        frame_with_roi, (x1, y1, x2, y2) = draw_roi(frame, roi_size=roi_size)
        roi_frame = frame[y1:y2, x1:x2]

        for i in range(4):
            # ✅ 将第4个图使用 sign=2
            sign = i if i < 3 else 2
            val = cac_k(roi_frame, sign)
            x_data[i].append(len(x_data[i]))
            y_data[i].append(val)

            if i == 3 and len(y_data[i]) > 60:
                y_plot = bandpass_filter(list(y_data[i]), 0.5, 3, 20, 2)
            else:
                y_plot = list(y_data[i])

            update_y_axis(axs[i], y_data[i], i)
            lines[i].set_data(range(len(x_data[i])), y_data[i])
            axs[i].set_xlim(100, max(500, len(x_data[i])))

        return lines
    ani = FuncAnimation(fig, update_plot, blit=True, interval=1000/fps)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    s_DSCA_all(initial_power=150, camera_index=0, fps=60, size=496, roi_size=50)
