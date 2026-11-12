from django.urls import path

from . import sheet_views, views

urlpatterns = [
    path('deals/<int:pk>/documents/', views.DocumentsView.as_view()),
    path('documents/<int:document_id>/', views.DocumentView.as_view()),
    path('documents/<int:document_id>/archive/', views.ArchiveView.as_view()),
    path('documents/<int:document_id>/restore/', views.RestoreView.as_view()),
    path('documents/<int:document_id>/download/', views.DownloadView.as_view()),
    path('documents/<int:document_id>/sheet/', sheet_views.SheetView.as_view()),
    path('documents/<int:document_id>/sheet/find/', sheet_views.SheetFindView.as_view()),
]
