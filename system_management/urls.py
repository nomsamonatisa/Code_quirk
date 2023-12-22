from django.urls import path
from system_management import views

urlpatterns = [
    path('register/', views.register, name='register')
]