# AI Media Cleaner (free starter)

A small browser-based app for cleaning up photos and videos you own or are authorized to edit.

## Windows setup

1. Install Python 3.10 or 3.11 from https://www.python.org/downloads/
   - During installation, tick **Add Python to PATH**.
2. Extract this ZIP file.
3. Open the extracted `ai_media_cleaner` folder.
4. In the folder address bar, type `cmd` and press Enter.
5. Run:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

6. Open http://127.0.0.1:7860 in your browser.
7. Keep the command window open while using the app. Press Ctrl+C to stop it.

## Photo workflow

- Open **Clean a photo**.
- Upload a photo in the image editor.
- Use the brush to paint the exact area to clean.
- Click **Clean photo** and download the result.

## Video workflow (starter limitation)

- Create a black-and-white PNG with exactly the same width and height as the video.
- Paint the area to edit white; keep everything else black.
- Open **Clean a video**, upload the video and mask, then click **Clean video**.
- This starter uses a fixed mask for all frames and does not preserve audio.
- For moving objects or moving camera footage, a future version should add object tracking and audio muxing.

## Important

This uses OpenCV inpainting, not a large generative AI model. It works best for small unwanted objects on relatively simple backgrounds. Results may look imperfect on detailed backgrounds. Use only on media you own or are authorized to modify; do not use it to remove creator/platform attribution.
