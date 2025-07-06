import sys
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.uic import loadUi

APP_VERSION = "V1.2"
"用python重写的激光器控制程序，主要是为了分解串口命令，为leaser_control程序提供基础"

class FringeSetting(QMainWindow):
    def __init__(self):
        super().__init__()
        # 使用 PyQt Designer 创建的 .ui 文件
        loadUi("FringeSetting.ui", self)

        self.setWindowTitle(f"IMAI HPL Controller {APP_VERSION}")
        self.serial_port = None
        self.timer = QTimer(self)

        self.open = "aa00000100018e"
        self.close = "aa00000000008e"
        self.power = "aa00030000038e"
        self.leaser_para = "aa00060000068e"

        # 填充串口下拉框
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.comboBox.addItem(port.device)

        # 初始化 UI 状态
        self.lineEdit.setText("50")
        self.lineEdit.setEnabled(False)
        self.pushButton_Open_3.setEnabled(False)
        self.checkBox.setEnabled(False)
        self.checkBox_fan.setEnabled(False)

        # 信号连接
        self.pushButton_Open.clicked.connect(self.toggle_serial_port)
        self.pushButton_Open_3.clicked.connect(self.set_power)
        self.checkBox.clicked.connect(self.toggle_laser)
        self.checkBox_fan.clicked.connect(self.toggle_fan)
        self.timer.timeout.connect(self.timer_update)
        # self.timer.start(200)

    def init_serial(self, port_name):
        """初始化串口"""
        try:
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
            )
            return True
        except serial.SerialException as e:
            QMessageBox.critical(self, "Error", f"Failed to open port {port_name}: {e}")
            return False

    def toggle_serial_port(self):
        """打开/关闭串口"""
        if self.serial_port and self.serial_port.is_open:
            # 关闭串口
            self.timer.stop()
            self.serial_port.close()
            self.pushButton_Open.setText("Open")
            self.label_ComSta.setPixmap(QPixmap("res/invisible.png"))
            self.lineEdit.setEnabled(False)
            self.pushButton_Open_3.setEnabled(False)
            self.checkBox.setEnabled(False)
            self.checkBox_fan.setEnabled(False)
        else:
            # 打开串口
            port_name = self.comboBox.currentText()  # COM6
            if self.init_serial(port_name):
                self.pushButton_Open.setText("Close")
                self.label_ComSta.setPixmap(QPixmap("res/visible.png"))
                self.lineEdit.setEnabled(True)
                self.pushButton_Open_3.setEnabled(True)
                self.checkBox.setEnabled(True)
                self.checkBox_fan.setEnabled(True)
                self.write_command("aa00060000068e")  # 查询激光状态
                self.timer.start(200)

    def write_command(self, command):
        """发送命令到串口"""
        if self.serial_port and self.serial_port.is_open:
            # 将命令转换为 QByteArray 类型
            data = self.string_to_hex(command)

            # 计算校验位
            checksum = 0
            for i in range(1, 5):  # 假设校验位是对前四个字节进行异或
                checksum ^= data[i]  # 直接使用 data[i]，它本身是 int 类型

            # 更新校验位
            data[5] = checksum

            # 发送数据到串口
            self.serial_port.write(data)

    def string_to_hex(self, str_data):
        """将字符串转换为字节数组（hex）"""
        return bytearray.fromhex(str_data)

    def timer_update(self):
        """定时器回调，用于发送查询命令"""
        commands = [
            "aa00020000028e",  # 版本号
            "aa00030000038e",  # 功率
            "aa000e00000e8e",  # TEC 温度
            "aa000f00000f8e",  # TEC 电流
            "aa00100000108e",  # LD 电流
        ]
        static_counter = getattr(self, "_counter", 0)
        self.write_command(commands[static_counter])
        static_counter = (static_counter + 1) % len(commands)
        setattr(self, "_counter", static_counter)
        # 激光器参数读取接口
        self.read_data()

    def toggle_laser(self):
        """控制激光器开关"""
        if self.checkBox.isChecked():
            self.write_command("aa00000100018e")
            self.label_Laser_Status.setPixmap(QPixmap("res/laser.png"))
        else:
            self.write_command("aa00000000008e")
            self.label_Laser_Status.setPixmap(QPixmap("res/laser_gray.png"))

    def toggle_fan(self):
        """控制风扇开关"""
        if self.checkBox_fan.isChecked():
            self.write_command("aa00070000018e")
        else:
            self.write_command("aa00070100008e")

    def set_power(self):
        """设置激光器功率"""
        power = int(self.lineEdit.text())
        power = max(1, min(600, power))  # 限制范围
        self.lineEdit.setText(str(power))

        high_byte = (power >> 8) & 0xFF
        low_byte = power & 0xFF
        command = f"aa000103{high_byte:02x}{low_byte:02x}8e"
        self.write_command(command)

    def read_data(self):
        """读取并解析串口数据"""
        if self.serial_port and self.serial_port.is_open:
            # 读取数据并解析
            data = self.serial_port.read(16)
            if data:
                # 解析数据，根据命令的返回值显示不同的信息
                if data[0] == 0x84:
                    # 假设返回值是版本号
                    version = f"{data[1]}.{data[2]}"
                    self.label_7.setText(f"Version: {version}")
                elif data[0] == 0x83:
                    # 假设返回值是功率信息
                    power = data[2] * 255 + data[3]
                    self.label_6.setText(f"Power: {power} mW")
                elif data[0] == 0x0E:
                    # 假设返回值是TEC温度
                    temperature = (data[2] * 255 + data[3]) / 100.0
                    self.label_3.setText(f"TEC Temp: {temperature:.2f} °C")
                elif data[0] == 0x0F:
                    # 假设返回值是TEC电流
                    current = (data[2] * 255 + data[3])
                    self.label_4.setText(f"TEC Current: {current} mA")
                elif data[0] == 0x10:
                    # 假设返回值是LD电流
                    ld_current = data[2] * 255 + data[3]
                    self.label_5.setText(f"LD Current: {ld_current} mA")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FringeSetting()
    window.show()
    sys.exit(app.exec_())
