# Este proyecto pertenece al vídeo: https://youtu.be/cICZ5H-I6WU

# General ReportBro

Este proyecto es una generalización del ejemplo dado por el proyecto [ReportBro](https://www.reportbro.com/home/index) para el uso de esta librería, puedes ver el ejemplo original en: [AlbumApp](https://github.com/jobsta/albumapp-django)

### Configuración Inicial

Este proyecto include migraciones inciales que puedes ver en el Taller, además incluye una SQLITE DB con data de ejemplo.
This project include default migrations that you can see on the course, also include a SQLITE DB with example data. 

1.- Clona el repositorio:

                        git clone https://github.com/developerpe/general-reportbro

2.- Crea un entorno virtual :

                                 virtualenv name_env

3.- Activa el entorno.

4.- Instala las librerías necesarias.

                    (env) pip install -r requirements.txt 

5.- Copia la aplicación report a tu proyecto.

6.- Agrega la aplicación report a tu INSTALLED_APPS:

```
    INSTALLED_APPS = [
        ...
        'report',
        ...
    ]
```

7.- Incluye las URLS de la aplicación report a tu proyecto:

```
    ...
    path('report/', include(('report.urls', 'report'))),
```

8.- Agrega los archivos index.html y edit.html a tu proyecto, si los colocarás dentro de otra carpeta, edita la funcion **edit** del archivo report de la aplicación report.

```
@ensure_csrf_cookie
def edit(request, report_type):
    """Shows a page with ReportBro Designer to edit our objects report template."""
    context = dict()
    if ReportDefinition.objects.filter(report_type=report_type).count() == 0:
        create_base_report_template(report_type)

    # load ReportBro report definition stored in our report_definition table
    row = ReportDefinition.objects.get(report_type=report_type)
    context['report_type'] = report_type
    context['report_definition'] = SafeString(row.report_definition)
    return render(request, template, context)
```

9.- El template **index.html** debe contener el mismo contenido de este repositorio para que pueda funcionar el template **edit.html**

10.- Inspeccina el template **index.html** y observa estas URLS:

```
    <!-- Reeplace tag with your tags: person is an example -->
    <a href="/">Inicio</a>
    <!-- Example -->
    <a href=" {% url 'report:report_edit' 'person' %} ">Personas</a>
    <a href=" {% url 'report:report_edit' 'tag' %} ">Usuarios</a>
```

Reemplaza **person** por el tag que desees asociar para generar un lienzo en blanco para diseñar tu PDF, los tag son únicos y para cada nuevo tag se genera un registro en la BD, siempre se verifica si existe ya el tag, en caso existir, se carga el diseño ya definido.

Para mas información o un vistazo a como funciona o como se genera todo, revisar el vídeo: https://youtu.be/cICZ5H-I6WU

11.- Crea tu vista para obtener la data necesaria para exportar el diseño que haz realizado de tu PDF, aquí tienes un ejemplo.

Recuerda que debes enviar un Diccionario que contenga las variables tal cual las has nombrado en tu diseño de PDF, debes visualizar el tutorial o taller para que lo puedas entender mejor.

En caso desees enviar una **imagen** al PDF debes realizar un conversión a base64 de la misma, tal como se muestra en esta vista de ejemplo, de cualquier forma te dejo el código de la función **convert_to_64()** que realiza esta función.

```
def exportUsersPDF(request):
    """Example of ExportPDF"""
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


def convert_to_64(path):
    # converto image to base64
    
    import base64

    from django.conf import settings

    with open(str(settings.BASE_DIR) + path, "rb") as image_file:
        return f"data:image/png;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"

```


---

Si quieres apoyar realizando una donación, puedes hacerla a este enlace:

- [Donación al Proyecto](https://www.paypal.com/paypalme/oliversando)

## Redes Sociales

[Web](http://www.developerpe.com)

[Facebook](https://www.facebook.com/developerper​)

[Instagram](https://www.instagram.com/developer.pe/​)

[Twitter](https://twitter.com/Developerpepiur​)

[Youtube](Developer.pe)

**Correo: developerpeperu@gmail.com**