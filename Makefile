version = master

.PHONY: clean test publish build

clean:
	find . -name __pycache__ -type d -exec rm -rf {} +

test:
	py.test tests

publish:
	spynl dev translate -a refresh -p spynl
	spynl dev translate -p spynl
	python setup.py sdist bdist_wheel upload -r swcloud

build:
	cd docker; \
		docker build -t spynl \
		--build-arg BUILD_NR=${BUILD_NR} \
		--build-arg BUILD_TIME="$(date)" \
		--build-arg VERSION=$(version) .
