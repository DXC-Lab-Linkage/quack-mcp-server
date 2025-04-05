# Use the prebuilt cs5740-quack-base image
FROM container.cs.vt.edu/steve72/cs5740-quack-base:latest

# Set working directory inside the container
WORKDIR /app

# Copy only the project files (excluding base dependencies)
COPY . .

# Ensure Python dependencies are installed (if any are added by students)
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi