from django.contrib import admin
from django.urls import (
    include,
    path,
)
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from main.settings import VERSION
from rest_framework.permissions import AllowAny

# Schema view settings.
schema_view = get_schema_view(
    openapi.Info(
        title="DJANGO MLOPS DOCKER API",
        default_version=VERSION,
        description="Django API adaptation. (MLOps, TFLite, Hdf5Json, Pipeline...)",
        terms_of_service="https://github.com/Nouvellie/django-tflite/blob/main/readme.md",
        contact=openapi.Contact(email="roberto.rocuantv@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    # url="https://nouvellie.django", # Swagger schema will be https.
    public=True,
    permission_classes=(AllowAny,),
)


urlpatterns = [

    # Admin:
    path('nouve-admin/', admin.site.urls),

    # Core app:
    path(
        '',
        include('apps.core.urls'),
    ),

    # Apps:
    path(
        'mlops/',
        include('apps.mlops.urls'),
    ),

    path(
        'auth/',
        include('apps.authentication.urls'),
    ),

    # Swagger:
    path(
        'swagger',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema_swagger_ui'
    ),
    path(
        'swagger/apis.json',
        schema_view.without_ui(cache_timeout=0),
        name='schema_swagger_ui'
    ),
    path(
        'docs',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema_redoc'
    ),
]

handler404 = 'main.exceptions.http_404_not_found'
handler500 = 'main.exceptions.http_500_internal_server_error'