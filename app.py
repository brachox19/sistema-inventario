import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Sistema de Gestión de Inventario", layout="wide")

# Conexión a la base de datos
conn = sqlite3.connect("inventario.db", check_same_thread=False)
c = conn.cursor()

# Creación de tablas
c.execute('''CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                nombre TEXT,
                categoria TEXT,
                precio REAL,
                costo REAL,
                stock INTEGER
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cedula TEXT UNIQUE,
                nombre TEXT,
                telefono TEXT,
                direccion TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                cliente TEXT,
                tipo_pago TEXT,
                metodo_pago TEXT,
                total REAL,
                vendedor TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS detalle_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER,
                producto TEXT,
                cantidad INTEGER,
                precio_unitario REAL,
                subtotal REAL,
                FOREIGN KEY (venta_id) REFERENCES ventas (id)
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS cuentas_por_cobrar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER,
                cliente TEXT,
                monto_total REAL,
                monto_pendiente REAL,
                estado TEXT,
                FOREIGN KEY (venta_id) REFERENCES ventas (id)
            )''')
conn.commit()

# Autenticación de usuarios
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["username"] = ""

def login():
    st.title("🔑 Inicio de Sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        if username == "admin" and password == "admin123":
            st.session_state["logged_in"] = True
            st.session_state["user_role"] = "Admin"
            st.session_state["username"] = "admin"
            st.rerun()
        elif username == "vendedora" and password == "vende123":
            st.session_state["logged_in"] = True
            st.session_state["user_role"] = "Vendedora"
            st.session_state["username"] = "vendedora"
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

if not st.session_state["logged_in"]:
    login()
else:
    st.sidebar.title(f"👤 {st.session_state['username'].capitalize()}")
    st.sidebar.caption(f"Rol: {st.session_state['user_role']}")
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["logged_in"] = False
        st.rerun()

    # Menú principal adaptado según el rol
    menu_options = ["🛒 Punto de Venta", "📦 Productos / Inventario", "👥 Clientes", "💳 Cuentas por Cobrar"]
    if st.session_state["user_role"] == "Admin":
        menu_options.extend(["📊 Reportes de Ventas", "📈 Ganancias / Finanzas", "⚙️ Mantenimiento / Reset"])

    opcion = st.sidebar.selectbox("Navegación", menu_options)

    # ----------------------------------------------------
    # PUNTO DE VENTA (OPTIMIZADO PARA VENDEDORA)
    # ----------------------------------------------------
    if opcion == "🛒 Punto de Venta":
        st.header("🛒 Punto de Venta Rápidas")
        
        if "carrito" not in st.session_state:
            st.session_state["carrito"] = []

        prods = pd.read_sql_query("SELECT id, codigo, nombre, precio, stock FROM productos WHERE stock > 0", conn)
        clientes_df = pd.read_sql_query("SELECT cedula, nombre FROM clientes", conn)

        col1, col2 = st.columns([1.6, 1.2])

        with col1:
            st.subheader("1️⃣ Buscar y Seleccionar Producto")
            if not prods.empty:
                opciones_prods = {f"{row['nombre']} | Cód: {row['codigo']} | ${row['precio']} (Disponibles: {row['stock']})": row for _, row in prods.iterrows()}
                prod_selected_str = st.selectbox("Escribe o selecciona un producto:", list(opciones_prods.keys()))
                prod_actual = opciones_prods[prod_selected_str]
                
                stock_disponible = int(prod_actual["stock"])
                cant_en_carrito = sum(item["cantidad"] for item in st.session_state["carrito"] if item["id"] == prod_actual["id"])
                stock_restante_para_carrito = stock_disponible - cant_en_carrito

                col_a, col_b = st.columns([1, 1])
                with col_a:
                    cant = st.number_input("Cantidad:", min_value=1, value=1, step=1)
                with col_b:
                    st.write("")
                    st.write("")
                    if st.button("➕ Agregar al Carrito", use_container_width=True):
                        if cant > stock_restante_para_carrito:
                            if stock_restante_para_carrito <= 0:
                                st.error(f"❌ Stock agotado en carrito. ({stock_disponible} en inventario)")
                            else:
                                st.error(f"❌ Solo puedes agregar {stock_restante_para_carrito} más.")
                        else:
                            st.session_state["carrito"].append({
                                "id": int(prod_actual["id"]),
                                "nombre": str(prod_actual["nombre"]),
                                "precio": float(prod_actual["precio"]),
                                "cantidad": int(cant),
                                "subtotal": float(prod_actual["precio"] * cant)
                            })
                            st.success(f"✅ Agregado")
                            st.rerun()
            else:
                st.warning("⚠️ No hay productos con stock disponible en este momento.")

            st.divider()
            st.subheader("🛒 Carrito de Compras")
            if st.session_state["carrito"]:
                df_carrito = pd.DataFrame(st.session_state["carrito"])
                st.dataframe(df_carrito[["nombre", "cantidad", "precio", "subtotal"]], use_container_width=True)
                
                if st.button("🗑️ Vaciar Carrito"):
                    st.session_state["carrito"] = []
                    st.rerun()
            else:
                st.info("El carrito está vacío.")

        with col2:
            st.subheader("2️⃣ Finalizar Cobro")
            if st.session_state["carrito"]:
                df_carrito = pd.DataFrame(st.session_state["carrito"])
                total_venta = df_carrito["subtotal"].sum()
                
                # Monto destacado visualmente
                st.metric(label="TOTAL A PAGAR", value=f"${total_venta:.2f}")

                st.markdown("---")
                cliente_nombre = st.selectbox("Seleccionar Cliente:", ["Cliente General"] + list(clientes_df["nombre"]))

                # Registro rápido de cliente en un click
                with st.expander("➕ ¿Cliente Nuevo? Registrar aquí rápido"):
                    with st.form("pos_fast_client", clear_on_submit=True):
                        new_cedula = st.text_input("Cédula / ID")
                        new_nombre = st.text_input("Nombre Completo")
                        new_tel = st.text_input("Teléfono")
                        new_dir = st.text_input("Dirección")
                        submit_cli = st.form_submit_button("💾 Guardar y Seleccionar")

                        if submit_cli:
                            if new_cedula and new_nombre:
                                try:
                                    c.execute("INSERT INTO clientes (cedula, nombre, telefono, direccion) VALUES (?, ?, ?, ?)",
                                              (new_cedula, new_nombre, new_tel, new_dir))
                                    conn.commit()
                                    st.success(f"✅ Guardado. Ahora selecciónalo en la lista.")
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    st.error("Esa Cédula / ID ya está registrada.")
                            else:
                                st.warning("Ingresa al menos Cédula y Nombre.")

                tipo_pago = st.radio("Forma de Venta:", ["Contado", "Crédito"], horizontal=True)
                
                metodo_pago = "Crédito"
                if tipo_pago == "Contado":
                    metodo_pago = st.selectbox("Método de Pago:", ["Pago Móvil", "Efectivo", "Zelle", "Binance"])

                if st.button("✅ REGISTRAR VENTA", type="primary", use_container_width=True):
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    c.execute("INSERT INTO ventas (fecha, cliente, tipo_pago, metodo_pago, total, vendedor) VALUES (?, ?, ?, ?, ?, ?)",
                              (fecha, cliente_nombre, tipo_pago, metodo_pago, total_venta, st.session_state["username"]))
                    venta_id = c.lastrowid

                    for item in st.session_state["carrito"]:
                        c.execute("INSERT INTO detalle_ventas (venta_id, producto, cantidad, precio_unitario, subtotal) VALUES (?, ?, ?, ?, ?)",
                                  (venta_id, item["nombre"], item["cantidad"], item["precio"], item["subtotal"]))
                        c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item["cantidad"], item["id"]))

                    if tipo_pago == "Crédito":
                        c.execute("INSERT INTO cuentas_por_cobrar (venta_id, cliente, monto_total, monto_pendiente, estado) VALUES (?, ?, ?, ?, ?)",
                                  (venta_id, cliente_nombre, total_venta, total_venta, "Pendiente"))

                    conn.commit()
                    st.session_state["carrito"] = []
                    st.balloons()
                    st.success("🎉 ¡Venta realizada con éxito!")
                    st.rerun()

    # ----------------------------------------------------
    # PRODUCTOS / INVENTARIO
    # ----------------------------------------------------
    elif opcion == "📦 Productos / Inventario":
        st.header("📦 Gestión de Inventario")
        
        if st.session_state["user_role"] == "Admin":
            tab1, tab2, tab3 = st.tabs(["📋 Lista de Productos", "➕ Registrar Producto", "✏️ Editar / 🗑️ Eliminar"])
        else:
            tab1, tab2 = st.tabs(["📋 Lista de Productos", "➕ Registrar Producto"])

        with tab1:
            st.subheader("Inventario Actual")
            if st.session_state["user_role"] == "Admin":
                df_prods = pd.read_sql_query("SELECT id, codigo, nombre, categoria, precio, costo, stock FROM productos", conn)
            else:
                df_prods = pd.read_sql_query("SELECT id, codigo, nombre, categoria, precio, stock FROM productos", conn)
                
            st.dataframe(df_prods, use_container_width=True)

        with tab2:
            st.subheader("Registrar Nuevo Producto")
            
            with st.form("form_nuevo_prod", clear_on_submit=True):
                codigo = st.text_input("Código de Producto")
                nombre = st.text_input("Nombre del Producto")
                cat = st.text_input("Categoría")
                precio = st.number_input("Precio de Venta ($)", min_value=0.0, format="%.2f")
                
                if st.session_state["user_role"] == "Admin":
                    costo = st.number_input("Costo ($)", min_value=0.0, format="%.2f")
                else:
                    costo = 0.0

                stock = st.number_input("Stock Inicial", min_value=0, step=1)
                
                submit_p = st.form_submit_button("Guardar Producto")

                if submit_p:
                    try:
                        c.execute("INSERT INTO productos (codigo, nombre, categoria, precio, costo, stock) VALUES (?, ?, ?, ?, ?, ?)",
                                  (codigo, nombre, cat, precio, costo, stock))
                        conn.commit()
                        st.success("Producto registrado exitosamente.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("El código del producto ya existe.")

        if st.session_state["user_role"] == "Admin":
            with tab3:
                st.subheader("Modificar o Eliminar un Producto")
                df_prods = pd.read_sql_query("SELECT * FROM productos", conn)
                
                if not df_prods.empty:
                    opciones = {f"{r['id']} - {r['nombre']} (Cód: {r['codigo']})": r for _, r in df_prods.iterrows()}
                    prod_sel_key = st.selectbox("Seleccionar producto a gestionar", list(opciones.keys()))
                    prod_data = opciones[prod_sel_key]

                    col_e1, col_e2 = st.columns(2)
                    
                    with col_e1:
                        st.markdown("### **Editar Producto**")
                        edit_codigo = st.text_input("Código", value=str(prod_data["codigo"]), key="edit_cod")
                        edit_nombre = st.text_input("Nombre", value=str(prod_data["nombre"]), key="edit_nom")
                        edit_cat = st.text_input("Categoría", value=str(prod_data["categoria"]), key="edit_cat")
                        edit_precio = st.number_input("Precio ($)", value=float(prod_data["precio"]), format="%.2f", key="edit_prec")
                        edit_costo = st.number_input("Costo ($)", value=float(prod_data["costo"]), format="%.2f", key="edit_cost")
                        edit_stock = st.number_input("Stock actual", value=int(prod_data["stock"]), step=1, key="edit_stk")

                        if st.button("💾 Actualizar Producto"):
                            c.execute("""UPDATE productos 
                                         SET codigo=?, nombre=?, categoria=?, precio=?, costo=?, stock=? 
                                         WHERE id=?""",
                                      (edit_codigo, edit_nombre, edit_cat, edit_precio, edit_costo, edit_stock, prod_data["id"]))
                            conn.commit()
                            st.success("Producto actualizado correctamente.")
                            st.rerun()

                    with col_e2:
                        st.markdown("### **Eliminar Producto**")
                        st.warning(f"¿Estás seguro de eliminar '{prod_data['nombre']}'?")
                        if st.button("🗑️ Eliminar Producto Definitivamente"):
                            c.execute("DELETE FROM productos WHERE id=?", (prod_data["id"],))
                            conn.commit()
                            st.success("Producto eliminado.")
                            st.rerun()
                else:
                    st.info("No hay productos registrados.")

    # ----------------------------------------------------
    # CLIENTES
    # ----------------------------------------------------
    elif opcion == "👥 Clientes":
        st.header("👥 Gestión de Clientes")
        
        if st.session_state["user_role"] == "Admin":
            tab1, tab2, tab3 = st.tabs(["📋 Lista de Clientes", "➕ Registrar Cliente", "✏️ Editar / 🗑️ Eliminar"])
        else:
            tab1, tab2 = st.tabs(["📋 Lista de Clientes", "➕ Registrar Cliente"])

        with tab1:
            st.subheader("Clientes Registrados")
            df_clientes = pd.read_sql_query("SELECT * FROM clientes", conn)
            st.dataframe(df_clientes, use_container_width=True)

        with tab2:
            st.subheader("Registrar Nuevo Cliente")
            
            with st.form("form_nuevo_cli", clear_on_submit=True):
                cedula = st.text_input("Cédula / RIF / ID")
                nombre = st.text_input("Nombre Completo")
                telefono = st.text_input("Teléfono")
                direccion = st.text_area("Dirección")
                
                submit_c = st.form_submit_button("Guardar Cliente")

                if submit_c:
                    try:
                        c.execute("INSERT INTO clientes (cedula, nombre, telefono, direccion) VALUES (?, ?, ?, ?)",
                                  (cedula, nombre, telefono, direccion))
                        conn.commit()
                        st.success("Cliente registrado con éxito.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("La cédula/ID ya se encuentra registrada.")

        if st.session_state["user_role"] == "Admin":
            with tab3:
                st.subheader("Modificar o Eliminar un Cliente")
                df_clientes = pd.read_sql_query("SELECT * FROM clientes", conn)

                if not df_clientes.empty:
                    opciones_c = {f"{r['id']} - {r['nombre']} (ID: {r['cedula']})": r for _, r in df_clientes.iterrows()}
                    cli_sel_key = st.selectbox("Seleccionar cliente a gestionar", list(opciones_c.keys()))
                    cli_data = opciones_c[cli_sel_key]

                    col_c1, col_c2 = st.columns(2)

                    with col_c1:
                        st.markdown("### **Editar Cliente**")
                        edit_cedula = st.text_input("Cédula / ID", value=str(cli_data["cedula"]), key="edit_ced")
                        edit_cnombre = st.text_input("Nombre", value=str(cli_data["nombre"]), key="edit_cnom")
                        edit_tel = st.text_input("Teléfono", value=str(cli_data["telefono"]), key="edit_ctel")
                        edit_dir = st.text_area("Dirección", value=str(cli_data["direccion"]), key="edit_cdir")

                        if st.button("💾 Actualizar Cliente"):
                            c.execute("UPDATE clientes SET cedula=?, nombre=?, telefono=?, direccion=? WHERE id=?",
                                      (edit_cedula, edit_cnombre, edit_tel, edit_dir, cli_data["id"]))
                            conn.commit()
                            st.success("Cliente actualizado con éxito.")
                            st.rerun()

                    with col_c2:
                        st.markdown("### **Eliminar Cliente**")
                        st.warning(f"¿Deseas borrar al cliente '{cli_data['nombre']}'?")
                        if st.button("🗑️ Eliminar Cliente"):
                            c.execute("DELETE FROM clientes WHERE id=?", (cli_data["id"],))
                            conn.commit()
                            st.success("Cliente eliminado.")
                            st.rerun()
                else:
                    st.info("No hay clientes registrados.")

    # ----------------------------------------------------
    # CUENTAS POR COBRAR
    # ----------------------------------------------------
    elif opcion == "💳 Cuentas por Cobrar":
        st.header("💳 Cuentas por Cobrar")
        
        cxc_df = pd.read_sql_query("SELECT * FROM cuentas_por_cobrar WHERE estado = 'Pendiente'", conn)
        
        if not cxc_df.empty:
            st.dataframe(cxc_df, use_container_width=True)
            
            st.subheader("Registrar Pago / Abono")
            cxc_sel = st.selectbox("Seleccionar Deuda", cxc_df["id"].astype(str) + " - Cliente: " + cxc_df["cliente"] + " - Pendiente: $" + cxc_df["monto_pendiente"].astype(str))
            selected_id = int(cxc_sel.split(" - ")[0])
            monto_act = cxc_df[cxc_df["id"] == selected_id]["monto_pendiente"].values[0]
            
            monto_pago = st.number_input("Monto a Abonar ($)", min_value=0.01, max_value=float(monto_act), format="%.2f")
            
            if st.button("Registrar Abonado"):
                nuevo_pendiente = monto_act - monto_pago
                nuevo_estado = "Pagado" if nuevo_pendiente <= 0 else "Pendiente"
                c.execute("UPDATE cuentas_por_cobrar SET monto_pendiente = ?, estado = ? WHERE id = ?",
                          (nuevo_pendiente, nuevo_estado, selected_id))
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

        if not df_v.empty:
            st.subheader("Detalle de Ventas")
            df_dv = pd.read_sql_query("SELECT * FROM detalle_ventas", conn)
            st.dataframe(df_dv, use_container_width=True)

            st.divider()
            st.subheader("❌ Anular / Borrar una Venta Especial")
            st.caption("Al borrar una venta, los productos vendidos serán devueltos automáticamente al stock.")
            
            venta_cancel_sel = st.selectbox("Seleccionar Venta a Anular", df_v["id"].astype(str) + " - Fecha: " + df_v["fecha"] + " - Cliente: " + df_v["cliente"] + " - Total: $" + df_v["total"].astype(str))
            venta_id_to_del = int(venta_cancel_sel.split(" - ")[0])

            if st.button("🗑️ Anular y Revertir Venta"):
                detalles = c.execute("SELECT producto, cantidad FROM detalle_ventas WHERE venta_id=?", (venta_id_to_del,)).fetchall()
                for prod_nom, cant in detalles:
                    c.execute("UPDATE productos SET stock = stock + ? WHERE nombre=?", (cant, prod_nom))

                c.execute("DELETE FROM detalle_ventas WHERE venta_id=?", (venta_id_to_del,))
                c.execute("DELETE FROM cuentas_por_cobrar WHERE venta_id=?", (venta_id_to_del,))
                c.execute("DELETE FROM ventas WHERE id=?", (venta_id_to_del,))
                conn.commit()
                st.success("Venta anulada con éxito y productos retornados al stock.")
                st.rerun()

    # ----------------------------------------------------
    # GANANCIAS / FINANZAS (ADMIN)
    # ----------------------------------------------------
    elif opcion == "📈 Ganancias / Finanzas":
        st.header("📈 Ganancias y Finanzas")
        
        df_fin = pd.read_sql_query('''
            SELECT dv.producto, dv.cantidad, dv.precio_unitario, dv.subtotal,
                   (dv.cantidad * p.costo) as costo_total,
                   (dv.subtotal - (dv.cantidad * p.costo)) as ganancia_neta
            FROM detalle_ventas dv
            JOIN productos p ON dv.producto = p.nombre
        ''', conn)
        
        df_creditos = pd.read_sql_query("SELECT SUM(monto_pendiente) as total_credito FROM cuentas_por_cobrar WHERE estado = 'Pendiente'", conn)
        total_credito_pendiente = df_creditos["total_credito"].values[0] if not df_creditos.empty and df_creditos["total_credito"].values[0] is not None else 0.0

        if not df_fin.empty:
            total_ingresos = df_fin["subtotal"].sum()
            total_costos = df_fin["costo_total"].sum()
            total_ganancia = df_fin["ganancia_neta"].sum()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Ingresos", f"${total_ingresos:.2f}")
            col2.metric("Total Costos", f"${total_costos:.2f}")
            col3.metric("Ganancia Neta Est.", f"${total_ganancia:.2f}")
            col4.metric("Crédito Pendiente 💳", f"${total_credito_pendiente:.2f}")

            st.subheader("Detalle Financiero por Producto Vendido")
            st.dataframe(df_fin, use_container_width=True)
        else:
            col1, col2 = st.columns(2)
            col1.metric("Crédito Pendiente 💳", f"${total_credito_pendiente:.2f}")
            st.info("Aún no se registran ventas para calcular ingresos y costos.")

    # ----------------------------------------------------
    # MANTENIMIENTO / RESET (ADMIN ONLY)
    # ----------------------------------------------------
    elif opcion == "⚙️ Mantenimiento / Reset":
        st.header("⚙️ Opciones de Mantenimiento y Limpieza")
        st.warning("⚠️ Atención: Las siguientes acciones eliminarán la información de la base de datos de manera irreversible.")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🗑️ Limpiar Historial de Ventas")
            st.write("Elimina solo el registro de ventas, cuentas por cobrar y el historial financiero, manteniendo tus productos y clientes intactos.")
            
            confirm_ventas = st.checkbox("Confirmo que deseo borrar todas las ventas")
            if st.button("Borrar Solo Ventas"):
                if confirm_ventas:
                    c.execute("DELETE FROM ventas")
                    c.execute("DELETE FROM detalle_ventas")
                    c.execute("DELETE FROM cuentas_por_cobrar")
                    conn.commit()
                    st.success("✅ Historial de ventas limpiado correctamente.")
                    st.rerun()
                else:
                    st.error("Debes marcar la casilla de confirmación para proceder.")

        with col2:
            st.subheader("🔥 Reiniciar Todo el Sistema (Reset Total)")
            st.write("Borra **TODA** la información: productos del inventario, lista de clientes, historial de ventas y deudas.")
            
            confirm_todo = st.checkbox("Confirmo que deseo Borrar TODO el sistema")
            if st.button("REINICIAR SISTEMA COMPLETO"):
                if confirm_todo:
                    c.execute("DELETE FROM ventas")
                    c.execute("DELETE FROM detalle_ventas")
                    c.execute("DELETE FROM cuentas_por_cobrar")
                    c.execute("DELETE FROM productos")
                    c.execute("DELETE FROM clientes")
                    conn.commit()
                    st.session_state["carrito"] = []
                    st.success("✅ La base de datos ha sido reiniciada completamente.")
                    st.rerun()
                else:
                    st.error("Debes marcar la casilla de confirmación para proceder.")