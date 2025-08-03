# Use a slim Python base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the contents of backend/ into the container
COPY . /app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the Flask app's port
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
