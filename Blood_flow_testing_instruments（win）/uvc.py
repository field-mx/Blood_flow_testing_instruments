import os
import cv2
import numpy as np
import time
import subprocess

"本程序用于测试uvc驱动下，利用命令行控制曝光，进行多曝光测试，输出拟合血流指数"
from matplotlib import pyplot as plt
from LM_cac import cac_LM
from leaser_control import ComSetting
from s_DSCA import cac_k

def set_roi(frame, roi_size=50):
    height, width, _ = frame.shape
    x1 = (width - roi_size) // 2
    y1 = (height - roi_size) // 2
    x2 = x1 + roi_size
    y2 = y1 + roi_size
    return frame, (x1, y1, x2, y2)

def set_exposure_time(exposure):
    """
    使用 v4l2-ctl 设置相机手动曝光时间。
    :param exposure: 曝光时间（微秒）
    """
    cmd = f"v4l2-ctl -d /dev/video0 --set-ctrl=auto_exposure=0"  # 关闭自动曝光
    subprocess.run(cmd, shell=True)

    cmd = f"v4l2-ctl -d /dev/video0 --set-ctrl=exposure_time_absolute={exposure}"
    subprocess.run(cmd, shell=True)

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

    # 确认输出路径存在
    os.makedirs(output_dir, exist_ok=True)
    # 存储所有曝光时间的平均 k 值
    k_averages = []
    k_average_all = []

    # 相机开机
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Error: Unable to access the camera.")
        return
    cap.set(cv2.CAP_PROP_FPS, fps)

    # 创建窗口并设置为持续显示模式
    cv2.namedWindow('Camera Feed', cv2.WINDOW_NORMAL)

    # 根据曝光序列截取帧
    for idx, exposure in enumerate(exposure_times):
        # 设置曝光时间（通过 Linux 命令）
        set_exposure_time(exposure * 1000)  # 转换为微秒（ms到us）

        # 根据序列设定激光器功率
        power = leaser_powers[idx]
        controller.set_power_state(power)

        k_values = []  # 存储当前曝光时间下的 k 值

        # Capture a frame and display it continuously
        for i in range(num):
            ret, frame = cap.read()
            if not ret:
                print(f"Error: Unable to capture frame {i + 1} for exposure {exposure} ms.")
                continue

            # roi区域截取图形，并计算k值
            frame_with_roi, (x1, y1, x2, y2) = set_roi(frame, roi_size=roi_size)
            roi_frame = frame[y1:y2, x1:x2]

            # 显示当前帧
            cv2.imshow('Camera Feed', frame)

            # 计算k
            k_temple = cac_k(roi_frame, 2)  # 标志位：0为k方分1，1为k，2为k方
            k_values.append(k_temple)

            # 等待10ms，以便更新窗口显示
            if cv2.waitKey(10) & 0xFF == ord('q'):  # 按'q'键退出
                print("Exiting...")
                break

        if k_values:
            k_average = np.mean(k_values)
            k_average_all.append(k_average)  # 保存k均值
            k_averages.append((exposure, k_average))  # 保存曝光时间及其均值
            print(f"曝光时间 {exposure} ms 的平均 k 值: {k_average:.2f}")
        else:
            print(f"曝光时间 {exposure} ms 没有有效的 k 值。")

    # 打印所有结果
    print("\n所有曝光时间的平均 k 值：")
    for exposure, k_avg in k_averages:
        print(f"曝光时间 {exposure} ms: 平均 k 值 = {k_avg:.2f}")

    print("\n=== k 值数组 ===")
    print(["{:.4f}".format(float(x)) for x in k_average_all])  # k_average_all为所有k方的数组

    # 关闭窗口
    cv2.destroyAllWindows()
    cap.release()

    print("Capture complete. Images saved in:", output_dir)

    return k_average_all


if __name__ == "__main__":
    # 曝光2，只有20帧率，最小调节步长为1
    # exposure_times = [0.05, 0.1, 0.15, 0.20, 0.3, 0.5, 1, 2, 4, 6, 8, 12, 20, 30]
    # 打开串口
    controller = ComSetting()
    port_name = "/dev/ttyUSB0"  # 修改为Linux上的串口端口

    # 初始化串口连接
    if controller.init_serial(port_name):
        # 打开激光器
        controller.send_data(controller.open_cmd)
        time.sleep(0.5)

        # 设置激光器功率
        # controller.set_power(200)

    # control = ComSetting()
    # 测光用的曝光序列，用实际曝光时长
    exposure_times = [0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1, 2, 4, 6, 8, 12, 20, 30]  # 单位为毫秒
    camera_index = 0
    output_dir = "m_pictures"
    roi_size = 100
    fps = 20  # 最小帧率，对应最大曝光时间
    num = 10  # 平均值计算用的帧数
    k_min = 25
    k_max = 130

    # 测光
    leaser_powers = controller.leaser_calibration(k_min, k_max, exposure_times, camera_index, fps=20, roi_size=50, initial_power=200)
    # 某一次标定得到的激光功率
    print(f"激光器功率序列为：{leaser_powers}")
    k_average_all = capture_images_with_exposure(camera_index, roi_size, fps, exposure_times, output_dir, num, leaser_powers, controller)

    print(f"k值为：{k_average_all}")
