"""The client portal's routes, under /api/portal/ (plan.md §7.14). The moved page's route comes first: a token is 43
characters, so it can never be `moved`."""

from django.urls import path

from . import questionnaire_views as forms
from . import views

urlpatterns = [
    path('moved/', views.MovedView.as_view()),
    path('<str:token>/', views.PageView.as_view()),
    path('<str:token>/verify/', views.VerifyView.as_view()),
    path('<str:token>/save/', views.SaveView.as_view()),
    path('<str:token>/submit/', views.SubmitView.as_view()),
    path('<str:token>/files/', views.FilesView.as_view()),
    path('<str:token>/people/', views.PeopleView.as_view()),
    path('<str:token>/sign/', views.SignView.as_view()),
    path('<str:token>/questions/', views.QuestionsView.as_view()),
    path('<str:token>/seen/', views.SeenView.as_view()),
    path('<str:token>/stamp/', views.StampView.as_view()),
    path('<str:token>/census-template/', views.TemplateView.as_view()),
    path('<str:token>/questionnaires/<str:form>/spec/', forms.SpecView.as_view()),
    path('<str:token>/questionnaires/<str:form>/blank/', forms.BlankView.as_view()),
    path('<str:token>/questionnaires/<str:form>/rows/', forms.RowsView.as_view()),
    path('<str:token>/questionnaires/<str:form>/rows/<str:block>/<int:row_id>/', forms.RowView.as_view()),
    path('<str:token>/questionnaires/<str:form>/sign/', forms.SignView.as_view()),
]
