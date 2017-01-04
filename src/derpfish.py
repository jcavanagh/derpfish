import argparse, logging, sys, traceback

# Hacks
sys.setcheckinterval(10000)

# CL args
parser = argparse.ArgumentParser(description='Derpfish, a derpy chess engine')
parser.add_argument('-d', '--debug', dest='debug', action='store_true')
parser.add_argument('--log-file', dest='logfile', default='derpfish.log')
args = parser.parse_args()

# Set logging level
level = logging.DEBUG if args.debug else logging.INFO
logging.basicConfig(filename=args.logfile, level=level)

logger = logging.getLogger('derpfish')
logger.info('Derpfish starting...')

from comm import XBoard
from engine import Engine

try:
	engine_comms = XBoard()
	engine = Engine()
	engine.set_output(engine_comms)

	engine_comms.on('new', lambda evt: engine.new())
	engine_comms.on('user_move', lambda evt: engine.user_move(evt.args[0]))
	engine_comms.on('go', lambda evt: engine.go())

	engine_comms.listen()
except:
	etype, evalue, tb = sys.exc_info()
	logger.error(''.join(traceback.format_exception(etype, evalue, tb)))
