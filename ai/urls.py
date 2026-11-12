from django.urls import path

from . import chat_views, views

urlpatterns = [
    path('deals/<int:pk>/ai/', views.DealAiView.as_view()),
    path('deals/<int:pk>/ai/locate/', views.LocateView.as_view()),
    path('deals/<int:pk>/ai/reads/', views.ReadsView.as_view()),
    path('deals/<int:pk>/ai/sends/', views.SendsView.as_view()),
    path('deals/<int:pk>/ai/chats/', chat_views.ChatsView.as_view()),
    path('deals/<int:pk>/ai/messages/', chat_views.SendView.as_view()),
    path('ai/chats/<int:chat_id>/', chat_views.ChatView.as_view()),
    path('ai/chats/<int:chat_id>/messages/', chat_views.MessagesView.as_view()),
    path('ai/jobs/<int:job_id>/', views.JobView.as_view()),
    path('ai/jobs/<int:job_id>/cancel/', views.CancelView.as_view()),
    path('ai/jobs/<int:job_id>/discard/', views.DiscardView.as_view()),
    path('ai/jobs/<int:job_id>/apply/', views.ApplyView.as_view()),
    path('ai/jobs/<int:job_id>/undo/', views.UndoView.as_view()),
    path('ai/jobs/<int:job_id>/retry/', views.RetryView.as_view()),
]
