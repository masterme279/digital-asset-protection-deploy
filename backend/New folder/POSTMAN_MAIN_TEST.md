# Postman Main Test Guide

## Goal
Validate the main API flow end-to-end:
1. Auth flow (register, login, profile)
2. Protected access behavior
3. Asset upload and CRUD flow

## Prerequisites
- Django server running on http://127.0.0.1:8000
- MongoDB running (required for asset endpoints)
- Postman installed

## Create Postman Environment
Create an environment named Sentinel Local with variables:

- base_url = http://127.0.0.1:8000
- access_token =
- asset_id =

Select this environment before running requests.

## Main Test Sequence

### 1. Server Health
Request:
- Method: GET
- URL: {{base_url}}/

Expected:
- Status 200
- Response text includes backend running message

---

### 2. Register User
Request:
- Method: POST
- URL: {{base_url}}/api/auth/register/
- Headers: Content-Type: application/json
- Body:

```json
{
  "full_name": "Postman User",
  "email": "postman.user@example.com",
  "password": "Password123!",
  "password_confirm": "Password123!",
  "contact_no": "9876543210"
}
```

Expected:
- Status 201 (or 400 if already exists)
- Success message with user object

---

### 3. Login User
Request:
- Method: POST
- URL: {{base_url}}/api/auth/login/
- Headers: Content-Type: application/json
- Body:

```json
{
  "email": "postman.user@example.com",
  "password": "Password123!"
}
```

Expected:
- Status 200
- Response contains access and refresh

Action:
- Copy access token and set environment variable access_token

Optional Test Script (Tests tab in login request):

```javascript
const res = pm.response.json();
if (res.access) {
  pm.environment.set("access_token", res.access);
}
pm.test("Login success", function () {
  pm.response.to.have.status(200);
});
```

---

### 4. Profile (Authorized)
Request:
- Method: GET
- URL: {{base_url}}/api/auth/profile/
- Authorization tab: Bearer Token
- Token: {{access_token}}

Expected:
- Status 200
- User profile data returned

---

### 5. Profile (Unauthorized Check)
Request:
- Duplicate previous profile request
- Remove Authorization header/token

Expected:
- Status 401
- Message like authentication credentials were not provided

---

### 6. Upload Asset (Valid File)
Request:
- Method: POST
- URL: {{base_url}}/api/assets/upload/
- Authorization: Bearer {{access_token}}
- Body type: form-data
- Key: file (type File)
- Value: choose one valid file (.jpg, .jpeg, .png, .mp4)

Expected:
- Status 200 or 201
- Response includes created asset id

Action:
- Save returned id into environment variable asset_id

Optional Test Script:

```javascript
const res = pm.response.json();
if (res.id) {
  pm.environment.set("asset_id", res.id);
}
if (res._id) {
  pm.environment.set("asset_id", res._id);
}
pm.test("Upload success", function () {
  pm.expect(pm.response.code).to.be.oneOf([200, 201]);
});
```

---

### 7. List Assets
Request:
- Method: GET
- URL: {{base_url}}/api/assets/
- Authorization: Bearer {{access_token}}

Expected:
- Status 200
- List or paginated results containing uploaded item

---

### 8. Get Asset Detail
Request:
- Method: GET
- URL: {{base_url}}/api/assets/{{asset_id}}/
- Authorization: Bearer {{access_token}}

Expected:
- Status 200
- Asset details for the selected id

---

### 9. Delete Asset
Request:
- Method: DELETE
- URL: {{base_url}}/api/assets/{{asset_id}}/
- Authorization: Bearer {{access_token}}

Expected:
- Status 200 or 204

---

### 10. Confirm Delete
Request:
- Method: GET
- URL: {{base_url}}/api/assets/{{asset_id}}/
- Authorization: Bearer {{access_token}}

Expected:
- Status 404

---

## Negative Validation Tests

### A. Invalid Login
- POST {{base_url}}/api/auth/login/ with wrong password
- Expected: 401

### B. Invalid File Type Upload
- Upload a .txt file to asset upload endpoint
- Expected: 400

### C. File Size Limit
- Upload file greater than 50 MB
- Expected: 400

## Common Failures and Fixes

### 401 on profile endpoint
- Ensure URL is exactly /api/auth/profile/
- Ensure Authorization header is present
- Header must be: Bearer {{access_token}}
- Ensure access token is used (not refresh token)

### 404 on profile endpoint
- Check typo in path (for example lprofile)

### 500 on asset endpoints
- Usually MongoDB issue
- Verify MONGO_URI in .env
- Verify MongoDB service is running

## Final Pass Criteria
All main tests pass when:
- Auth endpoints behave correctly
- Protected endpoint returns 200 with token and 401 without token
- Asset upload, list, detail, delete, and post-delete check behave as expected
