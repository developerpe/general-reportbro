from django.urls import path

from report.report import *

urlpatterns = [
    path('edit/<str:report_type>/', edit, name='report_edit'),
    path('run/', run, name='report_run'),
    path('save/<str:report_type>/', save, name='report_save')
]