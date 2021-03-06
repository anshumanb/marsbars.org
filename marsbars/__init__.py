# -*- coding: utf-8 -*-

from flask import (Flask, render_template, send_from_directory,
                   Markup, url_for)
from flask_sqlalchemy import SQLAlchemy
import pytz


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

def league(slug, template):
    league = IndoorLeague.query.filter_by(slug=slug).first_or_404()
    return render_template(template,
            league=league)

def redirect(to):
    return render_template('redirect.html', to=url_for(to))

@app.route('/')
def index():
    return render_template('index.html', players=Player.query.filter(Player.active==True))

@app.route('/fixtures/')
def fixtures():
    matches = IndoorMatch.query.filter_by(result=None).order_by(
                    IndoorMatch.datetime.desc())
    return render_template('fixtures.html', matches=matches)

@app.route('/results/')
def results():
    matches = IndoorMatch.query.filter(db.not_(
                    IndoorMatch.result==None)).order_by(
                    IndoorMatch.datetime.desc())
    return render_template('results.html', matches=matches)

# Combining multiple routes into one function resulted in only
# one URL being frozen
@app.route('/2016/central-autumn/fixtures/')
def central_autumn_fixtures():
    return redirect('fixtures')

@app.route('/2016/super-league/fixtures/')
def super_league_fixtures():
    return redirect('fixtures')

@app.route('/2016/central-autumn/results/')
def central_autumn_results():
    return redirect('results')

@app.route('/2016/super-league/results/')
def super_league_results():
    return redirect('results')

@app.route('/stats/')
def stats():
    return redirect('profiles')

@app.route('/profiles/')
def profiles():
    return render_template('profiles.html',
            players=Player.query.filter(Player.active==True).order_by(Player.name))

@app.route('/<slug>/')
def player(slug):
    player = Player.query.filter_by(active=True, slug=slug).first_or_404()
    return render_template('player.html',
            player=player)

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

@app.template_filter('localtime')
def localtime(s):
    tz = pytz.timezone('Pacific/Auckland')
    utc = pytz.timezone('UTC')
    utc_time = s.replace(tzinfo=utc)
    # stftime format string might be Linux specific.
    date = utc_time.astimezone(tz).strftime('%d-%b')
    time = utc_time.astimezone(tz).strftime('%-I:%M%P').replace(':00','')
    return Markup(u'{} <span class="time">{}</span>'.format(date, time))


OUTS = ['ro', 'r', 'st', 's', 'lbw', 'lb', 'h', 'hw', 'm', 'c', 'b']

def calc_run(outcome, inhouse_league):
    if outcome in OUTS:
        result = -5
    elif 'w' in outcome or 'nb' in outcome or 'n' in outcome:
        additional = outcome.strip('nbw')
        result = 3 if 'w' in outcome  and inhouse_league else 2
        result += int(additional) if additional != '' else 0
    else:
        result = int(outcome)
    return result

class StatisticsMixin(object):
    @property
    def pships(self):
        return self.query.all()

    @property
    def innings(self):
        return len(self.pships)

    @property
    def partnership_runs(self):
        return reduce(lambda x, y: x+y.score, self.pships, 0)

    @property
    def skins_won(self):
        add_skins = lambda x, y: x + 1 if y.skin else x + 0
        return reduce(add_skins, self.pships, 0)

    @property
    def ave_partnership_runs(self):
        if self.innings == 0:
            return 0
        return float(self.partnership_runs) / self.innings


class PlayerBase(StatisticsMixin):
    def __init__(self, **kwargs):
        self.query = kwargs['query']


class PlayerLeague(PlayerBase):
    def __init__(self, **kwargs):
        super(PlayerLeague, self).__init__(**kwargs)
        league = kwargs['league']
        self.short_name = league.short_name
        self.slug = league.slug


class PlayerPartner(PlayerBase):
    def __init__(self, **kwargs):
        super(PlayerPartner, self).__init__(**kwargs)
        partner = kwargs['partner']
        self.name = partner.name
        self.slug = partner.slug


