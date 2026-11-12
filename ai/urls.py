from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/ai/', views.DealAiView.as_view()),
    path('deals/<int:pk>/ai/locate/', views.LocateView.as_view()),
    path('deals/<int:pk>/ai/reads/', views.ReadsView.as_view()),
    path('ai/jobs/<int:job_id>/', views.JobView.as_view()),
    path('ai/jobs/<int:job_id>/cancel/', views.CancelView.as_view()),
    path('ai/jobs/<int:job_id>/discard/', views.DiscardView.as_view()),
    path('ai/jobs/<int:job_id>/apply/', views.ApplyView.as_view()),
    path('ai/jobs/<int:job_id>/undo/', views.UndoView.as_view()),
]
