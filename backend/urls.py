from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path

from . import spa
from .health import health
from .meta import MetaView

admin.site.site_header = '2Vantage admin'
admin.site.site_title = '2Vantage admin'

urlpatterns = [
    path('admin/', admin.site.urls),
    # Django's own password-change pages (admin-styled templates); nothing else from auth.urls (§7.2).
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('api/health/', health),
    path('api/meta/', MetaView.as_view()),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('deals.urls')),
    path('api/', include('documents.urls')),
    path('api/', include('ai.urls')),
    path('api/', include('intake.urls')),
    path('api/', include('census.urls')),
    path('api/', include('quotes.urls')),
    path('api/', include('proposals.urls')),
]

# The built SPA answers every other path (the production image; slice 69, §11.2). Last, so every route above wins.
urlpatterns += [re_path(r'^(?!(?:api|admin|accounts|static)(?:/|$)).*$', spa.index)]
