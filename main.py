import os
from flask import Flask, request, jsonify
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting, Part
from google.cloud import storage
from google.oauth2 import service_account
from flask_cors import CORS
import os
from flask import send_from_directory

app = Flask(__name__)
CORS(app)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join('marketing-agent-fe', 'dist', path)):
        return send_from_directory(os.path.join('marketing-agent-fe', 'dist'), path)
    else:
        return send_from_directory(os.path.join('marketing-agent-fe', 'dist'), 'index.html')

# Set up credentials using the service account JSON file
credentials_path = os.path.join(os.path.dirname(__file__), "tr-media-analysis-be9da703ffec.json")
credentials = service_account.Credentials.from_service_account_file(credentials_path)

# Initialize Google Cloud Storage client with credentials
storage_client = storage.Client(credentials=credentials)
bucket_name = "video-marketing"
bucket = storage_client.bucket(bucket_name)

# Gemini API configuration
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}

safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
]

# Global variable to store the chat session
chat_session = None

def get_prompt(platform):
    if platform == 'linkedin':
        return """Analyze the following LinkedIn video as a professional social media strategist. Provide a comprehensive evaluation of its effectiveness, considering the following aspects:

Content and messaging: Relevance to LinkedIn's professional audience, Clarity and value of the main message, Appropriateness for B2B or professional networking context

Video structure and length: Effectiveness of the first 6-10 seconds in capturing attention, Overall video length (optimal range is 30 seconds to 2 minutes), Pacing and information density

Visual elements: Professional appearance and production quality, Use of captions or on-screen text (considering 80% of LinkedIn videos are watched on mute), Branding elements and visual consistency

Engagement factors: Call-to-action effectiveness, Potential for generating comments, shares, or professional discussions, Use of hashtags and their relevance

LinkedIn-specific optimization: Native video vs. embedded link (native is preferred), Mobile-friendly format (square or vertical video), Compliance with LinkedIn's video specifications

Professional value: Educational or informative content, Thought leadership potential, Networking or relationship-building aspects

Industry relevance: Alignment with current trends in the professional's field, Demonstration of expertise or unique insights

Accessibility and inclusivity: Use of captions or subtitles, Clarity of speech and visuals for diverse audiences

Areas for improvement: Identify specific elements that could be enhanced, Suggest actionable recommendations for optimization

Provide a balanced analysis, highlighting both strengths and areas for improvement. Support your evaluation with specific examples from the video and relevant LinkedIn best practices. Consider how the video aligns with LinkedIn's professional environment and user behavior. Conclude with an overall assessment of the video's potential effectiveness in achieving its presumed goals on the LinkedIn platform."""
    else:
        return """Analyze the following video as a professional social media analyst. Provide a comprehensive evaluation of its effectiveness, considering the following aspects:

Content and messaging: Clarity and coherence of the main message, Relevance to the target audience, Storytelling elements and narrative structure

Visual elements: Quality of cinematography and editing, Use of graphics, animations, or special effects, Color grading and overall aesthetic appeal

Audio components: Quality of sound design, Effectiveness of music or background audio, Clarity of voiceovers or dialogue (if applicable)

Engagement factors: Hook and retention strategies in the first few seconds, Pacing and overall video length, Call-to-action effectiveness

Platform optimization: Suitability for the intended social media platform(s), Adherence to platform-specific best practices, Potential for cross-platform adaptation

Brand alignment: Consistency with brand voice and values, Integration of brand elements (logo, colors, etc.)

Technical aspects: Video resolution and overall production quality, Mobile-friendliness and accessibility features

Potential for virality: Shareability factors, Trendjacking or timely elements

Areas for improvement: Identify specific elements that could be enhanced, Suggest actionable recommendations for optimization

Provide a balanced analysis, highlighting both strengths and areas for improvement. Support your evaluation with specific examples from the video and relevant industry best practices. Conclude with an overall assessment of the video's potential effectiveness in achieving its presumed goals on social media platforms."""

def initialize_chat():
    global chat_session
    vertexai.init(project="tr-media-analysis", location="europe-central2", credentials=credentials)
    model = GenerativeModel("gemini-1.5-pro-002")
    chat_session = model.start_chat()

def analyze_video(video_uri, platform):
    global chat_session
    if chat_session is None:
        initialize_chat()
    
    video_part = Part.from_uri(
        mime_type="video/mp4",
        uri=video_uri,
    )
    text_prompt = get_prompt(platform)
    response = chat_session.send_message(
        [video_part, text_prompt],
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    return response.text

@app.route('/api/analyze', methods=['POST'])
def analyze():
    global chat_session
    try:
        if 'video' in request.files:
            video_file = request.files['video']
            if video_file.filename == '':
                return jsonify({"error": "No video file selected"}), 400
            
            platform = request.form.get('platform', 'tiktok')
            if platform not in ['tiktok', 'linkedin']:
                return jsonify({"error": "Invalid platform selected"}), 400
            
            # Save the video to Google Cloud Storage
            blob = bucket.blob(video_file.filename)
            blob.upload_from_string(
                video_file.read(),
                content_type=video_file.content_type
            )
            
            # Generate the GCS URI for the uploaded video
            video_uri = f"gs://{bucket_name}/{video_file.filename}"
            
            # Analyze the video
            analysis_result = analyze_video(video_uri, platform)
            return jsonify({"analysis": analysis_result})
        
        elif 'message' in request.json:
            message = request.json['message']
            if chat_session is None:
                initialize_chat()
            response = chat_session.send_message(message)
            return jsonify({"reply": response.text})
        
        else:
            return jsonify({"error": "No video file or message provided"}), 400
    
    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)