from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from core import views as v
urlpatterns = [path('simulate/',v.simulate,name='simulate'),path('admin/',admin.site.urls),path('login/',auth.LoginView.as_view(),name='login'),path('logout/',auth.LogoutView.as_view(),name='logout'),path('',v.dashboard,name='dashboard'),path('transactions/',v.transactions,name='transactions'),path('transactions/<str:pk>/',v.detail,name='detail'),path('cases/',v.cases,name='cases'),path('cases/<int:pk>/',v.case_detail,name='case'),path('accounts/',v.accounts,name='accounts'),path('accounts/<str:pk>/',v.account,name='account'),path('algorithms/',v.algorithms,name='algorithms'),path('analysis/run/',v.run_analysis,name='run_analysis'),path('data/import/',v.import_data,name='import_data'),path('audit/',v.audit,name='audit'),path('export/',v.export,name='export')]
