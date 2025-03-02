# app.py
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from midiutil import MIDIFile
from tayuya import MIDIParser, Tabs
import os
import tempfile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Sheet Music to MIDI Conversion (Simplified)
def sheet_to_midi(image_path):
    # Image preprocessing
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    # Simplified note detection (customize based on SheetVision logic)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Create MIDI file
    midi = MIDIFile(1)
    track = 0
    time = 0
    midi.addTrackName(track, time, "Guitar Track")
    midi.addTempo(track, time, 120)

    # Map detected contours to notes (simplified)
    for i, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        note = 60 + (i % 12)  # Map to middle C octave
        midi.addNote(track, 0, note, time + i, 1, 100)
    
    return midi

# MIDI to Guitar Tab Conversion
def midi_to_tab(midi_file):
    try:
        mid = MIDIParser(midi_file, track=0)
        tabs = Tabs(notes=mid.notes_played(), key=mid.get_key())
        notes = tabs.generate_notes(tabs.find_start())
        
        # Create 22-fret tab visualization
        tab_lines = ['e|' + '-'*22, 'B|' + '-'*22, 'G|' + '-'*22,
                     'D|' + '-'*22, 'A|' + '-'*22, 'E|' + '-'*22]
        
        for note in notes:
            string = 5 - (note[1] - 1)  # Map to tab position
            fret = min(note[2], 22)      # Limit to 22 frets
            pos = max(0, fret - 1)
            tab_line = list(tab_lines[string])
            tab_line[pos+2] = str(fret)
            tab_lines[string] = ''.join(tab_line)
            
        return '\n'.join(tab_lines)
    except Exception as e:
        return f"Error generating tabs: {str(e)}"

@app.route('/convert', methods=['POST'])
def convert_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    filename = secure_filename(file.filename)
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_path)
    
    try:
        # Convert sheet music to MIDI
        midi = sheet_to_midi(temp_path)
        midi_temp = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.mid')
        
        with open(midi_temp, 'wb') as f:
            midi.writeFile(f)
        
        # Convert MIDI to guitar tab
        tab_output = midi_to_tab(midi_temp)
        return jsonify({'tab': tab_output})
    
    except Exception as e:
        return jsonify({'error': str(e)})
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(midi_temp):
            os.remove(midi_temp)

if __name__ == '__main__':
    app.run(debug=True)
