"""
crear_bd.py - Script que construye la base de datos relacional SQLite
'cun_sistema.db' (Objetivo 2 del taller).

Se puede ejecutar solo:      python crear_bd.py
o ser importado por main.py (la app reutiliza crear_tablas).
"""
import sqlite3

NOMBRE_BD = "cun_sistema.db"


def crear_tablas(conn: sqlite3.Connection) -> None:
    """Crea las tablas si no existen (idempotente)."""
    cursor = conn.cursor()

    # Tabla Estudiantes (exactamente como la pide la guía)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estudiantes (
            id_estudiante TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            programa TEXT NOT NULL,
            promedio REAL DEFAULT 0.0
        )
    ''')

    # Tabla Docentes (tercera entidad del caso de estudio)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS docentes (
            id_docente TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            especialidad TEXT NOT NULL
        )
    ''')

    # Tabla Tickets de Soporte TI (la guía + docente asignado, opcional)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets_soporte (
            id_ticket INTEGER PRIMARY KEY AUTOINCREMENT,
            id_estudiante TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            estado TEXT DEFAULT 'ABIERTO',
            id_docente_asignado TEXT,
            FOREIGN KEY (id_estudiante) REFERENCES estudiantes (id_estudiante),
            FOREIGN KEY (id_docente_asignado) REFERENCES docentes (id_docente)
                ON DELETE SET NULL
        )
    ''')
    conn.commit()


def crear_base_datos_cun(ruta: str = NOMBRE_BD) -> None:
    """Conecta a SQLite, crea las tablas y cierra la conexión."""
    conn = sqlite3.connect(ruta)
    try:
        crear_tablas(conn)
    finally:
        conn.close()
    print(f"[Exitoso] Base de datos '{ruta}' creada correctamente.")


if __name__ == '__main__':
    crear_base_datos_cun()