class Player(db.Model, StatisticsMixin):
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

    # Following stats per league and total
    # Line graph of -- partnership runs + team total percentage
    # Pie graph of partner preference + partner runs percentage: Favourite partner
    # For now, assumes each player only has one innings per match.
    #def matches(self):
    #    pass
    @property
    def pships(self):
        return self.partnerships.all()

    @property
    def leagues(self):
        leagues = []
        for league in IndoorLeague.query.all():
            query = self.partnerships.join(
                    IndoorInnings, IndoorMatch, IndoorLeague).order_by(
                    IndoorMatch.datetime).filter(
                    IndoorLeague.slug==league.slug)
            if query.count() > 0:
                leagues.append(PlayerLeague(league=league, query=query))
        return leagues

    def _calc_runs(self, deliveries):
        balls = [calc_run(d.outcome, d.over._is_central_inhouse())
                 for d in deliveries]
        return sum(balls)


    @property
    def runs_scored(self):
        return self._calc_runs(self.balls_faced.all())

    @property
    def detailed_innings(self):
        return len([i for i in self.partnerships.all() if i.has_over_detail()])

    @property
    def deliveries_faced(self):
        return self.balls_faced.count()

    @property
    def runs_ave(self):
        innings = self.detailed_innings
        return float(self.runs_scored)/innings if innings != 0 else 0

    @property
    def batting_strike_rate(self):
        balls = self.deliveries_faced
        return float(self.runs_scored)*100/balls if balls != 0 else 0

    @property
    def outs(self):
        return len([i for i in self.balls_faced.all() if i.outcome in OUTS])

    @property
    def sevens(self):
        return len([i for i in self.balls_faced.all()
                    if calc_run(i.outcome, False) >= 7])

    @property
    def bowling_economy(self):
        overs = self.num_overs_bowled
        return float(self.runs_conceded)/overs if overs != 0 else 0

    @property
    def wickets(self):
        return reduce(lambda x, y: x + y.wickets, self.overs_bowled.all(), 0)

    @property
    def num_overs_bowled(self):
        return self.overs_bowled.count()

    @property
    def runs_conceded(self):
        return reduce(lambda x, y: x + y.runs, self.overs_bowled.all(), 0)

    @property
    def wides(self):
        return reduce(lambda x, y: x + y.wides, self.overs_bowled.all(), 0)

    @property
    def no_balls(self):
        return reduce(lambda x, y: x + y.no_balls, self.overs_bowled.all(), 0)

    @property
    def partners(self):
        _ = []
        for p in self.partnerships.all():
            _.extend([q for q in p.members if q != self and q.active])
        unique_partners = set(_)
        partners = []
        for up in unique_partners:
            query = self.partnerships.join(Player, 'members').filter(
                    Player.id==up.id)
            partners.append(PlayerPartner(partner=up, query=query))
        return partners


class IndoorLeague(db.Model):
    __tablename__ = 'indoor_league'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    short_name = db.Column(db.String(255))
    year = db.Column(db.Integer)
    grade = db.Column(db.String(255))
    slug = db.Column(db.String(255))

    def __init__(self, name, short_name, year, grade, slug):
        self.name = name
        self.short_name = short_name
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

    @property
    def completed_matches(self):
        return self.matches.filter(db.not_(IndoorMatch.result==None))

    @property
    def upcoming_matches(self):
        return self.matches.filter_by(result=None)


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
    title = db.Column(db.String(255))
    result = db.Column(db.String(255))
    margin = db.Column(db.Integer)
    skins = db.Column(db.Integer)
    points = db.Column(db.Integer)

    def __init__(self, league, datetime, venue, court, opponent, result,
                 margin, skins, points, title=None):
        self.league = league
        self.datetime = datetime
        self.venue = venue
        self.court = court
        self.opponent = opponent
        self.title = title
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
    def title_slug(self):
        return self.title.lower().replace(' ', '-')

    @property
    def is_completed(self):
        return self.result is not None

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

    def has_over_detail(self):
        return self.overs.count() > 0

class IndoorOver(db.Model):
    __tablname__ = 'indoor_over'
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer)
    partnership_id = db.Column(db.Integer, db.ForeignKey('indoor_partnership.id'))
    partnership = db.relationship('IndoorPartnership',
                      backref=db.backref('overs',
                                order_by='IndoorOver.position',
                                lazy='dynamic'))
    bowler_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    bowler = db.relationship('Player',
                      backref=db.backref('overs_bowled',
                                lazy='dynamic'))

    def _detail(self):
        return map(lambda d: d.outcome, self.deliveries)

    def _is_central_inhouse(self):
        return self.partnership.innings.match.league.slug != 'super-league'

    @property
    def runs(self):
        total = 0
        for i in self._detail():
            total += calc_run(i, self._is_central_inhouse())
        return total

    @property
    def wickets(self):
        total = 0
        for i in self._detail():
            total += 1 if i in OUTS else 0
        return total

    def _calc_extras(self, extra):
        total = 0
        for i in self._detail():
            if extra in i and 'hw' not in i:
                total += 1
                additional = i.strip(extra)
                total += int(additional) if additional != '' else 0
        return total

    @property
    def wides(self):
        return self._calc_extras('w')

    @property
    def no_balls(self):
        return self._calc_extras('nb')

    def __init__(self, position, partnership, bowler):
        self.position = position
        self.partnership = partnership
        self.bowler = bowler


class IndoorBall(db.Model):
    __tablename__ = 'indoor_ball'
    id = db.Column(db.Integer, primary_key=True)
    over_id = db.Column(db.Integer, db.ForeignKey('indoor_over.id'))
    over = db.relationship('IndoorOver',
                      backref=db.backref('deliveries',
                                order_by='IndoorBall.position',
                                lazy='dynamic'))
    position = db.Column(db.Integer)
    batsman_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    batsman = db.relationship('Player',
                      backref=db.backref('balls_faced',
                                lazy='dynamic'))
    outcome = db.Column(db.String(5))

    def __init__(self, position, over, batsman, outcome):
        self.position = position
        self.over = over
        self.batsman = batsman
        self.outcome = outcome
