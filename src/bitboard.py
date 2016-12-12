from collections import namedtuple
from gmpy2 import mpz, bit_scan1

BitboardFields = ['pawn', 'knight', 'bishop', 'rook', 'king', 'queen']
BitboardSymbols = ['', 'N', 'B', 'R', 'K', 'Q']
BitboardFiles = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
BitboardColor = namedtuple('BitboardColor', BitboardFields)

Move = namedtuple('Move', [
	'piece',
	'start_pos',
	'end_pos',
	'is_check',
	'is_checkmate',
	'is_capture',
	'is_promotion'
])

TOP_EDGE_MASK = mpz(255)<<56
BOTTOM_EDGE_MASK = mpz(255)
LEFT_EDGE_MASK = mpz(1)<<7 | mpz(1)<<15 | mpz(1)<<23 | mpz(1)<<31 | mpz(1)<<39 | mpz(1)<<47 | mpz(1)<<55 | mpz(1)<<63
RIGHT_EDGE_MASK = mpz(1)<<0 | mpz(1)<<8 | mpz(1)<<16 | mpz(1)<<24 | mpz(1)<<32 | mpz(1)<<40 | mpz(1)<<48 | mpz(1)<<56

class Bitboard:
	def __init__(self, color):
		self.color = color
		self.white = BitboardColor(
			pawn = mpz(255<<8),
			knight = mpz(66),
			bishop = mpz(36),
			rook = mpz(129),
			king = mpz(8),
			queen = mpz(16)
		)

		self.black = BitboardColor(
			pawn = mpz(255<<48),
			knight = mpz(66<<56),
			bishop = mpz(36<<56),
			rook = mpz(129<<56),
			king = mpz(8<<56),
			queen = mpz(16<<56)
		)
		self.player = self.white if color == 'white' else self.black
		self.opponent = self.black if color == 'white' else self.white
		self.history = []
		self.positions = {}

	def __repr__(self):
		return self._format(self._pos_bb())

	def _pos_bb(self, board=None):
		if board is None:
			return (self._pos_bb(self.player) ^ self._pos_bb(self.opponent))
		else:
			all = mpz(0)
			for item in board:
				all = all ^ item

			return all

	def _format(self, board):
		digits = board.digits(2).rjust(64, '0')
		index = 0
		formatted = ''
		while index < 64:
			formatted += digits[index:index+8]+'\n'
			index += 8
		return formatted

	# Shifts an absolute mask relative to a bitboard
	def _shift_abs(self, num, shift):
		return num<<shift if self.color == 'white' else (num<<(64 - shift))>>shift

	# Shifts a position relative to a bitboard
	def _shift(self, num, shift):
		return num<<shift if self.color == 'white' else num>>shift

	def hash(self):
		hash = 0
		for index in range(len(BitboardFields)):
			key = BitboardFields[index]
			hash += (getattr(self.player, key) & getattr(self.opponent, key)) * (index + 1)

		return hash.digits(10)

	def _rank(self, pos):
		rank = 0
		for i in range(0, 7):
			if(pos & (BOTTOM_EDGE_MASK<<(8 * i))):
				rank = i + 1
				break

		return rank

	def _file(self, pos):
		file = 0
		for i in range(0, 7):
			if(pos & (RIGHT_EDGE_MASK<<i)):
				file = i + 1
				break

		return file

	def _create_move(self, piece, initial, final, capture=False, promotion=False):
		check = self.is_check(final)
		checkmate = self.is_checkmate(final) if check else False
		return Move(piece, initial, final, check, checkmate, capture, promotion)

	def moves(self, board=None):
		board = board or self.player
		position_hash = self.hash()
		position_cache = self.positions.get(position_hash, None)
		moves = []

		if(position_cache is None):
			for move_list in map(lambda key: getattr(self, '_moves_' + key)(getattr(board, key)), board._fields):
				if(move_list): moves += move_list

			self.positions[position_hash] = moves;
			return moves
		else:
			return self.positions[position_hash]

	def _moves_pawn(self, pawns):
		prev_pos = self.history[len(self.history) - 1] if len(self.history) > 0 else None

		moved_pawns = pawns & ~(self._shift_abs(255, 8))
		unmoved_pawns = pawns & (self._shift_abs(255, 8))

		print(self._format(moved_pawns))
		print(self._format(unmoved_pawns))

		def _pawn_move_1(pawn):
			return self._shift(pawn, 8) & ~(self._pos_bb())

		def _pawn_move_2(pawn):
			move_1 = _pawn_move_1(pawn)
			return self._shift(move_1, 8) & ~(self._pos_bb()) if move_1 else 0

		def _pawn_capture_left(pawn):
			return self._shift(pawns & LEFT_EDGE_MASK, 9) & self._pos_bb(self.opponent)

		def _pawn_capture_right(pawn):
			return self._shift(pawns & RIGHT_EDGE_MASK, 7) & self._pos_bb(self.opponent)

		def _pawn_promote(pawn):
			return _pawn_move_1(pawn) & TOP_EDGE_MASK

		def _pawn_en_passant(pawn):
			return 0

		moves = []
		index = -1
		while(1):
			index = bit_scan1(pawns, index + 1)
			print('pawn index:', index)
			if index is None: break

			pawn = mpz(1)<<index
			
			move_1 = _pawn_move_1(pawn)
			if move_1: moves.append(self._create_move('pawn', pawn, move_1))

			capture_left = _pawn_capture_left(pawn)
			if capture_left: moves.append(self._create_move('pawn', pawn, capture_left))

			capture_right = _pawn_capture_right(pawn)
			if capture_right: moves.append(self._create_move('pawn', pawn, capture_right))
		
		index = -1
		while(1):
			index = bit_scan1(unmoved_pawns, index + 1)
			print('unmoved pawn index:', index)
			if index is None: break

			pawn = mpz(1)<<index

			move_2 = _pawn_move_2(pawn)
			if move_2: moves.append(self._create_move('pawn', pawn, move_2))

		return moves

	def _moves_knight(self, knights):
		return None

	def _moves_bishop(self, bishops):
		return None

	def _moves_rook(self, rooks):
		return None

	def _moves_king(self, kings):
		return None

	def _moves_queen(self, queens):
		return None

	def is_capture(self, move):
		return False

	def is_check(self, move):
		return False

	def is_checkmate(self, move):
		return False

	def algebraic(self, moves):
		return list(map(self._algebraic_move, moves))

	def _algebraic_move(self, move):
		# TODO: Resolve piece ambiguity
		sym = BitboardSymbols[BitboardFields.index(move.piece)]
		buf = ''
		start_file = self._file(move.start_pos)
		end_rank = str(self._rank(move.end_pos))
		end_file = BitboardFiles[self._file(move.end_pos)]

		if(move.is_capture):
			if(move.piece == 'pawn'):
				buf += start_file + 'x' + end_file + end_rank
			else:
				buf += sym + 'x' + end_file + end_rank
		else:
			if(move.piece == 'pawn'):
				buf += end_file + end_rank
			else:
				buf += sym + end_file + end_rank

		# TODO: Underpromotion
		if(move.is_promotion):
			buf += '=Q'

		if(move.is_checkmate):
			buf += '#'
		elif(move.is_check):
			buf += '+'
		
		return buf

	def _algebraic_bitboard(self, board):
		rank = board % 8
		return 

	def from_fen(self):
		return None

	def to_fen(self):
		return None

if __name__ == "__main__":
	b = Bitboard('white')
	print(list(b.moves()))
	print(list(b.algebraic(b.moves())))
