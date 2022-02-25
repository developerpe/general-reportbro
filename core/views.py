from django.shortcuts import render

from django.contrib.auth.models import User
from django.views.generic import TemplateView

from report.utils import convert_to_64
from report.report import report
from core.models import Person

class Index(TemplateView):
    template_name = "index.html"

def exportUsersPDF(request):
    users = User.objects.all()

    users_list = []
    for user in users:
        users_list.append({
            'name': user.first_name,
            'username': user.username
        })
    
    person = Person.objects.filter(id=1).first()
    data = {
        'users': users_list,
        'image': convert_to_64(person.image.url)
    }

    return report(request, 'users', data)
    