from popisinventara import app, db, login_manager
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from sqlalchemy.ext.hybrid import hybrid_property

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class School(db.Model):
    """Model škole sa osnovnim informacijama i vezama ka drugim tabelama."""
    __tablename__ = 'school'
    
    id = db.Column(db.Integer, primary_key=True)
    schoolname = db.Column(db.String(50), unique=True, nullable=False)
    address = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(10), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    municipality = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    mb = db.Column(db.String(20), nullable=False)
    jbkjs = db.Column(db.String(20), nullable=False)
    settings_show_quantity = db.Column(db.Boolean, nullable=False, default=False)
    use_legacy_system = db.Column(db.Boolean, nullable=False, default=True)  # Flag za stari/novi sistem
    
    # Relacije
    users = db.relationship('User', back_populates='school', cascade='all, delete-orphan')
    buildings = db.relationship('Building', back_populates='school', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<School {self.schoolname}>'

class Building(db.Model):
    """Model zgrade sa osnovnim informacijama i vezama."""
    __tablename__ = 'building'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    
    # Relacije
    school = db.relationship('School', back_populates='buildings')
    rooms = db.relationship('Room', back_populates='building', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Building {self.name}>'

class Room(db.Model):
    """Model prostorije sa vezama ka zgradi i predmetima."""
    __tablename__ = 'room'
    
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('building.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    dynamic_name = db.Column(db.String(50), nullable=False)
    
    # Relacije
    building = db.relationship('Building', back_populates='rooms')
    single_items = db.relationship('SingleItem', back_populates='room', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Room {self.name} ({self.dynamic_name})>'

class Item(db.Model):
    """Legacy model tipa predmeta - zadržan zbog kompatibilnosti."""
    __tablename__ = 'item'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    depreciation_rate_id = db.Column(db.Integer, db.ForeignKey('depreciation_rate.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    
    # Relacije
    depreciation_rate = db.relationship('DepreciationRate', back_populates='items')
    category = db.relationship('Category', back_populates='items')
    single_items = db.relationship('SingleItem', 
                                 back_populates='item', 
                                 foreign_keys='SingleItem.item_id')

    def __repr__(self):
        return f'<Item {self.name}>'

class User(UserMixin, db.Model):
    """Model korisnika sa autentifikacijom."""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    name = db.Column(db.String(20), nullable=False)
    surname = db.Column(db.String(20), nullable=False)
    authorization = db.Column(db.String(20), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id', ondelete='CASCADE'), nullable=True)
    
    # Relacije
    school = db.relationship('School', back_populates='users')

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

    def __repr__(self):
        return f'<User {self.email}>'

class DepreciationRate(db.Model):
    """Model stope amortizacije."""
    __tablename__ = 'depreciation_rate'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rate = db.Column(db.Float(), nullable=False)
    
    # Relacije
    items = db.relationship('Item', back_populates='depreciation_rate')
    single_items = db.relationship('SingleItem', 
                                    back_populates='depreciation_rate',
                                    foreign_keys='SingleItem.depreciation_rate_id')

    def __repr__(self):
        return f'<DepreciationRate {self.name}>'

class Category(db.Model):
    """Model konta."""
    __tablename__ = 'category'
    
    id = db.Column(db.Integer, primary_key=True)
    category_number = db.Column(db.String(6), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    # Relacije
    items = db.relationship('Item', back_populates='category')
    single_items = db.relationship('SingleItem', 
                                    back_populates='category',
                                    foreign_keys='SingleItem.category_id')
    
    def __repr__(self):
        return f'<Category {self.category_number}>'

class SingleItem(db.Model):
    """Model pojedinačnog predmeta sa podrškom za stari i novi sistem."""
    __tablename__ = 'single_item'
    
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(50), nullable=False)
    inventory_number = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    supplier = db.Column(db.String(50), nullable=True)
    invoice_number = db.Column(db.String(50), nullable=True)
    initial_price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    current_price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    expediture_price = db.Column(db.Numeric(precision=10, scale=2), nullable=True)
    input_in_app_date = db.Column(db.Date, nullable=True)
    deprecation_value = db.Column(db.Numeric(precision=10, scale=2), nullable=True)
    purchase_date = db.Column(db.Date, nullable=False)
    expediture_date = db.Column(db.Date, nullable=True)
    reverse_person = db.Column(db.String(50), nullable=True)
    reverse_date = db.Column(db.Date, nullable=True)
    
    # Veza za stari sistem
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=True)
    
    # Veze za novi sistem
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    depreciation_rate_id = db.Column(db.Integer, db.ForeignKey('depreciation_rate.id'), nullable=True)
    
    # Relacije
    room = db.relationship('Room', back_populates='single_items')
    item = db.relationship('Item', back_populates='single_items', foreign_keys=[item_id])
    category = db.relationship('Category', back_populates='single_items', foreign_keys=[category_id])
    depreciation_rate = db.relationship('DepreciationRate', back_populates='single_items', foreign_keys=[depreciation_rate_id])

    @hybrid_property
    def effective_category_id(self):
        """Vraća category_id iz novog ili starog sistema u zavisnosti od podešavanja škole."""
        if hasattr(self, '_effective_category_id'):
            return self._effective_category_id
        
        if self.room and self.room.building and self.room.building.school:
            if self.room.building.school.use_legacy_system:
                return self.item.category_id if self.item else None
            return self.category_id
        return self.category_id

    @hybrid_property
    def effective_depreciation_rate_id(self):
        """Vraća depreciation_rate_id iz novog ili starog sistema u zavisnosti od podešavanja škole."""
        if hasattr(self, '_effective_depreciation_rate_id'):
            return self._effective_depreciation_rate_id
        
        if self.room and self.room.building and self.room.building.school:
            if self.room.building.school.use_legacy_system:
                return self.item.depreciation_rate_id if self.item else None
            return self.depreciation_rate_id
        return self.depreciation_rate_id

    def __repr__(self):
        return f'<SingleItem {self.inventory_number}>'

class Inventory(db.Model):
    """Model popisa."""
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    date = db.Column(db.Date, nullable=False)
    initial_data = db.Column(db.Text, nullable=False)
    working_data = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<Inventory {self.id} ({self.status})>'


# @login_manager.user_loader
# def load_user(user_id):
#     return User.query.get(int(user_id))


# class School(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     schoolname = db.Column(db.String(50), unique=True, nullable=False)
#     address = db.Column(db.String(50), nullable=False)
#     zip_code = db.Column(db.String(10), nullable=False)
#     city = db.Column(db.String(50), nullable=False)
#     municipality = db.Column(db.String(50), nullable=False)
#     country = db.Column(db.String(50), nullable=False)
#     mb = db.Column(db.String(20), nullable=False)
#     jbkjs = db.Column(db.String(20), nullable=False)
#     settings_show_quantity = db.Column(db.Boolean, nullable=False, default=False)
    
#     users = db.relationship('User', backref='user_school', lazy='dynamic')
#     buildings = db.relationship('Building', backref='building_school', lazy='dynamic')

#     def __repr__(self):
#         return self.schoolname
    
    
# class Building(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
#     name = db.Column(db.String(50), nullable=False)
#     address = db.Column(db.String(50), nullable=False)
#     city = db.Column(db.String(50), nullable=False)
#     rooms = db.relationship('Room', backref='room_building', lazy='dynamic')
    
    
# class Room(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     building_id = db.Column(db.Integer, db.ForeignKey('building.id'), nullable=False)
#     name = db.Column(db.String(50), nullable=False) # prostorija 101, prostorija 102, prostorija 103... prostorija 201, prostorija 202...
#     dynamic_name = db.Column(db.String(50), nullable=False) # učionica I-1, učionica I-2... učionica II-1... kancelarija, biblioteka...
#     single_items = db.relationship('SingleItem', backref='single_item_room', lazy='dynamic')
    

# class Item(db.Model): #! ovo je tip predmeta
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50), nullable=False)
#     depreciation_rate_id = db.Column(db.Integer, db.ForeignKey('depreciation_rate.id'), nullable=False)
#     category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
#     single_items = db.relationship('SingleItem', backref='single_item_item', lazy='dynamic')

# class User(db.Model, UserMixin):
#     id = db.Column(db.Integer, primary_key=True)
#     email = db.Column(db.String(120), unique=True, nullable=False)
#     password = db.Column(db.String(60), nullable = False)
#     name = db.Column(db.String(20), unique=False, nullable=False)
#     surname = db.Column(db.String(20), unique=False, nullable=False)
#     authorization = db.Column(db.String(20), unique=False, nullable=False)
#     school_id = db.Column(db.Integer, db.ForeignKey('school.id', ondelete='CASCADE'), nullable = True)
    
#     def get_reset_token(self, expires_sec=1800):
#         s = Serializer(app.config['SECRET_KEY'], expires_sec)
#         return s.dumps({'user_id': self.id}).decode('utf-8')
#     @staticmethod
#     def verify_reset_token(token):
#         s = Serializer(app.config['SECRET_KEY'])
#         try:
#             user_id = s.loads(token)['user_id']
#         except:
#             return None
#         return User.query.get(user_id)


# class DepreciationRate(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     rate = db.Column(db.Float(), nullable=False)
#     items = db.relationship('Item', backref='item_depreciation_rate', lazy='dynamic')

# class Category(db.Model): #! ovo je Konto
#     id = db.Column(db.Integer, primary_key=True)
#     category_number = db.Column(db.String(6), nullable=False) #! broj konta
#     name = db.Column(db.String(100), nullable=False)
#     items = db.relationship('Item', backref='item_category', lazy='dynamic')


# class SingleItem(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     serial = db.Column(db.String(50), nullable=False)
#     inventory_number = db.Column(db.String(50), nullable=False)
#     name = db.Column(db.String(50), nullable=False)
#     supplier = db.Column(db.String(50), nullable=True)
#     invoice_number = db.Column(db.String(50), nullable=True)
#     initial_price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
#     current_price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
#     expediture_price = db.Column(db.Numeric(precision=10, scale=2), nullable=True)
#     input_in_app_date = db.Column(db.Date(), nullable=True) #! datum unosa u aplikaciju
#     deprecation_value = db.Column(db.Numeric(precision=10, scale=2), nullable=True) #! vrednost otpisa koju je škola dala kao input
#     purchase_date = db.Column(db.Date(), nullable=False)
#     expediture_date = db.Column(db.Date(), nullable=True)
#     reverse_person = db.Column(db.String(50), nullable=True)
#     reverse_date = db.Column(db.Date(), nullable=True)
#     room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
#     item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)


# class Inventory(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     description = db.Column(db.String(500), nullable=False)
#     date = db.Column(db.Date(), nullable=False)
#     initial_data = db.Column(db.Text(), nullable=False)
#     working_data = db.Column(db.Text(), nullable=False)
#     status = db.Column(db.String(20), nullable=False) #! ideja je da se odrede statusi: u toku, završen


db.create_all()