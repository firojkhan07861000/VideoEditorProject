import os
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, vfx, CompositeVideoClip, ColorClip
from moviepy.audio.AudioClip import AudioArrayClip, CompositeAudioClip

# Settings
TARGET_W, TARGET_H = 1920, 1080
MOVIE_SCALE = 0.65
ZOOM_CYCLE_SEC = 10.0
MAX_ZOOM_LEVEL = 1.5

def generate_noise(duration):
    rate = 44100
    audio_array = np.random.uniform(-1, 1, (int(duration * rate), 2))
    return AudioArrayClip(audio_array, fps=rate).volumex(0.02)

def zoom_and_mirror_effect(get_frame, t):
    frame = get_frame(t)
    h, w, _ = frame.shape
    cycle_pos = (t % ZOOM_CYCLE_SEC) / ZOOM_CYCLE_SEC
    
    if cycle_pos <= 0.5:
        progress = cycle_pos * 2
        scale_factor = 1.0 + (progress * (MAX_ZOOM_LEVEL - 1.0))
        mirror_now = False
    else:
        progress = (cycle_pos - 0.5) * 2
        scale_factor = MAX_ZOOM_LEVEL - (progress * (MAX_ZOOM_LEVEL - 1.0))
        mirror_now = True

    new_w, new_h = w / scale_factor, h / scale_factor
    x1 = int((w/2) - (new_w/2))
    y1 = int((h/2) - (new_h/2))
    
    # Safe Crop
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, int(x1+new_w)), min(h, int(y1+new_h))
    
    cropped = frame[y1:y2, x1:x2]
    final_frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
    
    if mirror_now:
        final_frame = cv2.flip(final_frame, 1)
    return final_frame

def process_video():
    input_folder = "Input_Videos"
    output_folder = "Output_Videos"
    assets_folder = "Assets"
    bg_file = os.path.join(assets_folder, "bg.mp4")

    for f in [input_folder, output_folder, assets_folder]:
        if not os.path.exists(f): os.makedirs(f)

    files = [f for f in os.listdir(input_folder) if f.endswith(('.mp4', '.mkv', '.avi'))]
    
    if not files:
        print("No videos found inside Input_Videos folder!")
        return

    print("Starting Processing...")
    for file_name in files:
        try:
            in_path = os.path.join(input_folder, file_name)
            out_path = os.path.join(output_folder, "Final_" + file_name)
            
            clip = VideoFileClip(in_path)
            clip = clip.fx(vfx.speedx, 1.05)
            
            effect_clip = clip.fl(zoom_and_mirror_effect)
            effect_clip = effect_clip.resize(height=TARGET_H * MOVIE_SCALE).set_position((50, "center"))
            
            if os.path.exists(bg_file):
                bg_clip = VideoFileClip(bg_file).resize(newsize=(TARGET_W, TARGET_H))
                bg_clip = bg_clip.fx(vfx.loop, duration=clip.duration).without_audio()
            else:
                bg_clip = ColorClip(size=(TARGET_W, TARGET_H), color=(0,0,0), duration=clip.duration)

            final = CompositeVideoClip([bg_clip, effect_clip], size=(TARGET_W, TARGET_H))
            final.audio = CompositeAudioClip([clip.audio, generate_noise(clip.duration)])
            
            final.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
            
            clip.close()
            final.close()
            print(f"Done: {out_path}")
        except Exception as e:
            print(f"Error: {e}")
    
    input("Processing Complete. Press Enter to exit...")

if __name__ == "__main__":
    process_video()
