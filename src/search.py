import math
import precompute

class Search:
  def __init__(self):
    self.all_moves = precompute.all_moves()
    self.transposition = {}

  def think(self, position, max_time):
    return _search(position, 0, -math.inf, math.inf, position['on_move'])

  def ponder(self, position):
    return _search(position, 0, -math.inf, math.inf, position['off_move'])
    
  def _search(self, position, depth, alpha, beta, color):
    # If we can capture the king, the previous move was awful
    