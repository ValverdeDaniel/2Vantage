from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/proposal/', views.ProposalView.as_view()),
]
