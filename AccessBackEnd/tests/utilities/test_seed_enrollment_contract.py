from pathlib import Path


def test_seed_enrollments_reference_seeded_class_names():
    root = Path(__file__).resolve().parents[3]
    classes_sql = (root / 'AccessBackEnd/instance/seed_classes.sql').read_text(encoding='utf-8')
    enroll_sql = (root / 'AccessBackEnd/instance/seed_user_class_enrollments.sql').read_text(encoding='utf-8')

    assert 'Soup Basics 101' in classes_sql
    assert 'Soup Lab' in classes_sql
    assert "class_record.name IN ('Soup Basics 101', 'Soup Lab')" in enroll_sql
