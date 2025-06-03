try:
    import struct
    import os
    import re
    from math import ceil
    import openpyxl
    from datetime import datetime
    import logging
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                 QPushButton, QLabel, QLineEdit, QComboBox, QMessageBox,
                                 QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
                                 QFormLayout, QDialogButtonBox)
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    import sys
except ImportError as e:
    print(f"Error al importar módulos: {e}")
    print("Ejecuta: pip install PyQt5 openpyxl")
    exit(1)

logging.basicConfig(level=logging.DEBUG)

# Constantes
MAX_CLIENTE = 50
MAX_FECHA = 11
MAX_PRODUCTO = 30
MAX_CHAPA = 20
PIN_CORRECTO = "1234"
CHAPA_ANCHO = 150.0
CHAPA_ALTO = 300.0
FILE_NAME = "presupuestos.dat"
STOCK_FILE = "stock.dat"

# Estructura para presupuestos (definida antes de cualquier función que la use)
PRESUPUESTO_STRUCT = f"{MAX_CLIENTE}s i {MAX_FECHA}s {MAX_PRODUCTO}s {MAX_CHAPA}s 7f"
PRESUPUESTO_SIZE = struct.calcsize(PRESUPUESTO_STRUCT)

# Estructura para guardar el stock en un archivo binario
STOCK_STRUCT = "20s d i"  # tipo_chapa (20 chars), espesor (double), cantidad (int)
STOCK_SIZE = struct.calcsize(STOCK_STRUCT)

# Stock inicial
stock = [
    {"tipo_chapa": "Comun", "espesor": 1.5, "cantidad": 10},
    {"tipo_chapa": "Acero", "espesor": 2.0, "cantidad": 5},
    {"tipo_chapa": "Galvanizada", "espesor": 1.8, "cantidad": 8}
]

def cargar_stock():
    """Carga el stock desde el archivo stock.dat al iniciar el programa."""
    global stock
    if os.path.exists(STOCK_FILE):
        stock.clear()
        with open(STOCK_FILE, "rb") as f:
            while True:
                data = f.read(STOCK_SIZE)
                if not data:
                    break
                tipo_chapa, espesor, cantidad = struct.unpack(STOCK_STRUCT, data)
                stock.append({
                    "tipo_chapa": tipo_chapa.decode().rstrip("\0"),
                    "espesor": espesor,
                    "cantidad": cantidad
                })

def guardar_stock():
    """Guarda el stock actual en el archivo stock.dat."""
    with open(STOCK_FILE, "wb") as f:
        for item in stock:
            tipo_chapa = item["tipo_chapa"].encode().ljust(20, b"\0")
            f.write(struct.pack(STOCK_STRUCT, tipo_chapa, item["espesor"], item["cantidad"]))

# Cargar stock al iniciar el programa
cargar_stock()

def validar_fecha(fecha):
    return bool(re.match(r"^\d{2}/\d{2}/\d{4}$", fecha))

def validar_string(s, max_len, nombre):
    return isinstance(s, str) and 0 < len(s.strip()) <= max_len

def validar_numero(n, nombre):
    try:
        n = float(n)
        return n > 0
    except (ValueError, TypeError):
        return False

def validar_ganancia(n):
    try:
        n = float(n)
        return n >= 0
    except (ValueError, TypeError):
        return False

def validar_stock(tipo_chapa, espesor, chapas_necesarias):
    for item in stock:
        if item["tipo_chapa"] == tipo_chapa and item["espesor"] == espesor:
            if item["cantidad"] >= chapas_necesarias:
                item["cantidad"] -= chapas_necesarias
                guardar_stock()  # Actualizar el archivo stock.dat
                return True
            return False
    return False

