from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import easyocr
import cv2
import numpy as np
import io
import json
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

print("Loading EasyOCR model...")
reader = easyocr.Reader(['en'], gpu=False) # Changed to gpu=False for better compatibility if no CUDA
print("Model loaded successfully.")

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    
    try:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({'error': 'Failed to decode image'}), 400
        
        # Perform OCR
        results = reader.readtext(img, paragraph=False)
        
        # We need to send back the text and their bounding boxes
        # results format: [([[x,y], [x,y], [x,y], [x,y]], text, conf), ...]
        blocks = []
        for i, res in enumerate(results):
            bbox = res[0]
            # bbox is a list of 4 points: top-left, top-right, bottom-right, bottom-left
            # Convert to standard format [x, y, w, h] for easier handling in frontend
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            x, y = int(min(x_coords)), int(min(y_coords))
            w, h = int(max(x_coords) - x), int(max(y_coords) - y)
            
            blocks.append({
                'id': i,
                'text': res[1],
                'x': x,
                'y': y,
                'w': w,
                'h': h
            })
            
        return jsonify({'blocks': blocks})
        
    except Exception as e:
import os

def get_font(size):
    # Use built-in Windows font for reliable scaling and unicode (Rupee) support
    windows_font_path = "C:\\Windows\\Fonts\\arial.ttf"
    if os.path.exists(windows_font_path):
        try:
            return ImageFont.truetype(windows_font_path, int(size))
        except Exception as e:
            print(f"Failed to load Arial: {e}")
    
    # Fallback if Arial is somehow missing
    return ImageFont.load_default()

@app.route('/render', methods=['POST'])
def render():
    if 'image' not in request.files or 'edits' not in request.form:
        return jsonify({'error': 'Missing image or edits'}), 400
        
    file = request.files['image']
    edits = json.loads(request.form['edits'])
    
    try:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # Convert to PIL Image for better text rendering
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        for edit in edits:
            x, y, w, h = edit['x'], edit['y'], edit['w'], edit['h']
            new_text = edit['text']
            
            # Sample background color from just outside the bounding box
            bg_y = max(0, y - 2)
            bg_x = max(0, x - 2)
            bg_color_bgr = img[bg_y, bg_x].tolist() # [B, G, R]
            bg_color_rgb = (bg_color_bgr[2], bg_color_bgr[1], bg_color_bgr[0])
            
            # Erase old text by drawing a rectangle
            draw.rectangle([x, y, x + w, y + h], fill=bg_color_rgb)
            
            # Determine text color based on brightness
            brightness = bg_color_rgb[0] * 0.299 + bg_color_rgb[1] * 0.587 + bg_color_rgb[2] * 0.114
            text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
            
            # Write new text using a nice font
            font_size = h * 0.85 # Scale font size to fit height
            font = get_font(font_size)
            
            # Center the text vertically in the bounding box
            text_y = y + (h - font_size) / 2
            
            draw.text((x, text_y), new_text, font=font, fill=text_color)
            
        # Convert back to cv2 for encoding
        img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        
        # Encode image to send back
        _, buffer = cv2.imencode('.png', img)
        io_buf = io.BytesIO(buffer)
        
        return send_file(io_buf, mimetype='image/png')
        
    except Exception as e:
        print(f"Error rendering image: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
