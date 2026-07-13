# NVGesture fused prototype training

The trainable video encoder combines:

- DINOv2-S/14 CLS and mean patch-token features for every RGB frame;
- a 175-D MediaPipe geometry vector containing normalized landmarks, bone and
  fingertip vectors, joint-angle cosines, fingertip distances, palm normals,
  centre/scale, detection confidence and handedness;
- first and second temporal differences of the geometry features;
- gated feature fusion followed by a causal dilated TCN;
- an L2-normalized video embedding trained with episodic prototype loss.

The first five epochs keep DINOv2 frozen. From epoch six onward only its final
two Transformer blocks and final LayerNorm are trainable. NVGesture's official
subject-independent train/test lists are retained.

## Server commands

Run from `/home/aoxiang/visiondrive/app/algorithm`:

```bash
/home/aoxiang/miniconda3/envs/gesture_train/bin/python -m gesture.training.prepare_nvgesture \
  --dataset-root /home/aoxiang/visiondrive/data/nvgesture_raw \
  --output-dir /home/aoxiang/visiondrive/data/nvgesture_prepared \
  --gesture-model /home/aoxiang/visiondrive/app/algorithm/gesture/app/public/models/gesture_recognizer.task

/home/aoxiang/miniconda3/envs/gesture_train/bin/python -m gesture.training.train \
  --config gesture/training/config.nvgesture.yaml \
  --output-dir /home/aoxiang/visiondrive/output/gesture_dinov2_tcn_proto
```

Use `--limit 10` during preprocessing and `--smoke-test` during training for a
small end-to-end validation before starting the complete experiment.

The loader accepts both the original `sk_color.avi` files and mirrors where an
AVI has already been expanded into a sorted `sk_color/img*.jpg` directory.

`run_server_pipeline.sh` is the server-side resumable sequence used for this
experiment. It waits for the exact archive size, extracts only RGB files and
official lists, preprocesses all clips, runs a smoke test and starts the full
training only if every previous stage succeeds.
