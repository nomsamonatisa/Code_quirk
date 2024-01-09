from datetime import timedelta
import io
import json
import re
from django.shortcuts import render
from django.db.models import Count, Max, Avg, F, ExpressionWrapper, FloatField
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from coding_excercise.models import Attempt, Challenge
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

    saved_challenge = Challenge.objects.create(name=challenge['challenge title'], difficulty_level=challenge['difficulty level'], problem_statement=challenge['problem statement'],function_signature=challenge['function signature'], input=challenge['function inputs'], example=challenge['example'])
    challenge['challenge_id'] = saved_challenge.id

    return JsonResponse({'data': challenge})

@login_required
def run_code(request):
    if request.method == 'POST':
        source_code = request.POST.get('code')

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

            # Optionally, return some values from safe_globals
            return JsonResponse({'result': output})
        except Exception as e:
            return JsonResponse({'result': 'Error: ' + str(e)})

    return JsonResponse({'result': 'Invalid request'})


@login_required
def submit_code(request):
    if request.method == 'POST':
        source_code = request.POST.get('code')
        challenge_id = request.POST.get('challenge_id')
        challenge_example = Challenge.objects.get(id=challenge_id).example

        prompt = f"""
        Given the following source code: {source_code}

        Will you run the code using inputs from {challenge_example} and check if it will give the expected result from the {challenge_example}

        Please return only a boolean for the result of running the function:
        True if the expected results are achieved
        False if the expected results are not achieved
        False if there are errors executing the function

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
            max_tokens=10,
            top_p=1
        )
        challenge_result = response.choices[0].message.content

        if challenge_result == 'True':
            Attempt.objects.create(user=request.user, challenge_id=challenge_id, success=True)
            result = {'result' : True,
             'output' : 'Success!'
            }
        elif challenge_result == 'False':
            Attempt.objects.create(user=request.user, challenge_id=challenge_id, success=False)
            result = {'result' : False,
             'output' : 'Solution is incorrect. Please try again!'
            }
        else:
            Attempt.objects.create(user=request.user, challenge_id=challenge_id, success=False)
            result = {'result' : False,
             'output' : 'An error occured while executing your code, please try again!'
            }
        
        return JsonResponse({'result': result})

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


def progress(request):
    user_challenges = Attempt.objects.filter(user=request.user)

    challenges_attempted = user_challenges.values('challenge_id').annotate(count=Count('challenge_id'))

    current_streak = calculate_streak(user_challenges)

    average_attempts = user_challenges.aggregate(avg_attempts=Avg('id'))

    average_number_of_attempts = average_attempts['avg_attempts']

    completion_percentage = get_completion_percentage(user_challenges)

    latest_attempts = user_challenges.values('success', 'challenge_id', 'challenge__name', 'challenge__difficulty_level').annotate(latest_attempt=Max('attempt_time'))

    combined_result = []

    for challenge_attempt in challenges_attempted:
        challenge_id = challenge_attempt['challenge_id']
        
        matching_attempt = next((attempt for attempt in latest_attempts if attempt['challenge_id'] == challenge_id), None)
        
        if matching_attempt:
            combined_result.append({
                'challenge_id': challenge_id,
                'count': challenge_attempt['count'],
                'success': matching_attempt['success'],
                'challenge__name': matching_attempt['challenge__name'],
                'challenge__difficulty_level': matching_attempt['challenge__difficulty_level'],
                'latest_attempt': matching_attempt['latest_attempt']
            })
    

    context = {
        'challenges' : combined_result,
        'challenges_attempted' : challenges_attempted,
        'current_streak' : current_streak,
        'average_number_of_attempts' : average_number_of_attempts,
        'completion_percentage' : completion_percentage
    }
    return render(request,'coding_excercise/progress.html',context=context)


def profile(request):
    return render(request,'coding_excercise/profile.html')


def calculate_streak(attempts):
    # Sort attempts by timestamp in ascending order
    sorted_attempts = sorted(attempts, key=lambda x: x.attempt_time)
    
    current_streak = 0
    longest_streak = 0
    today = timezone.now().date()
    
    for attempt in sorted_attempts:
        attempt_date = attempt.attempt_time.date()
        
        if attempt_date == today:
            current_streak += 1
        elif attempt_date == today - timedelta(days=1):
            current_streak += 1
        else:
            current_streak = 0
        
        if current_streak > longest_streak:
            longest_streak = current_streak
        
        today = attempt_date
    
    return longest_streak

def get_completion_percentage(user_attempts):
    completion_percentage = user_attempts.aggregate(
        total_attempts=Count('id'),
        successful_attempts=Count('id', filter=F('success')),
        completion_percentage=ExpressionWrapper(
            Count('id', filter=F('success')) * 100.0 / Count('id'),
            output_field=FloatField()
        )
    )
    return completion_percentage
