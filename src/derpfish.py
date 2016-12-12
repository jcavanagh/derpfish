import comm
import engine

engine_input = comm.XBoard()

engine_input.on('new', engine.new)