def crear_presupuesto(datos):
    logging.debug(f"Datos recibidos: {datos}")
    errors = []
    if not validar_string(datos.get("cliente", ""), MAX_CLIENTE, "Cliente"):
        errors.append("Cliente no válido")
    if not validar_numero(datos.get("numero_cliente", 0), "Número de cliente"):
        errors.append("Número de cliente debe ser mayor a 0")
    if not validar_fecha(datos.get("fecha", "")):
        errors.append("Fecha debe ser dd/mm/yyyy")
    try:
        fecha = datetime.strptime(datos.get("fecha", ""), "%d/%m/%Y")
        if not (2025 <= fecha.year <= 2030):
            errors.append("El año debe estar entre 2025 y 2030")
    except ValueError:
        errors.append("Fecha no válida")
    if not validar_string(datos.get("producto", ""), MAX_PRODUCTO, "Producto"):
        errors.append("Producto no válido")
    if not validar_string(datos.get("tipo_chapa", ""), MAX_CHAPA, "Tipo de chapa"):
        errors.append("Tipo de chapa no válido")
    if not validar_numero(datos.get("espesor", 0), "Espesor"):
        errors.append("Espesor debe ser mayor a 0")
    if not validar_numero(datos.get("ancho", 0), "Ancho"):
        errors.append("Ancho debe ser mayor a 0")
    if not validar_numero(datos.get("largo", 0), "Alto"):
        errors.append("Alto debe ser mayor a 0")
    if not validar_numero(datos.get("precio_chapa", 0), "Precio chapa"):
        errors.append("Precio chapa debe ser mayor a 0")
    if not validar_numero(datos.get("precio_mano_obra", 0), "Mano de obra"):
        errors.append("Mano de obra debe ser mayor a 0")
    if not validar_ganancia(datos.get("ganancia", -1)):
        errors.append("Ganancia no válida o negativa")

    try:
        numero_cliente = int(datos["numero_cliente"])
        existing = buscar_por_numero(numero_cliente)
        if existing:
            errors.append(f"El número de cliente {numero_cliente} ya existe. Use un número diferente.")
    except (ValueError, TypeError) as e:
        errors.append("Número de cliente no válido")

    if errors:
        return {"success": False, "error": "; ".join(errors)}

    try:
        datos["numero_cliente"] = int(datos["numero_cliente"])
        datos["espesor"] = float(datos["espesor"])
        datos["ancho"] = float(datos["ancho"])
        datos["largo"] = float(datos["largo"])
        datos["precio_chapa"] = float(datos["precio_chapa"])
        datos["precio_mano_obra"] = float(datos["precio_mano_obra"])
        datos["ganancia"] = float(datos["ganancia"])
    except (ValueError, TypeError) as e:
        return {"success": False, "error": f"Error en los datos numéricos: {str(e)}"}

    chapas_x = ceil(datos["ancho"] / CHAPA_ANCHO)
    chapas_y = ceil(datos["largo"] / CHAPA_ALTO)
    total_chapas = chapas_x * chapas_y

    if not validar_stock(datos["tipo_chapa"], datos["espesor"], total_chapas):
        return {"success": False, "error": f"Stock insuficiente para {datos['tipo_chapa']} ({datos['espesor']} mm)"}

    costo_base = (total_chapas * datos["precio_chapa"]) + datos["precio_mano_obra"]
    precio_total = costo_base * (1 + datos["ganancia"] / 100)
    datos["precio_total"] = precio_total

    try:
        with open(FILE_NAME, "ab") as f:
            cliente = datos["cliente"].encode().ljust(MAX_CLIENTE, b"\0")
            fecha = datos["fecha"].encode().ljust(MAX_FECHA, b"\0")
            producto = datos["producto"].encode().ljust(MAX_PRODUCTO, b"\0")
            tipo_chapa = datos["tipo_chapa"].encode().ljust(MAX_CHAPA, b"\0")
            f.write(struct.pack(PRESUPUESTO_STRUCT,
                               cliente,
                               datos["numero_cliente"],
                               fecha,
                               producto,
                               tipo_chapa,
                               datos["espesor"],
                               datos["ancho"],
                               datos["largo"],
                               datos["precio_chapa"],
                               datos["precio_mano_obra"],
                               datos["ganancia"],
                               datos["precio_total"]))

        # Guardar en una carpeta por cliente con archivo Excel
        cliente = datos["cliente"].strip()
        fecha_obj = datetime.strptime(datos["fecha"], "%d/%m/%Y")
        mes = fecha_obj.strftime("%B").capitalize()  # Nombre del mes en español
        año = fecha_obj.year
        meses = {
            "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
            "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
            "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
        }
        mes = meses.get(mes, mes)
        cliente_dir = os.path.join("Presupuestos_Clientes", cliente)
        os.makedirs(cliente_dir, exist_ok=True)
        excel_file = os.path.join(cliente_dir, f"{mes}_{año}.xlsx")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Presupuesto"
        headers = ["Cliente", "Número", "Fecha", "Producto", "Tipo de chapa", "Espesor", "Ancho", "Alto",
                   "Precio chapa", "Mano de obra", "Ganancia", "Total"]
        ws.append(headers)
        ws.append([
            datos["cliente"], datos["numero_cliente"], datos["fecha"], datos["producto"],
            datos["tipo_chapa"], datos["espesor"], datos["ancho"], datos["largo"],
            datos["precio_chapa"], datos["precio_mano_obra"], datos["ganancia"], datos["precio_total"]
        ])
        wb.save(excel_file)

        return {"success": True, "total": precio_total, "chapas": total_chapas}
    except Exception as e:
        return {"success": False, "error": f"Error al guardar: {str(e)}"}

