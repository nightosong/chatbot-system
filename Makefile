.PHONY: help build up down restart logs logs-backend logs-frontend clean rebuild status shell-backend shell-frontend

help: ## 显示帮助信息
	@echo "AI Chat System - Docker 命令"
	@echo ""
	@echo "使用方式: make [command]"
	@echo ""
	@echo "命令列表:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

build: ## 构建 Docker 镜像
	@echo "🔨 构建 Docker 镜像..."
	docker-compose build

build-backend: ## 仅构建后端镜像
	@echo "🔨 构建后端镜像..."
	docker-compose build backend

build-frontend: ## 仅构建前端镜像
	@echo "🔨 构建前端镜像..."
	docker-compose build frontend

up: ## 启动服务
	@echo "🚀 启动服务..."
	docker-compose up -d
	@echo "✅ 服务已启动！"
	@echo "📍 前端: http://localhost:3000"
	@echo "📍 后端 API: http://localhost:8000"
	@echo "📍 API 文档: http://localhost:8000/docs"

up-backend: ## 仅启动后端
	@echo "🚀 启动后端..."
	docker-compose up -d backend

up-frontend: ## 仅启动前端
	@echo "🚀 启动前端..."
	docker-compose up -d frontend

down: ## 停止服务
	@echo "🛑 停止服务..."
	docker-compose down
	@echo "✅ 服务已停止！"

restart: ## 重启服务
	@echo "🔄 重启服务..."
	docker-compose restart
	@echo "✅ 服务已重启！"

restart-backend: ## 重启后端
	@echo "🔄 重启后端..."
	docker-compose restart backend

restart-frontend: ## 重启前端
	@echo "🔄 重启前端..."
	docker-compose restart frontend

logs: ## 查看所有日志
	docker-compose logs -f

logs-backend: ## 查看后端日志
	docker-compose logs -f backend

logs-frontend: ## 查看前端日志
	docker-compose logs -f frontend

clean: ## 清理容器和镜像
	@echo "🧹 清理 Docker 资源..."
	docker-compose down -v
	docker-compose rm -f
	@echo "✅ 清理完成！"

rebuild: clean build up ## 完全重建并启动

rebuild-backend: ## 重建后端
	@echo "🔄 重建后端..."
	docker-compose stop backend
	docker-compose rm -f backend
	docker-compose build backend
	docker-compose up -d backend

rebuild-frontend: ## 重建前端
	@echo "🔄 重建前端..."
	docker-compose stop frontend
	docker-compose rm -f frontend
	docker-compose build frontend
	docker-compose up -d frontend

status: ## 查看服务状态
	@echo "📊 服务状态:"
	docker-compose ps

shell-backend: ## 进入后端容器 shell
	docker-compose exec backend /bin/bash

shell-frontend: ## 进入前端容器 shell
	docker-compose exec frontend /bin/sh

health: ## 检查服务健康状态
	@echo "🏥 检查服务健康状态..."
	@echo "后端健康检查:"
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ 后端未响应"
	@echo ""
	@echo "前端健康检查:"
	@curl -s http://localhost:3000/health || echo "❌ 前端未响应"

# 默认命令
.DEFAULT_GOAL := help
