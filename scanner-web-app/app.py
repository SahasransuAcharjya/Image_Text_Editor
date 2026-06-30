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
        print(f"Error processing image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/render', methods=['POST'])
def render():
    if 'image' not in request.files or 'edits' not in request.form:
        return jsonify({'error': 'Missing image or edits'}), 400
        
    file = request.files['image']
    edits = json.loads(request.form['edits'])
    
    try:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        for edit in edits:
            x, y, w, h = edit['x'], edit['y'], edit['w'], edit['h']
            new_text = edit['text']
            
            # 1. Erase old text by filling the bounding box with the background color
            # Sample background color from just outside the bounding box (top-left corner ideally)
            bg_y = max(0, y - 2)
            bg_x = max(0, x - 2)
            bg_color = img[bg_y, bg_x].tolist() # Returns [B, G, R]
            
            # Fill the bounding box with the background color
            cv2.rectangle(img, (x, y), (x + w, y + h), bg_color, -1)
            
            # 2. Determine text color (simple contrast check: if bg is dark, use white; if light, use black)
            brightness = bg_color[0] * 0.114 + bg_color[1] * 0.587 + bg_color[2] * 0.299
            text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
            
            # 3. Write new text
            # We use OpenCV's putText, we'll scale the font size to roughly fit the height
            font_scale = h / 30.0 # Approximate scaling
            thickness = max(1, int(font_scale * 2))
            
            # Adjust text Y position because putText uses bottom-left corner
            text_y = y + int(h * 0.75) 
            cv2.putText(img, new_text, (x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thickness, cv2.LINE_AA)
            
        # Encode image to send back
        _, buffer = cv2.imencode('.png', img)
        io_buf = io.BytesIO(buffer)
        
        return send_file(io_buf, mimetype='image/png')
        
    except Exception as e:
        print(f"Error rendering image: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
