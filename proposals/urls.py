from django.urls import path

from . import deck_views, views, workbook_views

urlpatterns = [
    path('deals/<int:pk>/proposal/', views.ProposalView.as_view()),
    path('deals/<int:pk>/proposal/marks/', views.MarksView.as_view()),
    path('deals/<int:pk>/proposal/pages/', views.PagesView.as_view()),
    path('deals/<int:pk>/proposal/files/pdf/', deck_views.ClientPdfView.as_view()),
    path('deals/<int:pk>/proposal/files/pptx/', deck_views.ClientPptxView.as_view()),
    path('deals/<int:pk>/proposal/files/xlsx/', workbook_views.ClientWorkbookView.as_view()),
]
