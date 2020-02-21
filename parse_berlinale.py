#!/usr/bin/env python3
import bs4
import requests
import time
import json
import re
import sys


BASE_URL = 'https://www.berlinale.de'
URL = f'{BASE_URL}/en/programme/programme/berlinale-programme.html'
RE_FILM_ID = re.compile(r'film_id=(\d+)')
RE_COUNTRY_YEAR = re.compile(r'(.+?)\s+(\d{4})\s*')
RE_TCODE = re.compile(r'\d{4,8}')
YEAR = 2020
MONTHS = {'Feb': 2, 'Mar': 3}


def download_page(i):
    params = {
        'page': i,
        'film_nums': 377,
        'section_id': 0,
        'country_id': 0,
        'order_by': 1,
        'documentary': '',
        'screenings': 'efm_festival'
    }
    resp = requests.get(URL, params=params)
    if resp.status_code != 200:
        print(f'Failed: {resp.status_code} {resp.text}')
        return None
    return bs4.BeautifulSoup(resp.text, features='lxml')


def find_pages_count(text):
    return int(text.find('ul', class_='pagination').find('li', class_='pg__separator')
               .next_sibling.next_sibling.a.string)


def parse_movie_info(elem):
    movie = {}
    rows = elem.find_all('div', class_='row', recursive=False)

    image_wrap = rows[0].find('div', class_='fe__image-wrap')
    movie['image'] = BASE_URL + image_wrap.a.img.get('src')
    movie['section'] = image_wrap.find('span', class_='section-tag').text.strip()

    movie_link = rows[0].find('a', class_='film-title-wrap')
    movie['url'] = BASE_URL + movie_link.get('href')
    movie['id'] = int(RE_FILM_ID.search(movie['url']).group(1))
    movie['title'] = movie_link.find('h2', class_='ft__title').text.strip()
    other_title = movie_link.find('span', class_='ft__other-title')
    if other_title:
        movie['title2'] = other_title.text.strip()

    movie_meta = rows[0].find('div', class_='film-meta-wrap')
    for k in ('staff', 'country', 'lang', 'info', 'event'):
        tag = movie_meta.find('span', class_=k)
        if tag:
            movie[k] = tag.text.strip()
            if k == 'country':
                m = RE_COUNTRY_YEAR.match(movie[k])
                if m:
                    movie['country'] = m.group(1)
                    movie['year'] = int(m.group(2))
    taglen = movie_meta.find('span', class_='filmlength')
    if taglen:
        movie['length'] = int(taglen.text.strip().replace('’', ''))

    movie['description'] = rows[1].p.text.strip()
    return movie


def parse_screening(elem, movie):
    event = {'movie': movie}
    scr_day = elem.find('span', class_='scr__day').string.split()
    scr_time = elem.find('span', class_='scr__time').string.split(':')
    event['time'] = (f"{YEAR}-{MONTHS[scr_day[0]]:02d}-{int(scr_day[1]):02d}"
                     f"T{int(scr_time[0]):02d}:{int(scr_time[1]):02d}:00Z+01")
    info = elem.find('div', class_='scr__info')
    event['location'] = info.find('h3', class_='scr__location').string
    ev_info = info.find('p', class_='scr__info-icon')
    if ev_info:
        event['info'] = ev_info.string.strip()
    ev_code = info.find('p', class_='scr__code')
    if ev_code:
        event['ticket_code'] = RE_TCODE.search(ev_code.text).group()
    ical_link = info.find('a', class_='scr__ical')
    if ical_link:
        event['ical'] = ical_link.get('href')

    ticket = elem.find('a', class_='scr__ticket-btn')
    event['ticket_info'] = ticket.text.strip()
    if 'disabled' not in ticket['class']:
        event['ticket'] = ticket.get('href')
    return event


def parse_events(text, movies):
    events = []
    for entry in text.find_all('section', class_='film-entry'):
        movie = parse_movie_info(entry)
        movies[movie['id']] = movie
        for screening in entry.find_all('section', class_='screening'):
            event = parse_screening(screening, movie)
            events.append(event)
    return events


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Downloads Berlinale 2020 Program')
        print('Usage: {} <output.json>'.format(sys.argv[0]))
        sys.exit(1)

    events = []
    movies = {}
    pg1 = download_page(1)
    num_pages = find_pages_count(pg1)
    for page in range(num_pages):
        print(f'Page {page+1} of {num_pages}')
        if page > 0:
            text = download_page(page+1)
        else:
            text = pg1
        events.extend(parse_events(text, movies))
        time.sleep(1)
        break
    with open(sys.argv[1], 'w') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
