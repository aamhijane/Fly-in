#####################################
######### VENV | PACKAGES ###########
#####################################

VENV 		= .venv
VENV_PATH 	= $(VENV)/bin
MAP			= ./maps/hard/02_capacity_hell.txt
ARGS		?= $(MAP)

PYTHON		?= python3
FLAKE8 		?= flake8
MYPY 		?= mypy

ifdef VIRTUAL_ENV
	PYTHON := python3
	FLAKE8 := flake8
	MYPY   := mypy
endif

ifndef VERBOSE
.SILENT:
endif

#####################################
############## RULES ################
#####################################

$(VENV):
	@echo "Setting up venv..."
	@python3 -m venv $(VENV); true
	@echo ""
	@echo "Done! Run: source .venv/bin/activate"
	@echo ""

install: $(VENV)
	@echo "Installing dependencies..."
	@$(VENV_PATH)/python3 -m pip install -r requirements.txt; true
	@echo "Done!"

run:
	@$(PYTHON) main.py $(ARGS); true

debug:
	@$(PYTHON) -m pdb main.py; true

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	@echo "Project cleaned!"

lint:
	@$(FLAKE8) . --exclude .venv,__pycache__; true
	@$(MYPY) . --exclude '.venv|__pycache__' \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs; true

lint-strict:
	@$(FLAKE8) . --exclude .venv,__pycache__; true
	@$(MYPY) . --strict --exclude '.venv|__pycache__'; true
