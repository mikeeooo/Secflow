from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path

from core import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth.LoginView.as_view(), name='login'),
    path('logout/', auth.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
    path('transactions/', views.transactions, name='transactions'),
    path('transactions/<str:pk>/', views.detail, name='detail'),
    path('monitor/dashboard/', views.dashboard_data, name='dashboard_data'),
    path('monitor/playback/', views.playback_control, name='playback_control'),
    path('metrics/', views.metrics_endpoint, name='metrics_endpoint'),
    path('monitor/status/', views.monitor_status, name='monitor_status'),
    path('analysis/status/<str:pk>/', views.analysis_status, name='analysis_status'),
    path('cases/', views.cases, name='cases'),
    path('cases/<int:pk>/', views.case_detail, name='case'),
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/<str:pk>/', views.account, name='account'),
    path('algorithms/', views.algorithms, name='algorithms'),
    path('analysis/run/', views.run_analysis, name='run_analysis'),
    path('data/import/', views.import_data, name='import_data'),
    path('simulate/', views.simulate, name='simulate'),
    path('audit/', views.audit, name='audit'),
    path('export/', views.export, name='export'),
]
