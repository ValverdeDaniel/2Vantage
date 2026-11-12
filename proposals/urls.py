from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/proposal/', views.ProposalView.as_view()),
    path('deals/<int:pk>/proposal/pages/', views.PagesView.as_view()),
]
