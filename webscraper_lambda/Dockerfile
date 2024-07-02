# Docker image with built in Selenium support.
# Regularly updated and maintained with the latest versions of Python, Chromium, Chrome drivers and Selenium. Very nice.
# See https://github.com/umihico/docker-selenium-lambda
FROM umihico/aws-lambda-selenium-python:latest

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages/dependencies.
RUN pip install -r requirements.txt
COPY src ${LAMBDA_TASK_ROOT}
COPY utils ${LAMBDA_TASK_ROOT}/utils

# Set the CMD to your handler.
CMD [ "webscraper_handler.handler" ]