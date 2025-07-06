import matplotlib.pyplot as plt
import pandas as pd
"论文中数据绘图"
# 原始数据
data = [
    [50, 1.2, 128.32, 299],
    [75, 1.21, 126.2, 299],
    [100, 1.21, 127.6, 299],
    [125, 1.96, 125.62, 299],
    [150, 1.21, 127, 299],
    [175, 1.2, 128.26, 299],
    [200, 1.23, 128.26, 299],
    [225, 1.22, 128.26, 299],
    [250, 1.21, 125, 299],
    [275, 1.21, 128.26, 299],
    [300, 1.19, 128.26, 299],
    [325, 1.189, 128, 300],
    [350, 1.21, 125.26, 300],
    [375, 1.21, 128.26, 300],
    [400, 1.21, 130, 300],
    [425, 1.22, 128.26, 300],
    [450, 1.21, 126.7, 300],
    [500, 1.2, 128.26, 301],
    [1000, 1.21, 131, 302],
    [2000, 1.21, 129, 303],
    [4000, 1.22, 128.2, 303],
    [8000, 1.23, 129.01, 304]
]

df = pd.DataFrame(data, columns=["X", "Y1", "Y2", "Y3"])

# 绘图
plt.figure(figsize=(10, 6))

plt.plot(df["X"], df["Y1"], marker='o', label='T=6.25ms', color='blue')
plt.plot(df["X"], df["Y2"], marker='s', label='T=12.5ms', color='green')
plt.plot(df["X"], df["Y3"], marker='^', label='T=25ms', color='red')

plt.xscale('log')  # 横坐标使用对数刻度

# 美化
plt.xlabel("Blood flow rate(uL/min)")
plt.ylabel("1/K²")
plt.title("Single exposure blood flow measurement")
plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
plt.tight_layout()
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.tight_layout()

plt.show()
