# DINOv2-TCN 视频原型手势算法

该目录是与 `algorithm/gesture` 并列的第二套车主手势识别算法。原算法及其原型库保持不变。

输入为连续 12 帧手部 RGB 裁剪、MediaPipe 21 点图像/世界坐标、检测置信度和左右手信息；网络融合 DINOv2-S/14、175 维手部几何特征和因果 TCN，输出 128 维归一化视频嵌入并与当前算法自己的用户原型库匹配。

部署权重默认放在 `checkpoints/best_model.pt`，也可以通过 `GESTURE_DINOV2_CHECKPOINT` 指定。独立原型库存储在 `data/gesture_prototypes.json`，可通过 `GESTURE_DINOV2_PROTOTYPE_STORE` 覆盖。

服务启动时不会加载该模型。只有用户选择“DINOv2 + TCN 视频原型”后才会加载权重，因此缺少深度学习依赖或权重不会影响原 MediaPipe 算法启动。
