import cv2
import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import subprocess
from leaser_control import ComSetting
from scipy.signal import butter, sosfilt
from collections import deque

# 维护全局变量，存储最近的 Y 轴范围
prev_y_min, prev_y_max = None, None
adjust_threshold = 0.05  # 设定一个变化阈值（10%）
smoothing_factor = 0.95  # 0.8 表示新的数据占主导，降低突变影响
y_locked = False  # 是否锁定 Y 轴


def camera_initial(fps, size):
    """
    设置摄像头曝光值
    :param size: 画面大小
    :param fps: 帧率
    """
    command_size = f"v4l2-ctl --set-fmt-video=width={size},height={size},pixelformat=MJPG"
    command_fps = f"v4l2-ctl --set-parm={fps}"

    try:
        subprocess.run(command_size, shell=True, check=True, text=True, capture_output=True)
        subprocess.run(command_fps, shell=True, check=True, text=True, capture_output=True)
        print(f"帧率已设置为 {fps}")
    except subprocess.CalledProcessError as e:
        print(f"设置失败: {e.stderr}")


def update_y_axis(ax, filtered_y_data):
    global prev_y_min, prev_y_max

    if len(filtered_y_data) < 80:
        return  # 数据不足 60 帧，不调整

    # 取最近 30 帧数据
    recent_data = list(filtered_y_data)[-80:]
    y_min, y_max = min(recent_data), max(recent_data)

    # 计算 margin（增加一定的边界余量）
    margin = (y_max - y_min) * 1.3
    y_center = (y_max + y_min) / 2

    # **判断是否需要更新 Y 轴范围**
    if prev_y_min is not None and prev_y_max is not None:
        # 计算相对变化比例
        min_change = abs(y_min - prev_y_min) / max(abs(prev_y_min), 1e-5)
        max_change = abs(y_max - prev_y_max) / max(abs(prev_y_max), 1e-5)

        if min_change < adjust_threshold and max_change < adjust_threshold:
            return  # 变化小于 20%，不调整

    # **平滑更新 Y 轴范围**
    if prev_y_min is not None and prev_y_max is not None:
        y_min = smoothing_factor * y_min + (1 - smoothing_factor) * prev_y_min
        y_max = smoothing_factor * y_max + (1 - smoothing_factor) * prev_y_max

    # 更新 Y 轴范围
    ax.set_ylim(y_min - margin, y_max + margin)

    # 存储上一次的 Y 轴范围
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
    K = std_i / mean_i
    if sign == 0:
        if K != 0:
            return -1 / (K ** 2)
        else:
            return float('inf')
    elif sign == 1:
        return -K
    elif sign == 2:
        return -K ** 2
    elif sign == 3:
        return -mean_i

def butter_bandpass_sos(lowcut, highcut, fs, order=2):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist

    # 返回二阶节滤波器（sos），而不是 (b, a)
    sos = butter(order, [low, high], btype='band', output='sos')
    return sos


def bandpass_filter(data, lowcut, highcut, fs, order=2):
    sos = butter_bandpass_sos(lowcut, highcut, fs, order)
    return sosfilt(sos, data)  # 用 sos 滤波器处理数据


def s_DSCA(data_type=0,initial_power=50, camera_index=0, fps=60, size=496, roi_size=50):
    # 初始化相机
    # 初始化曝光值
    camera_initial(fps, size)

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("无法打开相机")
        return

    controller = ComSetting()
    port_name = "/dev/ttyACM0"

    if controller.init_serial(port_name):
        # 打开激光器
        controller.send_data(controller.open_cmd)
        time.sleep(0.5)

    controller.set_power_state(initial_power)

    # 初始化图形数据
    x_data = deque(maxlen=270)  # 使用 deque 实现 FIFO 结构
    y_data = deque(maxlen=270)  # 使用 deque 实现 FIFO 结构
    frame_count = 0
    k_squared_values = deque(maxlen=33)  # 用于存储前33帧的 k^2 值
    fig, ax = plt.subplots()
    line, = ax.plot([], [], 'r-')
    ax.set_xlabel("fps(60/s)")
    ax.set_ylabel("-1/k^2")

    def update_plot(frame_num):
        global y_locked
        nonlocal x_data, y_data, frame_count, k_squared_values  # 允许修改外部作用域的变量
        ret, frame = cap.read()
        if not ret:
            return line,

        # 按键检测并实时调整曝光
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # 退出程序
            plt.close(fig)
            cap.release()
            cv2.destroyAllWindows()
            time.sleep(1)
            # 关闭激光器
            controller.send_data(controller.close_cmd)
            time.sleep(1)
            # 关闭串口
            controller.close_serial()
            print("串口已关闭")
            return line,

        # 处理每一帧并计算处理值
        frame_with_roi, (x1, y1, x2, y2) = draw_roi(frame, roi_size=roi_size)
        roi_frame = frame[y1:y2, x1:x2]

        # 计算处理值
        processing_value = cac_k(roi_frame, data_type)

        x_data.append(len(x_data))
        y_data.append(processing_value)
        k_squared_values.append(processing_value)

        # 应用低通滤波器来平滑数据
        if len(y_data) > 60:
            filtered_y_data = bandpass_filter(list(y_data), 0.5, 4, fps+3, 2)
            filtered_y_data = deque(filtered_y_data, maxlen=500)  # 确保是 deque
        else:
            filtered_y_data = y_data

        # **调整纵坐标（每 30 帧更新一次，使用最新 30 帧数据）**
        update_y_axis(ax, filtered_y_data)

        # **更新绘图**
        line.set_data(range(len(x_data)), filtered_y_data)
        ax.set_xlim(100, max(270, len(x_data)))

        # 显示视频流
        #cv2.imshow('Camera Feed', frame_with_roi)

        return line,

    # 使用 FuncAnimation 进行实时绘图
    ani = FuncAnimation(fig, update_plot, blit=True, interval=16.67,save_count=500)  # 60帧每秒，间隔16.67ms
    plt.show()


if __name__ == "__main__":
    s_DSCA(data_type=0,initial_power=280, camera_index=0, fps=30, size=496, roi_size=100)