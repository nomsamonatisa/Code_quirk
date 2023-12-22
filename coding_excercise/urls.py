from django.urls import path
from coding_excercise import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('generate_challenge/', views.generate_challenge, name='generate_challenge'),
    path('run_code/', views.run_code, name='run_code')
   
]
