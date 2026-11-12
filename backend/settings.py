"""2Vantage settings. The only module that reads environment variables (plan.md §3.5)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name, default=''):
    return os.environ.get(name, default)


def _flag(name, default='False'):
    return _env(name, default).strip().lower() in ('true', '1', 'yes')


def _list(name, default=''):
    return [item.strip() for item in _env(name, default).split(',') if item.strip()]


SECRET_KEY = _env('DJANGO_SECRET_KEY', 'dev-only-not-secret')
DEBUG = _flag('DJANGO_DEBUG')
ENVIRONMENT = _env('ENVIRONMENT', 'local')
ALLOWED_HOSTS = ['*'] if DEBUG else _list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
FRONTEND_URL = _env('FRONTEND_URL', 'http://localhost:4001').rstrip('/')
GIT_SHA = _env('GIT_SHA', 'unknown')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'backend',
    'accounts',
    'deals',
    'documents',
    'ai',  # jobs and the worker (slice 16); Claude from slice 18
    'intake',  # coverage, intent and the lines to quote (slice 11); the form from slice 39
    'census',  # import, matching, validation, rollups and CensusFacts (slice 12); the roster grid from slice 41
    'quotes',
    'questionnaire',  # the carrier forms (slice 42): Florida Blue 51+, Warner 51+, the SIIA disclosure; PDFs slice 43
    'commission',  # rates, splits, Producers & partners and Settings (slice 48); booking and the Book from slice 49
    'rfp',  # RfpRequest and asked_by_line (slice 26); the RFP tab from slices 44–46
    'proposals',
    'review',  # requests, client links and the tab's counts (slice 53); the portal from slice 54
    'golden',  # seed only, last in the chain (§3.3)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'backend.middleware.JsonGZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'
WSGI_APPLICATION = 'backend.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _env('DB_NAME', 'vantage2'),
        'USER': _env('DB_USER', 'vantage'),
        'PASSWORD': _env('DB_PASSWORD', 'vantage-dev'),
        'HOST': _env('DB_HOST', 'localhost'),
        'PORT': _env('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Storage and API timestamps are UTC; dates people see use the agency's zone (deals/clock.py).
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = True
AGENCY_TIME_ZONE = _env('AGENCY_TIME_ZONE', 'America/New_York')

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Uploaded and issued files: a Docker volume, never a folder inside the repository (§3.4).
MEDIA_ROOT = _env('MEDIA_ROOT', '/data/media')
MEDIA_URL = '/media-not-served/'
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
# One file per request, under Cloud Run's 32 MiB request limit (§3.5, E7, OQ24).
FILE_UPLOAD_MAX_BYTES = 30 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sign-in: Django sessions (§3.8). The CSRF cookie stays readable so the SPA can echo it.
SESSION_COOKIE_AGE = int(_env('SESSION_COOKIE_AGE', '43200'))
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL] + [f'https://{host}' for host in _list('ALLOWED_HOSTS') if host != '*']
LOGIN_URL = '/login'
if ENVIRONMENT == 'production':
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

EMAIL_HOST = _env('EMAIL_HOST')
EMAIL_PORT = int(_env('EMAIL_PORT') or 587)
EMAIL_HOST_USER = _env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = _env('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = _env('DEFAULT_FROM_EMAIL', 'no-reply@localhost')
EMAIL_BACKEND = (
    'django.core.mail.backends.smtp.EmailBackend'
    if EMAIL_HOST_USER
    else 'django.core.mail.backends.console.EmailBackend'
)

# Claude (plan.md §3.5, §10.3; slice 18). Empty key: no Claude, every AI door hides and nothing calls out (D26).
ANTHROPIC_API_KEY = _env('ANTHROPIC_API_KEY')
AI_MODEL = _env('AI_MODEL') or 'claude-sonnet-5-5'
# Effort per job kind that calls Claude, until the golden-deal trial sets them (D.6, OQ31).
AI_EFFORT = {
    'turn': _env('AI_EFFORT_TURN') or 'low',
    'read': _env('AI_EFFORT_READ') or 'high',
    'recheck': _env('AI_EFFORT_RECHECK') or 'high',
}
AI_READ_LIMIT_USD = _env('AI_READ_LIMIT_USD') or '3'  # a run's cost cap (D53)
AI_DEAL_BUDGET_USD = _env('AI_DEAL_BUDGET_USD') or '25'  # a deal's AI budget (D99)
# The sum of every Claude call this database has recorded may not pass it; unset: no cap (production).
AI_TOTAL_BUDGET_USD = _env('AI_TOTAL_BUDGET_USD')
AI_READ_PARALLEL = 4  # a read's ranges in flight at once (D51)
# On: Claude's reads leave out the pages the member-data screen flagged at upload; off, files are read whole (OQ22).
AI_MEMBER_DATA_SCREEN = _flag('AI_MEMBER_DATA_SCREEN')
# Jobs run in the worker service (`manage.py run_worker`, §3.4); tests run them inline, in the request (§3.5).
AI_JOBS_INLINE = False

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['accounts.auth.SessionAuth'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    # `ai_poll`: the AI state and job polls alone (useAiState every 2 s on two tabs, §3.5, E.6). The client portal's
    # four, kept per link (slice 54; review/portal/throttles.py): the anonymous rate never applies to it.
    'DEFAULT_THROTTLE_RATES': {
        'anon': '200/hour',
        'user': '5000/hour',
        'login': '10/minute',
        'ai_poll': '3600/hour',
        'portal_read': '300/hour',
        'portal_write': '3600/hour',
        'portal_poll': '600/hour',
        'portal_pin': '10/hour',
    },
    'UNAUTHENTICATED_USER': 'django.contrib.auth.models.AnonymousUser',
}

# Logging (§3.5): one console handler at WARNING; SDK loggers pinned (their DEBUG output carries document text).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler', 'level': 'WARNING'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        **{name: {'level': 'WARNING'} for name in ('anthropic', 'httpx', 'httpcore', 'httpx2', 'httpcore2')},
        **{
            name: {'level': 'INFO'}
            for name in (
                'accounts',
                'deals',
                'documents',
                'ai',
                'intake',
                'census',
                'quotes',
                'commission',
                'rfp',
                'proposals',
            )
        },
    },
}

# ---- Production: staging on Cloud Run and every release (slice 69; plan.md §11, §3.5) -------------------------------
# Inert locally: the dev stack keeps runserver, MEDIA_ROOT on the filesystem and its logs. On Cloud Run, Secret Manager
# passes DJANGO_SECRET_KEY, DB_PASSWORD, EMAIL_HOST_PASSWORD and ANTHROPIC_API_KEY in as environment variables.
# The built SPA (the root Dockerfile's `production` target): Django answers its index.html for every page path
# (backend/spa.py), and WhiteNoise serves its assets under /static/ beside the admin's (§11.2).
SPA_DIR = BASE_DIR / 'spa'
if SPA_DIR.is_dir():
    STATICFILES_DIRS = [SPA_DIR]
# pdf.js's worker is an .mjs module and must be typed as JavaScript (E.6); Vite's hashed assets are cached for good.
WHITENOISE_MIMETYPES = {'.mjs': 'text/javascript'}
WHITENOISE_IMMUTABLE_FILE_TEST = r'^/static/assets/[^/]+[.-][0-9A-Za-z_-]{8,12}\.\w+$'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
# Files: MEDIA_ROOT unless a bucket is named, then the private Cloud Storage bucket (backend/storage.py), whose Google
# libraries load only then. Objects take the bucket's IAM (uniform access, no ACL) and are never overwritten.
GS_BUCKET_NAME = _env('GS_BUCKET_NAME')
if GS_BUCKET_NAME:
    STORAGES['default'] = {
        'BACKEND': 'backend.storage.PrivateBucket',
        'OPTIONS': {'bucket_name': GS_BUCKET_NAME, 'default_acl': None, 'file_overwrite': False},
    }
# Cloud SQL (§11.2): Cloud Run mounts the instance's socket under /cloudsql/ when the service names the instance. A
# private-IP connection sets DB_HOST instead and verifies the server: DB_SSLMODE=verify-full, DB_SSLROOTCERT=<CA file>.
CLOUD_SQL_INSTANCE = _env('CLOUD_SQL_INSTANCE')
if CLOUD_SQL_INSTANCE:
    DATABASES['default'].update(HOST=f'/cloudsql/{CLOUD_SQL_INSTANCE}', PORT='')
if _env('DB_SSLMODE'):
    DATABASES['default']['OPTIONS'] = {'sslmode': _env('DB_SSLMODE')}
    if _env('DB_SSLROOTCERT'):
        DATABASES['default']['OPTIONS']['sslrootcert'] = _env('DB_SSLROOTCERT')
# Cloud Run names every service (K_SERVICE) and job (CLOUD_RUN_JOB); an instance's disk goes with it (checks.py E005).
ON_CLOUD_RUN = bool(_env('K_SERVICE') or _env('CLOUD_RUN_JOB'))
if ENVIRONMENT == 'production':
    after_security = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1
    MIDDLEWARE.insert(after_security, 'whitenoise.middleware.WhiteNoiseMiddleware')
    STORAGES['staticfiles'] = {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'}
    # Cloud Run ends TLS at Google's front end, which says so in X-Forwarded-Proto (§3.8).
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r'^api/health/$']
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Request logs and error reports drop the token paths (§3.5, §11.2); gunicorn's access log: backend/gunicorn_log.py.
    LOGGING['filters'] = {'token_paths': {'()': 'backend.logs.DropTokenPaths'}}
    LOGGING['handlers']['console']['filters'] = ['token_paths']

# ---- The PHI gate (slice 47; plan.md §11.4, §3.5, §3.8) --------------------------------------------------------------
# Microsoft 365 sign-in (the firm's Entra ID directory, OpenID Connect with PKCE: accounts/oidc.py), on once the app
# registration is named: the directory (tenant) id, the client id and the client secret (Secret Manager on Cloud Run).
# Entra sends the browser back to FRONTEND_URL + /api/auth/microsoft/callback/, the redirect URI registered with it.
# AUTH_OIDC_ISSUER names another OpenID provider in place of Entra's (a local stand-in); deploy checks want HTTPS.
AUTH_OIDC_TENANT_ID = _env('AUTH_OIDC_TENANT_ID').strip()
AUTH_OIDC_CLIENT_ID = _env('AUTH_OIDC_CLIENT_ID').strip()
AUTH_OIDC_CLIENT_SECRET = _env('AUTH_OIDC_CLIENT_SECRET').strip()
AUTH_OIDC_ISSUER = (
    _env('AUTH_OIDC_ISSUER').strip()
    or (f'https://login.microsoftonline.com/{AUTH_OIDC_TENANT_ID}/v2.0' if AUTH_OIDC_TENANT_ID else '')
).rstrip('/')
AUTH_OIDC = bool(AUTH_OIDC_ISSUER and AUTH_OIDC_CLIENT_ID and AUTH_OIDC_CLIENT_SECRET)
AUTH_OIDC_REDIRECT_URI = f'{FRONTEND_URL}/api/auth/microsoft/callback/'
# Username and password (the sign-in page's and Django admin's): turned off at the gate, so that MFA and offboarding
# live in Microsoft 365 (§11.4 item 3). Every session, a firm account's too, finds its user again only while the user
# is active, so turning someone off in Django admin ends their access at their next request (§3.8).
AUTH_PASSWORD_SIGNIN = _flag('AUTH_PASSWORD_SIGNIN', 'True')
AUTHENTICATION_BACKENDS = [
    *(['django.contrib.auth.backends.ModelBackend'] if AUTH_PASSWORD_SIGNIN else []),
    'accounts.firm.FirmAccounts',
]
# The PHI-gate switch, turned on last (§11.4 item 7): only then do the census, intake and questionnaire readers
# register (ai/registry.py; O.3.3). vantage.E006 refuses it in production before sign-in moved to Microsoft 365.
AI_PHI_READERS = _flag('AI_PHI_READERS')
