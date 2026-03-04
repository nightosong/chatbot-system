# 🎮 五子棋游戏项目

一个功能完整的 Web 版五子棋游戏，支持人人对战和人机对战两种模式。

## 📁 项目结构

```
五子棋项目/
├── gomoku.py              # Python 桌面版（Pygame）
├── backend/               # 后端服务
│   ├── app.py            # Flask 服务器
│   └── requirements.txt  # Python 依赖
├── frontend/             # 前端页面
│   ├── index.html        # 主页面
│   ├── css/
│   │   └── style.css    # 样式文件
│   └── js/
│       └── game.js      # 游戏逻辑
└── README.md            # 项目说明
```

## 🎯 功能特点

### Web 版
- ✨ 现代化的 UI 设计
- 🎨 精美的棋盘和棋子动画
- 📱 响应式布局，支持移动端
- 🎯 双模式支持（人人对战/人机对战）
- 🤖 智能 AI 对手
- 🔄 实时游戏状态更新
- 💡 最后落子标记

### 桌面版（Pygame）
- 🖥️ 基于 Pygame 的图形界面
- 🎮 完整的游戏逻辑
- 🤖 AI 对手支持
- ⌨️ 键盘快捷键

## 🚀 快速开始

### Web 版

#### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 2. 启动后端服务器

```bash
python app.py
```

服务器将在 `http://localhost:5000` 运行

#### 3. 访问游戏

在浏览器中打开 `http://localhost:5000`

### 桌面版（Pygame）

#### 1. 安装依赖

```bash
pip install pygame
```

#### 2. 运行游戏

```bash
python gomoku.py
```

## 🎮 游戏玩法

### 基本规则
1. 黑棋先行，双方轮流落子
2. 率先在横、竖、斜任一方向形成五子连珠者获胜
3. 棋盘填满无人获胜则为平局

### 操作说明

**Web 版：**
- 点击棋盘交叉点落子
- 点击"重新开始"返回模式选择

**桌面版：**
- 鼠标点击落子
- R 键：重新开始
- ESC 键：退出游戏

## 🤖 AI 算法

AI 采用评估函数策略：

1. **优先级最高**：寻找获胜机会（形成五子连珠）
2. **防守优先**：阻止对手形成四子连珠
3. **进攻策略**：积极形成连子
4. **位置优势**：优先占据棋盘中心位置

## 📝 技术栈

### Web 版
**前端**
- HTML5
- CSS3
- Vanilla JavaScript
- Canvas API

**后端**
- Python 3
- Flask
- Flask-CORS

### 桌面版
- Python 3
- Pygame

## 🛠️ 开发说明

### API 接口

#### 创建新游戏
```
POST /api/new_game
Body: {
  "game_id": "default",
  "mode": "pvp" | "pve"
}
```

#### 落子
```
POST /api/move
Body: {
  "game_id": "default",
  "row": 0-14,
  "col": 0-14
}
```

#### 获取游戏状态
```
GET /api/game_state?game_id=default
```

## 📄 许可证

MIT License

## 👨‍💻 作者

Created with ❤️

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

**享受游戏！🎉**
