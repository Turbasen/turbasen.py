qa: flake8 test

.PHONY: flake8
flake8:
	docker-compose run --rm dev flake8 --statistics turbasen

.PHONY: test
test:
	docker-compose run --rm dev python -m unittest

.PHONY: build
build:
	docker-compose build dev

.PHONY: publish
publish:
	python setup.py sdist bdist_egg upload --sign

.PHONY: clean
clean:
	python setup.py clean -a
	find . -name \*.pyc -delete
	rm -rf .cache/ dist/ *.egg-info/
