from gmpy2 import mpz

WHITE = 1
BLACK = -1

Colors = [WHITE, BLACK]

Pieces = ['pawn', 'knight', 'bishop', 'rook', 'king', 'queen']
PieceSymbols = {
  'pawn': 'P',
  'knight': 'N',
  'bishop': 'B',
  'rook': 'R',
  'king': 'K',
  'queen': 'Q'
}

Files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
FileIndexes = {
  'a': 1,
  'b': 2,
  'c': 3,
  'd': 4,
  'e': 5,
  'f': 6,
  'g': 7,
  'h': 8
}

Movements = {
  'bishop': [ 'NE', 'NW', 'SE', 'SW' ],
  'rook': [ 'N', 'S', 'E', 'W' ],
  'queen': [ 'NE', 'NW', 'SE', 'SW', 'N', 'S', 'E', 'W' ]
}

Weights = {
  'material': {
    'pawn': 100,
    'knight': 300,
    'bishop': 300,
    'rook': 500,
    'queen': 900,
    'king': 1000000
  },
  'structure': {
    'doubled_pawn': 70,
    'passed_pawn': 110,
    'isolated_pawn': 80
  }
}

MASK_RANK_1 = mpz(255)
MASK_RANK_2 = MASK_RANK_1<<8
MASK_RANK_3 = MASK_RANK_1<<16
MASK_RANK_4 = MASK_RANK_1<<24
MASK_RANK_5 = MASK_RANK_1<<32
MASK_RANK_6 = MASK_RANK_1<<40
MASK_RANK_7 = MASK_RANK_1<<48
MASK_RANK_8 = MASK_RANK_1<<56

MASK_FILE_A = mpz(1)<<7 | mpz(1)<<15 | mpz(1)<<23 | mpz(1)<<31 | mpz(1)<<39 | mpz(1)<<47 | mpz(1)<<55 | mpz(1)<<63
MASK_FILE_B = MASK_FILE_A>>1
MASK_FILE_C = MASK_FILE_A>>2
MASK_FILE_D = MASK_FILE_A>>3
MASK_FILE_E = MASK_FILE_A>>4
MASK_FILE_F = MASK_FILE_A>>5
MASK_FILE_G = MASK_FILE_A>>6
MASK_FILE_H = MASK_FILE_A>>7