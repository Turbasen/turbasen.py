test:
	docker-compose run --rm dev py.test

build:
	docker-compose build dev

publish:
	python setup.py sdist bdist_egg upload --sign

clean:
	python setup.py clean -a
	find . -name \*.pyc | xargs rm

.PHONY: test publish clean