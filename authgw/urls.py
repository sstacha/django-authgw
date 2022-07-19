from django.urls import path

from . import views

urlpatterns = [
    # authentication routes
    # ---------------------
    # ex: /auth/login/
    path('login/', views.login, name='login'),
    # ex: /auth/logout/
    path('logout/', views.logout, name='logout'),
]