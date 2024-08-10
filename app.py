from flask import Flask, render_template, request, send_file, make_response
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
    predefined_answers = {
        "write a short note on dbms": (
            "A Database Management System (DBMS) is software that is used to manage databases. "
            "It provides an interface for users and applications to interact with databases, "
            "allowing for the creation, retrieval, updating, and deletion of data. DBMS ensures "
            "data integrity, security, and consistency while enabling multi-user access and supporting "
            "transactions. Popular DBMSs include MySQL, PostgreSQL, Oracle, and Microsoft SQL Server."
        ),
        "define inheritance": (
            "Inheritance is a fundamental concept in object-oriented programming that allows one class "
            "to inherit properties and methods from another class. The class that inherits is called the "
            "child or subclass, while the class being inherited from is known as the parent or superclass. "
            "Inheritance promotes code reusability and establishes a relationship between the parent and "
            "child classes, where the child class can override or extend the behavior of the parent class."
        ),
    }
    
    question_lower = question.lower().strip()
    if question_lower in predefined_answers:
        return predefined_answers[question_lower]
    
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
    margin_x = 1 * inch  # Left margin
    max_width = width - 2 * inch  # Available width for text

    # Calculate line height based on the bounding box of the text
    line_height = font.getbbox('A')[3] - font.getbbox('A')[1] + 10

    for i, question in enumerate(questions, start=1):
        question_text = f"Q{i}: {question}"
        answer_text = generate_gpt_answer(question)

        # Draw question
        current_height = draw_text_on_pdf(pdf_canvas, question_text, font, margin_x, current_height, max_width, line_height)
        
        # Draw answer
        current_height = draw_text_on_pdf(pdf_canvas, answer_text, font, margin_x + 0.5 * inch, current_height, max_width - 0.5 * inch, line_height)
        current_height -= 20  # Add extra space between questions

        # If the content exceeds the current page height, create a new page
        if current_height < 1 * inch:
            pdf_canvas.showPage()
            current_height = height - 1 * inch

    pdf_canvas.save()
    pdf_buffer.seek(0)  # Go to the beginning of the BytesIO buffer
    return pdf_buffer

def draw_text_on_pdf(pdf_canvas, text, font, x, y, max_width, line_height):
    # Create a temporary image to measure text size
    img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(img)

    lines = []
    for line in text.splitlines():
        # Wrap text to fit within max_width
        wrapped_lines = textwrap.wrap(line, width=int(max_width / (font.getbbox('A')[2] - font.getbbox('A')[0])))
        lines.extend(wrapped_lines)

    for line in lines:
        # Measure text size
        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Create image for the text
        img = Image.new('RGB', (text_width, text_height), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), line, font=font, fill='black')

        # Save the text image as a temporary file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            img.save(temp_file, format='PNG')
            temp_file_path = temp_file.name

        # Draw the image on the PDF
        pdf_canvas.drawImage(temp_file_path, x, y - text_height, width=text_width, height=text_height)

        # Move the y-coordinate up for the next line
        y -= line_height

        # Remove the temporary file after it's been used
        os.remove(temp_file_path)

    return y


@app.route('/')
def index():
    return render_template('index.html')

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
