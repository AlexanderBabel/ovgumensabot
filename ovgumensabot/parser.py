from datetime import datetime
from typing import List

import pytz
from bs4 import BeautifulSoup, ResultSet
from maubot import Plugin

from .meal import Meal
from .menu import Menu

TZ = pytz.timezone('Europe/Berlin')


async def get_menus(mensabot: Plugin, url: str) -> List:
    async with mensabot.http.get(url) as resp:
        page = await resp.text()
    mensabot.log.debug(page)
    soup = BeautifulSoup(page, 'html.parser')
    div_mensa = soup.find_all("div", class_="mensa")

    if div_mensa:
        menu_tables = div_mensa[0].find_all("table")
    else:
        return []

    menus = []
    for menu_table in menu_tables:
        mensabot.log.debug(f"mensa_table {menu_table}")
        menus.append(parse_table(menu_table))
    return menus


def parse_table(menu_table) -> Menu:
    date_string = menu_table.find("thead").find("tr").find("td").string.split(',')[1].strip()
    day = datetime.strptime(date_string, "%d.%m.%Y").date()
    meals = []
    for meal_element in menu_table.find("tbody").find_all("tr"):
        if "Beilagen:" in meal_element.find_all("td")[0].text:
            name = meal_element.find_all("td").pop(0).contents[0]
            price = meal_element.find_all("td").pop(0).contents.pop(4).string
        else:
            name = meal_element.find_all("td").pop(0).find("strong").contents.pop(0).string
            price = meal_element.find_all("td").pop(0).contents.pop(2).string
        meal = Meal(name=name, price=price)
        meals.append(meal)
    menu: Menu = Menu(day=day,
                      last_updated=datetime.now(TZ),
                      meals=meals)
    return menu


# parse hoersaal im dunkeln movie calendar
# https://www.unifilm.de/studentenkinos/MD_HiD
async def parse_movies(mensabot: Plugin, url: str) -> list[tuple[datetime, str]]:
    async with mensabot.http.get(url) as resp:
        page = await resp.text()
    # mensabot.log.debug(page)
    soup = BeautifulSoup(page, "html.parser")

    # locate calendar for current semester
    div_semester = soup.find("div", class_="kino-detail-spielplan spielplan-thisSemester")

    # locate all movies in current semester
    div_movie: List[BeautifulSoup] = div_semester.find_all("div", class_="semester-film-row")

    movies_dict = {}

    # for each movie locate date, time and title
    for movie in div_movie:
        date = movie.find("div", class_="film-row-text film-row-datum").text
        time = movie.find("div", class_="film-row-text film-row-uhrzeit").text
        date_time_str = f"{date.strip().split(' ', 1)[1]}-{time.split(' ', 1)[0]}"
        parsed_datetime: datetime = datetime.strptime(date_time_str, "%d.%m.%Y-%H:%M")
        # ignore space at the end of each title
        title = movie.find("div", class_="film-row-text film-row-titel").text.strip()

        movies_dict[parsed_datetime] = title

    return sorted(movies_dict.items())
