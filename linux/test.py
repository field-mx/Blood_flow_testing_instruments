import cv2
import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import subprocess
from scipy.signal import butter, sosfilt
from collections import deque
from scipy.fft import fft, fftfreq
from leaser_control import ComSetting
from s_DSCA import update_y_axis
from camera_control import calculate_fps

# Global variables for y-axis adjustment
prev_y_min, prev_y_max = None, None
adjust_threshold = 0.05
smoothing_factor = 0.95
y_locked = False

# FFT parameters
fft_window_size = 300
#sample_rate = 30  # Sampling rate (same as fps)
last_update_time = time.time()


def camera_initial(fps, size):
    """Set camera parameters"""
    command_size = f"v4l2-ctl --set-fmt-video=width={size},height={size},pixelformat=MJPG"
    command_fps = f"v4l2-ctl --set-parm={fps}"



    try:
        subprocess.run(command_size, shell=True, check=True, text=True, capture_output=True)
        subprocess.run(command_fps, shell=True, check=True, text=True, capture_output=True)
        print(f"Frame rate set to {fps}")
    except subprocess.CalledProcessError as e:
        print(f"Setup failed: {e.stderr}")

def draw_roi(frame, roi_size=50):
    """Draw ROI region"""
    height, width, _ = frame.shape
    x1 = (width - roi_size) // 2
    y1 = (height - roi_size) // 2
    x2 = x1 + roi_size
    y2 = y1 + roi_size
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    return frame, (x1, y1, x2, y2)


def cac_k(roi_frame, sign):
    """Calculate image feature value"""
    gray_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
    mean_i = np.mean(gray_roi)
    std_i = np.std(gray_roi)
    K = std_i / mean_i
    if sign == 0:
        if K != 0:
            return 50 - (1 / (K ** 2))
        else:
            return float('inf')
    elif sign == 1:
        return 50 - K
    elif sign == 2:
        return 50 - (K ** 2)
    elif sign == 3:
        return 50 - mean_i


def butter_bandpass_sos(lowcut, highcut, fs, order=2):
    """Design bandpass filter"""
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    sos = butter(order, [low, high], btype='band', output='sos')
    return sos


def bandpass_filter(data, lowcut, highcut, fs, order=2):
    """Apply bandpass filter"""
    sos = butter_bandpass_sos(lowcut, highcut, fs, order)
    return sosfilt(sos, data)


