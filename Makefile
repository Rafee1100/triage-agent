.PHONY: install dev dev-web dev-server eval deploy-web deploy-server deploy

install:
	cd server && uv sync
	cd web && pnpm install

dev:
	@echo "Web: http://localhost:3000 · Server: http://localhost:8000"
	@$(MAKE) -j 2 dev-server dev-web

dev-server:
	cd server && uv run uvicorn src.api.main:app --reload --port 8000

dev-web:
	cd web && pnpm dev

eval:
	cd server && uv run python scripts/run_eval.py

deploy-server:
	cd server && fly deploy

deploy-web:
	cd web && vercel --prod

deploy: deploy-server deploy-web
