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

def encrypt_caesar(plaintext: str, shift: int = 3) -> str:
    """
    Encrypts plaintext using a Caesar cipher.
    >>> encrypt_caesar("PYTHON")
    'SBWKRQ'
    >>> encrypt_caesar("python")
    'sbwkrq'
    >>> encrypt_caesar("Python3.6")
    'Sbwkrq3.6'
    >>> encrypt_caesar("")
    ''
    """

    ciphertext = ""
    for c in plaintext:
        if is_alpha(c):
            ciphertext += shift_char(c, shift)
        else:
            ciphertext += c
    
    return ciphertext


def decrypt_caesar(ciphertext: str, shift: int = 3) -> str:
    """
    Decrypts a ciphertext using a Caesar cipher.
    >>> decrypt_caesar("SBWKRQ")
    'PYTHON'
    >>> decrypt_caesar("sbwkrq")
    'python'
    >>> decrypt_caesar("Sbwkrq3.6")
    'Python3.6'
    >>> decrypt_caesar("")
    ''
    """
    plaintext = ""
    for c in ciphertext:
        if is_alpha(c):
            plaintext += shift_char(c, -shift)
        else:
            plaintext += c
    
    return plaintext
