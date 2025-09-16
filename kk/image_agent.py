from strands import Agent
from strands.models import BedrockModel
from tools import serpapi_search
from dotenv import load_dotenv
import boto3

# 1. Load .env into environment so boto3 can use it (if it exists)
load_dotenv(override=False)

# 2. Create boto3 session to auto-pick credentials from env
session = boto3.Session()

# 3. Configure Claude 3 Haiku via AWS Bedrock
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
    region_name="us-east-1",
    temperature=0.0,
    boto3_session=session,
)

# 4. Define Agent with Python list-of-dicts instructions
agent = Agent(
    model=bedrock_model,
    system_prompt="""
You are an AI agent that evaluates the authenticity of images. 
You have the following tools available:

- serpapi_search(image_url: str) → Returns a Python list of dictionaries with reverse image search results.

For every image URL provided:

1. ONLY pass the image URL as input to the appropriate tool. 
2. Call the tools exactly by name using structured Python calls.
3. Wait for all tools to return before reasoning.
4. Return a single **Python list containing one dictionary per image URL** with all results and reasoning.

The Python list-of-dicts format:

[
    {
        "image_url": "<original image URL>",
        "tools_called": ["serpapi_search", "sensity_check"],
        "tool_results": {
            "serpapi_search": <Python list of dicts from serpapi_search>
        },
        "assessment": <float 0.0 to 1.0>,
        "evidence": "<short paragraph explaining your reasoning based on the tools>"
    }
]

Assessment scale:
0.0 = 100% AI-generated or manipulated
1.0 = 100% Authentic, non-AI generated

Important constraints:
- Do NOT add explanations outside the list-of-dicts.
- If a tool fails, include the error as a Python dict in "tool_results" but still return a valid list-of-dicts.
- Call each tool only once per image.
- Always return exactly **one dictionary per image URL inside the list**.
- Do NOT attempt alternative reasoning, retries, or multiple list entries.

Example tool call for a single image:
Input: https://i.imgur.com/5bGzZi7.jpg

Tool call in Python:
serpapi_search("https://i.imgur.com/5bGzZi7.jpg")
""",
    tools=[serpapi_search],
)

# 5. Function to call from orchestrator
def evaluate_image(image_url: str) -> list:
    """
    Calls the agent and returns a Python list containing a single dictionary
    with tool results, assessment, and evidence.
    """
    result_obj = agent(image_url)  # AgentResult object
    # The assistant's response is already a Python list-of-dicts
    result_list = result_obj.message['content'][0]['text']
    return result_list
