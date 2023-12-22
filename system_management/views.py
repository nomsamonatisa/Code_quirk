from django.shortcuts import render, redirect
from django.contrib.auth import login

from system_management.models import CustomUser


def home(request):
    return render(request,"index.html")


def redirect_user(request):
    return redirect('dashboard')


def register(request):
    if request.method == 'POST':
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Check if the username is already taken
        if CustomUser.objects.filter(email=email).exists():
            return render(request, 'registration/register.html', {'error': 'Username already taken'})

        # Create a new user
        user = CustomUser.objects.create_user(first_name=firstname, email=email, password=password, last_name=lastname)
        login(request, user)  # Log the user in
        return redirect('home')  # Replace 'home' with your desired URL after successful registration

    return render(request, 'registration/register.html')