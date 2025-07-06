import cv2

"测试使用的临时程序"
def set_roi(frame, roi_size=50):
    height, width, _ = frame.shape
    x1 = (width - roi_size) // 2
    y1 = (height - roi_size) // 2
    x2 = x1 + roi_size
    y2 = y1 + roi_size
    return frame, (x1, y1, x2, y2)

def leaser_calibration( exposure_times, camera_index, fps=20, roi_size=50, initial_power=500):
    """
    激光曝光标定序列
    :param fps: 采样帧率
    :param camera_index: 相机编号
    :param exposure_times:相机曝光序列
    :return: 激光输出功率序列[w1, w2, w3, ...wn]

    阶梯测光：
    相机最低曝光——激光器功率从大到小，当满足测光条件，记录曝光功率w1
    相机增加曝光——激光器功率从w1开始减小，满足测光条件，记录曝光功率w2
    以此类推
    输出激光器曝光功率序列[w1, w2, w3, ...wn],其中n为相机曝光次数
    """
    # 相机开机

    power = initial_power

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Error: Unable to access the camera.")
        return
    cap.set(cv2.CAP_PROP_FPS, fps)

    # 根据曝光序列截取帧
    laser_powers = []  # 用于记录激光器的功率序列

    for idx, exposure in enumerate(exposure_times):
        cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
        cv2.waitKey(500)

        # Capture a frame
        ret, frame = cap.read()
        cv2.imshow('Camera Feed', frame)
        if not ret:
            print(f"Error: Unable to capture frame for exposure {exposure} ms.")
            continue

        # roi
        frame_with_roi, (x1, y1, x2, y2) = set_roi(frame, roi_size=roi_size)
        roi_frame = frame[y1:y2, x1:x2]

        # 计算roi区域内均值mean
        mean = self.calculate_histogram_mean(roi_frame)

        # 判断均值是否在范围内
        if 75 <= mean <= 95:  # 根据需求的均值范围进行调整
            laser_powers.append(power)  # 满足条件时记录当前功率
        else:
            # 如果均值不在范围内，则调整激光功率
            while not (75 <= mean <= 95) and power < 600:  # 最大功率限制
                power = power - 10  # 增加功率
                # 重新捕获图像
                cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
                cv2.waitKey(500)
                ret, frame = cap.read()
                if not ret:
                    print(f"Error: Unable to capture frame for exposure {exposure} ms after adjusting power.")
                    continue
                # roi处理
                frame_with_roi, (x1, y1, x2, y2) = self.set_roi(frame, roi_size=roi_size)
                roi_frame = frame[y1:y2, x1:x2]
                mean = self.calculate_histogram_mean(roi_frame)  # 重新计算均值

            laser_powers.append(power)  # 记录调整后的功率

        # 释放相机
    cap.release()
    cv2.destroyAllWindows()

    return laser_powers