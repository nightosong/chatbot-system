const API_URL = 'http://localhost:5000/api';
const BOARD_SIZE = 15;
const CELL_SIZE = 40;
const PADDING = 20;
const BOARD_WIDTH = CELL_SIZE * (BOARD_SIZE - 1) + PADDING * 2;

let canvas, ctx;
let gameMode = null;
let board = [];
let currentPlayer = 1;
let gameOver = false;
let lastMove = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    canvas = document.getElementById('gameBoard');
    ctx = canvas.getContext('2d');
    
    canvas.width = BOARD_WIDTH;
    canvas.height = BOARD_WIDTH;
    
    canvas.addEventListener('click', handleClick);
});

function showModeSelection() {
    document.getElementById('modeSelection').style.display = 'block';
    document.getElementById('gameBoardContainer').style.display = 'none';
    document.getElementById('restartBtn').style.display = 'none';
    document.getElementById('status').textContent = '请选择游戏模式';
    gameOver = false;
    lastMove = null;
}

async function startGame(mode) {
    gameMode = mode;
    
    try {
        const response = await fetch(`${API_URL}/new_game`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_id: 'default',
                mode: mode
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            board = data.board;
            currentPlayer = data.current_player;
            gameOver = false;
            lastMove = null;
            
            document.getElementById('modeSelection').style.display = 'none';
            document.getElementById('gameBoardContainer').style.display = 'flex';
            document.getElementById('restartBtn').style.display = 'inline-block';
            
            updateStatus();
            drawBoard();
        }
    } catch (error) {
        console.error('Error starting game:', error);
        alert('无法连接到服务器，请确保后端服务已启动');
    }
}

function drawBoard() {
    // Clear canvas
    ctx.fillStyle = '#daa520';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 1;
    
    for (let i = 0; i < BOARD_SIZE; i++) {
        // Vertical lines
        ctx.beginPath();
        ctx.moveTo(PADDING + i * CELL_SIZE, PADDING);
        ctx.lineTo(PADDING + i * CELL_SIZE, PADDING + (BOARD_SIZE - 1) * CELL_SIZE);
        ctx.stroke();
        
        // Horizontal lines
        ctx.beginPath();
        ctx.moveTo(PADDING, PADDING + i * CELL_SIZE);
        ctx.lineTo(PADDING + (BOARD_SIZE - 1) * CELL_SIZE, PADDING + i * CELL_SIZE);
        ctx.stroke();
    }
    
    // Draw star points
    const starPoints = [
        [3, 3], [3, 11], [11, 3], [11, 11], [7, 7]
    ];
    
    ctx.fillStyle = '#000';
    starPoints.forEach(([x, y]) => {
        ctx.beginPath();
        ctx.arc(PADDING + x * CELL_SIZE, PADDING + y * CELL_SIZE, 4, 0, 2 * Math.PI);
        ctx.fill();
    });
    
    // Draw pieces
    for (let i = 0; i < BOARD_SIZE; i++) {
        for (let j = 0; j < BOARD_SIZE; j++) {
            if (board[i][j] !== 0) {
                drawPiece(i, j, board[i][j]);
            }
        }
    }
    
    // Draw last move marker
    if (lastMove) {
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.arc(
            PADDING + lastMove.col * CELL_SIZE,
            PADDING + lastMove.row * CELL_SIZE,
            5,
            0,
            2 * Math.PI
        );
        ctx.fill();
    }
}

function drawPiece(row, col, player) {
    const x = PADDING + col * CELL_SIZE;
    const y = PADDING + row * CELL_SIZE;
    const radius = CELL_SIZE * 0.4;
    
    // Draw shadow
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.beginPath();
    ctx.arc(x + 2, y + 2, radius, 0, 2 * Math.PI);
    ctx.fill();
    
    // Draw piece
    const gradient = ctx.createRadialGradient(x - radius * 0.3, y - radius * 0.3, 0, x, y, radius);
    
    if (player === 1) {
        gradient.addColorStop(0, '#666');
        gradient.addColorStop(1, '#000');
    } else {
        gradient.addColorStop(0, '#fff');
        gradient.addColorStop(1, '#ccc');
    }
    
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.fill();
    
    // Draw border
    ctx.strokeStyle = player === 1 ? '#000' : '#999';
    ctx.lineWidth = 2;
    ctx.stroke();
}

async function handleClick(event) {
    if (gameOver) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    const col = Math.round((x - PADDING) / CELL_SIZE);
    const row = Math.round((y - PADDING) / CELL_SIZE);
    
    if (row < 0 || row >= BOARD_SIZE || col < 0 || col >= BOARD_SIZE) return;
    if (board[row][col] !== 0) return;
    
    try {
        const response = await fetch(`${API_URL}/move`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_id: 'default',
                row: row,
                col: col
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            board = data.board;
            currentPlayer = data.current_player;
            gameOver = data.game_over;
            lastMove = { row, col };
            
            drawBoard();
            updateStatus();
            
            // Handle AI move in PVE mode
            if (data.ai_move) {
                setTimeout(() => {
                    lastMove = { row: data.ai_move.row, col: data.ai_move.col };
                    drawBoard();
                    updateStatus();
                }, 300);
            }
            
            if (gameOver) {
                setTimeout(() => {
                    if (data.winner === 0) {
                        alert('平局！');
                    } else if (gameMode === 'pve' && data.winner === 2) {
                        alert('AI 获胜！');
                    } else {
                        const winnerText = data.winner === 1 ? '黑棋' : '白棋';
                        alert(`${winnerText}获胜！`);
                    }
                }, 100);
            }
        }
    } catch (error) {
        console.error('Error making move:', error);
    }
}

function updateStatus() {
    const statusEl = document.getElementById('status');
    
    if (gameOver) {
        statusEl.textContent = '游戏结束';
    } else {
        const playerText = currentPlayer === 1 ? '黑棋' : (gameMode === 'pve' ? 'AI' : '白棋');
        statusEl.textContent = `当前回合：${playerText}`;
    }
}
