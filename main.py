"""
main.py - Mesa de Ayuda de TI y Gestión Académica CUN
Taller práctico integrador de Programación Orientada a Objetos.

Conceptos aplicados (guía, puntos 1-3):
  * Encapsulamiento : atributos privados (__promedio, __estado, __nombre...)
                      con propiedades/getters/setters que validan.
  * Herencia        : Estudiante(UsuarioCUN) y Docente(UsuarioCUN).
  * Polimorfismo    : obtener_rol() abstracto, cada subclase responde distinto.
  * Abstracción     : UsuarioCUN es una clase abstracta (ABC).
  * Composición     : MesaAyuda "tiene un" BaseDatos que crea y destruye ella
                      misma (el hijo no existe sin el padre).
  * Excepciones     : try/except con ValueError y sqlite3.Error.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from abc import ABC, abstractmethod

from crear_bd import crear_tablas, NOMBRE_BD

CATEGORIAS = [
    "Red / Internet",
    "Plataforma virtual",
    "Correo institucional",
    "Equipos y aulas",
    "Cuenta y contraseña",
    "Otro",
]
ESTADOS = ["ABIERTO", "EN_PROCESO", "CERRADO"]


def ruta_base_datos() -> str:
    """La BD queda junto al .exe (o junto a main.py si se corre con Python)."""
    if getattr(sys, "frozen", False):          # ejecutando como .exe
        carpeta = os.path.dirname(sys.executable)
    else:
        carpeta = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(carpeta, NOMBRE_BD)


# =====================================================================
#  1. MODELO DE CLASES (POO)
# =====================================================================
class UsuarioCUN(ABC):
    """Clase abstracta base: define el contrato común de las personas."""

    def __init__(self, identificador: str, nombre: str):
        self.__identificador = self._texto_obligatorio(identificador, "El documento / ID")
        self.__nombre = ""
        self.nombre = nombre                      # pasa por el setter (valida)

    @staticmethod
    def _texto_obligatorio(valor: str, campo: str) -> str:
        valor = (valor or "").strip()
        if not valor:
            raise ValueError(f"{campo} no puede estar vacío.")
        return valor

    @property
    def identificador(self) -> str:
        return self.__identificador

    @property
    def nombre(self) -> str:
        return self.__nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self.__nombre = self._texto_obligatorio(valor, "El nombre")

    @abstractmethod
    def obtener_rol(self) -> str:
        """Contrato obligatorio: cada subclase lo implementa a su manera."""

    def __str__(self) -> str:
        return f"{self.identificador} - {self.nombre}"


class Estudiante(UsuarioCUN):
    def __init__(self, identificador: str, nombre: str, programa: str, promedio: float = 0.0):
        super().__init__(identificador, nombre)
        self.programa = self._texto_obligatorio(programa, "El programa")
        self.__promedio = 0.0                      # atributo privado
        self.actualizar_promedio(promedio)

    # --- getter / setter con validación (encapsulamiento) ---
    def obtener_promedio(self) -> float:
        return self.__promedio

    def actualizar_promedio(self, nuevo_promedio) -> None:
        try:
            valor = float(str(nuevo_promedio).replace(",", "."))
        except ValueError:
            raise ValueError("El promedio debe ser un número (ej: 4.2).")
        if not 0.0 <= valor <= 5.0:
            raise ValueError("El promedio debe estar entre 0.0 y 5.0")
        self.__promedio = round(valor, 2)

    @property
    def promedio(self) -> float:
        return self.__promedio

    def obtener_rol(self) -> str:
        return f"Estudiante activo del programa: {self.programa}"


class Docente(UsuarioCUN):
    def __init__(self, identificador: str, nombre: str, especialidad: str):
        super().__init__(identificador, nombre)
        self.especialidad = self._texto_obligatorio(especialidad, "La especialidad")

    def obtener_rol(self) -> str:
        return f"Docente de la facultad en área: {self.especialidad}"


class TicketSoporte:
    """Solicitud técnica de la Mesa de Ayuda. El estado es privado y solo
    puede avanzar ABIERTO -> EN_PROCESO -> CERRADO."""

    def __init__(self, id_estudiante: str, categoria: str, descripcion: str,
                 estado: str = "ABIERTO", id_ticket: int | None = None,
                 id_docente: str | None = None):
        self.id_ticket = id_ticket
        self.id_estudiante = UsuarioCUN._texto_obligatorio(id_estudiante, "El estudiante")
        if categoria not in CATEGORIAS:
            raise ValueError("Selecciona una categoría válida.")
        self.categoria = categoria
        descripcion = (descripcion or "").strip()
        if len(descripcion) < 5:
            raise ValueError("La descripción debe tener al menos 5 caracteres.")
        self.descripcion = descripcion
        if estado not in ESTADOS:
            raise ValueError("Estado de ticket no válido.")
        self.__estado = estado                     # atributo privado
        self.id_docente = id_docente

    @property
    def estado(self) -> str:
        return self.__estado

    def cambiar_estado(self, nuevo_estado: str) -> None:
        if nuevo_estado not in ESTADOS:
            raise ValueError("Estado de ticket no válido.")
        if self.__estado == "CERRADO":
            raise ValueError("El ticket ya está CERRADO y no puede modificarse.")
        if ESTADOS.index(nuevo_estado) <= ESTADOS.index(self.__estado):
            raise ValueError(f"El ticket está '{self.__estado}'; solo puede avanzar de estado.")
        self.__estado = nuevo_estado

    def __str__(self) -> str:
        return f"Ticket #{self.id_ticket} [{self.estado}] {self.categoria}"


# =====================================================================
#  2. CAPA DE BASE DE DATOS (SQLite)
# =====================================================================
class BaseDatos:
    def __init__(self, ruta: str):
        self.conn = sqlite3.connect(ruta)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        crear_tablas(self.conn)

    def cerrar(self) -> None:
        self.conn.close()

    def ejecutar(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def consultar(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()


# =====================================================================
#  3. LÓGICA DE NEGOCIO: COMPOSICIÓN  (MesaAyuda "tiene un" BaseDatos)
# =====================================================================
class MesaAyuda:
    def __init__(self, ruta_bd: str):
        self.__bd = BaseDatos(ruta_bd)             # composición

    def cerrar(self) -> None:
        self.__bd.cerrar()

    # ---------------- Estudiantes ----------------
    def registrar_estudiante(self, id_, nombre, programa, promedio) -> Estudiante:
        est = Estudiante(id_, nombre, programa, promedio)       # valida
        try:
            self.__bd.ejecutar(
                "INSERT INTO estudiantes VALUES (?, ?, ?, ?)",
                (est.identificador, est.nombre, est.programa, est.promedio))
        except sqlite3.IntegrityError:
            raise ValueError(f"Ya existe un estudiante con documento {est.identificador}.")
        return est

    def listar_estudiantes(self) -> list[Estudiante]:
        filas = self.__bd.consultar("SELECT * FROM estudiantes ORDER BY nombre")
        return [Estudiante(f["id_estudiante"], f["nombre"], f["programa"], f["promedio"])
                for f in filas]

    def actualizar_promedio(self, id_, nuevo_promedio) -> Estudiante:
        f = self.__bd.consultar("SELECT * FROM estudiantes WHERE id_estudiante = ?", (id_,))
        if not f:
            raise ValueError("No existe un estudiante con ese documento.")
        est = Estudiante(f[0]["id_estudiante"], f[0]["nombre"], f[0]["programa"], f[0]["promedio"])
        est.actualizar_promedio(nuevo_promedio)                 # valida
        self.__bd.ejecutar("UPDATE estudiantes SET promedio = ? WHERE id_estudiante = ?",
                           (est.promedio, est.identificador))
        return est

    def eliminar_estudiante(self, id_) -> None:
        try:
            self.__bd.ejecutar("DELETE FROM estudiantes WHERE id_estudiante = ?", (id_,))
        except sqlite3.IntegrityError:
            raise ValueError("No se puede eliminar: el estudiante tiene tickets registrados.")

    # ---------------- Docentes ----------------
    def registrar_docente(self, id_, nombre, especialidad) -> Docente:
        doc = Docente(id_, nombre, especialidad)
        try:
            self.__bd.ejecutar("INSERT INTO docentes VALUES (?, ?, ?)",
                               (doc.identificador, doc.nombre, doc.especialidad))
        except sqlite3.IntegrityError:
            raise ValueError(f"Ya existe un docente con ID {doc.identificador}.")
        return doc

    def listar_docentes(self) -> list[Docente]:
        filas = self.__bd.consultar("SELECT * FROM docentes ORDER BY nombre")
        return [Docente(f["id_docente"], f["nombre"], f["especialidad"]) for f in filas]

    def eliminar_docente(self, id_) -> None:
        self.__bd.ejecutar("DELETE FROM docentes WHERE id_docente = ?", (id_,))

    # ---------------- Tickets ----------------
    def crear_ticket(self, id_estudiante, categoria, descripcion) -> TicketSoporte:
        ticket = TicketSoporte(id_estudiante, categoria, descripcion)   # valida
        try:
            cur = self.__bd.ejecutar(
                "INSERT INTO tickets_soporte (id_estudiante, categoria, descripcion, estado) "
                "VALUES (?, ?, ?, ?)",
                (ticket.id_estudiante, ticket.categoria, ticket.descripcion, ticket.estado))
        except sqlite3.IntegrityError:
            raise ValueError("El estudiante indicado no existe.")
        ticket.id_ticket = cur.lastrowid
        return ticket

    def _cargar_ticket(self, id_ticket: int) -> TicketSoporte:
        f = self.__bd.consultar("SELECT * FROM tickets_soporte WHERE id_ticket = ?", (id_ticket,))
        if not f:
            raise ValueError("El ticket no existe.")
        f = f[0]
        return TicketSoporte(f["id_estudiante"], f["categoria"], f["descripcion"],
                             f["estado"], f["id_ticket"], f["id_docente_asignado"])

    def listar_tickets(self, estado: str | None = None) -> list[sqlite3.Row]:
        """Consulta con JOIN: ticket + nombre del estudiante + docente asignado."""
        sql = ("SELECT t.id_ticket, t.id_estudiante, e.nombre AS estudiante, t.categoria, "
               "t.descripcion, t.estado, COALESCE(d.nombre, '—') AS docente "
               "FROM tickets_soporte t "
               "JOIN estudiantes e ON e.id_estudiante = t.id_estudiante "
               "LEFT JOIN docentes d ON d.id_docente = t.id_docente_asignado ")
        params: tuple = ()
        if estado and estado in ESTADOS:
            sql += "WHERE t.estado = ? "
            params = (estado,)
        sql += "ORDER BY t.id_ticket DESC"
        return self.__bd.consultar(sql, params)

    def cambiar_estado_ticket(self, id_ticket: int, nuevo_estado: str) -> TicketSoporte:
        ticket = self._cargar_ticket(id_ticket)
        ticket.cambiar_estado(nuevo_estado)                     # valida transición
        self.__bd.ejecutar("UPDATE tickets_soporte SET estado = ? WHERE id_ticket = ?",
                           (ticket.estado, id_ticket))
        return ticket

    def asignar_docente(self, id_ticket: int, id_docente: str) -> None:
        ticket = self._cargar_ticket(id_ticket)
        if ticket.estado == "CERRADO":
            raise ValueError("No se puede asignar un docente a un ticket CERRADO.")
        try:
            self.__bd.ejecutar(
                "UPDATE tickets_soporte SET id_docente_asignado = ? WHERE id_ticket = ?",
                (id_docente, id_ticket))
        except sqlite3.IntegrityError:
            raise ValueError("El docente indicado no existe.")

    # ---------------- Resumen ----------------
    def resumen(self) -> dict:
        r = {"estudiantes": 0, "docentes": 0, "tickets": 0}
        r["estudiantes"] = self.__bd.consultar("SELECT COUNT(*) c FROM estudiantes")[0]["c"]
        r["docentes"] = self.__bd.consultar("SELECT COUNT(*) c FROM docentes")[0]["c"]
        r["tickets"] = self.__bd.consultar("SELECT COUNT(*) c FROM tickets_soporte")[0]["c"]
        for est in ESTADOS:
            r[est] = self.__bd.consultar(
                "SELECT COUNT(*) c FROM tickets_soporte WHERE estado = ?", (est,))[0]["c"]
        return r

    def cargar_ejemplos(self) -> None:
        """Datos de demostración (ignora los que ya existan)."""
        for args in [("10184321", "Laura Gómez", "Ingeniería de Sistemas", 4.2),
                     ("10277455", "Ana Martínez", "Ingeniería de Sistemas", 3.8),
                     ("10399812", "Juan Pérez", "Administración", 4.5)]:
            try:
                self.registrar_estudiante(*args)
            except ValueError:
                pass
        for args in [("D-201", "Dr. Carlos Ruiz", "Ingeniería de Software"),
                     ("D-202", "Mg. Sofía Rojas", "Redes y Telecomunicaciones")]:
            try:
                self.registrar_docente(*args)
            except ValueError:
                pass
        if not self.listar_tickets():
            self.crear_ticket("10184321", "Plataforma virtual", "No puedo entrar al aula virtual de POO")
            self.crear_ticket("10277455", "Red / Internet", "El WiFi del aula 3 está caído")
            t = self.crear_ticket("10399812", "Correo institucional", "No recibo correos de la CUN")
            self.asignar_docente(t.id_ticket, "D-202")
            self.cambiar_estado_ticket(t.id_ticket, "EN_PROCESO")


# =====================================================================
#  4. INTERFAZ GRÁFICA (Tkinter)  ->  se empaqueta como .exe
# =====================================================================
def iniciar_gui() -> None:
    import tkinter as tk
    from tkinter import ttk, messagebox

    class App(tk.Tk):
        AZUL = "#0b3d91"

        def __init__(self):
            super().__init__()
            self.title("Mesa de Ayuda TI y Gestión Académica - CUN")
            self.geometry("1020x680")
            self.minsize(900, 600)
            self.mesa = MesaAyuda(ruta_base_datos())
            self.protocol("WM_DELETE_WINDOW", self._cerrar)

            estilo = ttk.Style(self)
            try:
                estilo.theme_use("clam")
            except tk.TclError:
                pass
            estilo.configure("Titulo.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.AZUL)
            estilo.configure("Treeview", rowheight=24)
            estilo.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

            menu = tk.Menu(self)
            archivo = tk.Menu(menu, tearoff=0)
            archivo.add_command(label="Cargar datos de ejemplo", command=self._ejemplos)
            archivo.add_separator()
            archivo.add_command(label="Salir", command=self._cerrar)
            menu.add_cascade(label="Archivo", menu=archivo)
            self.config(menu=menu)

            ttk.Label(self, text="Mesa de Ayuda TI y Gestión Académica — CUN",
                      style="Titulo.TLabel").pack(anchor="w", padx=14, pady=(10, 0))
            self.lbl_resumen = ttk.Label(self, text="")
            self.lbl_resumen.pack(anchor="w", padx=14, pady=(0, 4))

            nb = ttk.Notebook(self)
            nb.pack(fill="both", expand=True, padx=10, pady=8)
            self._tab_estudiantes(nb)
            self._tab_docentes(nb)
            self._tab_tickets(nb)
            self.refrescar()

        # ---------- utilidades ----------
        def _ejecutar(self, accion, exito: str | None = None) -> bool:
            try:
                accion()
            except (ValueError, sqlite3.Error) as err:
                messagebox.showerror("No se pudo completar", str(err))
                return False
            if exito:
                messagebox.showinfo("Listo", exito)
            self.refrescar()
            return True

        @staticmethod
        def _fila_form(parent, etiqueta, fila, columna=0, ancho=22, valores=None):
            ttk.Label(parent, text=etiqueta).grid(row=fila, column=columna, sticky="w", padx=(0, 6), pady=3)
            if valores is not None:
                w = ttk.Combobox(parent, values=valores, state="readonly", width=ancho - 2)
            else:
                w = ttk.Entry(parent, width=ancho)
            w.grid(row=fila, column=columna + 1, sticky="w", padx=(0, 16), pady=3)
            return w

        @staticmethod
        def _tabla(parent, columnas: list[tuple[str, int]]):
            cont = ttk.Frame(parent)
            cont.pack(fill="both", expand=True, pady=(8, 0))
            tree = ttk.Treeview(cont, columns=[c for c, _ in columnas], show="headings",
                                selectmode="browse")
            for nombre, ancho in columnas:
                tree.heading(nombre, text=nombre)
                tree.column(nombre, width=ancho, anchor="w")
            sb = ttk.Scrollbar(cont, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=sb.set)
            tree.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
            return tree

        def _seleccion(self, tree):
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Selecciona un registro", "Primero elige una fila de la tabla.")
                return None
            return sel[0]

        # ---------- pestaña Estudiantes ----------
        def _tab_estudiantes(self, nb):
            tab = ttk.Frame(nb, padding=12)
            nb.add(tab, text="  Estudiantes  ")
            form = ttk.LabelFrame(tab, text="Datos del estudiante", padding=10)
            form.pack(fill="x")
            self.e_id = self._fila_form(form, "Documento:", 0, 0)
            self.e_nombre = self._fila_form(form, "Nombre:", 0, 2, 28)
            self.e_prog = self._fila_form(form, "Programa:", 1, 0)
            self.e_prom = self._fila_form(form, "Promedio (0.0 - 5.0):", 1, 2, 10)
            self.e_prom.insert(0, "0.0")
            botones = ttk.Frame(form)
            botones.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))
            ttk.Button(botones, text="Registrar", command=self._reg_est).pack(side="left", padx=(0, 6))
            ttk.Button(botones, text="Actualizar promedio", command=self._act_prom).pack(side="left", padx=6)
            ttk.Button(botones, text="Eliminar seleccionado", command=self._del_est).pack(side="left", padx=6)
            ttk.Button(botones, text="Limpiar", command=self._limpiar_est).pack(side="left", padx=6)
            self.t_est = self._tabla(tab, [("Documento", 120), ("Nombre", 260), ("Programa", 260), ("Promedio", 90)])
            self.t_est.bind("<<TreeviewSelect>>", self._cargar_est)

        def _reg_est(self):
            self._ejecutar(lambda: self.mesa.registrar_estudiante(
                self.e_id.get(), self.e_nombre.get(), self.e_prog.get(), self.e_prom.get()),
                "Estudiante registrado.")

        def _act_prom(self):
            self._ejecutar(lambda: self.mesa.actualizar_promedio(
                self.e_id.get().strip(), self.e_prom.get()), "Promedio actualizado.")

        def _del_est(self):
            iid = self._seleccion(self.t_est)
            if iid and messagebox.askyesno("Confirmar", f"¿Eliminar al estudiante {iid}?"):
                self._ejecutar(lambda: self.mesa.eliminar_estudiante(iid))

        def _limpiar_est(self):
            for w in (self.e_id, self.e_nombre, self.e_prog):
                w.delete(0, "end")
            self.e_prom.delete(0, "end")
            self.e_prom.insert(0, "0.0")

        def _cargar_est(self, _evt=None):
            sel = self.t_est.selection()
            if sel:
                v = self.t_est.item(sel[0])["values"]
                self._limpiar_est()
                self.e_id.insert(0, sel[0])
                self.e_nombre.insert(0, v[1])
                self.e_prog.insert(0, v[2])
                self.e_prom.delete(0, "end")
                self.e_prom.insert(0, v[3])

        # ---------- pestaña Docentes ----------
        def _tab_docentes(self, nb):
            tab = ttk.Frame(nb, padding=12)
            nb.add(tab, text="  Docentes  ")
            form = ttk.LabelFrame(tab, text="Datos del docente", padding=10)
            form.pack(fill="x")
            self.d_id = self._fila_form(form, "ID docente:", 0, 0)
            self.d_nombre = self._fila_form(form, "Nombre:", 0, 2, 28)
            self.d_esp = self._fila_form(form, "Especialidad:", 1, 0, 28)
            botones = ttk.Frame(form)
            botones.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))
            ttk.Button(botones, text="Registrar", command=self._reg_doc).pack(side="left", padx=(0, 6))
            ttk.Button(botones, text="Eliminar seleccionado", command=self._del_doc).pack(side="left", padx=6)
            self.t_doc = self._tabla(tab, [("ID", 120), ("Nombre", 260), ("Especialidad", 260), ("Rol (polimorfismo)", 360)])

        def _reg_doc(self):
            def accion():
                self.mesa.registrar_docente(self.d_id.get(), self.d_nombre.get(), self.d_esp.get())
                for w in (self.d_id, self.d_nombre, self.d_esp):
                    w.delete(0, "end")
            self._ejecutar(accion, "Docente registrado.")

        def _del_doc(self):
            iid = self._seleccion(self.t_doc)
            if iid and messagebox.askyesno("Confirmar", f"¿Eliminar al docente {iid}?"):
                self._ejecutar(lambda: self.mesa.eliminar_docente(iid))

        # ---------- pestaña Tickets ----------
        def _tab_tickets(self, nb):
            tab = ttk.Frame(nb, padding=12)
            nb.add(tab, text="  Tickets de soporte TI  ")
            form = ttk.LabelFrame(tab, text="Nuevo ticket", padding=10)
            form.pack(fill="x")
            self.k_est = self._fila_form(form, "Estudiante:", 0, 0, 34, valores=[])
            self.k_cat = self._fila_form(form, "Categoría:", 0, 2, 24, valores=CATEGORIAS)
            self.k_desc = self._fila_form(form, "Descripción:", 1, 0, 60)
            self.k_desc.grid(columnspan=2, sticky="we")
            ttk.Button(form, text="Crear ticket", command=self._crear_ticket).grid(row=1, column=3, sticky="e")

            gestion = ttk.LabelFrame(tab, text="Gestionar ticket seleccionado", padding=10)
            gestion.pack(fill="x", pady=(8, 0))
            ttk.Label(gestion, text="Nuevo estado:").grid(row=0, column=0, padx=(0, 6))
            self.k_estado = ttk.Combobox(gestion, values=ESTADOS, state="readonly", width=14)
            self.k_estado.grid(row=0, column=1, padx=(0, 6))
            ttk.Button(gestion, text="Cambiar estado", command=self._cambiar_estado).grid(row=0, column=2, padx=(0, 24))
            ttk.Label(gestion, text="Docente:").grid(row=0, column=3, padx=(0, 6))
            self.k_doc = ttk.Combobox(gestion, values=[], state="readonly", width=30)
            self.k_doc.grid(row=0, column=4, padx=(0, 6))
            ttk.Button(gestion, text="Asignar docente", command=self._asignar).grid(row=0, column=5)

            filtro = ttk.Frame(tab)
            filtro.pack(fill="x", pady=(8, 0))
            ttk.Label(filtro, text="Filtrar por estado:").pack(side="left")
            self.k_filtro = ttk.Combobox(filtro, values=["TODOS"] + ESTADOS, state="readonly", width=14)
            self.k_filtro.set("TODOS")
            self.k_filtro.pack(side="left", padx=6)
            self.k_filtro.bind("<<ComboboxSelected>>", lambda _e: self.refrescar())

            self.t_tic = self._tabla(tab, [("N°", 50), ("Estudiante", 150), ("Categoría", 140),
                                           ("Descripción", 320), ("Estado", 100), ("Docente", 150)])

        def _crear_ticket(self):
            def accion():
                if not self.k_est.get():
                    raise ValueError("Selecciona un estudiante.")
                self.mesa.crear_ticket(self.k_est.get().split(" - ", 1)[0],
                                       self.k_cat.get(), self.k_desc.get())
                self.k_desc.delete(0, "end")
            self._ejecutar(accion, "Ticket creado en estado ABIERTO.")

        def _cambiar_estado(self):
            iid = self._seleccion(self.t_tic)
            if iid:
                self._ejecutar(lambda: self.mesa.cambiar_estado_ticket(int(iid), self.k_estado.get()),
                               "Estado actualizado.")

        def _asignar(self):
            iid = self._seleccion(self.t_tic)
            if iid:
                def accion():
                    if not self.k_doc.get():
                        raise ValueError("Selecciona un docente.")
                    self.mesa.asignar_docente(int(iid), self.k_doc.get().split(" - ", 1)[0])
                self._ejecutar(accion, "Docente asignado.")

        # ---------- refresco general ----------
        def refrescar(self):
            estudiantes = self.mesa.listar_estudiantes()
            docentes = self.mesa.listar_docentes()
            self._llenar(self.t_est, [(e.identificador, (e.identificador, e.nombre, e.programa, f"{e.promedio:.2f}"))
                                      for e in estudiantes])
            self._llenar(self.t_doc, [(d.identificador, (d.identificador, d.nombre, d.especialidad, d.obtener_rol()))
                                      for d in docentes])
            filtro = self.k_filtro.get()
            tickets = self.mesa.listar_tickets(None if filtro in ("", "TODOS") else filtro)
            self._llenar(self.t_tic, [(str(t["id_ticket"]),
                                       (t["id_ticket"], t["estudiante"], t["categoria"],
                                        t["descripcion"], t["estado"], t["docente"]))
                                      for t in tickets])
            self.k_est.config(values=[str(e) for e in estudiantes])
            self.k_doc.config(values=[str(d) for d in docentes])
            r = self.mesa.resumen()
            self.lbl_resumen.config(
                text=(f"Estudiantes: {r['estudiantes']}   |   Docentes: {r['docentes']}   |   "
                      f"Tickets: {r['tickets']} (abiertos {r['ABIERTO']}, en proceso {r['EN_PROCESO']}, "
                      f"cerrados {r['CERRADO']})"))

        @staticmethod
        def _llenar(tree, filas):
            tree.delete(*tree.get_children())
            for iid, valores in filas:
                tree.insert("", "end", iid=iid, values=valores)

        def _ejemplos(self):
            self._ejecutar(self.mesa.cargar_ejemplos, "Datos de ejemplo cargados.")

        def _cerrar(self):
            self.mesa.cerrar()
            self.destroy()

    App().mainloop()


if __name__ == "__main__":
    iniciar_gui()
