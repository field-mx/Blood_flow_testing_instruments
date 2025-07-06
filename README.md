# Blood_flow_testing_instruments
abstract：  
Blood flow velocity, volume, and pulse wave are key indicators of blood circulation and cardiovascular health. Continuous, quantitative in vivo measurements support health monitoring and treatment evaluation, with significant research and application value. Unlike bulky desktop devices, wearable blood flow detectors are lightweight, enable real-time monitoring, and are ideal for home and mobile healthcare. Diffuse speckle measurement, with high sensitivity, non-invasiveness, and a simple structure (light source and detector), suits integrated design. It uses coherent light to create a speckle pattern from scattered light in tissue, where red blood cell movement alters the pattern, allowing blood flow analysis through statistical changes.
This study focuses on the development and optimization of a wearable in vivo blood flow monitoring system, proposing and implementing a solution that integrates real-time monitoring, portability, and quantitative capability. The work spans four main areas: theoretical analysis, hardware design, algorithm development, and experimental validation.First, based on the principles of diffuse speckle detection, the system was optimized for wearable applications through simulations to determine the design parameters of the probe.Second, the mechanical components—including casing, support structures, and thermal management—were designed for system integration. A noise reduction and filtering algorithm tailored to the available hardware resources was implemented to ensure robust blood flow monitoring and pulse wave extraction under complex environmental conditions.Finally, a series of experiments—including multi-posture pulse wave measurements, blood flow occlusion tests, and quantitative flow velocity comparison experiments—were conducted to verify the system’s stability in heart rate and pulse wave detection, as well as the linearity of its quantitative blood flow measurements.The results demonstrate that the system can achieve stable and reliable monitoring of blood flow parameters under non-invasive and portable conditions, showing strong potential for clinical and home healthcare applications.  

中文摘要：  
本项目为一款穿戴式扩散散斑血流检测仪器的算法控制代码，包括散斑处理，单曝光血流脉搏波显示，多曝光血流定量测量等功能。可在win平台与linux平台上实现。  
使用方法：  
win：运行s_DSCA.py,系统进行单曝光测量，实时显示脉搏波形与心率。运行m_DSCA.py，系统进行一次多曝光血流检测返回血流指数，该指数与血流速度呈线性关系（0.85）。  
linux：复制linux文件夹中的s_DSCA.py与m_DSCA.py，替换win文件夹中的同名文件，运行后即可实现相功能。  

拥有仪器本体：  
硬件准备：树莓派通过usb口连接激光器与ccd，同时保证5V稳定供电，供电是波形显示帧率的关键。
step1 开机后打开pycharm，打开同名项目  
step2 运行s_DSCA.py与m_DSCA.py以分别实现单曝光与多曝光。  

ps：如果帧率较低，请检查树莓派供电，提供充足电流。
