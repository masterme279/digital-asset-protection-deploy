# SENTINEL Backend

Digital asset protection backend built with Django REST Framework, JWT auth, and MongoDB metadata storage.

## Overview

- Email-based custom user authentication
- JWT login with access and refresh tokens
- Asset upload for mp4, jpg, jpeg, png
- SHA256 duplicate detection
- MongoDB storage for asset metadata

## Tech Stack

- Python 3.11
- Django 4.2.7
- Django REST Framework 3.14.0
- djangorestframework-simplejwt 5.3.0
- PyMongo 4.6.0

## Quick Setup (Windows)

1. Create and activate virtual environment (Python 3.11):

```powershell
py -3.11 -m venv .venv
& ".venv/Scripts/Activate.ps1"
```

2. Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install django-extensions
```

3. Configure environment:

```powershell
Copy-Item .env.example .env
```

Set at least these values in `.env`:

```env
SECRET_KEY=change-me
DEBUG=True
MONGO_URI=mongodb://localhost:27017/sentinel
```

4. Run database and start server:

```powershell
python manage.py migrate
python manage.py runserver
```

Server URL: http://127.0.0.1:8000/

## API Endpoints

### Auth

- POST `/api/auth/register/`
- POST `/api/auth/login/`
- GET `/api/auth/profile/`

### Assets

- POST `/api/assets/upload/`
- GET `/api/assets/`
- GET `/api/assets/<asset_id>/`
- DELETE `/api/assets/<asset_id>/`

## Validation Rules

- Maximum file size: 50 MB
- Allowed extensions: mp4, jpg, jpeg, png

## Troubleshooting

- `ModuleNotFoundError: django_extensions`
  - Run: `python -m pip install django-extensions`
- `No Python at ...Python312...`
  - Recreate `.venv` with Python 3.11 and reinstall requirements.
- Mongo errors on asset APIs
  - Verify MongoDB is running and `MONGO_URI` is valid.

## Useful Commands

```powershell
python manage.py check
python manage.py test
python manage.py createsuperuser
```
    "id": 1,
    "full_name": "John Doe",
    "email": "john@example.com",
    "contact_no": "9876543210",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

### Login Response
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "full_name": "John Doe",
    "email": "john@example.com"
  }
}
```

### Upload Response
```json
{
  "message": "Upload successful",
  "asset_id": "65a1b2c3d4e5f6789012345",
  "file_hash": "a1b2c3d4e5f6...",
  "file_path": "/media/videos/uuid-filename.mp4",
  "metadata": {
    "size": 123456,
    "content_type": "video/mp4",
    "original_name": "video.mp4"
  }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Ensure MongoDB is running
   - Check MONGO_URI in .env file
   - Verify network connectivity

2. **File Upload Fails**
   - Check media directory permissions
   - Verify file size limits
   - Ensure allowed file types

3. **JWT Token Issues**
   - Check token expiration
   - Verify Authorization header format
   - Ensure proper token refresh

## 📞 Support

For issues and questions, please refer to the code documentation or create an issue in the project repository.
