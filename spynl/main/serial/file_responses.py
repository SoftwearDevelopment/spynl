import csv
from io import StringIO
from tempfile import NamedTemporaryFile

from openpyxl import Workbook
from pyramid.response import FileIter


def export_header(data, reference):
    """Return the column names ordered as they are found in the reference."""
    return sorted(data[0], key=lambda i: reference.index(i))


def export_data(data, header):
    """
    Return the data as a 2 dimensional list.

    The inner lists are ordered according the header.
    """
    return [
        [row[k] for k in header]
        for row in data
    ]


def export_excel(header, data, response, filename):
    """Export the data as an excel attachment."""
    tmp = NamedTemporaryFile()
    wb = Workbook()
    ws = wb.active

    ws.append(header)
    for row in export_data(data, header):
        ws.append(row)

    wb.save(tmp.name)
    tmp.seek(0)

    return serve_excel_response(response, tmp, filename)


def serve_excel_response(response, file, filename):
    response.content_disposition = 'attachment; filename=%s' % filename
    response.content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.app_iter = FileIter(file)
    return response


def export_csv(header, data, response):
    """Export the data as csv as a string."""
    with StringIO() as tmp:
        writer = csv.DictWriter(tmp, fieldnames=header)
        writer.writeheader()
        writer.writerows(data)
        data = tmp.getvalue()

    return serve_csv_response(response, data)


def serve_csv_response(response, data):
    response.content_type = 'text/csv'
    response.text = data
    return response
