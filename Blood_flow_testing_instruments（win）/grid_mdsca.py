import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
"该程序用于拟合直线绘图，作论文中图片用"
# 数据
x = np.array([150, 175, 200, 225, 250]).reshape(-1, 1)
y = np.array([2.07039, 2.31588, 2.33426, 2.36406, 2.724796])

# 拟合直线
model = LinearRegression()
model.fit(x, y)
y_pred = model.predict(x)
r2 = r2_score(y, y_pred)

plt.figure(figsize=(8, 6))
plt.plot(x, y_pred, 'r--', label='Least Squares Fit')  # 红色虚线
plt.scatter(x, y, color='blue', label='Data Points')   # 蓝色数据点
plt.xlabel('Flow Rate (μL/min)')
plt.ylabel('Inverse Correlation Time (ICT)')
plt.title('ICT versus Actual Flow Rate')
plt.ylim(1, 3.5)
plt.text(160, 3.3, f'$R^2 = {r2:.4f}$', fontsize=12, color='red')  # 可选：红色r²与拟合线一致
plt.legend()
plt.grid(False)
plt.tight_layout()
plt.show()

