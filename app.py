import os
import re  
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from pythonjsonlogger import jsonlogger

# Configure JSON Logging
class RemoveColorCodesFilter(logging.Filter):
    """Filter to remove ANSI color codes from logs for JSON formatting."""
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def filter(self, record):
        if not isinstance(record.msg, str):
            record.msg = str(record.msg)  # Convert to string if not already
        record.msg = self.ANSI_ESCAPE.sub('', record.msg)
        return True

# Setup Logger
logger = logging.getLogger("app_logger")
logHandler = logging.StreamHandler()  # Console logging
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
logger.addFilter(RemoveColorCodesFilter())

# Flask Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

# OpenTelemetry Setup
resource = Resource.create({"service.name": "course-catalog-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Configure OTLP Exporter for telemetry
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Automatically instrument Flask for telemetry
FlaskInstrumentor().instrument_app(app)

# Utility Functions
def load_courses():
    """Load the list of courses from the JSON file."""
    try:
        if not os.path.exists(COURSE_FILE):
            logger.warning({"message": f"Unable to find Course file {COURSE_FILE}. Returning empty list."})
            return []
        with open(COURSE_FILE, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error({"message": "There is an error loading the courses!", "error": str(e)})
        return []

def save_courses_to_file(courses):
    """Save the updated course list to the JSON file."""
    try:
        with open(COURSE_FILE, 'w') as file:
            json.dump(courses, file, indent=4)
        logger.info({"message": "Courses have been saved to file successfully."})
    except Exception as e:
        logger.error({"message": "Error! Unable to save courses to file", "error": str(e)})

def save_courses(data):
    """Save a new course to the JSON file."""
    try:
        with tracer.start_as_current_span("Save Course"):
            courses = load_courses()
            courses.append(data)
            save_courses_to_file(courses)
            logger.info({
                "message": "Course added successfully.",
                "course_name": data.get("name"),
                "course_code": data.get("code")
            })
    except Exception as e:
        logger.error({"message": "Error adding new course", "error": str(e)})

# Routes
@app.route('/')
def index():
    """Render the homepage."""
    logger.info({"message": "Homepage accessed."})
    return render_template('index.html')

@app.route('/catalog')
def course_catalog():
    """Render the course catalog page."""
    with tracer.start_as_current_span("Render Course Catalog Page") as span:
        try:
            courses = load_courses()
            span.set_attribute("course_count", len(courses))
            logger.info({
                "message": "Catalog page accessed.",
                "course_count": len(courses)
            })
            return render_template('course_catalog.html', courses=courses)
        except Exception as e:
            logger.error({"message": "Error rendering catalog page", "error": str(e)})

@app.route('/course/<code>')
def course_details(code):
    """Render the details page for a specific course."""
    with tracer.start_as_current_span("Render Course Details Page") as span:
        try:
            courses = load_courses()
            course = next((course for course in courses if course['code'] == code), None)
            span.set_attribute("course_code", code)
            if not course:
                span.set_attribute("error", True)
                logger.error({"message": f"Course not found: {code}", "error": True})
                flash(f"No course found with code '{code}'.", "error")
                return redirect(url_for('course_catalog'))
            logger.info({
                "message": "Course details rendered.",
                "course_name": course.get("name"),
                "course_code": course.get("code")
            })
            return render_template('course_details.html', course=course)
        except Exception as e:
            logger.error({"message": "Error displaying course details", "error": str(e)})

@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    """Handle the form for adding a new course."""
    with tracer.start_as_current_span("Add Course Page") as span:
        try:
            if request.method == 'POST':
                course_name = request.form.get('name').strip()
                course_code = request.form.get('code').strip()
                course_instructor = request.form.get('instructor').strip()
                course_semester = request.form.get('semester').strip()

                # Set span attributes for telemetry
                span.set_attribute("request.method", request.method)
                span.set_attribute("course.name", course_name)
                span.set_attribute("course.code", course_code)

                # Validation for mandatory fields
                if not course_name or not course_code or not course_instructor:
                    flash("Fields marked with * are the required fields.", "error")
                    span.set_attribute("error", True)
                    logger.error({
                        "message": "Failed to add course. Missing required fields.",
                        "error": True
                    })
                    return render_template('add_course.html')

                new_course = {
                    "name": course_name,
                    "code": course_code,
                    "instructor": course_instructor,
                    "semester": course_semester
                }
                save_courses(new_course)
                flash("Course added successfully!", "success")
                logger.info({
                    "message": "New course added.",
                    "course_name": course_name,
                    "course_code": course_code
                })
                return redirect(url_for('course_catalog'))
            logger.info({"message": "Add course form displayed."})
            return render_template('add_course.html')
        except Exception as e:
            logger.error({"message": "Error in add_course_page route", "error": str(e)})

@app.route('/delete_course/<code>', methods=['POST'])
def delete_course(code):
    """Handle deleting a course by its code."""
    with tracer.start_as_current_span("Delete Course Operation") as span:
        try:
            courses = load_courses()
            updated_courses = [course for course in courses if course['code'] != code]

            if len(courses) == len(updated_courses):
                span.set_attribute("error", True)
                logger.error({"message": f"Course not found for deletion: {code}"})
                flash(f"No course found with code '{code}'.", "error")
            else:
                save_courses_to_file(updated_courses)
                flash("Course deleted successfully!", "success")
                logger.info({"message": f"Course deleted successfully.", "course_code": code})

            return redirect(url_for('course_catalog'))
        except Exception as e:
            logger.error({"message": "Error in delete_course_action route", "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)
