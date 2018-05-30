.PHONY: all install-dev test test-all tox docs audit clean-pyc docs-upload

install-dev:
	pip install -q -e .[dev]

test: clean-pyc install-dev
	pytest

test-all: clean-pyc install-dev
	tox

tox: test-all

BUILDDIR = _build
docs: install-dev
	$(MAKE) -C docs html BUILDDIR=$(BUILDDIR)

check:
	python setup.py check -r -s

clean-pyc:
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +

# Only useful on Nicola's own machine :-)
docs-upload: BUILDDIR = ~/code/eve.docs
docs-upload: docs
	cd $(BUILDDIR)/html && \
		git commit -am "rebuild docs" && \
		git push
