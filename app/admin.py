import fastapi_admin
from fastapi_admin.app import app as admin_app
from fastapi_admin.resources import ModelView
from fastapi_admin.widgets import fields

app = admin_app()

class TaxiOrderAdmin(ModelView):
    column_list = ["start_location", "end_location", "status"]
    form_columns = ["start_location", "end_location", "status"]

app.add_view(TaxiOrderAdmin)
