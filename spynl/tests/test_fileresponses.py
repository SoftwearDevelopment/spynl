import io

import openpyxl

from spynl.main.serial.file_responses import (
    export_csv,
    serve_csv_response,
    export_excel,
    serve_excel_response,
    export_header,
    export_data,
)


def test_export_csv(dummyrequest):
    data = [
        {'collection': 'spring', 'brand': 'G-Star', 'warehouse': 'abc'},
        {'collection': 'summer', 'brand': 'Diesel', 'warehouse': 'xyz'},
    ]

    header = ['warehouse', 'collection', 'brand']
    temp_file = export_csv(header, data)
    resp = serve_csv_response(dummyrequest.response, temp_file)
    assert resp.content_type == 'text/csv'
    assert resp.text == (
        'warehouse,collection,brand\r\nabc,spring,G-Star\r\nxyz,summer,Diesel\r\n'
    )


def test_export_excel(dummyrequest):
    data = [
        {'collection': 'spring', 'brand': 'G-Star', 'warehouse': 'abc'},
        {'collection': 'summer', 'brand': 'Diesel', 'warehouse': 'xyz'},
    ]

    header = ['warehouse', 'collection', 'brand']
    temp_file = export_excel(header, data)
    resp = serve_excel_response(dummyrequest.response, temp_file, 'filename.xlsx')
    assert resp.content_disposition == 'attachment; filename=filename.xlsx'
    assert (
        resp.content_type
        == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    ws = openpyxl.load_workbook(io.BytesIO(resp.app_iter.file.read())).active

    expexted = [[cell.value for cell in row] for row in ws.rows]

    assert expexted == [
        ['warehouse', 'collection', 'brand'],
        ['abc', 'spring', 'G-Star'],
        ['xyz', 'summer', 'Diesel'],
    ]


def test_export_header_sorting(request):
    data = [
        {'collection': 'spring', 'brand': 'G-Star', 'warehouse': 'abc'},
        {'collection': 'summer', 'brand': 'Diesel', 'warehouse': 'xyz'},
    ]
    reference = ['warehouse', 'b', 'collection', 'c', 'd', 'brand']
    sorted_header = export_header(data, reference=reference)
    assert sorted_header == ['warehouse', 'collection', 'brand']


def test_export_data_sorting(request):
    data = [
        {'collection': 'spring', 'brand': 'G-Star', 'warehouse': 'abc'},
        {'collection': 'summer', 'brand': 'Diesel', 'warehouse': 'xyz'},
    ]

    reference = ['warehouse', 'b', 'collection', 'c', 'd', 'brand']
    sorted_header = export_header(data, reference=reference)
    sorted_data = export_data(data, sorted_header)
    assert sorted_data == [['abc', 'spring', 'G-Star'], ['xyz', 'summer', 'Diesel']]
