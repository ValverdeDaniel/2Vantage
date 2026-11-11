from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/documents/', views.DocumentsView.as_view()),
    path('documents/<int:document_id>/', views.DocumentView.as_view()),
    path('documents/<int:document_id>/download/', views.DownloadView.as_view()),
]
