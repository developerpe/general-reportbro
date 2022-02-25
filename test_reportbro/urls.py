from django.contrib import admin
from django.urls import path, include, re_path

from core.views import Index, exportUsersPDF

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', Index.as_view(), name='index'),
    path('report/', include(('report.urls', 'report'))),
    path('export_user_pdf/', exportUsersPDF, name='export_user')
]


