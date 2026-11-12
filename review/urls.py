from django.urls import include, path

from . import decision_views, views
from .portal import views as portal_views

urlpatterns = [
    path('deals/<int:pk>/review/board/', views.BoardView.as_view()),
    path('deals/<int:pk>/review/queue/', decision_views.QueueView.as_view()),
    path('deals/<int:pk>/review/approve/', decision_views.ApproveView.as_view()),
    path('deals/<int:pk>/review/reject/', decision_views.RejectView.as_view()),
    path('deals/<int:pk>/review/undo/', decision_views.UndoView.as_view()),
    path('deals/<int:pk>/review/requests/', views.RequestsView.as_view()),
    path('deals/<int:pk>/review/requests/<int:rid>/close/', views.CloseView.as_view()),
    path('links/<int:lid>/', views.LinkView.as_view()),
    path('links/<int:lid>/preview/', portal_views.PreviewView.as_view()),
    path('portal/', include('review.portal.urls')),
]
