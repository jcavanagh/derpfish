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

	def _rank_index(self, pos):
		rank = 0
		for i in range(8):
			if(pos & (MASK_RANK_1<<(8 * i))):
				rank = i + 1
				break

		return rank

	def _rank(self, pos):
		return str(self._rank_index(pos));

	def _file_index(self, pos):
		file = 0
		for i in range(8):
			if(pos & (MASK_FILE_A>>i)):
				file = i + 1
				break

		return file

	def _file(self, pos):
		return BitboardFiles[self._file_index(pos) - 1]

	def _file_mask(self, file):
		return globals()['MASK_FILE_' + file.upper()]

	def _rank_mask(self, rank):
		return globals()['MASK_RANK_' + str(rank)]

	def create_move(self, piece_name, initial, final, capture=False, promotion=False):
		check = self.is_check(final)
		checkmate = self.is_checkmate(final) if check else False
		return Move(piece_name, initial, final, check, checkmate, capture, promotion)

	def _create_moves_horizontal(self, piece_name, piece_pos, pos_us, pos_opp, file, moves):
		# Search left and right of piece
		for i in range(1, file):
			new_piece_pos = piece_pos<<i
			if(pos_us & new_piece_pos):
				break
			else:
				moves.append(self.create_move(piece_name, piece_pos, new_piece_pos))
				if(pos_opp & new_piece_pos):
					break

		for i in range(1, 9 - file):
			new_piece_pos = piece_pos>>i
			if(pos_us & new_piece_pos):
				break
			else:
				moves.append(self.create_move(piece_name, piece_pos, new_piece_pos))
				if(pos_opp & new_piece_pos):
					break

	def _create_moves_vertical(self, piece_name, piece_pos, pos_us, pos_opp, rank, moves):
		# Search up and down of piece
		for i in range(1, rank):
			new_piece_pos = piece_pos>>(8 * i)
			if(pos_us & new_piece_pos):
				break
			else:
				moves.append(self.create_move(piece_name, piece_pos, new_piece_pos))
				if(pos_opp & new_piece_pos):
					break

		for i in range(1, 9 - rank):
			new_piece_pos = piece_pos<<(8 * i)
			if(pos_us & new_piece_pos):
				break
			else:
				moves.append(self.create_move(piece_name, piece_pos, new_piece_pos))
				if(pos_opp & new_piece_pos):
					break

	def _create_moves_diagonal_right(self, piece_name, piece_pos, pos_us, pos_opp, file, rank, moves):
		# Search up-right and down-left of piece
		dist_up_right = min(8 - rank, 8 - file)
		for i in range(1, dist_up_right):
			new_piece_pos = piece_pos<<(7 * i)
			if(pos_us & new_piece_pos):
				break
			else:
				moves.append(self.create_move(piece_name, piece_pos, new_piece_pos))
				if(pos_opp & new_piece_pos):
					break

		dist_down_left = min(rank, file)
		for i in range(1, dist_down_left):
			new_piece_pos = piece_pos>>(7 * i)
			if(pos_us & new_piece_pos):
				break
			else:
				moves.append(self.create_move(piece_name, piece_pos, new_piece_pos))
				if(pos_opp & new_piece_pos):
					break

	def _create_moves_diagonal_left(self, piece_name, piece_pos, pos_us, pos_opp, file, rank, moves):
		# Search up-left and down-right of piece
		dist_up_left = min(8 - rank, file)
		for i in range(1, dist_up_left):
			new_piece_pos = piece_pos<<(9 * i)
			if(pos_us & new_piece_pos):
				break
			else:
				moves.append(self.create_move(piece_name, piece_pos, new_piece_pos))
				if(pos_opp & new_piece_pos):
					break

		dist_down_right = min(rank, 8 - file)
		for i in range(1, dist_down_right):
			new_piece_pos = piece_pos>>(9 * i)
			if(pos_us & new_piece_pos):
				break
			else:
				moves.append(self.create_move(piece_name, piece_pos, new_piece_pos))
				if(pos_opp & new_piece_pos):
					break

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

		for move_list in map(lambda key: getattr(self, '_moves_' + key)(getattr(side, key), moves), side._fields):
			pass

		return moves

	def _move_bb_gen(self, pieces_bb):
		index = -1
		while(1):
			index = bit_scan1(pieces_bb, index + 1)
			if index is None: raise StopIteration
			yield mpz(1)<<index

	def _move_append_if(self, piece_name, initial_pos, final_pos, moves):
		if(final_pos):
			moves.append(self.create_move(piece_name, initial_pos, final_pos))

	def _moves_pawn(self, pawns, moves):
		prev_pos = self.history[len(self.history) - 1] if len(self.history) > 0 else None

		moved_pawns = pawns & ~(self._shift_abs(255, 8))
		unmoved_pawns = pawns & (self._shift_abs(255, 8))

		def _pawn_move_1(pawn):
			return self._shift(pawn, 8) & ~self._pos_bb()

		def _pawn_move_2(pawn):
			move_1 = _pawn_move_1(pawn)
			return self._shift(move_1, 8) & ~self._pos_bb() if move_1 else 0

		def _pawn_capture_left(pawn):
			return self._shift(pawns & MASK_FILE_A, 9) & self._pos_bb(self.opponent)

		def _pawn_capture_right(pawn):
			return self._shift(pawns & MASK_FILE_H, 7) & self._pos_bb(self.opponent)

		def _pawn_promote(pawn):
			return _pawn_move_1(pawn) & MASK_RANK_8

		def _pawn_en_passant(pawn):
			# TODO: En passant
			return 0

		for pawn in self._move_bb_gen(pawns):
			self._move_append_if('pawn', pawn, _pawn_move_1(pawn), moves)
			self._move_append_if('pawn', pawn, _pawn_capture_left(pawn), moves)
			self._move_append_if('pawn', pawn, _pawn_capture_right(pawn), moves)
		
		for pawn in self._move_bb_gen(unmoved_pawns):
			self._move_append_if('pawn', pawn, _pawn_move_2(pawn), moves)

	def _moves_knight(self, knights, moves):
		def _knight_move_left_down(knight):
			return None
		def _knight_move_left_up(knight):
			return None
		def _knight_move_up_left(knight):
			return None
		def _knight_move_up_right(knight):
			return None
		def _knight_move_right_up(knight):
			return None
		def _knight_move_right_down(knight):
			return None
		def _knight_move_down_right(knight):
			return None
		def _knight_move_down_left(knight):
			return None

	def _moves_bishop(self, bishops, moves):
		pos_us = self._pos_bb(self.player)
		pos_opp = self._pos_bb(self.opponent)

		for bishop in self._move_bb_gen(bishops):
			rank = self._rank_index(bishop)
			file = self._file_index(bishop)

			self._create_moves_diagonal_right('bishop', bishop, pos_us, pos_opp, file, rank, moves)
			self._create_moves_diagonal_left('bishop', bishop, pos_us, pos_opp, file, rank, moves)

	def _moves_rook(self, rooks, moves):
		pos_us = self._pos_bb(self.player)
		pos_opp = self._pos_bb(self.opponent)

		for rook in self._move_bb_gen(rooks):
			rank = self._rank_index(rook)
			file = self._file_index(rook)

			self._create_moves_vertical('rook', rook, pos_us, pos_opp, rank, moves)
			self._create_moves_horizontal('rook', rook, pos_us, pos_opp, file, moves)

	def _moves_king(self, kings, moves):
		def _king_move_left_down(king):
			on_first_file = king & MASK_FILE_A
			on_first_rank = king & MASK_RANK_1
			return (king>>7) & ~self._pos_bb(self.player) if not (on_first_file or on_first_rank) else 0
		def _king_move_left(king):
			on_first_file = king & MASK_FILE_A
			return (king<<1) & ~self._pos_bb(self.player) if not on_first_file else 0
		def _king_move_left_up(king):
			on_first_file = king & MASK_FILE_A
			on_last_rank = king & MASK_RANK_8
			return (king<<7) & ~self._pos_bb(self.player) if not (on_first_file or on_last_rank) else 0
		def _king_move_up(king):
			on_last_rank = king & MASK_RANK_8
			return (king<<8) & ~self._pos_bb(self.player) if not on_last_rank else 0
		def _king_move_right_up(king):
			on_last_file = king & MASK_FILE_H
			on_last_rank = king & MASK_RANK_8
			return (king<<9) & ~self._pos_bb(self.player) if not (on_last_file or on_last_rank) else 0
		def _king_move_right(king):
			on_last_file = king & MASK_FILE_H
			return (king>>1) & ~self._pos_bb(self.player) if not on_last_file else 0
		def _king_move_right_down(king):
			on_last_file = king & MASK_FILE_H
			on_first_rank = king & MASK_RANK_1
			return (king>>9) & ~self._pos_bb(self.player) if not (on_last_file or on_first_rank) else 0
		def _king_move_down(king):
			on_first_rank = king & MASK_RANK_1
			return (king>>8) & ~self._pos_bb(self.player) if not on_first_rank else 0

		for king in self._move_bb_gen(kings):
			self._move_append_if('king', king, _king_move_left_down(king), moves)
			self._move_append_if('king', king, _king_move_left(king), moves)
			self._move_append_if('king', king, _king_move_left_up(king), moves)
			self._move_append_if('king', king, _king_move_up(king), moves)
			self._move_append_if('king', king, _king_move_right_up(king), moves)
			self._move_append_if('king', king, _king_move_right(king), moves)
			self._move_append_if('king', king, _king_move_right_down(king), moves)
			self._move_append_if('king', king, _king_move_down(king), moves)

	def _moves_queen(self, queens, moves):
		pos_us = self._pos_bb(self.player)
		pos_opp = self._pos_bb(self.opponent)

		for queen in self._move_bb_gen(queens):
			rank = self._rank_index(queen)
			file = self._file_index(queen)

			self._create_moves_vertical('queen', queen, pos_us, pos_opp, rank, moves)
			self._create_moves_horizontal('queen', queen, pos_us, pos_opp, file, moves)
			self._create_moves_diagonal_right('queen', queen, pos_us, pos_opp, file, rank, moves)
			self._create_moves_diagonal_left('queen', queen, pos_us, pos_opp, file, rank, moves)

	def is_capture(self, move):
		for piece in BitboardFields:
			if(move.end_pos & self.opponent[piece]):
				return piece

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
	# print(timeit.timeit(stmt="b.moves()", setup="from __main__ import Bitboard;b=Bitboard('white')", number=1))

	# import cProfile
	# b = Bitboard('white')
	# cProfile.run('b.moves()')

	b = Bitboard('white')
	print()
	# print(list(b.moves()))
	print(list(b.algebraic(b.moves())))
	# list(map(lambda m: print(b._format(m.end_pos)), b.moves()))
