import io
import json
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from decouple import config
from openai import OpenAI
import RestrictedPython
from RestrictedPython import compile_restricted
from RestrictedPython.PrintCollector import PrintCollector



api_key = config('OPEN_AI_KEY')
client = OpenAI(
    api_key=api_key
)

@login_required
def dashboard(request):
    return render(request, 'coding_excercise/dashboard.html')

@login_required
def generate_challenge(request):
    difficulty_level = request.POST.get('difficulty_level')

    prompt = f"""
    Create a coding challenge in the following format strictly and return it in a dictionary with the heading as keys:

    
    challenge title: [Title of the challenge]

    difficulty level: {difficulty_level}

    problem statement:
    [Description of the problem]

    function signature:
    [Python function signature with appropriate types and return]

    function inputs:
    [Detailed description of the inputs]

    example:
    [An example of input and expected output]
    """

    response = client.chat.completions.create(
        model='gpt-4',
        messages=[
            {
            "role": "user",
            "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=300,
        top_p=1
    )
    challenge = response.choices[0].message.content
    challenge = json.loads(challenge)
    print(challenge)

    return JsonResponse({'data': challenge})

@login_required
def run_code(request):
    if request.method == 'POST':
        source_code = request.POST.get('code')
        

        # source_code = '\nresult = printed'
        # print(source_code)

        try:
            custom_print = CustomPrint()            
            
            source_code = re.sub(r'print\s*\(', 'custom_print(', source_code)
            byte_code = compile_restricted(source_code, '<string>', 'exec')

            # Create a safe 'globals' dictionary
            safe_globals = {
                '__builtins__': RestrictedPython.safe_builtins,
                'custom_print': custom_print.print
            }

            # Execute the restricted code
            exec(byte_code, safe_globals)
            output = json.dumps(custom_print.outputs)
          
           
            # print(output)

            # Optionally, return some values from safe_globals
            return JsonResponse({'result': output})
        except Exception as e:
            return JsonResponse({'result': 'Error: ' + str(e)})

    return JsonResponse({'result': 'Invalid request'})


class CustomPrint:
    def __init__(self):
        self.outputs = []

    def print(self, *args, **kwargs):
        output = io.StringIO()
        print(*args, file=output, **kwargs)
        str_output = output.getvalue()
        self.outputs.append(str_output)
        output.close