from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sistema de Gestión de Inventario", layout="wide"
)

# ---------------------------------------------------------
# CONEXIÓN Y BASE DE DATOS
# ---------------------------------------------------------
conn = sqlite3.connect("inventario.db", check_same_thread=False)
c = conn.cursor()

# Creación de tablas
c.execute(
    """CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                nombre TEXT,
                categoria TEXT,
                precio REAL,
                costo REAL,
                stock INTEGER
            )"""
)

c.execute(
    """CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cedula TEXT UNIQUE,
                nombre TEXT,
                telefono TEXT,
                direccion TEXT
            )"""
)

c.execute(
    """CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                cliente TEXT,
                tipo_pago TEXT,
                metodo_pago TEXT,
                total REAL,
                vendedor TEXT
            )"""
)

c.execute(
    """CREATE TABLE IF NOT EXISTS detalle_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER,
                producto TEXT,
                cantidad INTEGER,
                precio_unitario REAL,
                subtotal REAL,
                FOREIGN KEY (venta_id) REFERENCES ventas (id)
            )"""
)

c.execute(
    """CREATE TABLE IF NOT EXISTS cuentas_por_cobrar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER,
                cliente TEXT,
                monto_total REAL,
                monto_pendiente REAL,
                estado TEXT,
                FOREIGN KEY (venta_id) REFERENCES ventas (id)
            )"""
)
conn.commit()

# Control de sesión simple para roles
if "rol" not in st.session_state:
    st.session_state["rol"] = "admin"

# ---------------------------------------------------------
# INTERFAZ Y NAVEGACIÓN
# ---------------------------------------------------------
st.sidebar.title("Menú Principal")
rol_usuario = st.sidebar.selectbox("Rol de Usuario", ["admin", "Isell"])
st.session_state["rol"] = rol_usuario

menu = [
    "🛒 Registrar Venta",
    "📦 Inventario de Productos",
    "👥 Clientes",
    "💳 Cuentas por Cobrar",
    "📊 Reportes de Ventas",
]
opcion = st.sidebar.radio("Navegación", menu)

# ----------------------------------------------------
# CUENTAS POR COBRAR
# ----------------------------------------------------
if opcion == "💳 Cuentas por Cobrar":
    st.header("💳 Cuentas por Cobrar")

    cxc_df = pd.read_sql_query(
        "SELECT * FROM cuentas_por_cobrar WHERE estado = 'Pendiente'", conn
    )

    if not cxc_df.empty:
        st.dataframe(cxc_df, use_container_width=True)

        st.subheader("Registrar Pago / Abono")
        cxc_sel = st.selectbox(
            "Seleccionar Deuda",
            cxc_df["id"].astype(str)
            + " - Cliente: "
            + cxc_df["cliente"]
            + " - Pendiente:  $"
            + cxc_df["monto_pendiente"].astype(str),
        )
        selected_id = int(cxc_sel.split(" - ")[0])
        monto_act = cxc_df[cxc_df["id"] == selected_id][
            "monto_pendiente"
        ].values[0]

        monto_pago = st.number_input(
            "Monto a Abonar ($)",
            min_value=0.01,
            max_value=float(monto_act),
            format="%.2f",
        )

        if st.button("Registrar Abonado"):
            nuevo_pendiente = monto_act - monto_pago
            nuevo_estado = (
                "Pagado" if nuevo_pendiente <= 0 else "Pendiente"
            )
            c.execute(
                "UPDATE cuentas_por_cobrar SET monto_pendiente = ?, estado = ? WHERE id = ?",
                (nuevo_pendiente, nuevo_estado, selected_id),
            )
            conn.commit()
            st.success("Pago registrado correctamente.")
            st.rerun()
    else:
        st.info("No hay cuentas pendientes por cobrar.")

# ----------------------------------------------------
# REPORTES DE VENTAS (ADMIN)
# ----------------------------------------------------
elif opcion == "📊 Reportes de Ventas":
    st.header("📊 Reportes y Cancelación de Ventas")

    df_v = pd.read_sql_query("SELECT * FROM ventas", conn)
    st.subheader("Historial de Ventas")
    st.dataframe(df_v, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🗑️ Limpiar Historial de Ventas")
        st.write(
            "Elimina solo el registro de ventas, cuentas por cobrar y el historial financiero, manteniendo tus productos y clientes intactos."
        )
        confirm_ventas = st.checkbox(
            "Confirmo que deseo borrar todas las ventas"
        )
        if st.button("Borrar Solo Ventas"):
            if confirm_ventas:
                c.execute("DELETE FROM ventas")
                c.execute("DELETE FROM detalle_ventas")
                c.execute("DELETE FROM cuentas_por_cobrar")
                conn.commit()
                st.success(
                    "✅ Historial de ventas limpiado correctamente."
                )
                st.rerun()
            else:
                st.error(
                    "Debes marcar la casilla de confirmación para proceder."
                )

    with col2:
        st.subheader("🔥 Reiniciar Todo el Sistema (Reset Total)")
        st.write(
            "Borra **TODA** la información: productos del inventario, lista de clientes, historial de ventas y deudas."
        )
        confirm_todo = st.checkbox(
            "Confirmo que deseo Borrar TODO el sistema"
        )
        if st.button("REINICIAR SISTEMA COMPLETO"):
            if confirm_todo:
                c.execute("DELETE FROM ventas")
                c.execute("DELETE FROM detalle_ventas")
                c.execute("DELETE FROM cuentas_por_cobrar")
                c.execute("DELETE FROM productos")
                c.execute("DELETE FROM clientes")
                conn.commit()
                if "carrito" in st.session_state:
                    st.session_state["carrito"] = []
                st.success(
                    "✅ La base de datos ha sido reiniciada completamente."
                )
                st.rerun()
            else:
                st.error(
                    "Debes marcar la casilla de confirmación para proceder."
                )

# ----------------------------------------------------
# OTRAS OPCIONES DEL MENÚ (Ej: Inventario, Clientes, Venta)
# ----------------------------------------------------
elif opcion == "🛒 Registrar Venta":
    st.header("🛒 Punto de Venta")
    st.info("Módulo de ventas operativo.")

elif opcion == "📦 Inventario de Productos":
    st.header("📦 Inventario de Productos")
    df_prod = pd.read_sql_query("SELECT * FROM productos", conn)
    st.dataframe(df_prod, use_container_width=True)

elif opcion == "👥 Clientes":
    st.header("👥 Gestión de Clientes")
    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)
    st.dataframe(df_cli, use_container_width=True)
