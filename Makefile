publish:
	pip install -U setuptools wheel twine
	python setup.py sdist
	python setup.py bdist_wheel
	twine upload dist/*
	rm -fr build dist sauna.egg-info

deb:
	docker build -t sauna-deb-package -f Dockerfile_deb .
	docker run --rm -v /tmp/sauna/:/output sauna-deb-package 
	@echo "Debian package available in /tmp/sauna"

clean:
	rm -fr build dist sauna.egg-info

