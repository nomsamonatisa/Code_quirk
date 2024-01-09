from django.db import models

from system_management.models import CustomUser

class Challenge(models.Model):
    name = models.CharField(max_length=100)
    difficulty_level = models.CharField(max_length=50)
    problem_statement = models.TextField()
    function_signature = models.TextField()
    input = models.TextField()
    example = models.TextField()

    def __str__(self):
        return self.name

class Attempt(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    attempt_time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField()

