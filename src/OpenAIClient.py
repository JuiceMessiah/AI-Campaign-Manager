import os
import json
import time
import asyncio

from utils.logger import get_logger
from utils.monitor import check_env_for_dev_flag
from typing import AsyncGenerator, Optional, Union
from openai import AsyncOpenAI, NOT_GIVEN
from dotenv import load_dotenv
from enum import Enum

logger = get_logger(__name__)

# Get the root directory
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
lambda_task_root = os.environ.get('LAMBDA_TASK_ROOT', parent_dir)   # Get either the lambda or parent directory.

# Define the instructions directory
if lambda_task_root == 'LAMBDA_TASK_ROOT':
    instructions_dir = os.path.join(lambda_task_root, '/var/task/instructions')
else:
    instructions_dir = os.path.join(lambda_task_root, 'instructions')

# Define a dictionary to hold the file names and their paths.
file_paths = {
    'campaign': 'campaign_instructions.txt',
    'buffered_campaign': 'buffered_campaign_instructions.txt',
    'platform': 'platform_guideline_instructions.txt',
    'summary': 'summary_instructions.txt',
    'invite': 'invite_instructions.txt',
    'welcome': 'welcome_instructions.txt',
    'reject': 'reject_instructions.txt'
}

# Update the dictionary values with the full file paths.
file_paths = {key: os.path.join(instructions_dir, value) for key, value in file_paths.items()}


# Define an Enum class to hold the identifiers and their corresponding .txt instructions.
class Identifiers(Enum):
    CAMPAIGN = open(file_paths["campaign"], 'r', encoding='utf-8').read()
    BUFFERED_CAMPAIGN = open(file_paths["buffered_campaign"], 'r', encoding='utf-8').read()
    PLATFORM = open(file_paths["platform"], 'r', encoding='utf-8').read()
    SUMMARY = open(file_paths["summary"], 'r', encoding='utf-8').read()
    INVITE = open(file_paths["invite"], 'r', encoding='utf-8').read()
    WELCOME = open(file_paths["welcome"], 'r', encoding='utf-8').read()
    REJECT = open(file_paths["reject"], 'r', encoding='utf-8').read()


logger.info(f"Currently in directory: \n{os.path.dirname(__file__)}")


def monitor_tokens(completion, identifier: Identifiers):
    """
    Small method for monitoring token usage with OpenAI API.
    OpenAI charges their customers on token usage, so monitoring tokens helps see how much each completion costs.
    """

    logger.info(f"{str(identifier.name).capitalize()} prompt tokens: " + str(completion.usage.prompt_tokens))
    logger.info(f"{str(identifier.name).capitalize()} completion tokens: " + str(completion.usage.completion_tokens))
    logger.info(f"{str(identifier.name).capitalize()} total tokens: " + str(completion.usage.total_tokens))
    logger.info(f"{str(identifier.name).capitalize()} finish Reason: " + str(completion.choices[0].finish_reason))


