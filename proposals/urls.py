from django.urls import path

from . import (
    cover_views,
    deck_views,
    firm_views,
    issue_views,
    preview_views,
    stop_loss_views,
    template_views,
    views,
    workbook_views,
)

urlpatterns = [
    path('deals/<int:pk>/proposal/', views.ProposalView.as_view()),
    path('deals/<int:pk>/proposal/marks/', views.MarksView.as_view()),
    path('deals/<int:pk>/proposal/pages/', views.PagesView.as_view()),
    path('deals/<int:pk>/proposal/files/pdf/', deck_views.ClientPdfView.as_view()),
    path('deals/<int:pk>/proposal/files/pptx/', deck_views.ClientPptxView.as_view()),
    path('deals/<int:pk>/proposal/files/letter/', deck_views.ClientLetterView.as_view()),
    path('deals/<int:pk>/proposal/files/xlsx/', workbook_views.ClientWorkbookView.as_view()),
    path('deals/<int:pk>/proposal/preview/', preview_views.ProposalPreviewView.as_view()),
    # the stop-loss analysis workbook (J166; slice 36): quotes' analysis, written here where the sheet writer lives
    path('deals/<int:pk>/plans/stop-loss/workbook/', stop_loss_views.StopLossWorkbookView.as_view()),
    # Issue to client and the issued versions (J96, J102, J103; slice 32)
    path('deals/<int:pk>/proposal/issue/', issue_views.IssueView.as_view()),
    path('deals/<int:pk>/proposal/issues/', issue_views.IssuesView.as_view()),
    path('deals/<int:pk>/proposal/issues/<int:version>/retry/', issue_views.RetryView.as_view()),
    *[
        path(
            f'deals/<int:pk>/proposal/issues/<int:version>/{file}/',
            issue_views.IssuedFileView.as_view(),
            {'file': file},
        )
        for file in ('pdf', 'pptx', 'xlsx', 'letter', 'packet')
    ],
    # the firm's cover images, pictures, pages and team, and saved templates (J32–J35, J68, J155; slice 34)
    path('proposal/covers/', cover_views.CoverTilesView.as_view()),
    path('proposal/cover-images/', cover_views.CoverImagesView.as_view()),
    path('proposal/cover-images/<int:image_id>/', cover_views.CoverImageView.as_view()),
    path('proposal/cover-images/<int:image_id>/thumb/', cover_views.CoverThumbView.as_view()),
    path('proposal/pictures/<str:key>/thumb/', cover_views.StockThumbView.as_view()),
    path('proposal/firm-pages/', firm_views.FirmPagesView.as_view()),
    path('proposal/team/', firm_views.TeamView.as_view()),
    path('proposal/team/<int:member_id>/', firm_views.PersonView.as_view()),
    path('proposal/team/<int:member_id>/photo/', firm_views.PhotoView.as_view()),
    path('proposal/templates/', template_views.TemplatesView.as_view()),
    path('proposal/templates/<int:template_id>/', template_views.TemplateView.as_view()),
]
