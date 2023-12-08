lint:
	djlint . --lint
	djlint . --reformat --format-css --format-js
	ruff check .
	ruff format .

test:
	pdm run python -m coverage run -m unittest discover tests


test-coverage:
	pdm run python -m coverage report --format="markdown"