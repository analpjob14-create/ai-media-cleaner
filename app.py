import os
import cv2
import gradio as gr
import numpy as np
from PIL import Image

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def _to_rgb_array(img):
    if isinstance(img, Image.Image):
        return np.array(img.convert("RGB"))
    arr = np.asarray(img)
    if arr.ndim == 2:
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
    if arr.shape[2] == 4:
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
    return arr[:, :, :3]

def _extract_editor_data(data):
    """Return the original RGB image and a white-on-black mask from Gradio ImageEditor."""
    if not isinstance(data, dict) or data.get("background") is None:
        raise ValueError("Please upload an image and paint over the area you want to edit.")
    original = _to_rgb_array(data["background"])
    mask = np.zeros(original.shape[:2], dtype=np.uint8)

    layers = data.get("layers") or []
    for layer in layers:
        if layer is None:
            continue
        layer_arr = np.array(layer.convert("RGBA") if isinstance(layer, Image.Image) else layer)
        if layer_arr.ndim == 3 and layer_arr.shape[2] == 4:
            alpha = layer_arr[:, :, 3]
            # Gradio's painted layer is transparent outside the brush strokes.
            mask = np.maximum(mask, np.where(alpha > 8, 255, 0).astype(np.uint8))
        elif layer_arr.ndim == 2:
            mask = np.maximum(mask, np.where(layer_arr > 8, 255, 0).astype(np.uint8))
    if not np.any(mask):
        raise ValueError("No painted mask was found. Use the brush to mark the area first.")
    return original, mask

def _inpaint(rgb, mask, radius=5):
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cleaned = cv2.inpaint(bgr, mask, int(radius), cv2.INPAINT_TELEA)
    return cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB)

def clean_photo(editor_data, radius):
    try:
        rgb, mask = _extract_editor_data(editor_data)
        result = _inpaint(rgb, mask, radius)
        out = os.path.join(OUTPUT_DIR, "cleaned_photo.png")
        Image.fromarray(result).save(out)
        return result, out, "Finished. Check the preview; complex backgrounds may need a smaller or more carefully drawn mask."
    except Exception as e:
        raise gr.Error(str(e))

def clean_video(video_path, mask_file, radius, every_n):
    if not video_path:
        raise gr.Error("Upload a video first.")
    if not mask_file:
        raise gr.Error("Upload a black-and-white mask image matching the video dimensions.")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise gr.Error("Could not open the uploaded video.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    mask_img = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        cap.release()
        raise gr.Error("Could not read the mask image.")
    if mask_img.shape[:2] != (height, width):
        cap.release()
        raise gr.Error(f"Mask size must be exactly {width} x {height}; uploaded mask is {mask_img.shape[1]} x {mask_img.shape[0]}.")
    _, mask = cv2.threshold(mask_img, 10, 255, cv2.THRESH_BINARY)
    if not np.any(mask):
        cap.release()
        raise gr.Error("The mask is empty. Paint the area white and keep the rest black.")
    out = os.path.join(OUTPUT_DIR, "cleaned_video.mp4")
    writer = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise gr.Error("Could not create MP4 output on this computer.")
    count = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        # Process every frame for consistent results; every_n is reserved for future speed modes.
        cleaned = cv2.inpaint(frame, mask, int(radius), cv2.INPAINT_TELEA)
        writer.write(cleaned)
        count += 1
    cap.release()
    writer.release()
    if count == 0:
        raise gr.Error("No video frames were read.")
    return out, f"Finished processing {count} frames at {fps:.2f} FPS. Audio is not preserved in this starter version."

with gr.Blocks(title="AI Media Cleaner", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# AI Media Cleaner\n"
        "A free, local-first photo and video cleanup tool for media you own or are authorized to edit.\n\n"
        "**How it works:** mark the area to edit; the app fills it using nearby image information. "
        "Results vary with movement, texture, and background complexity."
    )
    with gr.Tab("Clean a photo"):
        gr.Markdown("Upload a photo, then use the brush to paint over the unwanted object or mark. Paint only the area you have permission to edit.")
        photo_editor = gr.ImageEditor(label="Photo and edit mask", type="pil", image_mode="RGB")
        photo_radius = gr.Slider(1, 15, value=5, step=1, label="Inpainting radius")
        photo_btn = gr.Button("Clean photo", variant="primary")
        photo_preview = gr.Image(label="Preview")
        photo_download = gr.File(label="Download cleaned photo")
        photo_status = gr.Markdown()
        photo_btn.click(clean_photo, [photo_editor, photo_radius], [photo_preview, photo_download, photo_status])

    with gr.Tab("Clean a video"):
        gr.Markdown(
            "Upload a video and a matching black-and-white PNG mask. "
            "White marks the area to edit; black protects the rest. "
            "The mask stays in the same position for every frame."
        )
        video_in = gr.Video(label="Input video", sources=["upload"])
        mask_in = gr.File(label="Mask PNG (same width and height as video)", file_types=[".png"], type="filepath")
        video_radius = gr.Slider(1, 15, value=5, step=1, label="Inpainting radius")
        video_btn = gr.Button("Clean video", variant="primary")
        video_out = gr.Video(label="Cleaned video")
        video_download = gr.File(label="Download cleaned MP4")
        video_status = gr.Markdown()
        video_btn.click(clean_video, [video_in, mask_in, video_radius, gr.Number(value=1, visible=False)], [video_out, video_download, video_status])

    gr.Markdown(
        "### Notes\n"
        "- This app processes uploaded files on the hosting server; avoid uploading private or sensitive media.\n"
        "- The video tool uses one fixed mask across frames and does not preserve the original audio.\n"
        "- Do not use it to remove creator/platform attribution or marks from content you do not own or have permission to edit.\n"
        "- For best results, use a small, accurate mask and test on a copy of the original."
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")))
