FROM apify/actor-python:3.12

# Copy requirements.txt first for better Docker layer caching
COPY requirements.txt ./

# Install Python dependencies
RUN echo "Python version:" \
    && python --version \
    && echo "Pip version:" \
    && pip --version \
    && echo "Installing dependencies from requirements.txt:" \
    && pip install -r requirements.txt \
    && echo "All installed packages:" \
    && pip list

# Copy the source code
COPY . ./

# Set the command to run the Python script
CMD ["python", "main.py"]