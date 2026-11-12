from django.urls import path

from . import file_views, views

DEAL = 'deals/<int:pk>/questionnaires/'
FORM = DEAL + '<slug:form>/'

urlpatterns = [
    path('meta/questionnaires/<slug:form>/', views.SpecView.as_view()),
    path(DEAL, views.DealFormsView.as_view()),
    path(DEAL + 'choice/', views.ChoiceView.as_view()),
    path(FORM, views.FormView.as_view()),
    path(FORM + 'answers/', views.AnswersView.as_view()),
    path(FORM + 'rows/<slug:block>/', views.RowsView.as_view()),
    path(FORM + 'rows/<slug:block>/<int:row_id>/', views.RowView.as_view()),
    path(FORM + 'sign/', views.SignView.as_view()),
    path(FORM + 'reopen/', views.ReopenView.as_view()),
    path(FORM + 'sources/', views.SourcesView.as_view()),
    path(FORM + 'marks/', views.MarksView.as_view()),
    path(FORM + 'check/', file_views.CheckView.as_view()),
    path(FORM + 'pdf/', file_views.PdfView.as_view()),
    path(FORM + 'blank/', file_views.BlankView.as_view()),
]
