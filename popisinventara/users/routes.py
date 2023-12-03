from flask import Blueprint
from flask import  render_template, url_for, flash, redirect, request, abort
from flask_login import login_user, login_required, logout_user, current_user
from flask_mail import Message
from popisinventara import bcrypt, db, mail
from popisinventara.users.forms import LoginForm, RequestResetForm, ResetPasswordForm
from popisinventara.models import Inventory, User



users = Blueprint('users', __name__)


@users.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'Dobro došli, {user.name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash(f'Email ili lozinka nisu odgovarajući.', 'danger')
    return render_template('login.html', title='Prijavljivanje', form=form, legend='Prijavljivanje')


@users.route("/user_list", methods=['GET', 'POST'])
def user_list():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za prikaz korisnika.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    users = User.query.all()
    number_of_admins = User.query.filter_by(authorization='admin').count()
    return render_template('user_list.html', 
                            users=users, 
                            number_of_admins=number_of_admins,
                            active_inventory_list=active_inventory_list)


@users.route("/register_user", methods=['GET', 'POST'])
def register_user():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za registraciju korisnika.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće registrovati nove korisnike dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    name = request.form.get('name').capitalize()
    surname = request.form.get('surname').capitalize()
    authorization = request.form.get('authorization')
    email = request.form.get('email')
    hashed_password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
    new_user = User(name=name, 
                    surname=surname, 
                    authorization=authorization, 
                    email=email, 
                    school_id=1, 
                    password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    flash(f'Korisnik {name} {surname} je uspešno registrovan!', 'success')
    return redirect(url_for('users.user_list'))


@users.route("/edit_user", methods=['GET', 'POST'])
def edit_user():
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće menjati podatke profila korisnika dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za izmene korisnika.', 'danger')
        return redirect(url_for('main.home'))
    user_id = request.form.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    user.name = request.form.get('edit_name').capitalize()
    user.surname = request.form.get('edit_surname').capitalize()
    user.email = request.form.get('edit_email')
    user.authorization = request.form.get('edit_authorization')
    db.session.commit()
    
    flash(f'Profil korisnika {user.name} {user.surname} je uspešno izmenjen', 'success')
    return redirect(url_for('users.user_list'))


@users.route("/delete_user", methods=['GET', 'POST'])
def delete_user():
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće brisati profil korisnika dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za brisanje korisnika.', 'danger')
        return redirect(url_for('main.home'))
    user_id = request.form.get('delete_user_id')
    user = User.query.filter_by(id=user_id).first()
    db.session.delete(user)
    db.session.commit()
    flash(f'Korisnik {user.name} {user.surname} je uspešno izbrisan!', 'success')
    return redirect(url_for('users.user_list'))


@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Zahtev za resetovanje lozinke', sender='noreply@uplatnice.online', recipients=[user.email])
    msg.body = f'''Da biste resetovali lozinku, kliknite na sledeći link:
{url_for('users.reset_token', token=token, _external=True)}

Ako Vi niste napavili ovaj zahtev, molim Vas ignorišite ovaj mejl i neće biti napravljene nikakve izmene na Vašem nalogu.
    '''
    mail.send(msg)


@users.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
        if current_user.is_authenticated:
            return redirect(url_for('main.home'))
        form = RequestResetForm()
        if form.validate_on_submit():
            user  = User.query.filter_by(email=form.email.data).first()
            send_reset_email(user)
            flash('Mejl je poslat na Vašu adresu sa instrukcijama za resetovanje lozinke. ', 'info')
            return redirect(url_for('users.login'))
        return render_template('reset_request.html', title='Resetovanje lozinke', form=form, legend='Resetovanje lozinke')


@users.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
        if current_user.is_authenticated:
            return redirect(url_for('main.home'))
        user = User.verify_reset_token(token)
        if user is None:
            flash('Ovo je nevažeći ili istekli token.', 'warning')
            return redirect(url_for('users.reset_request'))
        form = ResetPasswordForm()
        if form.validate_on_submit():
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user.user_password = hashed_password
            db.session.commit()
            flash(f'Vaša lozinka je ažurirana!', 'success')
            return redirect(url_for('users.login'))

        return render_template('reset_token.html', title='Resetovanje lozinke', form=form)
