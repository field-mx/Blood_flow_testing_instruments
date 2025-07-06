import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

"本程序定义了lm算法，用途：在多曝光方法中调用cac——lm进行函数拟合"
# 定义模型函数
def model_func_k(t, p, tao, v_noise, beta=0.25):
    x = t / tao
    x_safe = np.where(x == 0, 1e-10, x)  # 避免分母为 0
    term1 = beta * p ** 2 * ((np.exp(-2 * x_safe) - 1 + 2*x_safe) / (2 * x_safe ** 2))
    term2 = 4 * beta * p * (1 - p) * ((np.exp(-x_safe) - 1 + x_safe) / (x_safe ** 2))
    term3 = beta * ((1 - p) ** 2)

    return term1 + term2 + term3 + v_noise


def cac_LM(exposure_times, y_data, initial_params):
    # 使用 Levenberg-Marquardt（'lm'）方法拟合数据
    #t_data = np.power(10, exposure_times)
    t_data = [x + 0 for x in exposure_times]
    #t_data = np.log10(10 ** np.array(exposure_times))
    params, params_covariance = curve_fit(model_func_k, t_data, y_data, p0=initial_params, method='lm')
    """
    dogbox
    trf
    lm
    """

    #qprint("拟合参数:", params)
    print(f"p={params[0]},tao_c={params[1]},v_niose={params[2]}")

    # 绘制结果
    plt.scatter(t_data, y_data, label='test_data', color='blue')
    plt.plot(t_data, model_func_k(t_data, *params), label='curve_fitting_line', color='red')
    plt.legend()
    plt.xlabel('exposure_time/ms')
    plt.ylabel('k^2 ')
    plt.title(' fitting results')
    plt.show()





# 生成样本数据
#t_data = np.linspace(0, 4, 50)  # 时间数据
#y_data = model_func_k(t_data, 0.25, 72.9, 0.0263) + 0.05 * np.random.normal(size=len(t_data))  # 生成带噪声的响应数据
"""
exposure_times = [-4, -3, -2, -1, 1, 2]
#exposure_times = [62.5, 125, 250, 500, 2000, 4000]
y_data = [0.0055, 0.0017, 0.0009, 0.0008,  0.0009, 0.0004]
# 使用 LM 算法拟合
initial_params = [0.5, 50, 0.05]  # 合理的初始参数
cac_LM(exposure_times, y_data, initial_params)  # 调用函数进行拟合和绘图

#exposure_times = [-5, -4, -3, -2, 0]
exposure_times = [31.25, 62.5, 125, 250, 500, 1000]
y_data = [0.0063, 0.0018, 0.0005, 0.0005,  0.0005, 0.0003]
# 使用 LM 算法拟合
initial_params = [0.5, 50, 0.05]  # 合理的初始参数
cac_LM(exposure_times, y_data, initial_params)  # 调用函数进行拟合和绘图
"""