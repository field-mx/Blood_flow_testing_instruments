import os

import cv2
import numpy as np
import time

from matplotlib import pyplot as plt

from LM_cac import cac_LM
from leaser_control import ComSetting
from s_DSCA import cac_k

"本程序为多曝光拟合程序，执行后多次曝光，拟合曲线显示，并在命令栏显示血流指数，由于树梅派算力有限，使用win平台运行"
def set_roi(frame, roi_size=50):
    height, width, _ = frame.shape
    x1 = (width - roi_size) // 2
    y1 = (height - roi_size) // 2
    x2 = x1 + roi_size
    y2 = y1 + roi_size
    return frame, (x1, y1, x2, y2)


import cv2
import numpy as np
import time
import os

def capture_images_with_exposure(camera_index, roi_size, fps, exposure_times, output_dir, num, leaser_powers, controller):
    """
    :param camera_index: 相机编号
    :param roi_size: 中心计算区域大小
    :param fps: 相机设定帧率
    :param exposure_times: 曝光时间序列
    :param output_dir: 采集图像输出路径
    :param num: 每个曝光时间的图像采样数
    :param leaser_powers: 激光功率序列
    :param controller: 控制激光功率的对象
    :return: 所有k方的数组，用于后续函数拟合
    """

    k_averages = []
    k_average_all = []

    # 相机开机
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Error: Unable to access the camera.")
        return
    cap.set(cv2.CAP_PROP_FPS, fps)

    # 禁用自动曝光（某些相机需要）
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)

    # 创建窗口并设置为持续显示模式
    cv2.namedWindow('Camera Feed', cv2.WINDOW_NORMAL)

    # 根据曝光序列采集图像
    for idx, exposure in enumerate(exposure_times):
        print(f"\n设置曝光时间为 {exposure} ms...")
        cap.set(cv2.CAP_PROP_EXPOSURE, float(exposure))
        time.sleep(1)  # 等待曝光设置生效

        power = leaser_powers[idx]
        print(f"设置激光功率为 {power}...")
        controller.set_power_state(power)
        time.sleep(1)  # 等待激光器稳定

        k_values = []

        for i in range(num):
            ret, frame = cap.read()
            if not ret:
                print(f"Error: Unable to capture frame {i + 1} for exposure {exposure} ms.")
                continue

            frame_with_roi, (x1, y1, x2, y2) = set_roi(frame, roi_size=roi_size)
            roi_frame = frame_with_roi[y1:y2, x1:x2]

            cv2.imshow('Camera Feed', frame)

            k_value = cac_k(roi_frame, 2)  # 计算k^2
            k_values.append(k_value)

            if cv2.waitKey(10) & 0xFF == ord('q'):
                print("Exiting...")
                break

        if k_values:
            k_average = np.mean(k_values)
            k_average_all.append(k_average)
            k_averages.append((exposure, k_average))
            print(f"曝光时间 {exposure} ms 的平均 k 值: {k_average:.4f}")
        else:
            print(f"曝光时间 {exposure} ms 没有有效的 k 值。")

    # 打印所有结果
    print("\n所有曝光时间的平均 k 值：")
    for exposure, k_avg in k_averages:
        print(f"曝光时间 {exposure} ms: 平均 k 值 = {k_avg:.4f}")

    print("\n=== k 值数组 ===")
    print(["{:.4f}".format(float(x)) for x in k_average_all])

    cap.release()
    cv2.destroyAllWindows()
    print("Capture complete. Images saved in:", output_dir)

    return k_average_all


if __name__ == "__main__":
    # 曝光2，只有20帧率，最小调节步长为1
    # exposure_times = [0.05, 0.1, 0.15, 0.20, 0.3, 0.5, 1, 2, 4, 6, 8, 12, 20, 30]
    # 打开串口
    controller = ComSetting()
    port_name = "COM6"

    # 初始化串口连接
    if controller.init_serial(port_name):
        # 打开激光器
        controller.send_data(controller.open_cmd)
        time.sleep(0.5)

        # 设置激光器功率
        # controller.set_power(200)

    # control = ComSetting()
    # 测光用的曝光序列，用实际曝光时长
    exposure_times = [ -4, -3 ,-2,-1, 2]
    #exposure_times = [-4, -3, -2, 0, -1, 2]
    #exposure_times = [-4, -3, 1, -2, -1, 2]
    camera_index = 0
    output_dir = "m_pictures"
    roi_size = 200
    fps = 20  # 最小帧率，对应最大曝光时间
    num = 10  # 平均值计算用的帧数
    k_min = 80
    k_max = 120

    # 测光
    #leaser_powers = controller.leaser_calibration(k_min, k_max,exposure_times, camera_index, fps=20, roi_size=50, initial_power=200)
    leaser_powers = [200, 160, 90, 83, 80 ]
    # 某一次标定得到的激光功率
    #leaser_powers = [310, 310, 200, 100, 100, 100]
    print(f"激光器功率序列为：{leaser_powers}")
    k_average_all = capture_images_with_exposure(camera_index, roi_size, fps, exposure_times, output_dir, num,leaser_powers, controller)
    initial_params = [0.5, 50, 0.05]
    # 数据拟合，一定要用正序列
    #exposure_times_fake = [16, 19, 24, 50, 100]
    exposure_times_fake = [6.25, 12.5, 25,50, 100]
    #exposure_times_fake = [6.25, 12.5, 25, 50, 100, 400]
    cac_LM(exposure_times_fake, k_average_all, initial_params)
    print(f"激光器功率序列为：{leaser_powers}")
