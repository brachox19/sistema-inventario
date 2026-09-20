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

# Control de sesión
if "rol" not in st.session_state:
    st.session_state["rol"] = "admin"

if "carrito" not in st.session_state:
    st.session_state["carrito"] = []

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
# REGISTRAR VENTA
# ----------------------------------------------------
if opcion == "🛒 Registrar Venta":
    st.header("🛒 Punto de Venta")

    productos_df = pd.read_sql_query("SELECT * FROM productos", conn)
    clientes_df = pd.read_sql_query("SELECT * FROM clientes", conn)

    if productos_df.empty:
        st.warning(
            "No hay productos en el inventario. Agrega productos primero."
        )
    else:
        col_1, col_2 = st.columns([2, 1])

        with col_1:
            st.subheader("Seleccionar Producto")
            prod_sel = st.selectbox(
                "Producto",
                productos_df["codigo"]
                + " - "
                + productos_df["nombre"]
                + " (Stock: "
                + productos_df["stock"].astype(str)
                + ")",
            )
            cant = st.number_input("Cantidad", min_value=1, value=1, step=1)

            if st.button("Agregar al Carrito"):
                codigo_prod = prod_sel.split(" - ")[0]
                p_info = productos_df[
                    productos_df["codigo"] == codigo_prod
                ].iloc[0]
                if cant > int(p_info["stock"]):
                    st.error("No hay suficiente stock disponible.")
                else:
                    encontrado = False
                    for item in st.session_state["carrito"]:
                        if item["codigo"] == codigo_prod:
                            item["cantidad"] += cant
                            encontrado = True
                            break
                    if not encontrado:
                        st.session_state["carrito"].append(
                            {
                                "codigo": codigo_prod,
                                "nombre": p_info["nombre"],
                                "precio": float(p_info["precio"]),
                                "cantidad": cant,
                            }
                        )
                    st.success("Producto agregado al carrito.")
                    st.rerun()

        with col_2:
            st.subheader("Carrito de Compras")
            if st.session_state["carrito"]:
                carrito_df = pd.DataFrame(st.session_state["carrito"])
                carrito_df["subtotal"] = (
                    carrito_df["precio"] * carrito_df["cantidad"]
                )
                st.dataframe(
                    carrito_df[["nombre", "cantidad", "precio", "subtotal"]],
                    use_container_width=True,
                )

                total_venta = carrito_df["subtotal"].sum()
                st.write(f"### Total: ${total_venta:.2f}")

                if st.button("Vaciar Carrito"):
                    st.session_state["carrito"] = []
                    st.rerun()
            else:
                st.info("El carrito está vacío.")

        if st.session_state["carrito"]:
            st.markdown("---")
            st.subheader("Finalizar Venta")

            if clientes_df.empty:
                cliente_nombre = st.text_input("Nombre del Cliente (Opcional)")
            else:
                cliente_opciones = ["Cliente General"] + list(
                    clientes_df["nombre"]
                )
                cliente_sel = st.selectbox("Cliente", cliente_opciones)
                cliente_nombre = (
                    "" if cliente_sel == "Cliente General" else cliente_sel
                )

            tipo_pago = st.radio("Tipo de Pago", ["Contado", "Crédito (A plazo)"])
            metodo_pago = "N/A"
            if tipo_pago == "Contado":
                metodo_pago = st.selectbox(
                    "Método de Pago",
                    ["Efectivo", "Pago Móvil", "Zelle", "Binance"],
                )

            if st.button("Procesar Venta"):
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute(
                    "INSERT INTO ventas (fecha, cliente, tipo_pago,"
                    " metodo_pago, total, vendedor) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        fecha_actual,
                        cliente_nombre if cliente_nombre else "General",
                        tipo_pago,
                        metodo_pago,
                        total_venta,
                        rol_usuario,
                    ),
                )
                venta_id = c.lastrowid

                for item in st.session_state["carrito"]:
                    subtotal = item["precio"] * item["cantidad"]
                    c.execute(
                        "INSERT INTO detalle_ventas (venta_id, producto,"
                        " cantidad, precio_unitario, subtotal) VALUES (?, ?,"
                        " ?, ?, ?)",
                        (
                            venta_id,
                            item["nombre"],
                            item["cantidad"],
                            item["precio"],
                            subtotal,
                        ),
                    )
                    c.execute(
                        "UPDATE productos SET stock = stock - ? WHERE codigo ="
                        " ?",
                        (item["cantidad"], item["codigo"]),
                    )

                if tipo_pago == "Crédito (A plazo)":
                    c.execute(
                        "INSERT INTO cuentas_por_cobrar (venta_id, cliente,"
                        " monto_total, monto_pendiente, estado) VALUES (?, ?,"
                        " ?, ?, ?)",
                        (
                            venta_id,
                            cliente_nombre if cliente_nombre else "General",
                            total_venta,
                            total_venta,
                            "Pendiente",
                        ),
                    )

                conn.commit()
                st.session_state["carrito"] = []
                st.success("¡Venta registrada exitosamente!")
                st.rerun()

