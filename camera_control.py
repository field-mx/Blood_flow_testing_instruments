import cv2
import numpy as np
import time

from matplotlib import pyplot as plt

from leaser_control import ComSetting

"该程序用于调试相机曝光时间与帧率，ws键分别控制曝光补偿增加或减小，通过帧率反算出绝对曝光时间"
def draw_roi(frame, roi_size=50):
    """在图像中心绘制一个ROI矩形并返回ROI坐标"""
    height, width, _ = frame.shape
    x1 = (width - roi_size) // 2
    y1 = (height - roi_size) // 2
    x2 = x1 + roi_size
    y2 = y1 + roi_size
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    return frame, (x1, y1, x2, y2)

def cac_sDSCA(roi_frame):
    """计算ROI区域的平均亮度值"""
    gray_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
    brightness = np.mean(gray_roi)
    return brightness

def plot_on_frame(frame, values, max_length=100):
    """在OpenCV窗口上绘制处理值曲线"""
    h, w, _ = frame.shape
    plot_h, plot_w = 100, 300  # 绘图区域的高度和宽度
    plot_x, plot_y = 10, h - plot_h - 10  # 绘图区域左上角坐标

    # 绘制背景框
    cv2.rectangle(frame, (plot_x, plot_y), (plot_x + plot_w, plot_y + plot_h), (255, 255, 255), -1)

    # 计算点位置
    if len(values) > max_length:
        values = values[-max_length:]  # 保留最近的 max_length 个值

    normalized_values = [int(plot_y + plot_h - (v / 255) * plot_h) for v in values]
    for i in range(1, len(normalized_values)):
        x1 = plot_x + int((i - 1) * plot_w / max_length)
        y1 = normalized_values[i - 1]
        x2 = plot_x + int(i * plot_w / max_length)
        y2 = normalized_values[i]
        cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 1)

    return frame

def main(camera_index=0, initial_exposure=-4, step=1, fps=30, roi_size=50):
    # 初始化相机
    controller = ComSetting()
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("无法打开相机")
        return

    # 设置曝光和帧率
    cap.set(cv2.CAP_PROP_EXPOSURE, initial_exposure)
    cap.set(cv2.CAP_PROP_FPS, fps)
    exposure_value = initial_exposure

    # 初始化图形数据
    x_data, y_data = [], []
    fig, ax = plt.subplots()
    line, = ax.plot([], [], 'r-')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 255)
    ax.set_xlabel("帧数")
    ax.set_ylabel("处理值")

    # 初始化帧率计算
    last_time = time.time()
    frame_count = 0
    fps_current = 0



    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法接收帧")
            break

        # 绘制ROI并计算ROI区域的处理值
        frame_with_roi, (x1, y1, x2, y2) = draw_roi(frame, roi_size=roi_size)
        roi_frame = frame[y1:y2, x1:x2]
        processing_value = cac_sDSCA(roi_frame)


        # 计算并显示帧率
        current_time = time.time()
        if current_time - last_time >= 0.5:  # 每0.5秒更新一次帧率
            fps_current = frame_count / (current_time - last_time)
            frame_count = 0
            last_time = current_time
        else:
            frame_count += 1

        # 在帧上显示帧率、曝光值和图像处理值
        cv2.putText(frame_with_roi, f'FPS: {fps_current:.1f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame_with_roi, f'Exposure: {exposure_value}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame_with_roi, f'Proc Value: {processing_value:.2f}', (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # 实时显示信息到图像上
        mean = controller.calculate_histogram_mean(roi_frame)
        cv2.putText(frame_with_roi, f"Mean: {mean:.2f}", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # 显示视频流
        cv2.imshow('Camera Feed with Plot', frame_with_roi)

        # 键盘控制曝光时间
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == ord('w'):
            exposure_value += step
            cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
            print(f"增加曝光值到: {exposure_value}")
        elif key == ord('s'):
            exposure_value -= step
            cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
            print(f"减少曝光值到: {exposure_value}")

    # 释放资源
    cap.release()
    cv2.destroyAllWindows()

# 运行主函数
if __name__ == "__main__":
    main(camera_index=0, initial_exposure=-4, step=1, fps=120, roi_size=50)
