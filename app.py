from flask import Flask,send_from_directory, request, send_file, make_response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from PIL import Image, ImageDraw, ImageFont
import textwrap
import io
import openai
import tempfile
import os

app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = 'your_openai_api_key'

def generate_gpt_answer(question):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        answer = response['choices'][0]['message']['content'].strip()
        return answer
    except Exception as e:
        return f"An error occurred: {str(e)}"

def create_handwritten_assignment(questions, font_path):
    font_size = 18
    font = ImageFont.truetype(font_path, font_size)

    pdf_buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter

    current_height = height - 1 * inch  # Start from the top with some margin
    max_width = int((width - 2 * inch) / (font.getbbox('A')[2] - font.getbbox('A')[0]))  # Maximum number of characters that fit in the page width

    line_height = font.getbbox('A')[3] - font.getbbox('A')[1] + 10

    for i, question in enumerate(questions, start=1):
        question_text = f"Q{i}: {question}"
        answer_text = generate_gpt_answer(question)

        # Draw question
        draw_text_on_pdf(pdf_canvas, question_text, font, 1 * inch, current_height, max_width)
        current_height -= line_height * (question_text.count('\n') + 1)

        # Draw answer
        draw_text_on_pdf(pdf_canvas, answer_text, font, 1.5 * inch, current_height, max_width)
        current_height -= line_height * (answer_text.count('\n') + 1) + 20

        # If the content exceeds the current page height, create a new page
        if current_height < 1 * inch:
            pdf_canvas.showPage()
            current_height = height - 1 * inch

    pdf_canvas.save()
    pdf_buffer.seek(0)  # Go to the beginning of the BytesIO buffer
    return pdf_buffer

def draw_text_on_pdf(pdf_canvas, text, font, x, y, max_width):
    # Create an image with the text using PIL
    img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(img)

    # Split text into lines that fit within max_width
    lines = []
    for line in text.splitlines():
        wrapped_lines = textwrap.wrap(line, width=max_width)
        lines.extend(wrapped_lines)

    # Calculate height needed for the text block
    text_block_height = sum([draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines])

    for line in lines:
        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        img = Image.new('RGB', (text_width, text_height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), line, font=font, fill=(0, 0, 0))

        # Save the text image as a temporary file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            img.save(temp_file, format='PNG')
            temp_file_path = temp_file.name

        # Draw the image on the PDF
        pdf_canvas.drawImage(temp_file_path, x, y - text_height, width=text_width, height=text_height)

        # Move the y-coordinate up for the next line
        y -= text_height

        # Delete the temporary file after it's been used
        os.remove(temp_file_path)

@app.route('/')
def index():
    return send_from_directory('.','index.html')

@app.route('/generate', methods=['POST'])
def generate():
    questions = request.form.getlist('questions')
    font_path = 'static/font (0).ttf'  # Ensure this path is correct and the font is accessible

    if not questions:
        return "No questions provided.", 400

    pdf_buffer = create_handwritten_assignment(questions, font_path)

    # Set response to display the PDF in the browser
    response = make_response(
        send_file(pdf_buffer, as_attachment=False, download_name="assignment.pdf")
    )
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=assignment.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True)
