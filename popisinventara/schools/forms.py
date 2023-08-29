from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired
from popisinventara.models import School
from wtforms import SelectField


class EditSchoolForm(FlaskForm):
    schoolname = StringField('Naziv škole')
    address = StringField('Adresa')
    zip_code = StringField('Poštanski broj')
    city = StringField('Mesto')
    municipality = StringField('Opština')
    country = StringField('Država')
    mb = StringField('MB')
    jbkjs = StringField('JBKJS')
    submit = SubmitField('Sačuvajte')
    
    
class AddNewBuildingForm(FlaskForm):
    name = StringField('Naziv objekta', validators=[DataRequired()])
    address = StringField('Adresa', validators=[DataRequired()])
    city = StringField('Mesto', validators=[DataRequired()])
    submit = SubmitField('Dodajte novu zgradu')


class EditNewBuildingForm(FlaskForm):
    name = StringField('Naziv objekta', validators=[DataRequired()])
    address = StringField('Adresa', validators=[DataRequired()])
    city = StringField('Mesto', validators=[DataRequired()])
    submit = SubmitField('Sačuvajte')


class AddNewRoomForm(FlaskForm):
    name = StringField('Naziv prostorije', validators=[DataRequired()])
    dynamic_name = StringField('Naziv prostorije (dinamički)')
    building_id = SelectField('ID zgrade', validators=[DataRequired()])
    submit = SubmitField('Dodajte novu sobu')


class EditNewRoomForm(FlaskForm):
    name = StringField('Naziv prostorije', validators=[DataRequired()])
    dynamic_name = StringField('Naziv prostorije (dinamički)')
    building_id = SelectField('ID zgrade', validators=[DataRequired()])
    submit = SubmitField('Dodajte novu sobu')