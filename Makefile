DOCKER_USERNAME = yasminsultana
IMAGE_NAME = cluster-monitor
VERSION = latest
NAMESPACE = default

build:
	docker build -t $(DOCKER_USERNAME)/$(IMAGE_NAME):$(VERSION) .

push:
	docker push $(DOCKER_USERNAME)/$(IMAGE_NAME):$(VERSION)

build-push: build push

deploy:
	kubectl apply -f cluster-monitor-deployment.yaml

update:
	kubectl set image deployment/cluster-monitor cluster-monitor=$(DOCKER_USERNAME)/$(IMAGE_NAME):$(VERSION) -n $(NAMESPACE)
	kubectl rollout status deployment/cluster-monitor -n $(NAMESPACE)

logs:
	kubectl logs -f deployment/cluster-monitor -n $(NAMESPACE)

status:
	kubectl get all -n $(NAMESPACE) -l app=cluster-monitor

port-forward:
	kubectl port-forward svc/cluster-monitor-service 8080:8080 -n $(NAMESPACE)

restart:
	kubectl rollout restart deployment/cluster-monitor -n $(NAMESPACE)

clean:
	kubectl delete -f cluster-monitor-deployment.yaml

all: build-push deploy

