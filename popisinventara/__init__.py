import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
# from flask_mail import Mail
from flask_migrate import Migrate

load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db' #os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['FLASK_APP'] = 'run.py'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db, compare_type=True, render_as_batch=True)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from popisinventara.schools.routes import schools
from popisinventara.users.routes import users
from popisinventara.main.routes import main
from popisinventara.items.routes import item
from popisinventara.single_items.routes import single_items
from popisinventara.inventory.routes import inventory




app.register_blueprint(schools)
app.register_blueprint(users)
app.register_blueprint(main)
app.register_blueprint(item)
app.register_blueprint(single_items)
app.register_blueprint(inventory)
