% 添加 mcxlab 的路径（根据你的安装路径修改）
addpath('D:\software\mcxlab-allinone-v2025\mcxlab\matlab');

% 读取 .mch 文件
%mch_file = 'C:\Users\32009\MCXOutput\mcxsessions\tju-毕设\tju-毕设.mch';
mch_file = 'C:\Users\32009\MCXOutput\mcxsessions\tissue\tissue.mch';
photons = loadmch(mch_file);

% 打开 mch 文件，读取文件头部分
fid = fopen(mch_file, 'rb');
if fid == -1
    error('无法打开文件: %s', mch_file);
end

% 读取 256 字节文件头
header = fread(fid, 256, 'uint8');

% 验证 magic 字节是否正确
magic = char(header(1:4)');
if ~strcmp(magic, 'MCXH')
    error('文件格式无效，未检测到 "MCXH" 魔法字节。');
end

% 读取各字段数据
version = fread(fid, 1, 'uint32');  % 版本号
maxmedia = fread(fid, 1, 'uint32');  % 最大介质数
detnum = fread(fid, 1, 'uint32');   % 检测器数量
colcount = fread(fid, 1, 'uint32'); % 每个光子数据的列数
totalphoton = fread(fid, 1, 'uint32'); % 总光子数
detected = fread(fid, 1, 'uint32');  % 检测到的光子数
savedphoton = fread(fid, 1, 'uint32'); % 保存的光子数
unitinmm = fread(fid, 1, 'float32');  % 每个体素的尺寸（单位：mm）
seedbyte = fread(fid, 1, 'uint32');   % 每个光子的 RNG 种子字节数
normalizer = fread(fid, 1, 'float32'); % 归一化因子
respin = fread(fid, 1, 'int32');      % 重复仿真次数
srcnum = fread(fid, 1, 'uint32');    % 光源数量
savedetflag = fread(fid, 1, 'uint32'); % 光子保存的检测标志
totalsource = fread(fid, 1, 'uint32'); % 总光源数量

% 输出文件头信息
fprintf('Magic: %s\n', magic);
fprintf('Version: %d\n', version);
fprintf('Max Media: %d\n', maxmedia);
fprintf('Detector Count: %d\n', detnum);
fprintf('Column Count: %d\n', colcount);
fprintf('Total Photons: %d\n', totalphoton);
fprintf('Detected Photons: %d\n', detected);
fprintf('Saved Photons: %d\n', savedphoton);
fprintf('Voxel Size (in mm): %.4f\n', unitinmm);
fprintf('Seed Byte Count: %d\n', seedbyte);
fprintf('Normalizer: %.4f\n', normalizer);
fprintf('Respin: %d\n', respin);
fprintf('Source Count: %d\n', srcnum);
fprintf('Save Detector Flag: %d\n', savedetflag);
fprintf('Total Source Count: %d\n', totalsource);
% 查看数据尺寸
fprintf('光子数据维度: %d 个光子，%d 个字段\n', size(photons,1), size(photons,2));




% 提取数据
step = photons(:, 3);      % 第3列：模长 / 步长
x0 = photons(:, 6);        % 第6列：起点 x
y0 = photons(:, 7);        % 第7列：起点 y
z0 = photons(:, 8);        % 第8列：起点 z
ux = photons(:, 9);        % 第9列：方向向量 x
uy = photons(:, 10);       % 第10列：方向向量 y
uz = photons(:, 11);       % 第11列：方向向量 z

% 计算终点坐标
x_end = x0 - step .* ux;
y_end = y0 - step .* uy;
z_end = z0 - step .* uz;





unitinmm = 0.1;
% 将终点坐标转换为毫米单位
x_end_mm = x_end * unitinmm;
y_end_mm = y_end * unitinmm;
z_end_mm = z_end * unitinmm;

% 反转 z 轴方向
z_end_mm = -z_end_mm;

% 创建颜色映射数组，初始化为黑色
colors = zeros(length(z_end_mm), 3);

% 反转颜色映射：大于 2.2 mm 用蓝色，介于 0.2 和 2.2 mm 之间用橙色，0 到 0.2 mm 用红色
colors(z_end_mm > -0.2, :) = repmat([31, 119, 180]/255, sum(z_end_mm > -0.2), 1);  % 蓝色：深层
colors(z_end_mm > -2.2 & z_end_mm <= -0.2, :) = repmat([255, 127, 14]/255, sum(z_end_mm > -2.2 & z_end_mm <= -0.2), 1);  % 橙色：中层
colors(z_end_mm <= -2.2, :) = repmat([1, 0, 0], sum(z_end_mm <= -2.2), 1);  % 红色：浅层


% 绘制带颜色的点云图
figure;
scatter3(x_end_mm, y_end_mm, z_end_mm, 5, colors, 'filled');
xlabel('X /mm');
ylabel('Y /mm');
zlabel('皮肤深度/mm');
title('探测到的光子来源分布');
axis equal;
grid on;
view(3);

% 添加图例说明（示意）
hold on;
h1 = scatter3(NaN, NaN, NaN, 30, [31, 119, 180]/255, 'filled'); % 浅层：蓝色
h2 = scatter3(NaN, NaN, NaN, 30, [255, 127, 14]/255, 'filled'); % 中层：橙色
h3 = scatter3(NaN, NaN, NaN, 30, [1 0 0], 'filled');            % 深层：红色

% 创建图例
lgd = legend([h1 h2 h3], ...
    {'0–0.2 mm（表皮层）', '0.2–2.2 mm（真皮层）', '>2.2 mm（皮下组织）'}, ...
    'Location', 'northeast', ...
    'Orientation', 'vertical');

% 设置图例为不透明背景
set(lgd, 'Box', 'on', 'Color', 'white', 'FontSize', 10);

% 调整图例位置：将其放置在图像的右上角
% 获取当前图像的轴（axes）大小
ax = gca;
pos = ax.Position;  % [left, bottom, width, height]

% 设置图例位置：右上角，保持图像高度一致
lgd.Position = [pos(1) + pos(3) + 0.02, pos(2) + pos(4) - 0.2, 0.1, 0.2];



% 设置 bin 的数量，例如划分为 100 个 z 区间
num_bins = 100;

% 将光子终点的 z 坐标转换为毫米单位
z_end_mm = z_end * 0.1;

% 计算直方图：z 轴终点分布（单位：mm）
[z_counts, z_edges] = histcounts(z_end_mm, num_bins);

% 仅使用 0 到 10 mm 之间的光子数据，过滤其他范围的光子
valid_indices = z_end_mm >= 0 & z_end_mm <= 10;
z_counts = histcounts(z_end_mm(valid_indices), z_edges);

% 绘制折线图
figure;
bar(z_edges(1:end-1), z_counts, 'histc');  % 使用 bar 绘制直方图
xlabel('皮肤深度/mm');
ylabel('光子数量');
title('探测到光子的深度分布');
grid on;

% 设置横坐标的范围从 0 到 10 mm
xlim([0 10]);

% 计算光子总数
total_photons = sum(z_counts);
disp(['光子总数: ', num2str(total_photons)]);




