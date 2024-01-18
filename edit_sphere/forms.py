from wtforms import Form, HiddenField, SelectField, StringField
from wtforms.validators import DataRequired

from resources.datatypes import DATATYPE_MAPPING


class UpdateTripleForm(Form):
    subject = HiddenField('Subject')
    predicate = HiddenField('Predicate')
    old_value = HiddenField('Old Value')
    new_value = StringField('New Value', [DataRequired()])

class CreateTripleFormWithInput(Form):
    subject = HiddenField('Subject')
    predicate = StringField('Property', [DataRequired()])
    object = StringField('Value', [DataRequired()])

class CreateTripleFormWithSelect(Form):
    subject = HiddenField('Subject', validators=[DataRequired()])
    predicate = SelectField('Property', choices=[], validators=[DataRequired()])
    object = StringField('Value', [DataRequired()])