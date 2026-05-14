import os
from pathlib import Path
from decouple import config
from datetime import timedelta
import cloudinary

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['.vercel.app', '127.0.0.1']
AUTH_USER_MODEL = 'accounts.User'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'drf_yasg',
    'rest_framework_simplejwt.token_blacklist',
    'rest_framework_simplejwt',
    "debug_toolbar",
    "rest_framework",
    'djoser',
    'django_filters',
    'api',
    'battle',
    'accounts',
    'analytics',
    'courses',
    'enrollments',
    'quizzes',
    "cloudinary",
    "cloudinary_storage",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = 'Skiled_Engineer.urls'

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

WSGI_APPLICATION = 'Skiled_Engineer.wsgi.app'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': config('user'),
        'PASSWORD': config('DB_password'),
        'HOST': config('host'),
        'PORT': config('port')
    }
}


# config cloudinary
cloudinary.config( 
  cloud_name = config('Cloud_name'), 
  api_key = config('Cloudinary_API_Key'), 
  api_secret = config('API_Secret'),
  secure=True
)

#Media storage settings
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'


INTERNAL_IPS = [
    "127.0.0.1",
]

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_ROOT = BASE_DIR / "staticfiles"
# STATIC_FILES_DIR = BASE_DIR/'static'
STATICFIELS_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

REST_FRAMEWORK = {
    'COERCE_DECIMAL_TO_STRING': False,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

SIMPLE_JWT = {
   'AUTH_HEADER_TYPES': ('JWT',),
   'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
   'REFRESH_TOKEN_LIFETIME': timedelta(days=30), 
   'BLACKLIST_AFTER_ROTATION': True,              
   'UPDATE_LAST_LOGIN': True,
}

DJOSER = {
    'LOGIN_FIELD': 'email',
    'TOKEN_MODEL': None,                    
 
    # Email verification
    'SEND_ACTIVATION_EMAIL': True,
    'ACTIVATION_URL': 'activate/{uid}/{token}',
 
    # Password reset
    'SEND_PASSWORD_RESET_EMAIL': True,
    'PASSWORD_RESET_CONFIRM_URL': 'password/reset/confirm/{uid}/{token}',
 
    # Custom serializers
    'SERIALIZERS': {
        'user_create': 'accounts.serializers.RegisterSerializer',
        'current_user': 'accounts.serializers.ProfileSerializer',
        'user': 'accounts.serializers.ProfileUpdateSerializer',
    },
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Enter your JWT token in the format: `JWT <your_token>`'
        }
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')