# file_utils.py

import hashlib
from pathlib import Path


def generate_file_hash(file_path: str | Path, num_bytes: int = 1024) -> str:
    """
    Gera um hash SHA256 baseado no tamanho do arquivo e em até 1024 bytes espaçados uniformemente.
    Retorna o hash como string hexadecimal.
    """
    file_path = Path(file_path)
    file_size = file_path.stat().st_size
    if file_size == 0:
        return hashlib.sha256(b'').hexdigest()

    with file_path.open('rb') as f:
        if file_size <= num_bytes:
            content = f.read()
        else:
            # Seleciona num_bytes espaçados uniformemente
            positions = [int(i * (file_size - 1) / (num_bytes - 1)) for i in range(num_bytes)]
            content = bytearray()
            for pos in positions:
                f.seek(pos)
                content.append(f.read(1)[0])

    hasher = hashlib.sha256()
    hasher.update(file_size.to_bytes(8, 'big'))  # 8 bytes para o tamanho
    hasher.update(content)
    return hasher.hexdigest()