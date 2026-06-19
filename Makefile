.PHONY: docker-up docker-down install dev-backend dev-frontend neo4j-init

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

install:
	cd packages/frontend && npm install
	cd backend && poetry install

dev-backend:
	cd backend && poetry run uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd packages/frontend && npm run dev

neo4j-init:
	docker compose -f docker/docker-compose.yml exec neo4j cypher-shell -u neo4j -p ${NEO4J_PASSWORD:-perfume_dev} -f /var/lib/neo4j/import/init-fragrances.cypher
