from marsbars import (db, Player, IndoorMatch,
        IndoorInnings, IndoorPartnership, IndoorLeague, IndoorOver,
        IndoorBall)
import yaml
import iso8601
import pytz
import glob
from sqlalchemy.orm.exc import NoResultFound


db.create_all()


def load_players(filename):
    with open(filename) as f:
        players = yaml.load(f)
    for player in players:
        db.session.add(Player(**player))
    db.session.commit()

def load_leagues(filename):
    with open(filename) as f:
        leagues = yaml.load(f)
    for league in leagues:
        db.session.add(IndoorLeague(**league))
    db.session.commit()


def unslugify(slug):
    return slug.replace('-', ' ').title()


def get_player(slug):
    try:
        player = Player.get(slug)
    except(NoResultFound):
        player = Player(name=unslugify(slug), slug=slug, active=False)
        db.session.add(player)
        db.session.commit()
    return player


def load_match(filename):
    print('Processing ' + filename + ' ...')
    with open(filename) as f:
        match = yaml.load(f)

    innings = match.pop('innings')
    # Store dates in UTC
    d = iso8601.parse_date(match['datetime'])
    match['datetime'] = d.astimezone(pytz.timezone('UTC'))
    match['league'] = IndoorLeague.get_by_human_id(match['league'])

    m = IndoorMatch(**match)
    db.session.add(m)

    for i, inning in enumerate(innings):
        inn = IndoorInnings(m, position=i, score=inning['score'],
                us=inning.get('us', False))
        db.session.add(inn)
        if 'partnerships' not in inning:
            continue
        for p, pship in enumerate(inning['partnerships']):
            members = []
            if 'members' in pship:
                members = map(lambda n: get_player(n), pship['members'])
            partnership = IndoorPartnership(
                    inn, position=p, score=pship['score'],
                    skin=pship.get('skin', False), members=members)
            db.session.add(partnership)
            if 'overs' in pship:
                for o, over in enumerate(pship['overs']):
                    indoor_over = IndoorOver(o, partnership, get_player(over['bowler']))
                    db.session.add(indoor_over)
                    for b, ball in enumerate(process_over(over)):
                        db.session.add(IndoorBall(b, indoor_over, **ball))

    db.session.commit()


def process_over(over):
    bat1 = get_player(over['batsman'][0]['name'])
    bat2 = get_player(over['batsman'][1]['name'])
    over_bat1 = over['batsman'][0]['over']
    over_bat2 = over['batsman'][1]['over']

    o = []
    for b1, b2 in zip(over_bat1.split(), over_bat2.split()):
        if b1 != '.' and b2 == '.':
            o.append({'outcome': b1, 'batsman': bat1})
        elif b1 == '.' and b2 != '.':
            o.append({'outcome': b2, 'batsman': bat2})
    return o


if __name__ == '__main__':
    load_players('data/players.yaml')
    load_leagues('data/leagues.yaml')
    for i in glob.glob('data/2016-*.yaml'):
        load_match(i)

