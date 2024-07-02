FROM public.ecr.aws/docker/library/python:3.12.0-slim-bullseye

# Copy Install Lambda stream response adapter to Lambda extensions directory.
# See https://github.com/awslabs/aws-lambda-web-adapter/tree/main/examples/fastapi-response-streaming
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.1 /lambda-adapter /opt/extensions/lambda-adapter

# Enable RESPONSE STREAM for the Lambda function.
ENV AWS_LWA_INVOKE_MODE=RESPONSE_STREAM

# Copy requirements.txt.
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages.
RUN pip install -r requirements.txt

# Copy function code/dependencies.
COPY src ${LAMBDA_TASK_ROOT}
COPY .env ${LAMBDA_TASK_ROOT}
COPY instructions ${LAMBDA_TASK_ROOT}/var/task/instructions

#Define Port.
ENV PORT=9000

# Set the CMD to your handler.
CMD [ "python", "main.py" ]