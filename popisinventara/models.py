from popisinventara import app, db, login_manager
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class School(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schoolname = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(10), nullable=False)
    city = db.Column(db.String(20), nullable=False)
    municipality = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(20), nullable=False)
    mb = db.Column(db.String(20), nullable=False)
    jbkjs = db.Column(db.String(20), nullable=False)
    
    users = db.relationship('User', backref='user_school', lazy='dynamic')
    buildings = db.relationship('Building', backref='building_school', lazy='dynamic')

    def __repr__(self):
        return self.schoolname
    
    
class Building(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    name = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(50), nullable=False)
    rooms = db.relationship('Room', backref='room_building', lazy='dynamic')
    
    
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('building.id'), nullable=False)
    name = db.Column(db.String(20), nullable=False) # prostorija 101, prostorija 102, prostorija 103... prostorija 201, prostorija 202...
    dynamic_name = db.Column(db.String(50), nullable=False) # učionica I-1, učionica I-2... učionica II-1... kancelarija, biblioteka...
    single_items = db.relationship('SingleItem', backref='single_item_room', lazy='dynamic')
    

class Item(db.Model): #! ovo je tip predmeta
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    depreciation_rate_id = db.Column(db.Integer, db.ForeignKey('depreciation_rate.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    single_items = db.relationship('SingleItem', backref='single_item_item', lazy='dynamic')

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable = False)
    name = db.Column(db.String(20), unique=False, nullable=False)
    surname = db.Column(db.String(20), unique=False, nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id', ondelete='CASCADE'), nullable = True)
    
    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')
    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)


class DepreciationRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    rate = db.Column(db.Float(), nullable=False)
    items = db.relationship('Item', backref='item_depreciation_rate', lazy='dynamic')

class Category(db.Model): #! ovo je Konto
    id = db.Column(db.Integer, primary_key=True)
    category_number = db.Column(db.String(6), nullable=False) #! broj konta
    name = db.Column(db.String(50), nullable=False)
    items = db.relationship('Item', backref='item_category', lazy='dynamic')


class SingleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(50), nullable=False)
    inventory_number = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    initial_price = db.Column(db.Float(), nullable=False)
    current_price = db.Column(db.Float(), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    purchase_date = db.Column(db.Date(), nullable=False)


class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    date = db.Column(db.Date(), nullable=False)
    initial_data = db.Column(db.Text(), nullable=False)
    working_data = db.Column(db.Text(), nullable=False)
    status = db.Column(db.String(20), nullable=False) #! ideja je da se odrede statusi: u toku, završen


db.create_all()