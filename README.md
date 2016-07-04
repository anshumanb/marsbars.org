# marsbars.org source code

## Development setup

Install Python 2.7.
Install virtualenv
Install NodeJS
Install npm

cd marsbars.org/
virtualenv2 .virtualenv
source .virtualenv/bin/activate
python bootstrap-buildout.py
bin/buildout
bin/npm install

bin/python loaddata.py
bin/flask run

## To scrape scorecard
bin/python extract.py <scoresheet URL> <results file to append to>

## To deploy
