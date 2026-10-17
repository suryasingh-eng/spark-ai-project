from api.database import init_db, connect
from api.auth import hash_password, verify_password

def main():
    init_db()
    hashed = hash_password("SparkTestPassword123")
    assert verify_password("SparkTestPassword123", hashed)
    assert not verify_password("wrong-password", hashed)
    with connect() as db:
        tables = {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {"users", "syllabi", "study_plans", "quiz_results"}
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"
    print("SPARK AI smoke test passed.")

if __name__ == "__main__":
    main()
