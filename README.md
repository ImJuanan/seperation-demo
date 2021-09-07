# seperation-demo
This repo shows a flask app about seperation of front-end and back-end.
Once you cloned the repo, you need to create a virtual environment first
```
pipenv install --dev
```
Then, reset the database
```
pipenv run flask resetdb
```
Now, you can run the program
```
pipenv run flask run
```
By the way, remember choose a correct ChromeDriver since the program uses selenium to acquire data.
