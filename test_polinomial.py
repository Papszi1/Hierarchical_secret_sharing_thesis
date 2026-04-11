import sqlite3
import json
from unittest.mock import MagicMock
import pytest
import secrets
from decomposition import string_to_int, int_to_string

def test_round_trip():
    original = "SecretMessage123"
    integer_value = string_to_int(original)
    final_string = int_to_string(integer_value)
    assert final_string == original

def test_empty_string():
    original = ""
    assert int_to_string(string_to_int(original)) == original

def test_unicode_characters():
    original = "Python"
    assert int_to_string(string_to_int(original)) == original


from decomposition import generate_coefficients

def test_xor_property():
    secret = 12345
    h = 5
    q = 65536
    
    coeffs = generate_coefficients(secret, h, q)
    
    total_xor = 0
    for c in coeffs:
        total_xor ^= c
        
    assert total_xor == secret

def test_correct_number_of_coefficients():
    h = 10
    coeffs = generate_coefficients(100, h, 1000)
    assert len(coeffs) == h

def test_coefficients_within_bounds():
    h = 5
    q = 256
    coeffs = generate_coefficients(10, h, q)
    
    for i in range(h - 1):
        assert coeffs[i] < q


from decomposition import evaluate_f

def test_evaluate_f_at_zero():
    q = 100
    a0 = 42
    coeffs = [1, 2, 3]
    result = evaluate_f(0, coeffs, a0, q)
    assert result == a0 % q

def test_evaluate_f_simple_linear():
    q = 100
    assert evaluate_f(1, [2], 5, q) == 7

def test_evaluate_f_modular_arithmetic():
    assert evaluate_f(1, [10], 10, 15) == 5

def test_evaluate_f_no_higher_coeffs():
    q = 100
    a0 = 10
    assert evaluate_f(5, [], a0, q) == a0 % q

def test_horner_logic_correctness():
    q = 100
    assert evaluate_f(2, [3, 2], 1, q) == 15


from decomposition import distribute_shares

@pytest.fixture
def temp_db():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE participants (id INTEGER, shares TEXT)")
    cursor.execute("INSERT INTO participants (id) VALUES (1), (2)")
    yield conn
    conn.close()

def test_distribute_shares_db_update(temp_db):
    p1 = MagicMock(i=1)
    p2 = MagicMock(i=2)
    
    hierarchy = MagicMock()
    hierarchy.h = 2
    hierarchy.levels = {
        1: [p1],
        2: [p2]
    }

    secret = "TopSecret"
    q = 65537
    distribute_shares(secret, hierarchy, q, temp_db)

    cursor = temp_db.cursor()
    
    cursor.execute("SELECT shares FROM participants WHERE id = 1")
    p1_shares = json.loads(cursor.fetchone()[0])
    assert len(p1_shares) == 1 
    
    cursor.execute("SELECT shares FROM participants WHERE id = 2")
    p2_shares = json.loads(cursor.fetchone()[0])
    assert len(p2_shares) == 2


from decryption import modular_inverse


def test_standard_inverse():
    assert modular_inverse(3, 7) == 5

def test_inverse_property():
    n = 42
    q = 101
    inv = modular_inverse(n, q)
    assert (n * inv) % q == 1

def test_inverse_large_prime():
    q = 2**31 - 1
    n = 1234567
    inv = modular_inverse(n, q)
    assert (n * inv) % q == 1

def test_invalid_inverse():
    with pytest.raises(ValueError):
        modular_inverse(10, 5)


from decryption import lagrange_interpolation
def test_lagrange_linear():
    q = 101
    points = [[1, 5], [2, 7]]
    result = lagrange_interpolation(points, q)
    assert result == [3, 2]

def test_lagrange_quadratic():
    q = 101
    points = [[1, 6], [2, 11], [3, 18]]
    result = lagrange_interpolation(points, q)
    assert result == [3, 2, 1]

def test_integration_evaluate_and_interpolate():
    q = 65537
    a0 = 15
    coeffs = [5, 10] 
    points = []
    for x in range(1, 4):
        y = evaluate_f(x, coeffs, a0, q)
        points.append([x, y])

    recovered_poly = lagrange_interpolation(points, q)
    assert recovered_poly[0] == a0
    reconstructed_coeffs = recovered_poly[1:]
    assert reconstructed_coeffs == coeffs


from decryption import recover_secret
def test_full_reconstruction_cycle():
    original_secret_int = 987654321
    h = 3
    q = 2**31 - 1
    a0 = 12345
    
    coeffs = generate_coefficients(original_secret_int, h, q)
    
    points = []
    for x in range(1, h + 2):
        y = evaluate_f(x, coeffs, a0, q)
        points.append([x, y])
        
    recovered_int = recover_secret(points, h, q)
    assert recovered_int == original_secret_int

def test_recover_secret_with_small_values():
    q = 65537 
    points = [[1, 25], [2, 71], [3, 143]] 

    assert recover_secret(points, 2, q) == (7 ^ 13)


from initialization import Hierarchy
def create_p(id, level):
    p = MagicMock()
    p.i = id
    p.j = level
    return p

def test_add_participant_valid():
    h = Hierarchy(3)
    p = create_p(1, 2)
    h.add_participant(p)
    assert p in h.levels[2]

def test_add_participant_invalid_level():
    h = Hierarchy(3)
    p = create_p(1, 4) 
    with pytest.raises(ValueError, match="Érvénytelen szint"):
        h.add_participant(p)

def test_is_qualified_power_threshold():
    h = Hierarchy(3)
    p1 = create_p(1, 1)
    p2 = create_p(2, 2)
    h.add_participant(p1)
    h.add_participant(p2)
    
    qualified, message = h.is_qualified([p1, p2])
    assert qualified is False
    assert "Alacsony hatalom" in message

def test_is_qualified_too_many_at_level():
    h = Hierarchy(3)
    p1 = create_p(1, 2)
    p2 = create_p(2, 2) 
    h.add_participant(p1)
    h.add_participant(p2)
    
    qualified, message = h.is_qualified([p1, p2])
    assert qualified is False
    assert "Tul sok resztvevo" in message

def test_is_qualified_success():
    h = Hierarchy(3)
    p1 = create_p(1, 3) 
    p2 = create_p(2, 1) 
    h.add_participant(p1)
    h.add_participant(p2)
    
    qualified, message = h.is_qualified([p1, p2])
    assert qualified is True
    assert "kvalifikált" in message