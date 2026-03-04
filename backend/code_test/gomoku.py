"""
五子棋游戏主程序
支持人人对战和人机对战
"""
import pygame
import sys
from enum import Enum

# 游戏配置
BOARD_SIZE = 15  # 棋盘大小
CELL_SIZE = 40   # 每个格子的大小
MARGIN = 40      # 边距
WINDOW_SIZE = BOARD_SIZE * CELL_SIZE + 2 * MARGIN

# 颜色定义
COLOR_BOARD = (220, 179, 92)
COLOR_LINE = (0, 0, 0)
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_TEXT = (50, 50, 50)

class Player(Enum):
    """玩家类型"""
    NONE = 0
    BLACK = 1
    WHITE = 2

class GameMode(Enum):
    """游戏模式"""
    PVP = 1  # 人人对战
    PVE = 2  # 人机对战

class Gomoku:
    """五子棋游戏类"""
    
    def __init__(self, mode=GameMode.PVP):
        """初始化游戏"""
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE + 60))
        pygame.display.set_caption("五子棋游戏")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.mode = mode
        self.board = [[Player.NONE for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = Player.BLACK
        self.game_over = False
        self.winner = None
        self.last_move = None
        
    def draw_board(self):
        """绘制棋盘"""
        self.screen.fill(COLOR_BOARD)
        
        # 绘制网格线
        for i in range(BOARD_SIZE):
            # 横线
            pygame.draw.line(self.screen, COLOR_LINE,
                           (MARGIN, MARGIN + i * CELL_SIZE),
                           (MARGIN + (BOARD_SIZE - 1) * CELL_SIZE, MARGIN + i * CELL_SIZE), 2)
            # 竖线
            pygame.draw.line(self.screen, COLOR_LINE,
                           (MARGIN + i * CELL_SIZE, MARGIN),
                           (MARGIN + i * CELL_SIZE, MARGIN + (BOARD_SIZE - 1) * CELL_SIZE), 2)
        
        # 绘制天元和星位
        star_positions = [(3, 3), (3, 11), (11, 3), (11, 11), (7, 7)]
        for x, y in star_positions:
            pygame.draw.circle(self.screen, COLOR_LINE,
                             (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE), 5)
    
    def draw_pieces(self):
        """绘制棋子"""
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.board[row][col] != Player.NONE:
                    color = COLOR_BLACK if self.board[row][col] == Player.BLACK else COLOR_WHITE
                    center = (MARGIN + col * CELL_SIZE, MARGIN + row * CELL_SIZE)
                    pygame.draw.circle(self.screen, color, center, CELL_SIZE // 2 - 2)
                    pygame.draw.circle(self.screen, COLOR_LINE, center, CELL_SIZE // 2 - 2, 2)
                    
                    # 标记最后一步
                    if self.last_move and self.last_move == (row, col):
                        pygame.draw.circle(self.screen, COLOR_RED, center, 5)
    
    def draw_info(self):
        """绘制游戏信息"""
        info_y = WINDOW_SIZE
        
        if self.game_over:
            if self.winner:
                text = f"游戏结束! {'黑棋' if self.winner == Player.BLACK else '白棋'}获胜!"
            else:
                text = "游戏结束! 平局!"
            color = COLOR_RED
        else:
            text = f"当前玩家: {'黑棋' if self.current_player == Player.BLACK else '白棋'}"
            color = COLOR_TEXT
        
        text_surface = self.small_font.render(text, True, color)
        self.screen.blit(text_surface, (20, info_y + 10))
        
        # 绘制提示
        hint = "按 R 重新开始 | 按 ESC 退出"
        hint_surface = self.small_font.render(hint, True, COLOR_TEXT)
        self.screen.blit(hint_surface, (20, info_y + 35))
    
    def get_board_position(self, mouse_pos):
        """将鼠标位置转换为棋盘坐标"""
        x, y = mouse_pos
        col = round((x - MARGIN) / CELL_SIZE)
        row = round((y - MARGIN) / CELL_SIZE)
        
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            return row, col
        return None
    
    def is_valid_move(self, row, col):
        """检查是否是有效的落子位置"""
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE and self.board[row][col] == Player.NONE
    
    def make_move(self, row, col):
        """落子"""
        if not self.is_valid_move(row, col) or self.game_over:
            return False
        
        self.board[row][col] = self.current_player
        self.last_move = (row, col)
        
        if self.check_winner(row, col):
            self.game_over = True
            self.winner = self.current_player
        elif self.is_board_full():
            self.game_over = True
            self.winner = None
        else:
            self.current_player = Player.WHITE if self.current_player == Player.BLACK else Player.BLACK
        
        return True
    
    def check_winner(self, row, col):
        """检查是否有玩家获胜"""
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # 横、竖、斜
        player = self.board[row][col]
        
        for dx, dy in directions:
            count = 1
            # 正向检查
            for i in range(1, 5):
                new_row, new_col = row + dx * i, col + dy * i
                if (0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE and
                    self.board[new_row][new_col] == player):
                    count += 1
                else:
                    break
            
            # 反向检查
            for i in range(1, 5):
                new_row, new_col = row - dx * i, col - dy * i
                if (0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE and
                    self.board[new_row][new_col] == player):
                    count += 1
                else:
                    break
            
            if count >= 5:
                return True
        
        return False
    
    def is_board_full(self):
        """检查棋盘是否已满"""
        for row in self.board:
            if Player.NONE in row:
                return False
        return True
    
    def reset(self):
        """重置游戏"""
        self.board = [[Player.NONE for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = Player.BLACK
        self.game_over = False
        self.winner = None
        self.last_move = None
    
    def ai_move(self):
        """简单的AI落子策略"""
        # 优先级：1.获胜 2.防守 3.进攻 4.随机
        best_move = None
        best_score = -1
        
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.board[row][col] == Player.NONE:
                    score = self.evaluate_position(row, col)
                    if score > best_score:
                        best_score = score
                        best_move = (row, col)
        
        if best_move:
            self.make_move(best_move[0], best_move[1])
    
    def evaluate_position(self, row, col):
        """评估位置的得分"""
        score = 0
        
        # 检查AI(白棋)能否获胜
        self.board[row][col] = Player.WHITE
        if self.check_winner(row, col):
            self.board[row][col] = Player.NONE
            return 10000
        self.board[row][col] = Player.NONE
        
        # 检查是否需要防守
        self.board[row][col] = Player.BLACK
        if self.check_winner(row, col):
            self.board[row][col] = Player.NONE
            return 5000
        self.board[row][col] = Player.NONE
        
        # 评估位置的战略价值
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dx, dy in directions:
            # 检查白棋连子数
            white_count = self.count_consecutive(row, col, dx, dy, Player.WHITE)
            black_count = self.count_consecutive(row, col, dx, dy, Player.BLACK)
            
            score += white_count * white_count * 10
            score += black_count * black_count * 5
        
        # 中心位置加分
        center = BOARD_SIZE // 2
        distance = abs(row - center) + abs(col - center)
        score += (BOARD_SIZE - distance) * 2
        
        return score
    
    def count_consecutive(self, row, col, dx, dy, player):
        """计算某方向上的连续棋子数"""
        count = 0
        for i in range(-4, 5):
            new_row, new_col = row + dx * i, col + dy * i
            if (0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE and
                self.board[new_row][new_col] == player):
                count += 1
            else:
                if count > 0:
                    break
        return count
    
    def run(self):
        """运行游戏主循环"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.reset()
                
                elif event.type == pygame.MOUSEBUTTONDOWN and not self.game_over:
                    if self.mode == GameMode.PVP or self.current_player == Player.BLACK:
                        pos = self.get_board_position(event.pos)
                        if pos:
                            row, col = pos
                            self.make_move(row, col)
                            
                            # 如果是人机模式且游戏未结束，AI落子
                            if (self.mode == GameMode.PVE and 
                                not self.game_over and 
                                self.current_player == Player.WHITE):
                                pygame.time.wait(300)  # 延迟一下让AI看起来在"思考"
                                self.ai_move()
            
            # 绘制游戏画面
            self.draw_board()
            self.draw_pieces()
            self.draw_info()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

def main():
    """主函数"""
    print("欢迎来到五子棋游戏!")
    print("1. 人人对战")
    print("2. 人机对战")
    
    choice = input("请选择游戏模式 (1/2): ").strip()
    
    if choice == '2':
        mode = GameMode.PVE
        print("你执黑棋，AI执白棋")
    else:
        mode = GameMode.PVP
        print("黑棋先行")
    
    game = Gomoku(mode)
    game.run()

if __name__ == "__main__":
    main()
