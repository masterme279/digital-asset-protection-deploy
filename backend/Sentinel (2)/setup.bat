@echo off
echo Setting up SENTINEL Backend...

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file...
    copy .env.example .env
    echo Please edit .env file with your configuration
)

REM Create media directories
echo Creating media directories...
if not exist media mkdir media
if not exist media\videos mkdir media\videos

REM Run Django migrations
echo Running Django migrations...
python manage.py makemigrations
python manage.py migrate

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Edit .env file with your MongoDB URI and secret key
echo 2. Run 'python manage.py runserver' to start the development server
echo 3. Visit http://localhost:8000/api/auth/register/ to test registration
echo.
pause
