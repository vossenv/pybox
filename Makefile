
output_dir = dist
ifeq ($(OS),Windows_NT)
	RM := rmdir /S /Q
else
	RM := rm -rf
endif

cleandir:
	-$(RM) $(output_dir)

standalone:
	python -m pip install --upgrade pip
	python -m pip install --upgrade pyinstaller
	python -m pip install --upgrade setuptools
	python -m pip install pywin32
	pyinstaller --clean --noconfirm .build/app.spec

wheel:
	make cleandir
	python setup.py sdist --formats=gztar  bdist_wheel

all:
	make wheel
	make standalone