# Run and verify (run one step at a time)

Open a terminal **inside the folder that contains `manage.py`**.

1. `py -m venv venv` then `venv\Scripts\activate`
2. `python -m pip install -r requirements.txt`
3. `python manage.py check`
4. `python manage.py makemigrations --check --dry-run` (expected: "No changes detected")
5. `python manage.py migrate` (applies `0003_request_workflow`; existing data is kept)
6. `python manage.py test -v 2`
7. `python manage.py runserver`

Back up first: copy `db.sqlite3` to `db.sqlite3.bak`.
