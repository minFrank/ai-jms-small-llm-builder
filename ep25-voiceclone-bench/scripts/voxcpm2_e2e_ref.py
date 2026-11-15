
import os, time, numpy as np, soundfile as sf
os.environ["OMNIVOICE_VOXCPM_MODEL"] = "D:/models/tts/voxcpm2"
os.environ["HF_HUB_OFFLINE"] = "1"
from voxcpm import VoxCPM
start = time.time()
model = VoxCPM.from_pretrained("D:/models/tts/voxcpm2", load_denoiser=False)
load_time = time.time()-start
wav = model.generate(
    text="关注AI积木师，带你从AI的视角解读和理解生活",
    reference_wav_path="D:/study/ai-jms/voice_samples/ref_new_16k.wav",
    prompt_text="关注AI积木师",
    cfg_value=2.0, inference_timesteps=10
)
arr = np.clip(np.asarray(wav).squeeze(), -1, 1)
out = "D:/study/ai-jms/voice_samples/ep25_run/voxcpm2_e2e.wav"
sf.write(out, arr, 48000)
dur = len(arr)/48000
import soundfile as sf
info = sf.info(out)
rms = np.sqrt(np.mean(arr**2))
with open("D:/study/ai-jms/voice_samples/ep25_run/voxcpm2_e2e_metrics.json","w") as f:
    json.dump({"load_s": load_time, "synth_s": time.time()-start-load_time, "dur_s": dur, "bytes": info.bytes, "rms": float(rms), "samples": len(arr), "sr": info.samplerate}, f)
print(f"OK out={out} dur={dur:.2f}s bytes={info.bytes} samples={len(arr)} sr={info.samplerate} rms={rms:.5f}")
