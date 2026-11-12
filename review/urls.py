from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/review/board/', views.BoardView.as_view()),
    path('deals/<int:pk>/review/requests/', views.RequestsView.as_view()),
    path('deals/<int:pk>/review/requests/<int:rid>/close/', views.CloseView.as_view()),
    path('links/<int:lid>/', views.LinkView.as_view()),
]
