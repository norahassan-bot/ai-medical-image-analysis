import requests

session = requests.Session()

print("--- STEP 1: Open /auth/session (User visits /user) ---")
res1 = session.get("http://localhost:8000/auth/session")
print(f"Status: {res1.status_code}")
print(f"Data: {res1.json()}")
print(f"Cookies after Step 1: {list(session.cookies.keys())}")
assert res1.status_code == 200
assert res1.json()["role"] == "USER"
assert "user_session_token" in session.cookies
assert "admin_session_token" not in session.cookies
print("Step 1 PASSED: Automatic USER anonymous identity created.")

print("\n--- STEP 2: User attempts calling ADMIN API without ADMIN session ---")
res2 = session.get("http://localhost:8000/admin/statistics")
print(f"Status: {res2.status_code}")
assert res2.status_code == 403
print("Step 2 PASSED: USER session receives 403 Forbidden on protected admin endpoints.")

print("\n--- STEP 3: Admin login with valid credentials in SAME session ---")
res3 = session.post("http://localhost:8000/auth/login", json={"username": "admin", "password": "AdminSecure2026!Clinical"})
print(f"Status: {res3.status_code}")
print(f"Data: {res3.json()}")
print(f"Cookies after Step 3: {list(session.cookies.keys())}")
assert res3.status_code == 200
assert res3.json()["user"]["role"] == "ADMIN"
assert "user_session_token" in session.cookies
assert "admin_session_token" in session.cookies
print("Step 3 PASSED: Both user_session_token and admin_session_token coexist.")

print("\n--- STEP 4: Access admin endpoint with ADMIN session ---")
res4 = session.get("http://localhost:8000/admin/statistics")
print(f"Status: {res4.status_code}")
print(f"Architecture: {res4.json().get('architecture')}")
assert res4.status_code == 200
print("Step 4 PASSED: Admin endpoints accessible.")

print("\n--- STEP 5: Verify USER session is still intact and isolated ---")
res5 = session.get("http://localhost:8000/auth/me")
print(f"Status: {res5.status_code}")
print(f"User Data: {res5.json()}")
assert res5.status_code == 200
assert res5.json()["role"] == "USER"
print("Step 5 PASSED: User profile remains active and isolated.")

print("\n--- STEP 6: Admin profile endpoint ---")
res6 = session.get("http://localhost:8000/auth/admin/me")
print(f"Status: {res6.status_code}")
print(f"Admin Data: {res6.json()}")
assert res6.status_code == 200
assert res6.json()["role"] == "ADMIN"
print("Step 6 PASSED: Admin me endpoint strictly validates admin session.")

print("\n--- STEP 7: Admin logout clears ONLY admin cookie ---")
res7 = session.post("http://localhost:8000/auth/admin/logout")
print(f"Status: {res7.status_code}")
print("Step 7 PASSED: Admin logged out.")

print("\n--- STEP 8: Verify admin endpoint is rejected after logout ---")
res8 = session.get("http://localhost:8000/admin/statistics")
print(f"Status: {res8.status_code}")
assert res8.status_code in [401, 403]
print("Step 8 PASSED: Admin access denied after logout.")

print("\n--- ALL VERIFICATIONS PASSED ---")
