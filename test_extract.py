import unittest
import extract
from lxml import html

partial_batsman = '''
<tr class="BallRow">
    <td class="BatsmanCell">Anshuman Bhaduri</td>
    <td class="BallCell">2</td>
    <td class="BallCell"></td>
    <td class="BallCell">4</td>
    <td class="extraBall">-5</td>
    <td class="OverTotalCell">10</td>
    <td class="BallCell">9</td>
    <td class="BallCell">0</td>
    <td class="BallCell"></td>
    <td class="OverTotalCell">12</td>
    <td class="TotalCell">45</td>
</tr>
'''

partial_innings = '''
<table class="OversTable">
    <tbody>
        <tr>
            <td class="Blank"></td>
            <td class="OverNo">1</td>
            <td colspan="2" class="Bwl">Bowler A</td>
            <td class="OverNo">2</td>
            <td colspan="2" class="Bwl">Bowler B</td>
        </tr>
        <tr class="BallRow">
            <td class="BatsmanCell">Anshuman Bhaduri</td>
            <td class="BallCell">-5</td>
            <td class="BallCell">2</td>
            <td class="OverTotalCell">10</td>
            <td class="BallCell">9</td>
            <td class="BallCell"></td>
            <td class="OverTotalCell">10</td>
        </tr>
        <tr class="SpacerRow"></tr>
        <tr>
            <td class="OverNo">3</td>
            <td colspan="3" class="Bwl">Bowler C</td>
            <td class="OverNo">4</td>
            <td colspan="2" class="Bwl">Bowler D</td>
        </tr>
        <tr class="BallRow">
            <td class="BatsmanCell">Mickey Mouse</td>
            <td class="BallCell">9</td>
            <td class="BallCell"></td>
            <td class="OverTotalCell">10</td>
            <td class="BallCell">2</td>
            <td class="BallCell">7</td>
            <td class="OverTotalCell">10</td>
        </tr>
        <tr class="BallRow">
            <td class="BatsmanCell">Pluto</td>
            <td class="BallCell">2</td>
            <td class="BallCell">7</td>
            <td class="OverTotalCell">10</td>
            <td class="BallCell">-5</td>
            <td class="BallCell">2</td>
            <td class="OverTotalCell">10</td>
        </tr>
    </tbody>
</table>
'''

class TestUtils(unittest.TestCase):

    def test_should_slugify(self):
        self.assertEqual(extract.slugify('Joe Bloggs XI'), 'joe-bloggs-xi')

    def test_should_fix_player_slugs(self):
        self.assertEqual(extract.slugify('Neil Unknown'), 'anshuman-bhaduri')

    def test_should_format_unfaced_deliveries_with_dots(self):
        self.assertEqual(extract.format_over(['0', '0', '3', '', '7', '']),
                         '0 0 3 . 7 .')


class TestBatsman(unittest.TestCase):

    def setUp(self):
        row = html.fragment_fromstring(partial_batsman)
        self.batsman = extract.Batsman(row)

    def test_should_get_batsman_name(self):
        self.assertEqual(self.batsman.name, 'Anshuman Bhaduri')

    def test_should_get_deliveries(self):
        self.assertSequenceEqual(self.batsman.get_deliveries(start=0, end=4),
                                 ['2', '', '4', '-5'])

    def test_should_get_slice_of_deliveries(self):
        self.assertSequenceEqual(self.batsman.get_deliveries(start=1, end=3),
                                 ['', '4'])

    def test_should_not_get_totals(self):
        self.assertItemsEqual(self.batsman.get_deliveries(start=0, end=10),
                              ['2', '', '4', '-5', '9', '0', ''])


class TestInnings(unittest.TestCase):

    def setUp(self):
        innings = html.fragment_fromstring(partial_innings)
        self.innings = extract.Innings(innings)

    def test_should_get_correct_batsman(self):
        self.assertEqual(self.innings.get_batsman(0).name, 'Anshuman Bhaduri')
        self.assertEqual(self.innings.get_batsman(2).name, 'Pluto')

    def test_should_get_correct_bowler(self):
        bowlers = self.innings.get_bowlers(partnership=2)
        self.assertEqual(bowlers[0].name, 'Bowler C')
        self.assertEqual(bowlers[1].name, 'Bowler D')

        bowlers = self.innings.get_bowlers(partnership=1)
        self.assertEqual(bowlers[0].name, 'Bowler A')

    def test_should_get_correct_number_deliveries_for_bowler(self):
        bowlers = self.innings.get_bowlers(partnership=2)
        self.assertEqual(bowlers[0].deliveries, 3)
        self.assertEqual(bowlers[1].deliveries, 2)


if __name__ == '__main__':
    unittest.main()
