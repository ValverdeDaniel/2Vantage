from django.urls import include, path

from . import confidence_views, decision_views, form_views, note_views, views
from .portal import views as portal_views

urlpatterns = [
    path('deals/<int:pk>/review/board/', views.BoardView.as_view()),
    path('deals/<int:pk>/review/queue/', decision_views.QueueView.as_view()),
    path('deals/<int:pk>/review/approve/', decision_views.ApproveView.as_view()),
    path('deals/<int:pk>/review/reject/', decision_views.RejectView.as_view()),
    path('deals/<int:pk>/review/undo/', decision_views.UndoView.as_view()),
    path('deals/<int:pk>/review/notes/', note_views.NotesView.as_view()),
    path('deals/<int:pk>/review/notes/<int:nid>/', note_views.NoteView.as_view()),
    path('deals/<int:pk>/review/tray/', note_views.TrayView.as_view()),
    path('deals/<int:pk>/review/tray/remove/', note_views.TrayRemoveView.as_view()),
    path('deals/<int:pk>/review/tray/send/', note_views.TraySendView.as_view()),
    path('deals/<int:pk>/review/seen/', note_views.SeenView.as_view()),
    path('deals/<int:pk>/review/request/', note_views.RequestPageView.as_view()),
    path('deals/<int:pk>/review/requests/', views.RequestsView.as_view()),
    path('deals/<int:pk>/review/requests/<int:rid>/close/', views.CloseView.as_view()),
    path('deals/<int:pk>/review/requests/<int:rid>/form/', form_views.FormView.as_view()),
    path('deals/<int:pk>/review/requests/<int:rid>/people/', form_views.PeopleView.as_view()),
    path('deals/<int:pk>/review/preview/', form_views.PreviewView.as_view()),
    path('deals/<int:pk>/review/enter/', form_views.EnterView.as_view()),
    path('deals/<int:pk>/review/census-blanks/', form_views.CensusBlanksView.as_view()),
    path('deals/<int:pk>/review/section/', form_views.SectionView.as_view()),
    path('deals/<int:pk>/review/rules/', form_views.RulesView.as_view()),
    path('deals/<int:pk>/review/marks/', confidence_views.MarksView.as_view()),  # slice 64: marks across owners
    path('deals/<int:pk>/confidence/', confidence_views.ConfidenceView.as_view()),  # the Overview's (slice 64)
    path('links/<int:lid>/', views.LinkView.as_view()),
    path('links/<int:lid>/preview/', portal_views.PreviewView.as_view()),
    path('portal/', include('review.portal.urls')),
]
