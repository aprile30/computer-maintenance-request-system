# Computer Maintenance Request System (Django)

Project folder: `cmrs`  |  Django project: `config`  |  App: `maintenance`

## Run it (step by step)
1. Open the `cmrs` folder in PyCharm (or VS Code).
2. Create and activate the virtual environment:
```
python -m venv .venv
.venv\Scripts\activate
```
3. Install the packages:
```
pip install -r requirements.txt
```
4. Start Apache and MySQL in XAMPP, then create an empty database named `cmrs_db` in phpMyAdmin. The database settings are in `config/settings.py`.
5. Create the database tables:
```
python manage.py makemigrations maintenance
python manage.py migrate
```
6. Add the demo accounts and sample records:
```
python manage.py seed
```
7. Start the server:
```
python manage.py runserver
```
8. Open http://127.0.0.1:8000/ and log in.

| Role | Username | Password |
|---|---|---|
| Administrator | admin | admin12345 |
| Technician | tech1 | tech12345 |
| Faculty / Staff | faculty1 | faculty12345 |

(The pages load Bootstrap from the internet, so keep your connection on.)

## Switch to MySQL (as in the paper)
1. Create an empty database, for example `cmrs_db`, in MySQL Workbench.
2. `pip install mysqlclient`
3. In `config/settings.py`, comment out the SQLite block and uncomment the MySQL block. Put in your own user, password and port.
4. Run `makemigrations` / `migrate` / `seed` again.

## Where each wireframe from the paper is
| Wireframe | Page | URL |
|---|---|---|
| 1 Login | login.html | /login/ |
| 2 Requester dashboard | dashboard.html + requests/index.html | /dashboard/, /requests/ |
| 3 Submit request | requests/add.html | /requests/add/ |
| 4 Administrator review | requests/review.html | /requests/<id>/review/ |
| 5 Technician update | requests/update.html | /requests/<id>/update/ |

## CRUD map
| Record | Create | Read | Update | Delete |
|---|---|---|---|---|
| Maintenance request | /requests/add/ | /requests/, /requests/<id>/ | /requests/<id>/edit/ (pending or rejected) | /requests/<id>/delete/ |
| Users | /manage/users/add/ | /manage/users/ | /manage/users/<id>/edit/ | /manage/users/<id>/delete/ |
| Locations | /manage/locations/add/ | /manage/locations/ | ...edit/ | ...delete/ |
| Computers | /manage/computers/add/ | /manage/computers/ | ...edit/ | ...delete/ |
| Issue categories | /manage/categories/add/ | /manage/categories/ | ...edit/ | ...delete/ |

## Files
- `maintenance/models.py` : the 7 tables from Section 10 of the paper
- `maintenance/forms.py` : forms
- `maintenance/views.py` : all logic (roles, workflow, CRUD)
- `maintenance/urls.py` : page addresses
- `maintenance/templates/master.html` : layout with the sidebar menu
- `maintenance/templates/` : dashboard, login, requests/, crud/, reports, notifications
