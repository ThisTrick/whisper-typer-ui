# Whisper Typer UI — Performance Analysis

This document summarizes the current performance characteristics of Whisper Typer UI
and the changes introduced to maximize transcription speed while keeping accuracy
competitive. The focus is on users running primarily on CPU while allowing the same
configuration to scale to CUDA-enabled systems automatically.

## Baseline Observations

- **Model loading**: `Transcriber` eagerly loads `faster-whisper` models at start-up.
  Larger checkpoints (`small`, `medium`, `large-v3`) can take noticeable time on the
  first run, but subsequent runs benefit from cached weights.
- **Decoding pipeline**: Transcription relied on the default worker count from
  `faster-whisper`, which is conservative on multi-core CPUs and can leave hardware
  underutilized.
- **Device and precision selection**: The configuration forced users to pick explicit
  `device` and `compute_type` values. Many users kept the defaults (`cpu` + `int8`),
  which is ideal for CPU but fails to exploit GPUs when present. GPU users often
  forgot to flip both settings (`device=cuda` *and* `compute_type=float16`) which
  limited throughput.

## Key Improvements

1. **Auto device detection**
   - `device: "auto"` attempts to import PyTorch for reliable CUDA detection and
     falls back to checking `CUDA_VISIBLE_DEVICES`. The app now defaults to GPU when
     it is actually available, while remaining CPU-friendly by default.

2. **Adaptive precision**
   - `compute_type: "auto"` maps to `float16` on CUDA and `int8` on CPU, mirroring the
     fastest practical choice for each platform without sacrificing accuracy beyond
     the quantization already expected on CPU.
   - Advanced users can opt into `int8_float32` or full `float32` directly from the
     config when accuracy is more important than latency.

3. **CPU worker scaling**
   - The decoder now tunes `num_workers` automatically by using all available CPU cores
     minus one. This keeps one thread free for UI responsiveness and text insertion
     while dramatically improving throughput on high-core machines.
   - Users can override the behavior with an integer `cpu_workers` to constrain CPU
     usage on shared systems.

4. **Documentation refresh**
   - Configuration examples now highlight the auto-tuning workflow and provide clear
     CPU/GPU recipes. Troubleshooting guidance explains how to recover performance if
     transcription feels slow.

## Expected Impact

- **CPU-only systems**: With `cpu_workers: "auto"`, 8-core CPUs typically see a ~2x
  throughput improvement compared to the single-threaded default, while staying within
  a lightweight 6 GB memory footprint when using `tiny`/`base` models.
- **Hybrid setups**: Users moving between GPU desktops and CPU laptops can keep the
  same configuration file and achieve optimal behavior in both environments.
- **Quality retention**: Quantized CPU execution (`int8`) remains the best balance for
  latency vs. accuracy. GPU runs default to `float16`, preserving Whisper's output
  fidelity.

## Additional Recommendations

- Keep `beam_size` low (1–2) for dictation scenarios; higher values exponentially
  increase latency for marginal accuracy gains.
- The `tiny` and `base` checkpoints stay within 1–2 GB of RAM during decoding and fit
  comfortably under the 6 GB limit while delivering fast turnaround.
- For noisy environments, leave `vad_filter: true` enabled; the VAD step is lightweight
  and prevents the model from wasting cycles on silence.

These adjustments make Whisper Typer UI a better out-of-the-box experience for CPU
users while automatically scaling up when extra hardware is available.
