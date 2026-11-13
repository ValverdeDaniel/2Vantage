from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/overview/', views.DealOverviewView.as_view()),
]
