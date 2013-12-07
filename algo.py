import search
import random
import tetris
import copy
import sys
from time import sleep


"""
What you need to know:
    - Board is represented by a two dimensional matrix, `grid`
    - A state is represented by a dict with keys "board" and "pieces", 
      where "pieces" is the remaining pieces (thus piece[0] is the next piece)
    - print_grid for a beautiful ASCII representation of your configuration
"""

debug = False
demo = False
TESTMODE = True

GRID_HEIGHT = 20
GRID_WIDTH = 10

def print_grid(grid, block=None):
    """
    Print ASCII version of our tetris for debugging
    """
    for y in xrange(GRID_HEIGHT):
        if debug: 
            # Column numbers
            print "%2d" % y,

        for x in xrange(GRID_WIDTH):
            block = grid[y][x]
            if block:
                print block,
            else:
                print ".",
        print  # Newline at the end of a row

def merge_grid_block(grid, block):
    """
    Given a grid and a block, add the block to the grid.
    This is called to "merge" a block into a grid. You can
    think of the grid as the static part of pieces that have already
    been placed down. `block` is the current piece that you're looking to 
    place down.

    See settle_block() from tetris.py. Same thing, except without game logic

    Returns:
        Nothing, modifies grid via side-effects
    """
    for square in block.squares:
        y, x = square.y / tetris.FULL_WIDTH, square.x / tetris.FULL_WIDTH
        if grid[y][x]:
            print get_height(grid)
            raise Exception("Tried to put a Tetris block where another piece already exists")
        else:
            grid[y][x]=square
    return

def get_height(grid):
    """
    Given a grid, calculates the maximum height of any column
    Returns:
        int representing the maximum height of any column
    """
    heights = []
    for index in range(GRID_WIDTH):
        temp = [i for i, x in enumerate([col[index] for col in grid][::-1]) if x != None]
        heights.append(0 if len(temp) == 0 else max(temp)+1) # 0-indexed lol
    return max(heights)

def get_num_holes(g):
    """
    Given a grid, calculates the number of ''holes'' in the placed pieces
    Returns:
        int - number of holes
    """
    grid = copy.deepcopy(g)
    # use sets to avoid dups
    holes = set()
    # first for loop finds initial underhangs
    for i in range(len(grid) - 1, 0, -1): # row
        for j in range(len(grid[i])): # col
            if i - 1 >= 0 and grid[i][j] is None and grid[i-1][j] is not None:
                holes.add((i, j))
    # new copy because can't change set while iterating.
    all_holes = copy.deepcopy(holes)
    # for each find earlier keep digging down to see how many holes additionally there are
    for i, j in holes:
        while i + 1 < len(grid) and grid[i + 1][j] is None:
            all_holes.add((i + 1, j))
            i += 1
    return len(all_holes)

def get_lines_cleared(gnew, gold):
    diff_lines = get_height(gnew) - get_height(gold)
    if diff_lines > -4:
        return -100 # strongly prefer clearing 4 at a time
    else:
        return 0
    return

def average_height(grid):
    heights = []
    for index in range(GRID_WIDTH):
        temp = [i for i, x in enumerate([col[index] for col in grid][::-1]) if x != None]
        heights.append(0 if len(temp) == 0 else max(temp)+1) # 0-indexed lol
    return float(sum(heights)) / GRID_WIDTH

""" gets best successor based on state score """
def getBestSuccessor(problem, state):
    successors = problem.getSuccessors(state)
    cur_max = float("-inf")
    cur_best = None
    if len(successors) == 0:
        print "Error"
        return None
    for s in successors:
        temp = evaluate_state(s['board'])
        if temp > cur_max:
            cur_best = s
            cur_max = temp
    return cur_best

def evaluate_state(state, problem):
    """
    Heuristic / scoring function for state
    """
    grid = state["board"]
    return -(10*get_num_holes(grid) + get_height(grid) + average_height(grid))

