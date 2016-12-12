from bitboard import Bitboard

class Engine:
	def __init__(self):
		self.position = Bitboard()

	def new(self):
		self.position = Bitboard()