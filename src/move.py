from collections import namedtuple

# Characterizes a possible move
Move = namedtuple('Move', [
  'piece',
  'start_pos',
  'end_pos',
  # Pawn edge cases
  'requires_capture',
  'is_promotion',
  'en_passant',
  # For sliding pieces, how many squares it would travel relative to its starting position
  'length',
  # As cardinal direction - N, S, E, W, NE, NW, SE, SW
  'direction'
])

Move.__new__.__defaults__ = (None, None, None, False, False, False, 0, None)