import comm
import sys, traceback

from engine import Engine

try:
	engine_input = comm.XBoard()
	engine = Engine()
	engine.set_output(engine_input)

	engine_input.on('new', lambda evt: engine.new())
	engine_input.on('usermove', lambda evt: (print(evt), engine.user_move(evt.args[0])))
	engine_input.on('go', lambda evt: engine.go())

	engine_input.listen()
except:
	# TODO: Logging
	etype, evalue, tb = sys.exc_info()
	traceback.print_exception(etype, evalue, tb)