def compute_fft(data, sample_rate):
    """计算FFT，精度达到0.02Hz"""
    n = len(data)
    if n < 2:
        return np.array([]), np.array([])

    # 方法1：增加采样点数（需要至少5秒数据）
    desired_resolution = 0.02  # 0.02Hz精度
    required_n = int(sample_rate / desired_resolution)

    # 如果数据不足，使用零填充
    if n < required_n:
        padded_data = np.zeros(required_n)
        padded_data[:n] = data  # 前面填充原始数据
    else:
        padded_data = data

    # 使用汉宁窗减少频谱泄漏
    window = np.hanning(len(padded_data))
    windowed_data = padded_data * window

    # 计算FFT
    yf = fft(windowed_data)
    xf = fftfreq(len(padded_data), 1 / sample_rate)[:len(padded_data) // 2]

    return xf, 2.0 / n * np.abs(yf[0:len(padded_data) // 2])


def s_DSCA(data_type=0, initial_power=50, camera_index=0, fps=60, size=496, roi_size=50):
    """Main function with FPS monitoring and counter reset"""
    camera_initial(fps, size)
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Camera not available")
        return
    controller = ComSetting()
    port_name = "/dev/ttyACM0"

    if controller.init_serial(port_name):
        controller.send_data(controller.open_cmd)
        time.sleep(0.5)

    controller.set_power_state(initial_power)

    # Initialize data containers
    x_data = deque(maxlen=500)
    y_data = deque(maxlen=500)
    frame_count = 0
    k_squared_values = deque(maxlen=33)
    peak_freq = 0.0
    last_peak_update = 0

    # FPS monitoring variables
    fps_counter = 0
    fps_last_time = time.time()
    current_fps = 0
    reset_threshold = 100  # 计数器达到100时清零

    # Create figure with custom layout
    fig = plt.figure(figsize=(12, 8))
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1])

    # Upper part - Waveform plot
    ax1 = fig.add_subplot(gs[0, :])
    line, = ax1.plot([], [], 'r-')
    ax1.set_xlabel("Time (frames)")
    ax1.set_ylabel("-1/k^2")
    ax1.set_title(f"Pulse Waveform @ Target FPS: {fps}")

    # Lower left - Status panel
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.axis('off')
    status_text = ax2.text(0.1, 0.5,
                           "Status:\n"
                           "Initializing...\n"
                           "Actual FPS: calculating...\n"
                           "Frame count: 0",
                           ha='left', va='center',
                           fontsize=10)

    # Lower right - Peak frequency display
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.axis('off')
    freq_display = ax3.text(0.5, 0.5, "Calculating...",
                            ha='center', va='center',
                            fontsize=12,
                            bbox=dict(facecolor='white', alpha=0.7))

    def update_plot(frame_num):
        nonlocal x_data, y_data, frame_count, k_squared_values
        nonlocal peak_freq, last_peak_update
        nonlocal fps_counter, fps_last_time, current_fps

        # FPS calculation and counter reset
        fps_counter += 1
        frame_count += 1

        # Reset counter when reaching threshold
        if fps_counter >= reset_threshold:
            fps_counter = 0
            fps_last_time = time.time()
            status_text.set_text(
                "Status:\n"
                f"Running (Target FPS: {fps})\n"
                f"Actual FPS: {current_fps:.1f}\n"

            )
        else:
            # Normal FPS calculation
            now = time.time()
            elapsed = now - fps_last_time
            if elapsed > 0:
                current_fps = fps_counter / elapsed
                status_text.set_text(
                    "Status:\n"
                    f"Running (Target FPS: {fps})\n"
                    f"Actual FPS: {current_fps:.1f}\n"
                )

        ret, frame = cap.read()
        if not ret:
            status_text.set_text("Status:\nFrame capture failed!")
            return line, freq_display, status_text

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            plt.close(fig)
            cap.release()
            cv2.destroyAllWindows()
            controller.send_data(controller.close_cmd)
            return line, freq_display, status_text

        # Process frame and calculate value
        frame_with_roi, (x1, y1, x2, y2) = draw_roi(frame, roi_size=roi_size)
        roi_frame = frame[y1:y2, x1:x2]
        processing_value = cac_k(roi_frame, data_type)

        x_data.append(len(x_data))
        y_data.append(processing_value)
        k_squared_values.append(processing_value)

        # Apply bandpass filter
        if len(y_data) > 60:
            filtered_y_data = bandpass_filter(list(y_data), 0.5, 4, 23, 2)
            filtered_y_data = deque(filtered_y_data, maxlen=500)
        else:
            filtered_y_data = y_data

        # Update time-domain plot
        line.set_data(range(len(x_data)), filtered_y_data)
        ax1.set_xlim(150, max(500, len(x_data)))
        update_y_axis(ax1, filtered_y_data)

        # Calculate peak frequency (update once per second)
        current_time = time.time()
        if current_time - last_peak_update >= 1.0 and len(filtered_y_data) >= fft_window_size:
            recent_data = list(filtered_y_data)[-fft_window_size:]
            xf, yf = compute_fft(recent_data, 20)

            if len(xf) > 0:
                mask = (xf >= 0) & (xf <= 5)
                if sum(mask) > 0:
                    max_idx = np.argmax(yf[mask])
                    peak_freq = xf[mask][max_idx]
                    freq_display.set_text(
                        f"Current Pulse Rate:\n"
                        f"{peak_freq * 60+2:.1f} BPM\n"
                    )
                    last_peak_update = current_time

        return line, freq_display, status_text

    ani = FuncAnimation(fig, update_plot, blit=True, interval=16.67, save_count=500)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    s_DSCA(data_type=0, initial_power=300, camera_index=0, fps=30, size=496, roi_size=100)