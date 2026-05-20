.PHONY: up down logs status restart backup deploy all

SERVICES = actual backrest immich media-stack nextcloud nginxproxymanager openwebui pihole portainer portainer-agent stirling upsnap vaultwarden watchtower wg-easy

ifdef SERVICE
	SERVICE_PATH = $(SERVICE)
else
	SERVICE_PATH = .
endif

api-fix:
	export DOCKER_API_VERSION=1.41

up:
	cd $(SERVICE_PATH) && docker compose up -d

down:
	cd $(SERVICE_PATH) && docker compose down

logs:
	cd $(SERVICE_PATH) && docker compose logs -f

status:
	cd $(SERVICE_PATH) && docker compose ps

restart:
	cd $(SERVICE_PATH) && docker compose restart

backup:
	mkdir -p backups && tar czf backups/homelab-$(shell date +%Y%m%d-%H%M%S).tar.gz $(SERVICE_PATH)

all-up:
	@for service in $(SERVICES); do \
		echo "Starting $$service..."; \
		(cd $$service && docker compose up -d); \
	done

all-down:
	@for service in $(SERVICES); do \
		echo "Stopping $$service..."; \
		(cd $$service && docker compose down); \
	done

all-status:
	@for service in $(SERVICES); do \
		echo "\n=== $$service ==="; \
		(cd $$service && docker compose ps); \
	done

all-restart:
	@for service in $(SERVICES); do \
		echo "Restarting $$service..."; \
		(cd $$service && docker compose restart); \
	done

clean:
	@for service in $(SERVICES); do \
		(cd $$service && docker compose down -v); \
	done
	docker system prune -f
