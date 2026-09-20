from datetime import datetime
import pandas as pd
import streamlit as st
import libsql

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sistema de Gestión de Inventario", layout="wide"
)

# ---------------------------------------------------------
# CONEXIÓN A TURSO (NUBE)
# ---------------------------------------------------------
url = "libsql://inventario-vps-brachox19.aws-us-west-2.turso.io"
auth_token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODk4NzAzMjMsImlkIjoiMDFhMGJjNmItNWUwMS03YTQ5LWIyNzUtNDVmNWVmNzZmMjdmIiwia2lkIjoiNHZndmFuRWwwLU42NXV0eUpHdGZwMUhIaVpYTTJ5djhpU1ZoMmQ2QnZObyIsInJpZCI6ImM0ZTQ2NGRhLTM0YjAtNDI1Zi04NTBlLTAxM2U4OWVjOWU5YyJ9._Ib0ChcvCfDY5lzbUKFThJ9lUfHEy0LsLsadImEkFs8K39y0yE1RiQNqoHDG30gDCQF88Ap0YFkGemqCy89zBg"

conn = libsql.connect(database=url, auth_token=auth_token)

# Función auxiliar para ejecutar consultas y retornar DataFrames fácilmente
def ejecutar_sql_df(query, params=()):
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    cols = [description[0] for description in cursor.description] if cursor.description else []
    return pd.DataFrame(rows, columns=cols)

# Creación de tablas en Turso
conn.execute(
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
conn.commit()

conn.execute(
    """CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cedula TEXT UNIQUE,
                nombre TEXT,
                telefono TEXT,
                direccion TEXT
            )"""
)
conn.commit()

conn.execute(
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
conn.commit()

conn.execute(
    """CREATE TABLE IF NOT EXISTS detalle_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER,
                producto TEXT,
                cantidad INTEGER,
                precio_unitario REAL,
                subtotal REAL
            )"""
)
conn.commit()

conn.execute(
    """CREATE TABLE IF NOT EXISTS cuentas_por_cobrar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER,
                cliente TEXT,
                monto_total REAL,
                monto_pendiente REAL,
                estado TEXT
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

    productos_df = ejecutar_sql_df("SELECT * FROM productos")
    clientes_df = ejecutar_sql_df("SELECT * FROM clientes")

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
                productos_df["codigo"].astype(str)
                + " - "
                + productos_df["nombre"].astype(str)
                + " (Stock: "
                + productos_df["stock"].astype(str)
                + ")",
            )
            cant = st.number_input("Cantidad", min_value=1, value=1, step=1)

            if st.button("Agregar al Carrito"):
                codigo_prod = prod_sel.split(" - ")[0]
                p_info = productos_df[
                    productos_df["codigo"].astype(str) == codigo_prod
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
                
                cursor_v = conn.execute(
                    "INSERT INTO ventas (fecha, cliente, tipo_pago, metodo_pago, total, vendedor) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        fecha_actual,
                        cliente_nombre if cliente_nombre else "General",
                        tipo_pago,
                        metodo_pago,
                        float(total_venta),
                        rol_usuario,
                    ),
                )
                conn.commit()
                venta_id = cursor_v.lastrowid

                for item in st.session_state["carrito"]:
                    subtotal = item["precio"] * item["cantidad"]
                    conn.execute(
                        "INSERT INTO detalle_ventas (venta_id, producto, cantidad, precio_unitario, subtotal) VALUES (?, ?, ?, ?, ?)",
                        (
                            int(venta_id),
                            str(item["nombre"]),
                            int(item["cantidad"]),
                            float(item["precio"]),
                            float(subtotal),
                        ),
                    )
                    conn.execute(
                        "UPDATE productos SET stock = stock - ? WHERE codigo = ?",
                        (int(item["cantidad"]), str(item["codigo"])),
                    )
                conn.commit()

                if tipo_pago == "Crédito (A plazo)":
                    conn.execute(
                        "INSERT INTO cuentas_por_cobrar (venta_id, cliente, monto_total, monto_pendiente, estado) VALUES (?, ?, ?, ?, ?)",
                        (
                            int(venta_id),
                            str(cliente_nombre if cliente_nombre else "General"),
                            float(total_venta),
                            float(total_venta),
                            "Pendiente",
                        ),
                    )
                    conn.commit()

                st.session_state["carrito"] = []
                st.success("¡Venta registrada exitosamente en la nube!")
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
                        conn.execute(
                            "INSERT INTO productos (codigo, nombre, categoria, precio, costo, stock) VALUES (?, ?, ?, ?, ?, ?)",
                            (codigo, nombre, categoria, float(precio), float(costo), int(stock)),
                        )
                        conn.commit()
                        st.success("Producto agregado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

    df_prod = ejecutar_sql_df("SELECT * FROM productos")
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
                    conn.execute(
                        "INSERT INTO clientes (cedula, nombre, telefono, direccion) VALUES (?, ?, ?, ?)",
                        (cedula, nombre, telefono, direccion),
                    )
                    conn.commit()
                    st.success("Cliente registrado con éxito.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar cliente: {e}")

    df_cli = ejecutar_sql_df("SELECT * FROM clientes")
    st.dataframe(df_cli, use_container_width=True)

# ----------------------------------------------------
# CUENTAS POR COBRAR
# ----------------------------------------------------
elif opcion == "💳 Cuentas por Cobrar":
    st.header("💳 Cuentas por Cobrar")

    cxc_df = ejecutar_sql_df(
        "SELECT * FROM cuentas_por_cobrar WHERE estado = 'Pendiente'"
    )

    if not cxc_df.empty:
        st.dataframe(cxc_df, use_container_width=True)

        st.subheader("Registrar Pago / Abono")
        cxc_sel = st.selectbox(
            "Seleccionar Deuda",
            cxc_df["id"].astype(str)
            + " - Cliente: "
            + cxc_df["cliente"].astype(str)
            + " - Pendiente:  $"
            + cxc_df["monto_pendiente"].astype(str),
        )
        selected_id = int(cxc_sel.split(" - ")[0])
        monto_act = float(
            cxc_df[cxc_df["id"] == selected_id]["monto_pendiente"].values[0]
        )

        monto_pago = st.number_input(
            "Monto a Abonar ($)",
            min_value=0.01,
            max_value=monto_act,
            format="%.2f",
        )

        if st.button("Registrar Abonado"):
            nuevo_pendiente = monto_act - monto_pago
            nuevo_estado = (
                "Pagado" if nuevo_pendiente <= 0 else "Pendiente"
            )
            conn.execute(
                "UPDATE cuentas_por_cobrar SET monto_pendiente = ?, estado = ? WHERE id = ?",
                (float(nuevo_pendiente), str(nuevo_estado), int(selected_id)),
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

    df_v = ejecutar_sql_df("SELECT * FROM ventas")
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
                    conn.execute("DELETE FROM ventas")
                    conn.execute("DELETE FROM detalle_ventas")
                    conn.execute("DELETE FROM cuentas_por_cobrar")
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
                    conn.execute("DELETE FROM ventas")
                    conn.execute("DELETE FROM detalle_ventas")
                    conn.execute("DELETE FROM cuentas_por_cobrar")
                    conn.execute("DELETE FROM productos")
                    conn.execute("DELETE FROM clientes")
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
