import asyncio
import json
import boto3
import re

from typing import Union, Tuple, AsyncGenerator
from fastapi import APIRouter, HTTPException
from utils.logger import get_logger

import OpenAIClient

logger = get_logger(__name__)
router = APIRouter()


class RequestHandler:
    """
    This class is responsible for handling requests and the logic for how we generate campaign and message templates.
    """

    def __init__(self, request: dict):
        self.request = request  # Load the request.
        self.body = self.get_event_body()  # Get the body of the request.

        self.ai = OpenAIClient.AIGenerator(self.body)  # Instantiate the OpenAI client.
        self.client = boto3.client('lambda', region_name='eu-central-1')  # Instantiate the boto3 client.

        self.generate_campaign_bool = self.should_generate_campaign()    # Determine if a campaign should be generated.
        self.customer_campaign = self.body.get('customer_campaign', 'default_customer_campaign')
        self.generate_message_bool = self.should_generate_message()  # Determine if a message should be generated.

    def get_event_body(self) -> dict:
        return json.loads(self.request['body']) if 'body' in self.request else self.request

    def should_generate_message(self) -> bool:
        mail_type = self.body.get('mail_type')
        return mail_type != 'default_mail_type'

    def should_generate_campaign(self) -> bool:
        customer_campaign = self.body.get('customer_campaign')
        url = self.body.get('url')
        return customer_campaign == 'default_customer_campaign' and url is not None

    async def fastapi_handler_buffered(self) -> Union[dict, Tuple[str, int]]:
        """ Method for handling buffered responses. This method does **NOT** include streaming, but simply returns the
        entire desired output upon completion.

        Note: Should webscraping fail, then the program returns an HTTP
        error code along with the accompanying error message.
        :param self: The body of a given request. Validated with Pydantic.
        :returns: A finished affiliate campaign and optional mail type, both as a single JSON object."""

        try:
            logger.info(f"Request Received! Generating Affiliate Campaign for {self.body.get('url')}\n\n")

            result = {}                                         # Initialize an empty dictionary to store the results.
            if self.should_generate_campaign():                 # Check if a campaign should be generated.
                logger.info("URL present. Scraping website...")
                site_text = self.invoke_webscraper_lambda()     # Invoke the WebScraper Lambda function.
                if isinstance(site_text, dict):                 # Check if the response is an error.
                    return site_text
                else:
                    pass                                        # If no error, continue with the process.

                logger.info("Generating campaign and guidelines...\n")
                logger.info(f"Language is: {self.body.get('lang', 'english')}")
                campaign, platform = await self.generate_campaign_and_guidelines(site_text)

                result.update(campaign)
                result.update(platform)

                if self.should_generate_message():
                    logger.info("mail_type present. Generating mail template...")
                    message = await self.generate_message(campaign)
                    result.update(message)

                return result
            else:
                logger.info(f"Campaign already present. Generating mail template for '{self.body.get('mail_type')}'")
                campaign = self.customer_campaign               # If campaign is already provided, use that instead.
                message = await self.generate_message(campaign)       # Generate the message.

                # Add the results to the dictionary.
                result.update(message)

                return result                                   # Return the results.
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            raise HTTPException(500, f"Error in buffered handler: {e}")

    async def fastapi_handler_stream(self) -> AsyncGenerator[str, None]:
        """ Method for handling streamed responses. This method **DOES** include streaming, first the campaign is
        streamed, then returns the entire desired JSON output upon completion.

        Note: Should webscraping fail, then the program returns an HTTP
        error code along with the accompanying error message.
        :param self: The body of a given request. Validated with Pydantic.
        :returns: A finished affiliate campaign and optional mail type, both as a single JSON object."""

        try:
            yield f"Request Received! Generating Affiliate Campaign for {self.body.get('url')}\n\n"

            result = {}                                         # Initialize an empty dictionary to store the results.
            if self.should_generate_campaign():                 # Check if a campaign should be generated.
                site_text = self.invoke_webscraper_lambda()     # Invoke the WebScraper Lambda function.
                if isinstance(site_text, dict):                 # Check if the response is an error.
                    yield json.dumps(site_text)
                else:
                    pass

                logger.info(f"Language is: {self.body.get('lang', 'english')}")
                summary = await self.ai.summarize_text(site_text)
                campaign_stream = self.ai.stream_campaign(summary)
                platform_future = asyncio.ensure_future(self.ai.create_platform_completion(summary))

                # Initialize an empty string to store the campaign, and then stream afterward.
                campaign = ""
                async for chunk in campaign_stream:
                    campaign += chunk
                    yield chunk

                platform = await platform_future      # Create platform completion while campaign is streaming.

                # Parse streamed completion and add the results to the dictionary.
                parsed_sections = self.parse_completion(campaign)
                result.update({
                    "title": parsed_sections["title"],
                    "aboutCompany": parsed_sections["aboutCompany"],
                    "description": parsed_sections["description"]
                })
                result.update(platform)

                yield "\n\n" + json.dumps(result, indent=3) + "\n\n"

                if self.should_generate_message():
                    message = await self.generate_message(campaign)
                    yield json.dumps({'message': message}, indent=3)
                return
            else:
                campaign = self.customer_campaign  # If campaign is already provided, use that instead.
                message = await self.generate_message(campaign)  # Generate the message.

                # Add the results to the dictionary.
                result['message'] = message

                yield "\n" + json.dumps(result) + "\n\n"
            return
        except Exception as e:
            raise HTTPException(500, f"Error in streaming handler: {e}")

    # TODO: Add API endpoint here, so we can call the webscraper directly from this API
    #  instead of the lambda function url.
    def invoke_webscraper_lambda(self) -> Union[str, dict]:
        """
        This method invokes the WebScraper Lambda function and returns the scraped text.

        :return: Scraped text from the website.
        """

        payload = {
            "url": self.body.get('url')
        }

        try:
            # Invoke the Lambda function
            response = self.client.invoke(
                FunctionName='WebScraper_Service',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload),
            )

            # Read the response from the Lambda function
            response_payload = json.loads(response['Payload'].read().decode('utf-8'))
            body = json.loads(response_payload['body'])

            logger.info(f"Response from WebScraper Lambda function: {body}")

            # Extract the scraped text from the response body.
            scraped_text = body['site_text']

            return scraped_text
        except Exception as e:
            raise HTTPException(500, f"Error invoking WebScraper Lambda function: {e}")

    async def generate_campaign_and_guidelines(self, site_text) -> tuple[dict, dict]:
        summary = await self.ai.summarize_text(site_text)     # Generate summary.

        # Wait for campaign and guidelines to finish and save upon completion.
        campaign, guidelines = await self.ai.create_buffered_campaign(summary)
        return campaign, guidelines

    async def generate_message(self, campaign) -> dict:
        return await self.ai.create_message_completion(self.body.get('mail_type'), campaign)

    # TODO: Currently parsing streamed completions into proper JSON format is only supported in english.
    #  Should be extended to other languages. Also, this method is static and should be moved to a utility class.
    #  However, it doesn't properly format the streamed completions unless it is inside this class????
    def parse_completion(self, text):
        sections = {
            "title": "",
            "aboutCompany": "",
            "description": ""
        }

        # Extracting the title
        title_match = re.search(r"\*\*Campaign Title\*\*\n(.+)\n", text)
        if title_match:
            sections["title"] = title_match.group(1).strip()

        # Extracting the aboutCompany section
        about_match = re.search(r"\*\*About the Company\*\*\n(.+?)\n\n\*\*Campaign Description\*\*", text, re.DOTALL)
        if about_match:
            sections["aboutCompany"] = about_match.group(1).strip()

        # Extracting the description and subsequent sections
        description_match = re.search(r"\*\*Campaign Description\*\*\n(.+)", text, re.DOTALL)
        if description_match:
            description = description_match.group(1).strip()
            sections["description"] = description

        return sections