# ----------------------------------------------------
# INVENTARIO DE PRODUCTOS
# ----------------------------------------------------
elif opcion == "📦 Inventario de Productos":
    st.header("📦 Inventario de Productos")
    if rol_usuario == "admin":
        with st.expander("Agregar Nuevo Producto"):
            with st.form("form_prod"):
                codigo = st.text_input("Código")
                nombre = st.text_input("Nombre del Producto")
                categoria = st.text_input("Categoría")
                precio = st.number_input(
                    "Precio de Venta", min_value=0.0, format="%.2f"
                )
                costo = st.number_input("Costo", min_value=0.0, format="%.2f")
                stock = st.number_input("Stock Inicial", min_value=0, step=1)
                submitted = st.form_submit_button("Guardar Producto")
                if submitted:
                    try:
                        c.execute(
                            "INSERT INTO productos (codigo, nombre, categoria,"
                            " precio, costo, stock) VALUES (?, ?, ?, ?, ?, ?)",
                            (codigo, nombre, categoria, precio, costo, stock),
                        )
                        conn.commit()
                        st.success("Producto agregado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

    df_prod = pd.read_sql_query("SELECT * FROM productos", conn)
    st.dataframe(df_prod, use_container_width=True)

# ----------------------------------------------------
# CLIENTES
# ----------------------------------------------------
elif opcion == "👥 Clientes":
    st.header("👥 Gestión de Clientes")
    with st.expander("Registrar Nuevo Cliente"):
        with st.form("form_cli"):
            cedula = st.text_input("Cédula / RIF")
            nombre = st.text_input("Nombre Completo")
            telefono = st.text_input("Teléfono")
            direccion = st.text_input("Dirección")
            sub_cli = st.form_submit_button("Guardar Cliente")
            if sub_cli:
                try:
                    c.execute(
                        "INSERT INTO clientes (cedula, nombre, telefono,"
                        " direccion) VALUES (?, ?, ?, ?)",
                        (cedula, nombre, telefono, direccion),
                    )
                    conn.commit()
                    st.success("Cliente registrado con éxito.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar cliente: {e}")

    df_cli = pd.read_sql_query("SELECT * FROM clientes", conn)
    st.dataframe(df_cli, use_container_width=True)

# ----------------------------------------------------
# CUENTAS POR COBRAR
# ----------------------------------------------------
elif opcion == "💳 Cuentas por Cobrar":
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
# REPORTES DE VENTAS
# ----------------------------------------------------
elif opcion == "📊 Reportes de Ventas":
    st.header("📊 Reportes y Finanzas")

    df_v = pd.read_sql_query("SELECT * FROM ventas", conn)
    st.subheader("Historial de Ventas")
    st.dataframe(df_v, use_container_width=True)

    if not df_v.empty:
        total_ingresos = df_v["total"].sum()
        st.metric("Total Ingresos Acumulados", f"${total_ingresos:.2f}")

    if rol_usuario == "admin":
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🗑️ Limpiar Historial de Ventas")
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
            st.subheader("🔥 Reiniciar Todo el Sistema")
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
