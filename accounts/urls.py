from django.urls import path

from . import signin_views, views

urlpatterns = [
    path('csrf/', views.CsrfView.as_view()),
    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),
    path('me/', views.MeView.as_view()),
    # Which ways in are open, and Microsoft 365 sign-in's two browser steps (slice 47; §7.2, §11.4).
    path('options/', signin_views.SignInOptionsView.as_view()),
    path('microsoft/', signin_views.MicrosoftStartView.as_view()),
    path('microsoft/callback/', signin_views.MicrosoftCallbackView.as_view()),
]
