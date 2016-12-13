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

MASK_RANK_1 = mpz(255)
MASK_RANK_2 = MASK_RANK_1<<8
MASK_RANK_2 = MASK_RANK_1<<16
MASK_RANK_2 = MASK_RANK_1<<24
MASK_RANK_2 = MASK_RANK_1<<32
MASK_RANK_2 = MASK_RANK_1<<40
MASK_RANK_2 = MASK_RANK_1<<48
MASK_RANK_8 = MASK_RANK_1<<56

MASK_FILE_A = mpz(1)<<7 | mpz(1)<<15 | mpz(1)<<23 | mpz(1)<<31 | mpz(1)<<39 | mpz(1)<<47 | mpz(1)<<55 | mpz(1)<<63
MASK_FILE_B = MASK_FILE_A>>1
MASK_FILE_C = MASK_FILE_A>>2
MASK_FILE_D = MASK_FILE_A>>3
MASK_FILE_E = MASK_FILE_A>>4
MASK_FILE_F = MASK_FILE_A>>5
MASK_FILE_G = MASK_FILE_A>>6
MASK_FILE_H = MASK_FILE_A>>7

KNIGHT_MASK = 0

class Bitboard:
	def __init__(self, color, debug=False):
		self.debug = debug
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
		self.on_move = 'player' if color == 'white' else 'opponent'
		self.off_move = 'opponent' if color == 'white' else 'player'
		self.history = []

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
			hash += (getattr(self.player, key) | getattr(self.opponent, key)) * (index + 1)

		return hash.digits(10)

	def bb_from_algebraic(self, file, rank):
		file_index = 7 - BitboardFiles.index(file)
		return mpz(1)<<((8 * rank) + file_index)

	def _rank(self, pos):
		rank = 0
		for i in range(8):
			if(pos & (MASK_RANK_1<<(8 * i))):
				rank = i + 1
				break

		return str(rank)

	def _file(self, pos):
		file = 0
		for i in range(8):
			if(pos & (MASK_FILE_A>>i)):
				file = i
				break

		return BitboardFiles[file]

	def _create_move(self, piece, initial, final, capture=False, promotion=False):
		check = self.is_check(final)
		checkmate = self.is_checkmate(final) if check else False
		return Move(piece, initial, final, check, checkmate, capture, promotion)

	def create_move_from_algebraic(self, notation):
		# TODO: O-O, O-O-O
		try:
			sym_index = BitboardSymbols.index(notation[0])
		except ValueError:
			# Pawn
			sym_index = 0

		piece = BitboardFields[sym_index]
		is_capture = notation.index('x') != -1
		is_promotion = notation.index('=') != -1
		is_check = notation.index('+') != -1
		is_checkmate = notation.index('#') != -1

		start_rank = None
		start_file = None
		end_rank = None
		end_file = None

		if piece == 'pawn':
			if(is_promotion):
				return
			elif(is_capture):
				split = notation.split('x')
				end_file = split[1][0]
				end_rank = split[1][1]
				start_file = split[0][0]
				start_rank = str(ord(end_rank) - 1)
			else:
				start_file = split[0][0]
				start_rank = split[0][1]
				end_file = split[1][0]
				end_rank = split[1][1]
		else:
			# TODO: Disambiguate
			if(is_capture):
				notation = notation.replace('x', '')

		start_pos = self.bb_from_algebraic(start_file, start_rank)
		end_pos = self.bb_from_algebraic(end_file, end_rank)
		return Move(piece, start_pos, end_pos, is_check, is_checkmate, is_capture, is_promotion)

	def make_move(self, move):
		on_move_bb = getattr(self, self.on_move)
		piece_bb = on_move_bb[move.piece]
		on_move_bb[move.piece] = piece_bb & ~move.start_pos & ~move.end_pos

		if(move.is_capture):
			off_move_bb = getattr(self, self.off_move)
			cap_piece_bb = off_move_bb[move.is_capture]
			off_move_bb[move.is_capture] = cap_piece_bb & ~move.end_pos

		if(self.on_move == 'player'):
			self.on_move = 'opponent'
			self.off_move = 'player'
		else:
			self.on_move = 'player'
			self.off_move = 'opponent'

	def moves(self, side=None):
		side = side or self.player
		moves = []

		for move_list in map(lambda key: getattr(self, '_moves_' + key)(getattr(side, key)), side._fields):
			if(move_list): moves += move_list

		return moves

	def _moves_pawn(self, pawns):
		prev_pos = self.history[len(self.history) - 1] if len(self.history) > 0 else None

		moved_pawns = pawns & ~(self._shift_abs(255, 8))
		unmoved_pawns = pawns & (self._shift_abs(255, 8))

		def _pawn_move_1(pawn):
			return self._shift(pawn, 8) & ~(self._pos_bb())

		def _pawn_move_2(pawn):
			move_1 = _pawn_move_1(pawn)
			return self._shift(move_1, 8) & ~(self._pos_bb()) if move_1 else 0

		def _pawn_capture_left(pawn):
			return self._shift(pawns & MASK_FILE_A, 9) & self._pos_bb(self.opponent)

		def _pawn_capture_right(pawn):
			return self._shift(pawns & MASK_FILE_H, 7) & self._pos_bb(self.opponent)

		def _pawn_promote(pawn):
			return _pawn_move_1(pawn) & MASK_RANK_8

		def _pawn_en_passant(pawn):
			# TODO: En passant
			return 0

		moves = []
		index = -1
		while(1):
			index = bit_scan1(pawns, index + 1)
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
		for piece in BitboardFields:
			if(move.end_pos & self.opponent[piece]):
				return piece

		return None

	def is_check(self, move):
		return False

	def is_checkmate(self, move):
		return False

	def algebraic(self, moves):
		return list(map(self.algebraic_move, moves))

	def algebraic_move(self, move):
		# TODO: Resolve piece ambiguity
		sym = BitboardSymbols[BitboardFields.index(move.piece)]
		buf = ''
		start_file = self._file(move.start_pos)
		end_rank = self._rank(move.end_pos)
		end_file = self._file(move.end_pos)

		if(move.is_capture):
			if(move.piece == 'pawn'):
				buf = start_file + 'x' + end_file + end_rank
			else:
				buf = sym + 'x' + end_file + end_rank
		else:
			buf = sym + end_file + end_rank

		# TODO: Underpromotion
		if(move.is_promotion):
			buf += '=Q'

		if(move.is_checkmate):
			buf += '#'
		elif(move.is_check):
			buf += '+'
		
		return buf

	def from_fen(self):
		return None

	def to_fen(self):
		return None

if __name__ == "__main__":
	# import timeit
	# print(timeit.timeit(stmt="b.moves()", setup="from __main__ import Bitboard;b=Bitboard('white')", number=100000))

	# import cProfile
	# b = Bitboard('white')
	# cProfile.run('b.moves()')

	b = Bitboard('white')
	print()
	print(list(b.moves()))
	print(list(b.algebraic(b.moves())))
	# list(map(lambda m: print(b._format(m.end_pos)), b.moves()))
