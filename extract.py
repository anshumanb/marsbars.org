import argparse
import os.path
from lxml import html
import yaml
from collections import OrderedDict


def slugify(name):
    name = name.lower().replace(' ', '-')
    if name == 'sai-ganesh':
        return 'sai-karnan'
    elif name == 'neil-unknown':
        return 'anshuman-bhaduri'
    return name


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


def format_over(deliveries):
    de = map(lambda d: d.replace('', '.'), deliveries)
    de = [d if d != '' else '.' for d in deliveries]
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
                    'overs': overs
                }
                partnerships.append(partnership)
            inning = {
                'partnerships': partnerships
            }
            innings.append(inning)

        return {
            'innings': innings
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
