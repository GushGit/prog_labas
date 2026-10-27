ALPHA_MOD = ord('z') - ord('a') + 1

def is_alpha(c: chr) -> bool:
    return  'a' <= c <= 'z' or \
            'A' <= c <= 'Z'

def get_idx(c: chr) -> int:
    if c <= 'Z':
        return ord(c) - ord('A')
    else:
        return ord(c) - ord('a')

def get_st(c: chr) -> int:
    if c <= 'Z':
        return ord('A')
    else:
        return ord('a')

def mod(x: int,  M: int) -> int:
    return ((x % M) + M) % M

def shift_char(c: chr, d: int) -> chr:
    return chr(get_st(c) + mod(get_idx(c) + d, ALPHA_MOD))

def encrypt_vigenere(plaintext: str, keyword: str) -> str:
    """
    Encrypts plaintext using a Vigenere cipher.
    >>> encrypt_vigenere("PYTHON", "A")
    'PYTHON'
    >>> encrypt_vigenere("python", "a")
    'python'
    >>> encrypt_vigenere("ATTACKATDAWN", "LEMON")
    'LXFOPVEFRNHR'
    """
    ciphertext = ""
    n = len(plaintext)
    m = len(keyword)

    for i in range(n):
        c = plaintext[i]
        if is_alpha(c):
            ciphertext += shift_char(c, get_idx(keyword[i % m]))
        else:
            ciphertext += c
    return ciphertext


def decrypt_vigenere(ciphertext: str, keyword: str) -> str:
    """
    Decrypts a ciphertext using a Vigenere cipher.
    >>> decrypt_vigenere("PYTHON", "A")
    'PYTHON'
    >>> decrypt_vigenere("python", "a")
    'python'
    >>> decrypt_vigenere("LXFOPVEFRNHR", "LEMON")
    'ATTACKATDAWN'
    """
    plaintext = ""
    n = len(ciphertext)
    m = len(keyword)

    for i in range(n):
        c = ciphertext[i]
        if is_alpha(c):
            plaintext += shift_char(c, -get_idx(keyword[i % m]))
        else:
            plaintext += c
    return plaintext