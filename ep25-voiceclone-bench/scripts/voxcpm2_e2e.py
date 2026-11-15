
import os, sys, time
os.environ["OMNIVOICE_VOXCPM_MODEL"] = "D:/models/tts/voxcpm2"
os.environ["HF_HUB_OFFLINE"] = "1"
start = time.time()
try:
    from voxcpm import VoxCPM
    model = VoxCPM.from_pretrained("D:/models/tts/voxcpm2", load_denoiser=False)
    print("MODEL_LOAD_OK", time.time()-start)
    # 最简合成（无参考音频则用描述）
    wav = model.generate(text="关注AI积木师", voice_description="男性中文播音", cfg_value=2.0, inference_timesteps=10)
    import numpy as np, soundfile as sf
    arr = np.clip(np.asarray(wav).squeeze(), -1, 1)
    out = "D:/study/ai-jms/voice_samples/ep25_run/voxcpm2_synth.wav"
    sf.write(out, arr, 48000)
    import os
    print("SYNTH_OK", out, os.path.getsize(out), "samples", len(arr), "dur_s", len(arr)/48000)
except Exception as e:
    import traceback
    print("ERROR:", type(e).__name__, str(e)[:500], traceback.format_exc()[:3000])
