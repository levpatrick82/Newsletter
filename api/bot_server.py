from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
import threading
from bulk_newsletter import main as newsletter_main

app = Flask(__name__)

# Global variables to track progress
current_progress = 0
is_running = False

def run_newsletter_bot(csv_path):
    global current_progress, is_running
    try:
        is_running = True
        # Run the newsletter registration process and track progress
        websites = load_websites_from_csv(csv_path)
        total_websites = len(websites)
        
        for i, website in enumerate(websites, 1):
            try:
                process_website(SIGNUP_EMAIL, website, i)
                current_progress = int((i / total_websites) * 100)
            except Exception as e:
                logging.error(f"Error processing website {website}: {e}")
                continue
                
        current_progress = 100
    except Exception as e:
        print(f"Error running bot: {e}")
    finally:
        is_running = False
        # Cleanup
        if os.path.exists(csv_path):
            os.remove(csv_path)

@app.route('/api/start-bot', methods=['POST'])
def start_bot():
    global current_progress
    
    if 'csv_file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)
        
        # Start the bot in a separate thread
        thread = threading.Thread(target=run_newsletter_bot, args=(filepath,))
        thread.start()
        
        return jsonify({'message': 'Bot started successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress', methods=['GET'])
def get_progress():
    return jsonify({
        'progress': current_progress,
        'status': 'completed' if current_progress == 100 else 'running'
    })

if __name__ == '__main__':
    app.run(port=5000)