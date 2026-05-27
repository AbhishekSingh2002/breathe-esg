from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.emissions.views import EmissionRecordViewSet, DataSourceViewSet, OrganizationViewSet

# API Router
router = routers.DefaultRouter()
router.register(r'emissions', EmissionRecordViewSet, basename='emission')
router.register(r'data-sources', DataSourceViewSet, basename='datasource')
router.register(r'organizations', OrganizationViewSet, basename='organization')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]
