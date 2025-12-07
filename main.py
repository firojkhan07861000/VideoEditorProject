import os
import cv2
import numpy as np
import math
from moviepy.editor import VideoFileClip, vfx, CompositeVideoClip, ColorClip, concatenate_videoclips
from moviepy.audio.AudioClip import AudioArrayClip, CompositeAudioClip

# ============================
#        SETTINGS
# ============================
INPUT_FOLDER = "Input_Videos"
OUTPUT_FOLDER = "Output_Videos"
ASSETS_FOLDER = "Assets"
BACKGROUND_FILE = os.path.join(ASSETS_FOLDER, "bg.mp4")

# Resolution & Layout
TARGET_W, TARGET_H = 1920, 1080  # Final Output Size
VIDEO_SCALE = 0.60               # Video 60% size ki hogi (taki bg dikhe)

# Cutting Logic (Sabse Important)
KEEP_DURATION = 15.0  # 15 second video chalegi
SKIP_DURATION = 5.0   # 5 second kat jayegi

# Effects
ZOOM_SPEED = 0.5      # Zoom kitna tez hoga
PAN_SPEED = 2.0       # Left-Right movement speed

def ensure_folders():
    for f in [INPUT_FOLDER, OUTPUT_FOLDER, ASSETS_FOLDER]:
        if not os.path.exists(f): os.makedirs(f)

# --- 1. AUDIO NOISE GENERATOR ---
def generate_noise(duration):
    rate = 44100
    # Random frequency noise (Anti-Fingerprint)
    audio_array = np.random.uniform(-0.05, 0.05, (int(duration * rate), 2))
    return AudioArrayClip(audio_array, fps=rate).volumex(0.1).set_duration(duration)

# --- 2. ADVANCED VISUAL EFFECT (Zoom + Pan + Mirror) ---
def advanced_visual_filter(get_frame, t):
    frame = get_frame(t)
    h, w, _ = frame.shape
    
    # --- A. ALWAYS MIRROR (Copyright Killer) ---
    frame = cv2.flip(frame, 1) # Horizontal Flip
    
    # --- B. DYNAMIC ZOOM (Breathing Effect) ---
    # Zoom 1.0 se 1.3 tak oscillate karega
    zoom_level = 1.0 + 0.3 * (1 + math.sin(t * ZOOM_SPEED)) / 2
    
    # --- C. PANNING (Focus Shift Left/Right) ---
    # Jab zoom hoga, to frame kabhi left kabhi right shift hoga
    pan_shift = math.cos(t * PAN_SPEED) # -1 se 1
    
    # Calculation for Cropping
    new_w = w / zoom_level
    new_h = h / zoom_level
    
    # Center calculation with Panning Shift
    # Agar pan_shift -1 hai to left, 1 hai to right
    max_shift_x = (w - new_w) / 2
    shift_x = max_shift_x * pan_shift * 0.8 # 0.8 thoda margin rakhne ke liye
    
    center_x = (w / 2) + shift_x
    center_y = h / 2
    
    x1 = int(center_x - new_w / 2)
    y1 = int(center_y - new_h / 2)
    
    # Safety Check (Bounds)
    x1, y1 = max(0, x1), max(0, y1)
    x2 = min(w, int(x1 + new_w))
    y2 = min(h, int(y1 + new_h))
    
    # Crop and Resize
    cropped = frame[y1:y2, x1:x2]
    final_frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
    
    return final_frame

# --- 3. SEGMENT CUTTER (The Chopper) ---
def cut_video_segments(clip):
    print(" -> Cutting video segments (15s Keep / 5s Skip)...")
    subclips = []
    t = 0
    full_duration = clip.duration
    
    while t < full_duration:
        end_t = min(t + KEEP_DURATION, full_duration)
        # Create subclip
        segment = clip.subclip(t, end_t)
        subclips.append(segment)
        
        # Jump ahead (Keep time + Skip time)
        t += (KEEP_DURATION + SKIP_DURATION)
    
    # Join all parts
    return concatenate_videoclips(subclips)

def process_video():
    ensure_folders()
    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.mp4', '.mkv', '.avi'))]
    
    if not files:
        print("Input folder khali hai!")
        return

    print(f"Starting Batch Process on {len(files)} videos...")
    
    for file_name in files:
        try:
            in_path = os.path.join(INPUT_FOLDER, file_name)
            out_path = os.path.join(OUTPUT_FOLDER, "Final_" + file_name)
            
            print(f"\nProcessing: {file_name}")
            
            # Load Original Video
            original_clip = VideoFileClip(in_path)
            
            # STEP 1: CUTTING (15s Play, 5s Delete)
            chopped_clip = cut_video_segments(original_clip)
            
            # STEP 2: SPEED & COLOR (Fingerprint Change)
            # Speed 1.05x (Audio Pitch change automatically)
            processed_clip = chopped_clip.fx(vfx.speedx, 1.05)
            
            # Color Correction (Slight Gamma & Saturation)
            processed_clip = processed_clip.fx(vfx.gamma_corr, 1.1) # Thoda bright
            processed_clip = processed_clip.fx(vfx.colorx, 1.1)     # Thoda vibrant
            
            # STEP 3: APPLY VISUAL EFFECTS (Zoom/Pan/Mirror)
            print(" -> Applying Mirror, Pan & Zoom effects...")
            effect_clip = processed_clip.fl(advanced_visual_filter)
            
            # STEP 4: LAYOUT & RESIZE
            # Video ko chota karke center me layenge
            effect_clip = effect_clip.resize(height=TARGET_H * VIDEO_SCALE)
            effect_clip = effect_clip.set_position("center")
            
            current_duration = effect_clip.duration # New duration after cutting/speed
            
            # STEP 5: BACKGROUND LAYER
            if os.path.exists(BACKGROUND_FILE):
                bg_clip = VideoFileClip(BACKGROUND_FILE)
                bg_clip = bg_clip.resize(newsize=(TARGET_W, TARGET_H))
                bg_clip = bg_clip.fx(vfx.loop, duration=current_duration)
                bg_clip = bg_clip.without_audio()
            else:
                print(" -> BG missing, using Black screen.")
                bg_clip = ColorClip(size=(TARGET_W, TARGET_H), color=(0,0,0), duration=current_duration)

            # STEP 6: MERGE LAYERS
            final_video = CompositeVideoClip([bg_clip, effect_clip], size=(TARGET_W, TARGET_H))
            
            # STEP 7: AUDIO MIXING (Noise Injection)
            print(" -> Injecting Audio Noise...")
            noise = generate_noise(current_duration)
            final_audio = CompositeAudioClip([processed_clip.audio, noise])
            final_video.audio = final_audio
            
            # Force Duration Set (Error fix)
            final_video = final_video.set_duration(current_duration)

            # EXPORT
            print(" -> Rendering (Isme time lagega)...")
            final_video.write_videofile(
                out_path, 
                codec="libx264", 
                audio_codec="aac", 
                fps=24, 
                preset="ultrafast",
                threads=4
            )
            
            original_clip.close()
            final_video.close()
            print(f"Success! Saved: {out_path}")

        except Exception as e:
            print(f"ERROR in {file_name}: {e}")
            
    input("All Done. Press Enter to exit...")

if __name__ == "__main__":
    process_video()
