from dotenv import load_dotenv
import os
import boto3

# Load environment variables from .env file
load_dotenv(".env")



# Function to ask Claude using AWS Bedrock
def ask_claude(prompt, system="You are a helpful assistant that can answer questions and help with tasks."):
    client = boto3.client('bedrock-runtime', region_name='us-east-1')
    response = client.converse(
    modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    messages=[{"role": "user", "content": [{"text": prompt}]}],
    system=[{"text": system}],
    inferenceConfig={"temperature": 0, "maxTokens": 200}
    )
    return response['output']['message']['content'][0]['text']

# Example usage
print(ask_claude("What is the capital of the moon?"))