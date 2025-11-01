import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv
from agents.tools import get_current_weather

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

client = OpenAI()

def run_conversation(messages, tools, available_tools):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        if tool_calls:
            logger.info("AI decided to call a tool")

            messages.append(response_message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_tools.get(function_name)

                if not function_to_call:
                    logger.error(f"Model tried to call unknown tool '{function_name}'")
                    continue

                function_args = json.loads(tool_call.function.arguments)

                function_response = function_to_call(**function_args)

                if not isinstance(function_response, str):
                    function_response = json.dumps(function_response)

                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )

            logger.info("Sending tool results back to AI")

            second_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )

            return second_response.choices[0].message
        else:
            return response_message

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None
