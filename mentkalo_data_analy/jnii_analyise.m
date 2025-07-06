% 添加 mcxlab 的路径
addpath('D:\software\mcxlab-allinone-v2025\mcxlab\matlab');

% 指定 mc2 文件路径
filename = 'C:\Users\32009\MCXOutput\mcxsessions\tju-毕设\tju-毕设.mc2';

% === 提供数据维度信息（请根据实际仿真设置修改这些值）===
Ns = 1;    % 样本数量，通常为1
Nx = 150;  % x方向体素数量（例如100）
Ny = 150;  % y方向体素数量
Nz = 10;  % z方向体素数量
Ng = 1;    % 时间窗数量（如果没有使用时间门控，设为1）

% 打开 mc2 文件
fid = fopen(filename, 'rb');
if fid == -1
    error('无法打开文件: %s', filename);
end

% 读取所有数据为单精度浮点数
raw_data = fread(fid, 'single');

% 关闭文件
fclose(fid);

% 重构为 5D 数组（MCX 使用列优先顺序）
data = reshape(raw_data, [Ns, Nx, Ny, Nz, Ng]);

% 输出尺寸信息
fprintf('数据维度为: Ns=%d, Nx=%d, Ny=%d, Nz=%d, Ng=%d\n', Ns, Nx, Ny, Nz, Ng);
fprintf('数据总长度：%d\n', numel(data));

% 统计每个标签（体素值）出现的次数
% 注意：这只是对单时间窗和单样本的示例统计
data_single = squeeze(data(1,:,:,:,1));  % 取出一个3D数据块
data_vec = data_single(:);
[val, ~, ic] = unique(data_vec);
counts = accumarray(ic, 1);
disp('各体素值及对应非零数量：');
for i = 1:length(val)
    if val(i) ~= 0
        fprintf('体素值 %.4f 出现次数 %d\n', val(i), counts(i));
    end
end
% 统计非零值数量
nonzero_count = nnz(data);
fprintf('非零光子数体素总数：%d\n', nonzero_count);

