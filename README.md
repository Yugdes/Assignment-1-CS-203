# CS203_Lab_01

This repository contains the submission for Assignment 1 of the course CS 203 - Software Tools and Techniques for AI, offered at the Indian Institute of Technology, Gandhinagar.

## Setup

### 1. Install the Dependencies

To install the necessary dependencies for the project, run the following command:

```bash
pip install flask opentelemetry-api opentelemetry-sdk opentelemetry-exporter-jaeger opentelemetry-instrumentation-flask
```
### 2. Save the File
Save the main Python application code in a file named app.py. You can use any code editor, such as Visual Studio Code to create the file.

### 3. Run the Flask Application
After saving the app.py file, open a terminal and navigate to the directory where the app.py file is located. Use the following command to start the Flask application:

```bash
python app.py
```

### 4. Open the Application in a Browser
Once the app starts, visit the following url on browser.
```bash
127.0.0.1:5000
```

## Jaeger
### 1. Install Docker Desktop
Ensure that Docker Desktop is installed on your computer.

### 2. Run Jaeger in Docker
To run Jaeger using Docker, open the Docker terminal and enter the following command:

```bash
docker run -d --name jaeger -e COLLECTOR_OTLP_ENABLED=true -p 4317:4317 -p 16686:16686 jaegertracing/all-in-one:1.46

```
### Open the Jaeger UI in the browser
```bash
127.0.0.1:16686
```
