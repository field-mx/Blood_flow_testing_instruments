import time

import cv2
import keyboard
import numpy as np
import serial


"本程序用于转译激光控制软件，重写串口通信函数，可直接调用程序中的函数进行激光器功率控制，详见各个函数注释"
class ComSetting:
    def __init__(self):
        self.serial_port = None  # 串口对象
        self.open_cmd = "aa00000100018e"
        self.close_cmd = "aa00000000008e"
        self.leaser_para_cmd = "aa00060000068e"
        self.power = "aa00030000038e"  # 功率
        self.TEC_temperature = "aa000e00000e8e"  # TEC 温度
        self.TEC_current = "aa000f00000f8e"  # TEC 电流
        self.LD_current = "aa00100000108e"  # LD 电流
        self._counter = 0  # 用于定时器回调的计数器

    def set_roi(self, frame, roi_size=50):
        height, width, _ = frame.shape
        x1 = (width - roi_size) // 2
        y1 = (height - roi_size) // 2
        x2 = x1 + roi_size
        y2 = y1 + roi_size
        return frame, (x1, y1, x2, y2)

    def calculate_histogram_mean(self, image):
        """
        计算灰度图像的均值
        :param image: 输入图像
        :return: 图像的灰度均值
        """
        # 转换为灰度图像
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 计算图像的均值
        mean = np.mean(gray_image)

        return mean

    def set_power_state(self, power):
        """
        power:设定的功率
        :return:0
        """
        # 设置功率
        self.set_power(power)
        time.sleep(0.1)
        while True:
            # 读取功率
            self.send_data(self.power)

            current_power = self.read_data()
            if current_power is not None and isinstance(current_power, (int, float)):
                # 计算功率误差
                power_error = abs(current_power - power)

                # 如果误差小于5，认为设置成功
                if power_error <= 5:
                    print(f"功率设置成功: 目标功率 {power}, 当前功率 {current_power}")
                    break
                else:
                    print(f"功率设置中: 目标功率 {power}, 当前功率 {current_power}, 误差 {power_error}")
            #else:
                # 如果读取的功率数据无效，则继续等待
                #print(f"当前功率读取无效，继续等待...")

        print(f"调整功率至 {power}")


    def leaser_calibration(self, k_min, k_max, exposure_times, camera_index, fps=20, roi_size=50, initial_power=500):
        """
        激光曝光标定序列
        :param fps: 采样帧率
        :param camera_index: 相机编号
        :param exposure_times: 相机曝光序列
        :return: 激光输出功率序列[w1, w2, w3, ...wn]
        """
        power = initial_power

        # 相机初始化
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("Error: Unable to access the camera.")
            return []
        cap.set(cv2.CAP_PROP_FPS, fps)

        laser_powers = []  # 记录激光器的功率序列

        for idx, exposure in enumerate(exposure_times):
            print(f"曝光{exposure}")
            cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
            time.sleep(0.5)  # 稳定相机参数

            # 调整激光功率和曝光参数
            while power > 0:
                # 读取图像
                ret, frame = cap.read()
                if not ret:
                    print(f"Error: Unable to capture frame for exposure {exposure} ms.")
                    break

                # 标记 ROI 区域
                frame_with_roi, (x1, y1, x2, y2) = self.set_roi(frame, roi_size=roi_size)
                roi_frame = frame[y1:y2, x1:x2]

                # 计算 ROI 区域内均值
                mean = self.calculate_histogram_mean(roi_frame)

                # 实时显示信息到图像上
                cv2.rectangle(frame_with_roi, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame_with_roi, f"Exposure: {exposure} ms", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame_with_roi, f"Power: {power}", (20, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame_with_roi, f"Mean: {mean:.2f}", (20, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                # 实时显示画面
                cv2.imshow("Calibration Feed", frame_with_roi)
                key = cv2.waitKey(1)
                if key == ord('q'):  # 按 q 键退出
                    cap.release()
                    cv2.destroyAllWindows()
                    return laser_powers

                # 判断均值是否满足范围
                if k_min <= mean <= k_max:
                    laser_powers.append(power)
                    print(f"曝光 {exposure} ms: 满足条件，记录功率 {power}")
                    break
                elif mean > k_max:
                    power -= 10  # 调整功率
                    # 确保功率不会低于下限
                    if power < 10:
                        power = 10
                    self.set_power_state(power)
                elif mean < k_min:
                    power += 10  # 调整功率
                    # 确保功率不会超过上限
                    if power > 500:
                        power = 500
                    self.set_power_state(power)
            if power <= 0:
                print("Warning: 激光器功率降到最小，未满足均值条件！")
                laser_powers.append(0)

        # 清理资源
        """
        cap.release()
        cv2.destroyAllWindows()
        """
        print("Calibration complete.")
        return laser_powers

    def send_data(self, command):
        """
        发送数据到串口
        """
        data = self.string_to_hex(command)
        if not data:
            print("命令转换失败，无法发送")
            return

        try:
            if self.serial_port and self.serial_port.is_open:
                bytes_written = self.serial_port.write(data)
                # print(f"成功发送 {bytes_written} 字节数据: {data}")
            else:
                print("串口未打开，无法发送数据")
        except Exception as e:
            print(f"发送数据失败: {e}")

    def read_data(self):
        """
        读取并解析串口返回数据
        """
        if not self.serial_port or not self.serial_port.is_open:
            print("串口未打开，无法读取数据")
            return None

        try:
            data = self.serial_port.read(16)  # 假设每次读取 16 字节数据
            if not data:
                #print("未接收到数据")
                return None

            print(f"收到的原始数据: {data}")
            # 数据解析逻辑，根据协议格式解析不同内容
            if data[0] == 0x84:  # 版本号
                version = f"{data[1]}.{data[2]}"
                print(f"Version: {version}")
                return version
            elif data[0] == 0x82:  # 激光器关闭
                print("Laser closed")
                return "Laser closed"
            elif data[0] == 0x83:  # 功率
                if data[1] == 0x03:
                    power = data[2] * 255 + data[3]
                    print(f"Power: {power} mW")
                    return power
                elif data[1] == 0x0E:  # TEC 温度
                    temperature = (data[2] * 255 + data[3]) / 100.0
                    print(f"TEC Temp: {temperature:.2f} °C")
                    return temperature
                elif data[1] == 0x0F:  # TEC 电流
                    current = data[2] * 255 + data[3]
                    print(f"TEC Current: {current} mA")
                    return current
                elif data[1] == 0x10:  # LD 电流
                    ld_current = data[2] * 255 + data[3]
                    print(f"LD Current: {ld_current} mA")
                    return ld_current

            else:
                #print("未知的返回数据类型")
                return None
        except Exception as e:
            print(f"读取数据失败: {e}")
            return None

    def set_power(self, power):
        """
        设置激光器功率
        """
        # 限制功率范围
        if power < 1:
            print("警告: 功率小于最小值，已设置为 1")
            power = 1
        elif power > 600:
            print("警告: 功率大于最大值，已设置为 600")
            power = 600

        # 转换功率为高低字节
        high_byte = (power >> 8) & 0xFF
        low_byte = power & 0xFF

        # 初始指令模板
        hex_string = "aa00010000008e"
        send_data = bytearray.fromhex(hex_string)

        # 替换功率字节
        send_data[3] = high_byte
        send_data[4] = low_byte

        # 计算校验和
        checksum = send_data[2] ^ send_data[3] ^ send_data[4]
        send_data[5] = checksum
        print("功率指令为：", send_data)
        # 发送数据
        self.send_data(send_data)

    def init_serial(self, port_name, baudrate=9600, timeout=1):
        """
        初始化串口连接
        """
        try:
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=8,  # 数据位
                parity='N',  # 无校验位
                stopbits=1,  # 停止位
                timeout=timeout  # 超时
            )
            if self.serial_port.is_open:
                print(f"成功打开串口: {port_name}")
                return True
        except Exception as e:
            print(f"打开串口失败: {e}")
        return False

    def string_to_hex(self, command):
        """
        将字符串命令转换为字节数组
        """
        try:
            # 如果传入的是 bytearray 类型，直接返回
            if isinstance(command, bytearray):
                hex_data = command
            # 如果是字符串类型，调用 fromhex 转换
            elif isinstance(command, str):
                hex_data = bytearray.fromhex(command)
            else:
                raise ValueError("命令必须是字符串或字节数组类型")

            # print(f"转换为十六进制: {hex_data}")
            return hex_data
        except ValueError as e:
            print(f"命令格式错误: {e}")
            return None

    def close_serial(self):
        """
        关闭串口
        """
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            print("串口已关闭")

    def timer_update(self):
        """定时器回调，用于发送查询命令"""
        # 查询命令列表
        commands = [
            "aa00020000028e",  # 版本号
            "aa00030000038e",  # 功率
            "aa000e00000e8e",  # TEC 温度
            "aa000f00000f8e",  # TEC 电流
            "aa00100000108e",  # LD 电流
        ]

        # 获取当前计数器值
        static_counter = self._counter
        self.send_data(commands[static_counter])

        # 更新计数器，循环发送命令
        self._counter = (self._counter + 1) % len(commands)

        # 等待并读取返回数据
        # time.sleep(1)
        result = self.read_data()
        if result:
            print(f"读取到的结果: {result}")
        else:
            print("没有读取到有效数据")


# 主程序
if __name__ == "__main__":
    # 初始化对象
    controller = ComSetting()

    port_name = "COM6"

    # 初始化串口连接
    if controller.init_serial(port_name):
        # 打开激光器
        controller.send_data(controller.open_cmd)
        time.sleep(0.5)

        # 设置激光器功率
        controller.set_power(500)

        # 启动定时器回调，用于定时查询
        while True:
            controller.send_data(controller.power)

            result = controller.read_data()
            if keyboard.is_pressed('enter'):  # 检测是否按下 'q' 键
                print("检测到'Enter'键，跳出循环")
                break

        # 关闭激光器
        controller.send_data(controller.close_cmd)
        time.sleep(1)

        # 关闭串口
        controller.close_serial()
    else:
        print(f"无法打开串口: {port_name}")
