# Use the official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /usr/src/app

# Copy and install dependencies
COPY . .
RUN pip install .

# Set environment variables if needed
# ENV FLASK_ENV=development

# Expose the port Flask runs on
EXPOSE 3000

# Start the Flask app
CMD ["python", "app.py"]