def leer_presupuestos():
    presupuestos = []
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "rb") as f:
            while True:
                data = f.read(PRESUPUESTO_SIZE)
                if not data:
                    break
                unpacked = struct.unpack(PRESUPUESTO_STRUCT, data)
                presupuestos.append({
                    "cliente": unpacked[0].decode().rstrip("\0"),
                    "numero_cliente": unpacked[1],
                    "fecha": unpacked[2].decode().rstrip("\0"),
                    "producto": unpacked[3].decode().rstrip("\0"),
                    "tipo_chapa": unpacked[4].decode().rstrip("\0"),
                    "espesor": unpacked[5],
                    "ancho": unpacked[6],
                    "largo": unpacked[7],
                    "precio_chapa": unpacked[8],
                    "precio_mano_obra": unpacked[9],
                    "ganancia": unpacked[10],
                    "precio_total": unpacked[11]
                })
    return presupuestos

def buscar_por_cliente(nombre):
    return [p for p in leer_presupuestos() if p["cliente"].lower() == nombre.lower()]

def buscar_por_numero(numero):
    return [p for p in leer_presupuestos() if p["numero_cliente"] == numero]

def buscar_por_mes_y_año(mes, año):
    presupuestos = leer_presupuestos()
    resultados = []
    for p in presupuestos:
        try:
            fecha = datetime.strptime(p["fecha"], "%d/%m/%Y")
            if fecha.month == mes and fecha.year == año:
                resultados.append(p)
        except ValueError:
            continue
    return {"success": True, "data": resultados}

def resumen_presupuestos():
    presupuestos = leer_presupuestos()
    total = sum(p["precio_total"] for p in presupuestos)
    count = len(presupuestos)
    return {
        "total_facturado": total,
        "presupuestos": count,
        "promedio": total / count if count else 0
    }

def modificar_presupuesto(numero_cliente, nuevos_datos):
    presupuestos = leer_presupuestos()
    found = False
    with open(FILE_NAME, "wb") as f:
        for p in presupuestos:
            if p["numero_cliente"] == numero_cliente:
                try:
                    p["cliente"] = nuevos_datos["cliente"]
                    p["numero_cliente"] = int(nuevos_datos["numero_cliente"])
                    p["fecha"] = nuevos_datos["fecha"]
                    p["producto"] = nuevos_datos["producto"]
                    p["tipo_chapa"] = nuevos_datos["tipo_chapa"]
                    p["espesor"] = float(nuevos_datos["espesor"])
                    p["ancho"] = float(nuevos_datos["ancho"])
                    p["largo"] = float(nuevos_datos["largo"])
                    p["precio_chapa"] = float(nuevos_datos["precio_chapa"])
                    p["precio_mano_obra"] = float(nuevos_datos["precio_mano_obra"])
                    p["ganancia"] = float(nuevos_datos["ganancia"])
                    chapas_x = ceil(p["ancho"] / CHAPA_ANCHO)
                    chapas_y = ceil(p["largo"] / CHAPA_ALTO)
                    total_chapas = chapas_x * chapas_y
                    costo_base = (total_chapas * p["precio_chapa"]) + p["precio_mano_obra"]
                    p["precio_total"] = costo_base * (1 + p["ganancia"] / 100)
                    found = True
                except (ValueError, TypeError) as e:
                    return {"success": False, "error": f"Error en los datos: {str(e)}"}
            cliente = p["cliente"].encode().ljust(MAX_CLIENTE, b"\0")
            fecha = p["fecha"].encode().ljust(MAX_FECHA, b"\0")
            producto = p["producto"].encode().ljust(MAX_PRODUCTO, b"\0")
            tipo_chapa = p["tipo_chapa"].encode().ljust(MAX_CHAPA, b"\0")
            f.write(struct.pack(PRESUPUESTO_STRUCT,
                               cliente,
                               p["numero_cliente"],
                               fecha,
                               producto,
                               tipo_chapa,
                               p["espesor"],
                               p["ancho"],
                               p["largo"],
                               p["precio_chapa"],
                               p["precio_mano_obra"],
                               p["ganancia"],
                               p["precio_total"]))
    return {"success": True, "message": "Presupuesto modificado"} if found else {"success": False, "error": "Presupuesto no encontrado"}

