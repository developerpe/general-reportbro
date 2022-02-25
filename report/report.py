import datetime
import json
import uuid

from django.db.models import Sum
from django.http import HttpResponseBadRequest, HttpResponse, HttpResponseServerError
from django.shortcuts import render
from django.utils.safestring import SafeString
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import ensure_csrf_cookie

from reportbro import Report, ReportBroError
from timeit import default_timer as timer

from report.models import ReportDefinition, ReportRequest
from report.utils import create_base_report_template, json_default

# keep max. 1000 MB of generated pdf files in db
MAX_CACHE_SIZE = 1000 * 1024 * 1024


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
    return render(request, 'edit.html', context)


@xframe_options_exempt
def run(request):
    """Generates a report for preview.

    This method is called by ReportBro Designer when the Preview button is clicked,
    the url is defined when initializing the Designer, see *reportServerUrl*
    in edit.html
    """
    now = datetime.datetime.now()

    response = HttpResponse('')
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, PUT, OPTIONS'
    response['Access-Control-Allow-Headers'] =\
        'Origin, X-Requested-With, X-HTTP-Method-Override, Content-Type, Accept, Authorization, Z-Key'
    if request.method == 'OPTIONS':
        # options request is usually sent by browser for a cross-site request, we only need to set the
        # Access-Control-Allow headers in the response so the browser sends the following get/put request
        return response

    additional_fonts = []
    # add additional fonts here if additional fonts are used in ReportBro Designer

    if request.method == 'PUT':
        # all data needed for report preview is sent in the initial PUT request, it contains
        # the format (pdf or xlsx), the report itself (report_definition), the data (test data
        # defined within parameters in the Designer) and is_test_data flag (always True
        # when request is sent from Designer)
        json_data = json.loads(request.body.decode('utf-8'))
        if not isinstance(json_data, dict) or not isinstance(json_data.get('report'), dict) or\
                not isinstance(json_data.get('data'), dict) or not isinstance(json_data.get('isTestData'), bool):
            return HttpResponseBadRequest('invalid report values')

        output_format = json_data.get('outputFormat')
        if output_format not in ('pdf', 'xlsx'):
            return HttpResponseBadRequest('outputFormat parameter missing or invalid')

        report_definition = json_data.get('report')
        data = json_data.get('data')
        is_test_data = json_data.get('isTestData')
        try:
            report = Report(report_definition, data, is_test_data,
                            additional_fonts=additional_fonts)
        except Exception as e:
            return HttpResponseBadRequest('failed to initialize report: ' + str(e))

        if report.errors:
            # return list of errors in case report contains errors, e.g. duplicate parameters.
            # with this information ReportBro Designer can select object containing errors,
            # highlight erroneous fields and display error messages
            return HttpResponse(json.dumps(dict(errors=report.errors)))
        try:
            # delete old reports (older than 3 minutes) to avoid table getting too big
            ReportRequest.objects.filter(created_on__lt=(
                now - datetime.timedelta(minutes=3))).delete()

            total_size = ReportRequest.objects.aggregate(Sum('pdf_file_size'))
            if total_size['pdf_file_size__sum'] and total_size['pdf_file_size__sum'] > MAX_CACHE_SIZE:
                # delete all reports older than 10 seconds to reduce db size for cached pdf files
                ReportRequest.objects.filter(created_on__lt=(
                    now - datetime.timedelta(seconds=10))).delete()

            start = timer()
            report_file = report.generate_pdf()
            end = timer()
            print('pdf generated in %.3f seconds' % (end-start))

            key = str(uuid.uuid4())
            # add report request into sqlite db, this enables downloading the report by url
            # (the report is identified by the key) without any post parameters.
            # This is needed for pdf and xlsx preview.
            ReportRequest.objects.create(
                key=key,
                report_definition=json.dumps(
                    report_definition, default=json_default),
                data=json.dumps(data, default=json_default),
                is_test_data=is_test_data,
                pdf_file=report_file,
                pdf_file_size=len(report_file),
                created_on=now
            )

            return HttpResponse('key:' + key)
        except ReportBroError as err:
            # in case an error occurs during report generation a ReportBroError exception is thrown
            # to stop processing. We return this error within a list so the error can be
            # processed by ReportBro Designer.
            return HttpResponse(json.dumps(dict(errors=[err.error])))

    elif request.method == 'GET':
        output_format = request.GET.get('outputFormat')
        if output_format not in ('pdf', 'xlsx'):
            return HttpResponseBadRequest('outputFormat parameter missing or invalid')
        key = request.GET.get('key')

        report = None
        report_file = None
        if key and len(key) == 36:
            # the report is identified by a key which was saved
            # in a table during report preview with a PUT request
            try:
                report_request = ReportRequest.objects.get(key=key)
            except ReportRequest.DoesNotExist:
                return HttpResponseBadRequest('report not found (preview probably too old), update report preview and try again')
            if output_format == 'pdf' and report_request.pdf_file:
                # For POSTGRESQL
                # report_file = report_request.pdf_file.tobytes()
                # For SQLITE
                report_file = report_request.pdf_file
            else:
                report_definition = json.loads(
                    report_request.report_definition)
                data = json.loads(report_request.data)
                is_test_data = report_request.is_test_data
                report = Report(report_definition, data,
                                is_test_data, additional_fonts=additional_fonts)
                if report.errors:
                    return HttpResponseBadRequest(reason='error generating report')
        else:
            # in case there is a GET request without a key we expect all report data to be available.
            # this is NOT used by ReportBro Designer and only added for the sake of completeness.
            json_data = json.loads(request.body.decode('utf-8'))
            if not isinstance(json_data, dict) or not isinstance(json_data.get('report'), dict) or\
                    not isinstance(json_data.get('data'), dict) or not isinstance(json_data.get('isTestData'), bool):
                return HttpResponseBadRequest('invalid report values')
            report_definition = json_data.get('report')
            data = json_data.get('data')
            is_test_data = json_data.get('isTestData')
            if not isinstance(report_definition, dict) or not isinstance(data, dict):
                return HttpResponseBadRequest('report_definition or data missing')
            report = Report(report_definition, data, is_test_data,
                            additional_fonts=additional_fonts)
            if report.errors:
                return HttpResponseBadRequest(reason='error generating report')

        try:
            # once we have the reportbro.Report instance we can generate
            # the report (pdf or xlsx) and return it
            if output_format == 'pdf':
                if report_file is None:
                    # as it is currently implemented the pdf file is always stored in the
                    # report_request table along the other report data. Therefor report_file
                    # will always be set. The generate_pdf call here is only needed in case
                    # the code is changed to clear report_request.pdf_file column when the
                    # data in this table gets too big (currently whole table rows are deleted)
                    report_file = report.generate_pdf()
                response = HttpResponse(
                    report_file, content_type='application/pdf')
                response['Content-Disposition'] = 'inline; filename="{filename}"'.format(
                    filename='report-' + str(now) + '.pdf')
            else:
                report_file = report.generate_xlsx()
                response = HttpResponse(
                    report_file, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'inline; filename="{filename}"'.format(
                    filename='report-' + str(now) + '.xlsx')
            return response
        except ReportBroError:
            return HttpResponseBadRequest('error generating report')
    return None


def save(request, report_type):
    """Save report_definition in our db table.

    This method is called by save button in ReportBro Designer.
    The url is called in *saveReport* callback from the Designer,
    see *saveCallback* in edit.html
    """
    json_data = json.loads(request.body.decode('utf-8'))

    # perform some basic checks if all necessary fields for report_definition are present
    if not isinstance(json_data, dict) or not isinstance(json_data.get('docElements'), list) or\
            not isinstance(json_data.get('styles'), list) or not isinstance(json_data.get('parameters'), list) or\
            not isinstance(json_data.get('documentProperties'), dict) or not isinstance(json_data.get('version'), int):
        return HttpResponseBadRequest('invalid values')

    report_definition = json.dumps(dict(
        docElements=json_data.get('docElements'), styles=json_data.get('styles'),
        parameters=json_data.get('parameters'),
        documentProperties=json_data.get('documentProperties'), version=json_data.get('version')))

    now = datetime.datetime.now()
    if ReportDefinition.objects.filter(report_type=report_type).update(
            report_definition=report_definition, last_modified_at=now) == 0:
        ReportDefinition.objects.create(
            report_type=report_type,
            report_definition=report_definition,
            last_modified_at=now
        )
    return HttpResponse('ok')


def report(request, report_type, data):
    """Prints a pdf file with data"""

    # NOTE: these params must match exactly with the parameters defined in the
    # report definition in ReportBro Designer, check the name and type (Number, Date, List, ...)
    # of those parameters in the Designer.
    params = data

    if ReportDefinition.objects.filter(report_type=report_type).count() == 0:
        create_base_report_template()

    report_definition = ReportDefinition.objects.get(report_type=report_type)
    if not report_definition:
        return HttpResponseServerError('no report_definition available')

    try:
        report_inst = Report(json.loads(
            report_definition.report_definition), params)
        if report_inst.errors:
            # report definition should never contain any errors,
            # unless you saved an invalid report and didn't test in ReportBro Designer
            raise ReportBroError(report_inst.errors[0])

        pdf_report = report_inst.generate_pdf()
        response = HttpResponse(pdf_report, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="{filename}"'.format(
            filename='albums.pdf')
        return response
    except ReportBroError as ex:
        return HttpResponseServerError('report error: ' + str(ex.error))
    except Exception as ex:
        return HttpResponseServerError('report exception: ' + str(ex))
