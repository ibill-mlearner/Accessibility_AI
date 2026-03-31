from pathlib import Path


def test_seed_enrollments_reference_seeded_class_names():
    root = Path(__file__).resolve().parents[3]
    classes_sql = (root / 'AccessBackEnd/instance/seed_classes.sql').read_text(encoding='utf-8')
    enroll_sql = (root / 'AccessBackEnd/instance/seed_user_class_enrollments.sql').read_text(encoding='utf-8')

    assert 'BIOL 110: Foundations of Cell Biology' in classes_sql
    assert 'CS 220: Data Structures and Algorithms' in classes_sql
    assert "'BIOL 110: Foundations of Cell Biology'" in enroll_sql
    assert "'CS 220: Data Structures and Algorithms'" in enroll_sql
