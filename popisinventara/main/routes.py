from flask import Blueprint
from flask import  render_template, flash, redirect, url_for
from flask_login import current_user
from popisinventara.models import Inventory, SingleItem
# import requests

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
def home():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    virtual_warehouse = SingleItem.query.filter_by(room_id=1).count()
    print(f'{virtual_warehouse=}')
    weather_data = get_weather_forecast("Gornji Milanovac", "Srbija")
    print(f'{weather_data=}')
    return render_template('home.html', title='Početna strana',
                            active_inventory_list=active_inventory_list,
                            virtual_warehouse=virtual_warehouse)


@main.route("/about")
def about():
    return render_template('about.html', title='About')


# def get_weather_forecast(city, country):
#     """
#     Dobija vremensku prognozu za dati grad i zemlju.

#     Args:
#         city: Grad za koji se dobija vremenska prognoza.
#         country: Zemlja za koju se dobija vremenska prognoza.
#         api_key: API ključ za OpenWeatherMap.

#     Returns:
#         Vremenska prognoza za dati grad i zemlju.
#     """

#     url = "https://api.openweathermap.org/data/2.5/weather?q={city},{country}&appid={api_key}".format(
#         city=city,
#         country=country,
#         api_key='e4ebf2e69926051f34ffc7798fc5d717',
#     )

#     response = requests.get(url)

#     if response.status_code == 200:
#         data = response.json()

#         return {
#             "temperature": data["main"]["temp"],
#             "humidity": data["main"]["humidity"],
#             "pressure": data["main"]["pressure"],
#             "wind_speed": data["wind"]["speed"],
#             "weather_description": data["weather"][0]["description"],
#         }
#     else:
#         return None



