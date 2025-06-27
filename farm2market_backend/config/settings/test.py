"""
Test settings for Farm2Market platform.
"""
from .base import *

# Test database (PostgreSQL with in-memory fallback)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_farm2market_db',
        'USER': 'farm2market_user',
        'PASSWORD': 'farm2market_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'connect_timeout': 60,
        },
        'TEST': {
            'NAME': 'test_farm2market_db',
        }
    }
}

# Disable migrations for faster testing
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Test email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Test file storage
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'

# Test media settings
MEDIA_ROOT = '/tmp/test_media'
MEDIA_URL = '/test_media/'

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Test security settings
SECRET_KEY = 'test-secret-key-for-testing-only'
DEBUG = True
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Disable CSRF for API testing
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Test JWT settings
SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=1),
    'ROTATE_REFRESH_TOKENS': True,
})

# Test Celery settings
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Test rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Test security settings
MAX_FAILED_LOGIN_ATTEMPTS = 3
ACCOUNT_LOCKOUT_DURATION = 1  # 1 minute for testing
PASSWORD_MIN_LENGTH = 6

# Test performance settings
SLOW_QUERY_THRESHOLD = 0.5  # 500ms
CACHE_DEFAULT_TIMEOUT = 60  # 1 minute

# Test backup settings
BACKUP_DIR = '/tmp/test_backups'
BACKUP_RETENTION_DAYS = 1

# Disable external services for testing
EXTERNAL_SERVICES_HEALTH_CHECK = {}

# Test analytics settings
ANALYTICS_ENABLED = True

# Test notification settings
NOTIFICATIONS_ENABLED = True

# Test search settings
SEARCH_ENABLED = True

# Password hashers for faster testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Test middleware (remove some for faster testing)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Test apps
INSTALLED_APPS += [
    'django_extensions',
]

# Test REST framework settings
REST_FRAMEWORK.update({
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'TEST_REQUEST_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ]
})

# Test CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Test file upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # 1MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # 1MB

# Test internationalization
USE_I18N = False
USE_L10N = False
USE_TZ = True

# Test static files
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Test database connection settings
CONN_MAX_AGE = 0  # Don't persist connections during tests

# Test session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Test security headers (disabled for testing)
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False

# Test API versioning
API_VERSION = 'v1'

# Test pagination
REST_FRAMEWORK['PAGE_SIZE'] = 10

# Test throttling (reduced for testing)
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour',
    'user': '1000/hour',
    'login': '10/hour',
}

# Test search settings
SEARCH_RESULTS_PER_PAGE = 10

# Test notification settings
NOTIFICATION_BATCH_SIZE = 10

# Test analytics settings
ANALYTICS_BATCH_SIZE = 100

# Test monitoring settings
HEALTH_CHECK_TIMEOUT = 5

# Test backup settings
BACKUP_ENCRYPTION_KEY = 'test-encryption-key'

# Test performance monitoring
PERFORMANCE_MONITORING_ENABLED = True
QUERY_MONITORING_ENABLED = True

# Test feature flags
FEATURE_FLAGS = {
    'ADVANCED_SEARCH': True,
    'REAL_TIME_NOTIFICATIONS': True,
    'ANALYTICS_DASHBOARD': True,
    'PAYMENT_PROCESSING': False,  # Disabled for testing
    'SMS_NOTIFICATIONS': False,   # Disabled for testing
}

# Test environment
ENVIRONMENT = 'test'

print("🧪 Test settings loaded successfully!")
