vol = ones(100, 100, 100);
vol(:, :, 3:22) = 2;
vol(:, :, 23:100) = 3;

fid = fopen('three_layer_volume.bin', 'wb');
fwrite(fid, uint8(vol), 'uint8');
fclose(fid);
