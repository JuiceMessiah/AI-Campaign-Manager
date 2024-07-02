import asyncio
import json
import time
import uvicorn
import os

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import ORJSONResponse, StreamingResponse
from APIhandler import RequestHandler, router

from utils import QueryRequest
from utils.logger import get_logger

app = FastAPI(title="AI-Campaign-Manager")
app.include_router(router)

logger = get_logger(__name__)
logger.info("API is starting up...")
logger.info(f"Currently in directory: \n {os.path.dirname(__file__)}")

# Note: run this command for testing:
# curl --location 'http://localhost:8080/streaming' --header 'Content-Type: application/json' --data '{ "url": "https://www.unboxboardom.com", "mail_type": "reject"}'


@app.post("/buffered", response_class=ORJSONResponse)
async def buffered_handler(request_body: QueryRequest = Body(None)):
    """Handler for parsing requests to the '/buffered' endpoint.

    :param request_body: The body of the request. Takes a JSON object containing the request parameters: URL,
        mail_type and customer_campaign.
    :returns: Complete affiliate campaign and optional mail template as a JSON object."""
    logger.info(f"Received request:\n{request_body}")
    try:
        request = request_body

        flag1 = time.perf_counter()

        handle = RequestHandler(request.model_dump(mode='json'))

        result = await handle.fastapi_handler_buffered()

        flag2 = time.perf_counter()

        # Calculate performance and return finished campaign and/or message templates.
        logger.info(f"Entire process was executed in {flag2 - flag1:.2f} seconds.")

        return result
    except Exception as e:
        logger.error(f"An error occurred: \n{str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Internal Server Error\n {e}")


@app.post("/streaming", response_class=StreamingResponse)
async def streaming_handler(request_body: QueryRequest = Body(None)):
    """Handler for parsing requests to the '/streaming' endpoint.

    :param request_body: The body of the request. Takes a JSON object containing the request parameters: URL,
        mail_type and customer_campaign.
    :returns: Streamed affiliate campaign and optional mail template as a JSON object."""

    logger.info(f"Received request: \n{request_body}\n")
    try:
        request = request_body
        flag1 = time.perf_counter()

        logger.info(f"Processed request: \n{request}\n")
        handle = RequestHandler(request.model_dump(mode='json'))

        flag2 = time.perf_counter()

        # Calculate performance and return finished campaign and/or message templates.
        logger.info(f"Entire process was executed in {flag2 - flag1:.2f} seconds.")

        # return await handle.fastapi_handler_stream()
        return StreamingResponse(handle.fastapi_handler_stream(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"An error occurred: \n{str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Internal Server Error\n {e}")


@app.get("/test")
async def multi_response():
    """ Small test endpoint. Returns a JSON object alongside with a small stream of data."""
    try:
        # Initial JSON response data
        initial_data = {"message": "This is the initial JSON response"}

        # Create a generator function to stream data
        async def stream_data():
            # Yield initial JSON response
            yield json.dumps(initial_data) + "\n\n"
            await asyncio.sleep(1)  # Simulate delay

            # Yield streaming data
            for i in range(10):
                yield f"data: {i}\n"
                await asyncio.sleep(1)

        # Return StreamingResponse
        return StreamingResponse(stream_data(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error\n {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), log_level="info")
