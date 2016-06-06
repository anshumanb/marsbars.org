# -*- coding: utf-8 -*-

from flask import Flask, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask import Markup


app = Flask(__name__, static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
# Get rid of annoying warning
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('assets/js', path)
@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('assets/css', path)
@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory('assets/img', path)


@app.route('/')
def index():
    return render_template('index.html', players=Player.query.filter(Player.active==True))

@app.route('/2016/<slug>/')
def league(slug):
    league = IndoorLeague.query.filter_by(slug=slug).first_or_404()
    return render_template('indoor_league.html',
            matches=league.matches,
            league=league)

@app.template_filter('last_name_initial')
def last_name_initial(s):
    name_parts = s.split()
    if len(name_parts) > 1:
        name_parts[-1] = name_parts[-1][0].upper() + '.'
        return ' '.join(name_parts)
    return s

@app.template_filter('negative')
def negative(s):
    return Markup(unicode(s).replace(u'-', u'<sup>−</sup>'))


class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    title = db.Column(db.String(255))
    slug = db.Column(db.String(255), unique=True)
    active = db.Column(db.Boolean)

    def __init__(self, name, title=None, slug=None, active=True):
        self.name = name
        self.slug = slug
        self.title = title
        self.active = active

    def __repr__(self):
        return '<Player {}>'.format(self.slug)

    @staticmethod
    def get(slug):
        return db.session.query(Player).filter_by(slug=slug).one()


class IndoorLeague(db.Model):
    __tablename__ = 'indoor_league'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    year = db.Column(db.Integer)
    grade = db.Column(db.String(255))
    slug = db.Column(db.String(255))

    def __init__(self, name, year, grade, slug):
        self.name = name
        self.year = year
        self.grade = grade
        self.slug = slug

    @staticmethod
    def get_by_human_id(human_id):
        year, _, slug = human_id.partition('-')
        return db.session.query(IndoorLeague).filter_by(
                year=int(year), slug=slug).one()

    def __repr__(self):
        return '<IndoorLeague {}-{}>'.format(self.year, self.name)

class IndoorMatch(db.Model):
    __tablename__ = 'indoor_match'
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('indoor_league.id'))
    league = db.relationship('IndoorLeague', backref=db.backref('matches',
                    order_by='desc(IndoorMatch.datetime)',
                    lazy='dynamic'))
    datetime = db.Column(db.DateTime)
    venue = db.Column(db.String(255))
    court = db.Column(db.Integer)
    opponent = db.Column(db.String(255))
    result = db.Column(db.String(255))
    margin = db.Column(db.Integer)
    skins = db.Column(db.Integer)
    points = db.Column(db.Integer)

    def __init__(self, league, datetime, venue, court, opponent, result,
                 margin, skins, points):
        self.league = league
        self.datetime = datetime
        self.venue = venue
        self.court = court
        self.opponent = opponent
        self.result = result
        self.margin = margin
        self.skins = skins
        self.points = points

    def __repr__(self):
        return '<IndoorMatch {}-{}-{}>'.format(self.league,
                self.opponent, self.venue)

    @property
    def score(self):
        return [innings.score for innings in self.innings]

    @property
    def is_completed(self):
        return True

    @property
    def has_partnerships(self):
        return self.innings.first().has_partnerships


class IndoorInnings(db.Model):
    __tablename__ = 'indoor_innings'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('indoor_match.id'))
    match = db.relationship('IndoorMatch', backref=db.backref('innings',
                    order_by='IndoorInnings.position',
                    lazy='dynamic'))
    position = db.Column(db.Integer)
    score = db.Column(db.Integer)
    us = db.Column(db.Boolean)

    def __init__(self, match, position, score, us=False):
        self.match = match
        self.position = position
        self.score = score
        self.us = us

    @property
    def has_partnerships(self):
        return not self.partnerships.count() == 0


player_indoor_partnership = db.Table('player_indoor_partnership', db.Model.metadata,
        db.Column('indoor_partnership', db.Integer, db.ForeignKey('indoor_partnership.id')),
        db.Column('player', db.Integer, db.ForeignKey('player.id')))

class IndoorPartnership(db.Model):
    __tablename__ = 'indoor_partnership'
    id = db.Column(db.Integer, primary_key=True)
    innings_id = db.Column(db.Integer, db.ForeignKey('indoor_innings.id'))
    innings = db.relationship('IndoorInnings',
                      backref=db.backref('partnerships',
                                order_by='IndoorPartnership.position',
                                lazy='dynamic'))
    members = db.relationship('Player',
                  secondary=player_indoor_partnership,
                  backref=db.backref('partnerships',
                            lazy='dynamic'))
    # Combination of innings and position should be unique
    position = db.Column(db.Integer)
    score = db.Column(db.Integer)
    skin = db.Column(db.Boolean)

    def __init__(self, innings, position, score, skin=False, members=[]):
        self.innings = innings
        self.position = position
        self.score = score
        self.members = members
        self.skin = skin

    def __repr__(self):
        return '<IndoorPartnership {}:{}>'.format(self.position, self.score)
