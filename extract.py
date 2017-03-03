import argparse
import os.path
from lxml import html
import yaml
from collections import OrderedDict


NAME_FIXES = {
    'sai-ganesh': 'sai-karnan',
    'brendon-raj': 'brendan-raj',
    'neil-unknown': 'anshuman-bhaduri',
    'jared-mascherenas': 'jared-mascarenhas',
    'daz-goonatilaka': 'dasith-goonatilaka',
    'daz-unknown': 'dasith-goonatilaka',
    'yohan-unknown': 'yohan',
    'chirag-unknown': 'chirag-ahuja',
    'kanish-unknown': 'kanishk-vaddiraju',
    'daniel-unknown': 'daniel-brown',
    'shovik-unknown': 'shovik-nandi',
    'nish-unknown': 'nishant-dogra',
    'rohan-unknown': 'rohan-kundu',
    'musa-unknown': 'musa-alam',
    'mouse-unknown': 'musa-alam',
    'jas-unknown': 'jaskirat-banipal',
    'gurpreet-unknown': 'gurpreet',
    'varun-unknown': 'varun-patel',
    'tej-unknown': 'tejpal-singh',
}

def fix_player_slug(name):
    return NAME_FIXES.get(name, name)


def slugify(name):
    name = name.lower().strip().replace(' ', '-')
    return fix_player_slug(name)


class Bowler(object):
    def __init__(self, name, deliveries):
        self.name = name
        self.deliveries = deliveries


class Batsman(object):
    def __init__(self, el_row):
        self.row = el_row

    @property
    def name(self):
        return self.row.xpath('./td[1]')[0].text_content()

    def get_deliveries(self, start, end):
        over_sel = './td[@class="BallCell" or @class="extraBall"]'
        return map(lambda e: e.text_content(),
                        self.row.xpath(over_sel)[start:end])


class Innings(object):
    def __init__(self, el_section):
        self.el = el_section

    def get_batsman(self, batsman):
        batsman_sel = './/tr[@class="BallRow"]'
        return Batsman(self.el.xpath(batsman_sel)[batsman])

    def get_bowlers(self, partnership):
        bowler_sel = './/tr[td[@class="OverNo"]][{}]/td[@class="Bwl"]'.format(
                            partnership)
        return map(lambda e: Bowler(e.text_content(),
                        int(e.get('colspan'))),
                        self.el.xpath(bowler_sel))


class Compat(object):
    """ Provides extra scorecard information so that existing code can
        continue working as before.
        Points, skins and margin are unused so leave them out."""
    team_sel = './/table[@class="Summary"]//tr[not(@class="SummaryTitle")][{}]/td'
    def __init__(self, results):
        self.results = results

    def team_score(self, team_num):
        sel = self.team_sel.format(team_num)
        return int(self.results.xpath(sel)[5].text_content().partition(' (')[0])

    def _is_us(self, team_name):
        return 'Mars Bars' in team_name or 'Central Black' in team_name

    def add_us(self, team_name, innings):
        if self._is_us(team_name):
            innings['us'] = True
        return innings

    def partnership_score(self, innings_num, pship_num):
        sel = self.team_sel.format(innings_num)
        return int(self.results.xpath(sel)[pship_num].text_content())

    def result(self):
        team1_name = self.results.xpath(self.team_sel.format(1))[0].text_content()
        if self._is_us(team1_name):
            us = self.team_score(1)
            them = self.team_score(2)
        else:
            them = self.team_score(1)
            us = self.team_score(2)
        if us == them:
            return 'tied'
        elif us > them:
            return 'won'
        elif us < them:
            return 'lost'
        return 'unknown'

    def _team_pships(self, team_num):
        return map(lambda e: int(e.text_content()),
                   self.results.xpath(self.team_sel.format(team_num))[1:5])


    def skin(self, innings_num, pship_num):
        # Can only handle only tied partnership.
        # Will fail for two consecutive tied partnerships.
        team1_pships = self._team_pships(1)
        team2_pships = self._team_pships(2)
        pships = zip(team1_pships, team2_pships)
        num = pship_num - 1
        a, b = pships[num]
        if a > b and innings_num == 1:
            return True
        elif a < b and innings_num == 2:
            return True
        elif a == b:
            if num == 3:
                # Last partnership
                num = 2
            else:
                num = num + 1
            c, d = pships[num]
            if c > d and innings_num == 1:
                return True
            elif c < d and innings_num == 2:
                return True
        return False


def format_over(deliveries):
    de = [d.lower() if d != '' else '.' for d in deliveries]
    return ' '.join(de)


class Extractor(object):
    def __init__(self, results):
        self.results = results

    def _assert_batting_order(self, innings_num, team):
        team_sel = '//table[@class="OversTable"]//td[@class="TeamHeader"][2]'
        name = self.results.xpath(team_sel)[innings_num].text_content()
        assert name == team

    def get_team_names(self):
        team_sel = './/table[@class="Summary"]//tr[not(@class="SummaryTitle")]/td[1]'
        teams = []
        for i in self.results.xpath(team_sel):
            teams.append(i.text_content())
        return teams

    def extract(self):
        compat = Compat(self.results)

        teams = self.get_team_names()
        innings = []
        for innings_num, team in enumerate(teams):
            self._assert_batting_order(innings_num, team)

            inn = Innings(self.results.xpath(
                        '//table[@class="OversTable"]')[innings_num])

            partnerships = []
            for pship_num, batsman_num in enumerate(range(0,7,2)):
                batsman1 = inn.get_batsman(batsman_num)
                batsman2 = inn.get_batsman(batsman_num + 1)
                bowlers = inn.get_bowlers(pship_num + 1)

                over_start = 0
                overs = []
                for bowler in bowlers:
                    over_end = over_start + bowler.deliveries
                    batsman1_over = batsman1.get_deliveries(
                            over_start, over_end)
                    batsman2_over = batsman2.get_deliveries(
                            over_start, over_end)
                    over_start = over_end

                    over = {
                        'bowler': slugify(bowler.name),
                        'batsman': [{
                            'name': slugify(batsman1.name),
                            'over': format_over(batsman1_over)
                        },{
                            'name': slugify(batsman2.name),
                            'over': format_over(batsman2_over)
                        }]
                    }
                    overs.append(over)
                partnership = {
                    'members': [
                        slugify(batsman1.name),
                        slugify(batsman2.name)
                    ],
                    'overs': overs,
                    'score': compat.partnership_score(innings_num + 1, pship_num + 1),
                    'skin': compat.skin(innings_num + 1, pship_num + 1)
                }
                partnerships.append(partnership)
            inning = {
                'partnerships': partnerships,
                'score': compat.team_score(innings_num + 1)
            }
            innings.append(compat.add_us(team, inning))

        return {
            'innings': innings,
            #'result': compat.result()
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('results_url')
    parser.add_argument('destination')

    args = parser.parse_args()
    dest = os.path.abspath(args.destination)
    results = html.parse(args.results_url)

    with open(dest, 'a') as f:
        data = Extractor(results).extract()
        yaml.safe_dump(data, f, default_flow_style=False)