def eliminar_presupuesto(numero_cliente):
    presupuestos = leer_presupuestos()
    found = False
    with open(FILE_NAME, "wb") as f:
        for p in presupuestos:
            if p["numero_cliente"] == numero_cliente:
                found = True
                continue
            cliente = p["cliente"].encode().ljust(MAX_CLIENTE, b"\0")
            fecha = p["fecha"].encode().ljust(MAX_FECHA, b"\0")
            producto = p["producto"].encode().ljust(MAX_PRODUCTO, b"\0")
            tipo_chapa = p["tipo_chapa"].encode().ljust(MAX_CHAPA, b"\0")
            f.write(struct.pack(PRESUPUESTO_STRUCT,
                               cliente,
                               p["numero_cliente"],
                               fecha,
                               producto,
                               tipo_chapa,
                               p["espesor"],
                               p["ancho"],
                               p["largo"],
                               p["precio_chapa"],
                               p["precio_mano_obra"],
                               p["ganancia"],
                               p["precio_total"]))
    return {"success": True, "message": "Presupuesto eliminado"} if found else {"success": False, "error": "Presupuesto no encontrado"}

def exportar_excel():
    try:
        presupuestos = leer_presupuestos()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Presupuestos"
        headers = ["Cliente", "Número", "Fecha", "Producto", "Tipo de chapa", "Espesor", "Ancho", "Alto",
                   "Precio chapa", "Mano de obra", "Ganancia", "Total"]
        ws.append(headers)
        for p in presupuestos:
            ws.append([
                p["cliente"], p["numero_cliente"], p["fecha"], p["producto"], p["tipo_chapa"],
                p["espesor"], p["ancho"], p["largo"], p["precio_chapa"], p["precio_mano_obra"],
                p["ganancia"], p["precio_total"]
            ])
        excel_file = "presupuestos.xlsx"
        wb.save(excel_file)
        return {"success": True, "message": f"Exportado a {excel_file}"}
    except Exception as e:
        return {"success": False, "error": f"Error al exportar: {str(e)}"}

class PresupuestoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Presupuestos - Idearte Chapa")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QPushButton { background-color: #4CAF50; color: white; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #45a049; }
            QLineEdit, QComboBox { padding: 6px; border: 1px solid #ccc; border-radius: 4px; }
            QLabel { font-size: 14px; }
            QTableWidget { border: 1px solid #ccc; }
        """)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)
        self.create_login()

    def create_login(self):
        self.clear_layout()
        title = QLabel("Gestión de Presupuestos - Idearte Chapa")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)
        self.layout.addStretch()
        pin_label = QLabel("Ingrese su PIN de acceso:")
        pin_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(pin_label)
        self.pin_entry = QLineEdit()
        self.pin_entry.setEchoMode(QLineEdit.Password)
        self.pin_entry.setFixedWidth(200)
        self.layout.addWidget(self.pin_entry, alignment=Qt.AlignCenter)
        login_btn = QPushButton("Ingresar")
        login_btn.setFixedWidth(100)
        login_btn.clicked.connect(self.check_pin)
        self.layout.addWidget(login_btn, alignment=Qt.AlignCenter)
        self.layout.addStretch()

    def check_pin(self):
        if self.pin_entry.text() == PIN_CORRECTO:
            self.create_menu()
        else:
            QMessageBox.critical(self, "Error", "PIN incorrecto")

    def clear_layout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def create_menu(self):
        self.clear_layout()
        title = QLabel("Sistema de Presupuestos")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)
        self.layout.addStretch()
        buttons = [
            ("Crear Presupuesto", self.create_form),
            ("Ver Presupuestos", self.view_presupuestos),
            ("Buscar por Cliente", self.search_cliente),
            ("Buscar por Número", self.search_numero),
            ("Buscar por Fecha", self.search_fecha),
            ("Modificar Presupuesto", self.modify_form),
            ("Eliminar Presupuesto", self.delete_form),
            ("Resumen", self.show_resumen),
            ("Exportar a Excel", self.export_excel),
            ("Gestionar Stock", self.manage_stock),
            ("Salir", self.close)
        ]
        for text, func in buttons:
            btn = QPushButton(text)
            btn.setFixedWidth(200)
            btn.clicked.connect(func)
            self.layout.addWidget(btn, alignment=Qt.AlignCenter)
        self.layout.addStretch()

    def create_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Crear Presupuesto")
        dialog.setFixedSize(400, 500)
        layout = QFormLayout()
        fields = [
            ("Cliente", QLineEdit),
            ("Número", QLineEdit),
            ("Fecha (dd/mm/yyyy)", QLineEdit),
            ("Producto", QLineEdit),
            ("Tipo de chapa", lambda: QComboBox()),
            ("Espesor (mm)", QLineEdit),
            ("Ancho (cm)", QLineEdit),
            ("Alto (cm)", QLineEdit),
            ("Precio chapa", QLineEdit),
            ("Mano de obra", QLineEdit),
            ("Ganancia (%)", QLineEdit)
        ]
        self.entries = {}
        for label, widget_type in fields:
            widget = widget_type()
            if label == "Tipo de chapa":
                widget.addItems([item["tipo_chapa"] for item in stock])  # Actualizar con tipos de chapa del stock
            layout.addRow(QLabel(label + ":"), widget)
            self.entries[label] = widget

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.button(QDialogButtonBox.Ok).setAutoDefault(False)
        buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        layout.addRow(buttons)

        dialog.setLayout(layout)
        if dialog.exec_() == QDialog.Accepted:
            datos = {
                "cliente": self.entries["Cliente"].text().strip(),
                "numero_cliente": self.entries["Número"].text().strip(),
                "fecha": self.entries["Fecha (dd/mm/yyyy)"].text().strip(),
                "producto": self.entries["Producto"].text().strip(),
                "tipo_chapa": self.entries["Tipo de chapa"].currentText().strip(),
                "espesor": self.entries["Espesor (mm)"].text().strip(),
                "ancho": self.entries["Ancho (cm)"].text().strip(),
                "largo": self.entries["Alto (cm)"].text().strip(),
                "precio_chapa": self.entries["Precio chapa"].text().strip(),
                "precio_mano_obra": self.entries["Mano de obra"].text().strip(),
                "ganancia": self.entries["Ganancia (%)"].text().strip()
            }
            result = crear_presupuesto(datos)
            if result["success"]:
                QMessageBox.information(self, "Éxito", f"Presupuesto creado: ${result['total']:.2f}, {result['chapas']} chapas")
            else:
                QMessageBox.critical(self, "Error", result["error"])
        dialog.deleteLater()

    def modify_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Modificar Presupuesto")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Número de Presupuesto:"))
        entry = QLineEdit()
        layout.addWidget(entry)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_():
            try:
                numero = int(entry.text().strip())
            except ValueError:
                QMessageBox.warning(self, "Error", "Ingrese un número válido")
                return
            resultados = buscar_por_numero(numero)
            if not resultados:
                QMessageBox.warning(self, "Error", "Presupuesto no encontrado")
                return
            presupuesto = resultados[0]

            dialog = QDialog(self)
            dialog.setWindowTitle("Modificar Presupuesto")
            dialog.setFixedSize(400, 500)
            layout = QFormLayout()
            fields = [
                ("Cliente", QLineEdit),
                ("Número", QLineEdit),
                ("Fecha (dd/mm/yyyy)", QLineEdit),
                ("Producto", QLineEdit),
                ("Tipo de chapa", lambda: QComboBox()),
                ("Espesor (mm)", QLineEdit),
                ("Ancho (cm)", QLineEdit),
                ("Alto (cm)", QLineEdit),
                ("Precio chapa", QLineEdit),
                ("Mano de obra", QLineEdit),
                ("Ganancia (%)", QLineEdit)
            ]
            self.entries = {}
            for label, widget_type in fields:
                widget = widget_type()
                if label == "Tipo de chapa":
                    widget.addItems([item["tipo_chapa"] for item in stock])
                    widget.setCurrentText(presupuesto["tipo_chapa"])
                else:
                    key = label.lower().replace(" ", "_").replace("(%)", "").replace("(mm)", "").replace("(cm)", "")
                    widget.setText(str(presupuesto.get(key, "")))
                layout.addRow(QLabel(label + ":"), widget)
                self.entries[label] = widget

            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)

            dialog.setLayout(layout)
            if dialog.exec_():
                datos = {
                    "cliente": self.entries["Cliente"].text().strip(),
                    "numero_cliente": self.entries["Número"].text().strip(),
                    "fecha": self.entries["Fecha (dd/mm/yyyy)"].text().strip(),
                    "producto": self.entries["Producto"].text().strip(),
                    "tipo_chapa": self.entries["Tipo de chapa"].currentText().strip(),
                    "espesor": self.entries["Espesor (mm)"].text().strip(),
                    "ancho": self.entries["Ancho (cm)"].text().strip(),
                    "largo": self.entries["Alto (cm)"].text().strip(),
                    "precio_chapa": self.entries["Precio chapa"].text().strip(),
                    "precio_mano_obra": self.entries["Mano de obra"].text().strip(),
                    "ganancia": self.entries["Ganancia (%)"].text().strip()
                }
                result = modificar_presupuesto(numero, datos)
                if result["success"]:
                    QMessageBox.information(self, "Éxito", result["message"])
                else:
                    QMessageBox.critical(self, "Error", result["error"])

    def view_presupuestos(self):
        self.clear_layout()
        presupuestos = leer_presupuestos()
        table = QTableWidget()
        table.setRowCount(len(presupuestos))
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Cliente", "Número", "Fecha", "Producto", "Tipo de chapa", "Total"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, p in enumerate(presupuestos):
            table.setItem(row, 0, QTableWidgetItem(p["cliente"]))
            table.setItem(row, 1, QTableWidgetItem(str(p["numero_cliente"])))
            table.setItem(row, 2, QTableWidgetItem(p["fecha"]))
            table.setItem(row, 3, QTableWidgetItem(p["producto"]))
            table.setItem(row, 4, QTableWidgetItem(p["tipo_chapa"]))
            table.setItem(row, 5, QTableWidgetItem(f"${p['precio_total']:.2f}"))
        self.layout.addWidget(table)
        back_btn = QPushButton("Volver")
        back_btn.clicked.connect(self.create_menu)
        self.layout.addWidget(back_btn)

    def search_cliente(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Buscar por Cliente")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Nombre del Cliente:"))
        entry = QLineEdit()
        layout.addWidget(entry)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_():
            nombre = entry.text().strip()
            if not nombre:
                QMessageBox.warning(self, "Error", "Ingrese un nombre")
                return
            resultados = buscar_por_cliente(nombre)
            self.show_results(resultados)

    def search_numero(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Buscar por Número")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Número de Cliente:"))
        entry = QLineEdit()
        layout.addWidget(entry)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_():
            try:
                numero = int(entry.text().strip())
            except ValueError:
                QMessageBox.warning(self, "Error", "Ingrese un número válido")
                return
            resultados = buscar_por_numero(numero)
            self.show_results(resultados)

    def search_fecha(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Buscar por Mes y Año")
        dialog.setFixedSize(300, 200)
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Seleccione el Mes:"))
        mes_combo = QComboBox()
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_combo.addItems(meses)
        layout.addWidget(mes_combo)
        
        layout.addWidget(QLabel("Seleccione el Año:"))
        año_combo = QComboBox()
        años = [str(año) for año in range(2025, 2031)]
        año_combo.addItems(años)
        layout.addWidget(año_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_():
            mes = mes_combo.currentIndex() + 1
            año = int(año_combo.currentText())
            result = buscar_por_mes_y_año(mes, año)
            if not result["success"]:
                QMessageBox.critical(self, "Error", result["error"])
            else:
                self.show_results(result["data"])

    def show_results(self, resultados):
        self.clear_layout()
        table = QTableWidget()
        table.setRowCount(len(resultados))
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Cliente", "Número", "Fecha", "Producto", "Tipo de chapa", "Total"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, p in enumerate(resultados):
            table.setItem(row, 0, QTableWidgetItem(p["cliente"]))
            table.setItem(row, 1, QTableWidgetItem(str(p["numero_cliente"])))
            table.setItem(row, 2, QTableWidgetItem(p["fecha"]))
            table.setItem(row, 3, QTableWidgetItem(p["producto"]))
            table.setItem(row, 4, QTableWidgetItem(p["tipo_chapa"]))
            table.setItem(row, 5, QTableWidgetItem(f"${p['precio_total']:.2f}"))
        self.layout.addWidget(table)
        back_btn = QPushButton("Volver")
        back_btn.clicked.connect(self.create_menu)
        self.layout.addWidget(back_btn)

    def delete_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Eliminar Presupuesto")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Número de Presupuesto:"))
        entry = QLineEdit()
        layout.addWidget(entry)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_():
            try:
                numero = int(entry.text().strip())
            except ValueError:
                QMessageBox.critical(self, "Error", "Ingrese un número válido")
                return
            result = eliminar_presupuesto(numero)
            if result["success"]:
                QMessageBox.information(self, "Éxito", result["message"])
            else:
                QMessageBox.critical(self, "Error", result["error"])

    def show_resumen(self):
        self.clear_layout()
        resumen = resumen_presupuestos()
        texto = QLabel(f"""
        <h2>Resumen de Presupuestos</h2>
        <p><b>Total Facturado:</b> ${resumen['total_facturado']:.2f}</p>
        <p><b>Cantidad:</b> {resumen['presupuestos']}</p>
        <p><b>Promedio:</b> ${resumen['promedio']:.2f}</p>
        """)
        texto.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(texto)
        back_btn = QPushButton("Volver")
        back_btn.clicked.connect(self.create_menu)
        self.layout.addWidget(back_btn)

    def export_excel(self):
        result = exportar_excel()
        if result["success"]:
            QMessageBox.information(self, "Éxito", result["message"])
        else:
            QMessageBox.critical(self, "Error", result["error"])

    def manage_stock(self):
        self.clear_layout()
        title = QLabel("Gestión de Stock")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)

        self.stock_table = QTableWidget()
        self.stock_table.setRowCount(len(stock))
        self.stock_table.setColumnCount(3)
        self.stock_table.setHorizontalHeaderLabels(["Tipo de Chapa", "Espesor (mm)", "Cantidad"])
        self.stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, item in enumerate(stock):
            # Columna "Tipo de Chapa" - No editable
            tipo_item = QTableWidgetItem(item["tipo_chapa"])
            tipo_item.setFlags(tipo_item.flags() & ~Qt.ItemIsEditable)
            self.stock_table.setItem(row, 0, tipo_item)

            # Columna "Espesor" - Editable
            espesor_item = QTableWidgetItem(str(item["espesor"]))
            espesor_item.setFlags(espesor_item.flags() | Qt.ItemIsEditable)
            self.stock_table.setItem(row, 1, espesor_item)

            # Columna "Cantidad" - Editable
            cantidad_item = QTableWidgetItem(str(item["cantidad"]))
            cantidad_item.setFlags(cantidad_item.flags() | Qt.ItemIsEditable)
            self.stock_table.setItem(row, 2, cantidad_item)

        self.layout.addWidget(self.stock_table)

        # Botones "Guardar Cambios" y "Volver"
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Guardar Cambios")
        save_btn.clicked.connect(self.save_stock_changes)
        save_btn.setFixedWidth(150)
        button_layout.addWidget(save_btn, alignment=Qt.AlignCenter)

        back_btn = QPushButton("Volver")
        back_btn.clicked.connect(self.create_menu)
        back_btn.setFixedWidth(150)
        button_layout.addWidget(back_btn, alignment=Qt.AlignCenter)

        self.layout.addLayout(button_layout)

    def save_stock_changes(self):
        # Actualizar la lista global 'stock' con los valores editados
        for row in range(self.stock_table.rowCount()):
            try:
                espesor = float(self.stock_table.item(row, 1).text())
                if espesor <= 0:
                    raise ValueError("El espesor debe ser mayor a 0")
                cantidad = int(self.stock_table.item(row, 2).text())
                if cantidad < 0:
                    raise ValueError("La cantidad no puede ser negativa")
                stock[row]["espesor"] = espesor
                stock[row]["cantidad"] = cantidad
            except ValueError as e:
                QMessageBox.critical(self, "Error", f"Error en la fila {row + 1}: {str(e)}")
                return
        guardar_stock()  # Guardar los cambios en stock.dat
        QMessageBox.information(self, "Éxito", "Cambios guardados correctamente")
        self.create_menu()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PresupuestoApp()
    window.show()
    sys.exit(app.exec_())