class TetrisSearchProblem(search.SearchProblem):
    def __init__(self):
        # Generate random sequence of pieces for offline tetris
        NUM_PIECES = 10
        self.all_pieces = [random.choice(tetris.SHAPES) for i in xrange(NUM_PIECES)]

        if demo:
            self.all_pieces = [tetris.LINE_SHAPE, tetris.SQUARE_SHAPE, tetris.SQUARE_SHAPE,
                 tetris.T_SHAPE, tetris.Z_SHAPE, tetris.L_SHAPE, tetris.LINE_SHAPE,
                 tetris.T_SHAPE, tetris.T_SHAPE] + \
                [tetris.LINE_SHAPE, tetris.SQUARE_SHAPE, tetris.INVERT_L_SHAPE, tetris.LINE_SHAPE, tetris.LINE_SHAPE] + \
                [random.choice(tetris.SHAPES) for i in xrange(30)] 

        # Taken from tetris.py: initial board setup
        self.initial_board = []  
        for i in range(GRID_HEIGHT):
            self.initial_board.append([])
            for j in range(GRID_WIDTH):
                self.initial_board[i].append(None)   

    def getStartState(self):
        # Tuple of configuration and past grids
        return { "pieces": self.all_pieces, "board": self.initial_board }

    def isGoalState(self, state):
        # TODO: Define this -- depends on what approach we want to take
        # Is it just if the state is ready to tetris and the next piece is a line piece?
        return len(state["pieces"]) == 20

    def _generateRotations(self, piece, grid):
        """
        Args:
            piece: Block() object
        Returns:
            List of Block objects for the possible rotations
        """
        rotated_pieces = []
        TOTAL_ROTATIONS = 4  # 0, 90, 180, 270
        for num_cw_rotations in xrange(TOTAL_ROTATIONS): 
            # Make a copy of the piece so we can manipulate it
            new_piece = copy.deepcopy(piece)

            # Short circuit logic for rotating the correct number of times CW
            # This might be buggy...not really sure what his can_CW function checks for
            did_rotate = True
            for _ in xrange(num_cw_rotations):
                if new_piece.can_CW(grid):
                    new_piece.rotate_CW(grid)
                else:
                    did_rotate = False

            # By default, tetris.py instantiates pieces in the middle.
            # Move it all the way to the left. move_left() side-effects.
            while new_piece.move_left(grid): pass

            if not did_rotate:
                continue
            else:
                rotated_pieces.append(new_piece)

        return rotated_pieces


    def getSuccessors(self, state):
        """
        Return a list of successor nodes
        using the board and current piece. 
        """
        if len(state["pieces"]) == 0:
            return None
        
        new_piece_type = state["pieces"][0]
        grid = state["board"]

        successors = []

        new_piece = tetris.Block(new_piece_type)

        # Because we're leveraging tetris.py, we have a lot of 
        # side-effecting code going on -- have to be careful


        possible_rotations = self._generateRotations(new_piece, grid)

        # Starting from the left-hand side this moves the 
        # piece to the right one column (i.e. every horizontal position).
        # Then we move the piece all the way down.
        # In this way, we enumerate all possible subsequent configurations.
        for rotated_piece in possible_rotations:
            can_move_right = True
            while can_move_right:
                # Copying the grids here might explode memory, but I think keeping
                # a reference to the same grid repeatedly is going to be really dangerous
                piece_copy = copy.deepcopy(rotated_piece)
                grid_copy = copy.deepcopy(grid)

                # Move the piece all the way down
                while piece_copy.move_down(grid_copy): pass

                # Add the block to the grid and clear lines
                # filter out a successor that makes a game ending move
                try:
                    merge_grid_block(grid_copy, piece_copy)

                    #  push a new random piece to replace the one we played
                    piece = random.choice(tetris.SHAPES)
                    state["pieces"].append(piece)

                    successors.append({
                        "board": grid_copy,
                        "pieces": state["pieces"][1:] 
                    })
                except:
                    print "failed move!"

                # Try the next configuration
                can_move_right = rotated_piece.move_right(grid)  # has side-effects

        return successors

    def getCostOfActions(self, actions):
        pass

def main():
    search_problem = TetrisSearchProblem()
    if TESTMODE:
        test_tetris(3)
    else:
        find_tetris(search_problem)


def test_tetris(ntrial=10, heuristic=evaluate_state):
    """
    Test harness
    """

    total_lines = 0
    for i in range(ntrial):
        problem = TetrisSearchProblem()

        current_node = None

        # 1) detect when it touches the top
        # 2) make game go on infinitely
        
        # Game loop: keep playing the game until all of the pieces are done
        while current_node is None or len(current_node["pieces"]) > 0:
            game_replay, goal_node = search.aStarSearch(problem, heuristic)
            current_node = goal_node

            lines_cleared = 0
            for i in range(len(game_replay)-1):
                before = get_height(game_replay[i])
                after = get_height(game_replay[i+1])
                if after < before:
                    lines_cleared += before - after

            print "Lines cleared: " + str(lines_cleared)
            break
            #return # TODO: remove once we have a real goal state

        total_lines += lines_cleared

    print "Total Lines: " + str(total_lines) + " in " + str(ntrial) + " games."

def find_tetris(problem):
    """
    Continues until we find a tetris
    """
    current_node = None

    # Game loop: keep playing the game until all of the pieces are done
    while current_node is None or len(current_node["pieces"]) > 0:
        game_replay, goal_node = search.aStarSearch(problem, heuristic=evaluate_state)
        current_node = goal_node

        for grid in game_replay:
            print_grid(grid)
            print

            sleep(1)

        return # TODO: remove once we have a real goal state
    


def example():
    """
    Saagar, Brandon: call this function and you'll get a concrete idea of how
    the next configurations are being generated
    """
    search_problem = TetrisSearchProblem()

    start = search_problem.getStartState()
    succ = search_problem.getSuccessors(start)
    for s in succ:
        print_grid(s["board"])
        print

    print "Now, let's look at the successors for just one of these states"
    more_succ = search_problem.getSuccessors(succ[0])
    for s in more_succ:
        print_grid(s["board"])
        print

    print "*******************brandon and saagar's testing*******************"
    print "next piece:"
    print more_succ[0]['pieces'][0]
    print_grid(more_succ[0]["board"])
    print
    print_grid(getBestSuccessor(search_problem, more_succ[0])['board'])
    
if __name__ == '__main__':
    main()
