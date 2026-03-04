from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='../frontend')
CORS(app)

class GomokuGame:
    def __init__(self):
        self.board = [[0 for _ in range(15)] for _ in range(15)]
        self.current_player = 1  # 1 for black, 2 for white
        self.game_over = False
        self.winner = None
        self.mode = 'pvp'  # pvp or pve
        
    def reset(self, mode='pvp'):
        self.board = [[0 for _ in range(15)] for _ in range(15)]
        self.current_player = 1
        self.game_over = False
        self.winner = None
        self.mode = mode
        
    def make_move(self, row, col):
        if self.game_over or self.board[row][col] != 0:
            return False
            
        self.board[row][col] = self.current_player
        
        if self.check_win(row, col):
            self.game_over = True
            self.winner = self.current_player
        elif self.is_board_full():
            self.game_over = True
            self.winner = 0  # Draw
        else:
            self.current_player = 3 - self.current_player  # Switch player
            
        return True
        
    def check_win(self, row, col):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        player = self.board[row][col]
        
        for dx, dy in directions:
            count = 1
            
            # Check positive direction
            r, c = row + dx, col + dy
            while 0 <= r < 15 and 0 <= c < 15 and self.board[r][c] == player:
                count += 1
                r += dx
                c += dy
                
            # Check negative direction
            r, c = row - dx, col - dy
            while 0 <= r < 15 and 0 <= c < 15 and self.board[r][c] == player:
                count += 1
                r -= dx
                c -= dy
                
            if count >= 5:
                return True
                
        return False
        
    def is_board_full(self):
        return all(self.board[i][j] != 0 for i in range(15) for j in range(15))
        
    def get_ai_move(self):
        # Simple AI strategy
        best_score = -1
        best_move = None
        
        for i in range(15):
            for j in range(15):
                if self.board[i][j] == 0:
                    score = self.evaluate_position(i, j)
                    if score > best_score:
                        best_score = score
                        best_move = (i, j)
                        
        return best_move
        
    def evaluate_position(self, row, col):
        score = 0
        
        # Check if AI can win
        self.board[row][col] = 2
        if self.check_win(row, col):
            self.board[row][col] = 0
            return 10000
        self.board[row][col] = 0
        
        # Check if need to block player
        self.board[row][col] = 1
        if self.check_win(row, col):
            self.board[row][col] = 0
            return 5000
        self.board[row][col] = 0
        
        # Evaluate position based on nearby pieces
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        for dx, dy in directions:
            ai_count = 0
            player_count = 0
            
            for k in range(-4, 5):
                r, c = row + k * dx, col + k * dy
                if 0 <= r < 15 and 0 <= c < 15:
                    if self.board[r][c] == 2:
                        ai_count += 1
                    elif self.board[r][c] == 1:
                        player_count += 1
                        
            score += ai_count * 10
            score += player_count * 5
            
        # Prefer center positions
        center_distance = abs(row - 7) + abs(col - 7)
        score += (14 - center_distance) * 2
        
        return score

# Store game instances
games = {}

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/new_game', methods=['POST'])
def new_game():
    data = request.json
    game_id = data.get('game_id', 'default')
    mode = data.get('mode', 'pvp')
    
    game = GomokuGame()
    game.reset(mode)
    games[game_id] = game
    
    return jsonify({
        'success': True,
        'board': game.board,
        'current_player': game.current_player
    })

@app.route('/api/move', methods=['POST'])
def make_move():
    data = request.json
    game_id = data.get('game_id', 'default')
    row = data.get('row')
    col = data.get('col')
    
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'})
        
    game = games[game_id]
    
    if game.make_move(row, col):
        response = {
            'success': True,
            'board': game.board,
            'current_player': game.current_player,
            'game_over': game.game_over,
            'winner': game.winner
        }
        
        # AI move in PVE mode
        if game.mode == 'pve' and not game.game_over and game.current_player == 2:
            ai_move = game.get_ai_move()
            if ai_move:
                game.make_move(ai_move[0], ai_move[1])
                response['ai_move'] = {'row': ai_move[0], 'col': ai_move[1]}
                response['board'] = game.board
                response['current_player'] = game.current_player
                response['game_over'] = game.game_over
                response['winner'] = game.winner
                
        return jsonify(response)
    else:
        return jsonify({'success': False, 'error': 'Invalid move'})

@app.route('/api/game_state', methods=['GET'])
def get_game_state():
    game_id = request.args.get('game_id', 'default')
    
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'})
        
    game = games[game_id]
    
    return jsonify({
        'success': True,
        'board': game.board,
        'current_player': game.current_player,
        'game_over': game.game_over,
        'winner': game.winner
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
