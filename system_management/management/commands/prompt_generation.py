import json
import requests
from decouple import config
from django.core.management.base import BaseCommand
from openai import OpenAI


class Command(BaseCommand):

    def handle(self, *args, **options):
        difficulty_level = "Beginner"

        prompt = f"""
        Create a coding challenge in the following format strictly and return it in a dictionary:

        
        title: [Title of the challenge]

        difficulty level: {difficulty_level}

        problem statement:
        [Description of the problem]

        function signature:
        [Python function signature with appropriate types and return]

        inputs:
        [Detailed description of the inputs]
        """
        challenge = generate_coding_challenge(prompt)
        challenge = json.loads(challenge)
        print(challenge)

def generate_coding_challenge(prompt):
    api_key = config('OPEN_AI_KEY')
    client = OpenAI(
        api_key=api_key
    )

    response = client.chat.completions.create(
        model='gpt-4',
        messages=[
            {
            "role": "user",
            "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=256,
        top_p=1
    )

    return response.choices[0].message.content
    

# Example usage