class AIGenerator:
    """
    Class for generating AI completions with OpenAI API.
    """

    def __init__(self, body: dict = None):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.body = body

        if self.api_key is None:
            raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

        self.Async_client = AsyncOpenAI(api_key=self.api_key)

        if check_env_for_dev_flag():
            self.monitor = True
        else:
            self.monitor = False

    async def create_completion(self, prompt: str, identifier: Identifiers, max_tokens: Optional[int] = None,
                                stream: Optional[bool] = False) -> Union[str, dict]:
        """
        Main method for generating chat completions with OpenAI's API.
        :param max_tokens: Maximum tokens for completion. Default is None.
        :param prompt: The prompt to be used for completion.
        :param identifier: The identifier to be used for completion. Can be e.g. 'Campaign', 'Platform', 'Summary',
        :param stream: If True, the completion will be streamed. Default is False.
        :return: Completion as a string when generating summary or campaign stream. Will return dict otherwise.
        """

        flag1 = time.perf_counter()

        instruction = identifier.value
        if not isinstance(identifier, Identifiers):
            raise ValueError(f"Invalid identifier: {identifier}. Expected one of: 'Campaign', 'Platform', 'Summary', "
                             f", 'Invite', 'Welcome' or 'Reject'.")

        # Define the model to be used for completions. GPT-3.5 is the cheapest model, and is used for summaries/mails.
        if identifier in [Identifiers.SUMMARY, Identifiers.INVITE, Identifiers.WELCOME, Identifiers.REJECT]:
            model = "gpt-3.5-turbo-0125"
        else:
            # GPT-4o is the more expensive/capable model, and is used for campaign/platform completions.
            model = "gpt-4o"

        # Set response format based on identifier. Should only be None for summary and streamed campaign completions.
        response_format = NOT_GIVEN if identifier == Identifiers.SUMMARY or identifier == Identifiers.CAMPAIGN \
            else {"type": "json_object"}

        language = "\nYou will generate this content in " + self.body.get('lang', 'english')

        chat = await self.Async_client.chat.completions.create(
            model=model,
            response_format=response_format,
            stream=stream,
            messages=[
                {"role": "system", "content": instruction + language},
                {"role": "user", "content": prompt}
            ],
            n=1,    # Option for number of completions to create. Usually AI picks the completion with best fit.
            temperature=0.6,  # Option for 'randomness', accepts values between 0-2. Lower values more deterministic.
            max_tokens=max_tokens  # Max token usage for chat completions. A.K.A max tokens for the output.
        )

        content = chat.choices[0].message.content

        flag2 = time.perf_counter()

        if self.monitor:
            monitor_tokens(chat, identifier)
            logger.info(f"{str(identifier.name).capitalize()} has been generated in {flag2 - flag1:.2f} seconds.")
            logger.debug(f"\n{str(identifier.name).capitalize()}: \n" + content)

        if response_format == {"type": "json_object"}:
            return json.loads(content)
        else:
            return content

    async def summarize_text(self, page_text: str) -> str:
        """In order to reduce token usage, when generating briefs with the more expensive AI models, we use GPT-3.5 for
        summarization. This is the cheapest model, and creates a coherent summary of the scraped website.
        Also is a cheap way to reduce the token usage of the more expensive models."""
        return await self.create_completion(page_text, Identifiers.SUMMARY)

    async def create_campaign_completion(self, summary: str) -> dict:
        return await self.create_completion(summary, Identifiers.BUFFERED_CAMPAIGN, 600)

    async def create_platform_completion(self, summary: str) -> dict:
        platform_guidelines = await self.create_completion(summary, Identifiers.PLATFORM)
        return platform_guidelines

    async def create_message_completion(self, mail_type: str, prompt: str) -> dict:
        logger.info(f"Mail type: {mail_type}\nGenerating message completion...")
        if mail_type == 'invite':
            return await self.create_completion(json.dumps(prompt), Identifiers.INVITE)
        elif mail_type == 'welcome':
            return await self.create_completion(json.dumps(prompt), Identifiers.WELCOME)
        elif mail_type == 'reject':
            return await self.create_completion(json.dumps(prompt), Identifiers.REJECT)
        else:
            raise ValueError(f"Invalid mail_type: {mail_type}. Expected one of: 'invite', 'welcome', 'reject'.")

    async def stream_campaign(self, summary: str) -> AsyncGenerator[str, None]:
        with open(file_paths['campaign'], 'r', encoding='utf-8') as file:
            campaign_instructions = file.read()

            language = "\nYou will generate this content in " + self.body.get('lang', 'english')

        campaign_stream = await self.Async_client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": campaign_instructions + language},
                {"role": "user", "content": summary}
            ],
            temperature=0.3,
            stream=True
        )
        final_response = ""
        async for chunk in campaign_stream:
            chunk_response = chunk.choices[0].delta.content
            if chunk_response:
                final_response += chunk_response
                yield chunk_response

    async def create_buffered_campaign(self, summary: str) -> tuple[dict, dict]:
        """
        Method to generate campaign with chat completion, based on generated summary.
        Campaign completion and platform completion are generated concurrently, and stored in separate variables.

        :param summary: Summary of text extracted from a website.
        :return: Campaign and platform guidelines as JSON objects.
        """

        flag1 = time.perf_counter()

        # Concurrently generates campaign and platform completions. Store them in separate variables.
        campaign_completion, platform_completion = await asyncio.gather(
            self.create_campaign_completion(summary),
            self.create_platform_completion(summary)
        )

        # Loads completion objects into variable.
        campaign = campaign_completion
        platform_guidelines = platform_completion

        flag2 = time.perf_counter()
        logger.info(f"Campaign has been generated in {flag2 - flag1:.2f} seconds.")
        logger.debug("Campaign: \n" + str(campaign))

        return campaign, platform_guidelines
