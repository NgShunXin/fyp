from flask import Flask, render_template, request, jsonify, Response
from QNA import QNA
from Emotion_Recognition import EmotionRecognition
import json
import os
from datetime import datetime
import cv2
import numpy as np
from flask_cors import CORS
from jamaibase import JamAI, protocol as p

app = Flask(__name__)
CORS(app)
qna = QNA()
emotion_recognition = EmotionRecognition()

# Update credentials
API_KEY = "jamai_sk_09081aedfccde72a8cfa4bc4db0ff23fa5bd47406c885b77"
PROJECT_ID = "proj_2e6b08f124289d82c1e430d3"
TABLE_ID = "fyp"  

# Initialize JamAI client
jamai = JamAI(api_key=API_KEY, project_id=PROJECT_ID)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/qna')
def qna_page():
    qna.reset()
    return render_template('qna.html')

@app.route('/get_question')
def get_question():
    question = qna.get_next_question()
    if question:
        return jsonify(question)
    return jsonify({'complete': True})

@app.route('/check_answer', methods=['POST'])
def check_answer():
    data = request.get_json()
    result = qna.check_answer(data['answer'])
    return jsonify(result)

@app.route('/get_score')
def get_score():
    return jsonify(qna.get_final_score())

@app.route('/save_quiz_results', methods=['POST'])
def save_quiz_results():
    stats = qna.get_emotion_stats()
    score = qna.get_final_score()
    
    test_data = {
        'test_taken': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'emotion_stats': stats,
        'overall_accuracy': (score['score'] / score['total']) * 100
    }
    
    history = load_history()
    history.append(test_data)
    save_history(history)
    return jsonify({'success': True})

@app.route('/dashboard')
def dashboard():
    history = load_history()
    formatted_history = []
    for test in history:
        emotion_accuracies = {
            emotion: (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            for emotion, stats in test['emotion_stats'].items()
        }

        formatted_test = {
            'test_taken': test['test_taken'],
            'emotion_accuracies': emotion_accuracies,
            'emotion_stats': test['emotion_stats'],
            'overall_accuracy': test['overall_accuracy'],
            'correct_count': sum(stats['correct'] for stats in test['emotion_stats'].values())
        }
        formatted_history.append(formatted_test)

    return render_template('dashboard.html', stats={'history': formatted_history})

@app.route('/delete_test/<int:index>', methods=['POST'])
def delete_test(index):
    try:
        history = load_history()
        if 0 <= index < len(history):
            history.pop(index)
            save_history(history)
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/emotion_recognition')
def emotion_recognition_page():
    return render_template('emotion_recognition.html')

@app.route('/video_feed')
def video_feed():
    return Response(
        emotion_recognition.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/analyze_image', methods=['POST'])
def analyze_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['image']
        # Read and convert image
        image_bytes = file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Analyze image
        results = emotion_recognition.analyze_image(image)
        return jsonify({'emotions': results})
        
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/report')
def report():
    return render_template('report.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400

        try:
            # Add user input to the action table
            completion = jamai.add_table_rows(
                "action",
                p.RowAddRequest(
                    table_id=TABLE_ID,
                    data=[{"question": user_message}],
                    stream=False
                )
            )

            # Get the response from the reply column
            if completion.rows:
                reply_output = completion.rows[0].columns.get("reply")
                if reply_output:
                    assistant_response = reply_output.text
                    return jsonify({'response': assistant_response})
                else:
                    return jsonify({'error': 'No output found in the reply column.'}), 500
            else:
                return jsonify({'error': 'Failed to get a response. Please try again.'}), 500

        except Exception as e:
            print(f"JamAI Error: {str(e)}")
            return jsonify({'error': f'JamAI Error: {str(e)}'}), 500
            
    except Exception as e:
        print(f"General Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat_history', methods=['GET'])
def chat_history():
    try:
        # Fetch the existing rows from the chat table
        rows = jamai.list_table_rows(
            "action",
            p.RowListRequest(table_id=TABLE_ID)
        )
        
        if not rows.items:
            return jsonify({'response': 'No previous chat found.'}), 404
        
        # Get the latest conversation
        latest_row = rows.items[-1]
        user_message = latest_row.columns.get("question", {}).text
        assistant_response = latest_row.columns.get("reply", {}).text

        return jsonify({
            'user_message': user_message,
            'response': assistant_response
        })
            
    except Exception as e:
        print(f"General Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def load_history():
    if os.path.exists('static/test_history.json'):
        with open('static/test_history.json', 'r') as f:
            return json.load(f)
    return []

def save_history(history):
    with open('static/test_history.json', 'w') as f:
        # Write opening bracket
        f.write('[\n')
        
        # Write each test record on its own line
        for i, test in enumerate(history):
            # Convert test to JSON string without newlines
            test_json = json.dumps(test, separators=(',', ':'))
            
            # Add comma if not the last item
            if i < len(history) - 1:
                f.write(f'    {test_json},\n')
            else:
                f.write(f'    {test_json}\n')
        
        # Write closing bracket
        f.write(']')

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

