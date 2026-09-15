import io
import os
import xmltodict
import pandas as pd
import streamlit as st

# Funciones de extracción reutilizadas de tu script base
def limpiar_valor(valor):
    if valor is None:
        return 'N/A'
    if isinstance(valor, dict):
        if '#text' in valor:
            return str(valor['#text']).strip()
        for k, v in valor.items():
            if not k.startswith('@'):
                return limpiar_valor(v)
        return 'N/A'
    if isinstance(valor, list):
        if len(valor) > 0:
            return limpiar_valor(valor[0])
        return 'N/A'
    return str(valor).strip()

def buscar_subclave(diccionario, clave_buscada):
    if isinstance(diccionario, dict):
        for k, v in diccionario.items():
            clean_key = k.split(':')[-1]
            if clean_key.lower() == clave_buscada.lower():
                return v
            if isinstance(v, (dict, list)):
                res = buscar_subclave(v, clave_buscada)
                if res is not None:
                    return res
    elif isinstance(diccionario, list):
        for item in diccionario:
            res = buscar_subclave(item, clave_buscada)
            if res is not None:
                return res
    return None

def extraer_nombre_tercero(party_node):
    if not party_node:
        return 'N/A'
    nombre = buscar_subclave(buscar_subclave(party_node, 'PartyName'), 'Name')
    if nombre and limpiar_valor(nombre) != 'N/A':
        return limpiar_valor(nombre)
    nombre = buscar_subclave(buscar_subclave(party_node, 'PartyLegalEntity'), 'RegistrationName')
    if nombre and limpiar_valor(nombre) != 'N/A':
        return limpiar_valor(nombre)
    return 'N/A'

def extraer_nit_tercero(party_node):
    if not party_node:
        return 'N/A'
    nit = (
        buscar_subclave(buscar_subclave(party_node, 'PartyTaxScheme'), 'CompanyID') or
        buscar_subclave(buscar_subclave(party_node, 'PartyLegalEntity'), 'CompanyID') or
        buscar_subclave(party_node, 'CompanyID')
    )
    return limpiar_valor(nit)

def procesar_xml_bytes(file_bytes, filename):
    raw_xml = file_bytes.decode('utf-8', errors='ignore')
    data = xmltodict.parse(raw_xml, process_namespaces=False)
    
    attached = buscar_subclave(data, 'AttachedDocument')
    if attached:
        attachment_node = buscar_subclave(attached, 'Attachment')
        xml_cdata = buscar_subclave(attachment_node, 'Description')
        if xml_cdata and isinstance(xml_cdata, str):
            for tag in ['<Invoice', '<CreditNote', '<DebitNote']:
                if tag in xml_cdata:
                    idx_start = xml_cdata.find(tag)
                    data = xmltodict.parse(xml_cdata[idx_start:], process_namespaces=False)
                    break

    doc_node = buscar_subclave(data, 'Invoice') or buscar_subclave(data, 'CreditNote') or buscar_subclave(data, 'DebitNote')
    if not doc_node:
        raise ValueError("Estructura XML de factura DIAN no válida.")

    numero_factura = limpiar_valor(buscar_subclave(doc_node, 'ID'))
    fecha_emision = limpiar_valor(buscar_subclave(doc_node, 'IssueDate'))
    cufe = limpiar_valor(buscar_subclave(doc_node, 'UUID'))
    
    emisor_nit = extraer_nit_tercero(buscar_subclave(buscar_subclave(doc_node, 'AccountingSupplierParty'), 'Party'))
    emisor_nombre = extraer_nombre_tercero(buscar_subclave(buscar_subclave(doc_node, 'AccountingSupplierParty'), 'Party'))
    
    cliente_nit = extraer_nit_tercero(buscar_subclave(buscar_subclave(doc_node, 'AccountingCustomerParty'), 'Party'))
    cliente_nombre = extraer_nombre_tercero(buscar_subclave(buscar_subclave(doc_node, 'AccountingCustomerParty'), 'Party'))

    totales_node = buscar_subclave(doc_node, 'LegalMonetaryTotal') or {}
    subtotal = limpiar_valor(buscar_subclave(totales_node, 'LineExtensionAmount'))
    total_pagar = limpiar_valor(buscar_subclave(totales_node, 'PayableAmount'))

    lineas = buscar_subclave(doc_node, 'InvoiceLine') or []
    if isinstance(lineas, dict): lineas = [lineas]

    filas_detalle = []
    descripciones = []
    for idx, linea in enumerate(lineas, start=1):
        item_node = buscar_subclave(linea, 'Item') or {}
        desc = limpiar_valor(buscar_subclave(item_node, 'Description') or 'Sin detalle')
        descripciones.append(desc)
        
        filas_detalle.append({
            'Archivo': filename,
            'Factura_No': numero_factura,
            'Fecha': fecha_emision,
            'Emisor': emisor_nombre,
            'NIT_Emisor': emisor_nit,
            'Cliente': cliente_nombre,
            'Item': idx,
            'Descripcion': desc,
            'Cantidad': limpiar_valor(buscar_subclave(linea, 'InvoicedQuantity') or 1),
            'Total_Linea': limpiar_valor(buscar_subclave(linea, 'LineExtensionAmount'))
        })

    resumen = {
        'Archivo': filename,
        'Factura_No': numero_factura,
        'Fecha': fecha_emision,
        'Emisor': emisor_nombre,
        'Cliente': cliente_nombre,
        'Cantidad_Items': len(lineas),
        'Resumen_Descripcion': " / ".join(descripciones),
        'Subtotal': subtotal,
        'Total_Pagar': total_pagar
    }

    return filas_detalle, resumen

# Interfaz Web con Streamlit
st.set_page_config(page_title="Validador y Extractor DIAN UBL 2.1", layout="wide")
st.title("🇨🇴 Extractor y Procesador de Facturas Electrónicas DIAN (UBL 2.1)")
st.markdown("Sube tus archivos XML de factura electrónica colombiana para procesarlos de forma estructurada.")

uploaded_files = st.file_uploader("Selecciona tus archivos XML", type=["xml"], accept_multiple_files=True)

if uploaded_files:
    detalles_global = []
    resumenes_global = []

    for file in uploaded_files:
        try:
            bytes_data = file.read()
            detalles, resumen = procesar_xml_bytes(bytes_data, file.name)
            detalles_global.extend(detalles)
            resumenes_global.append(resumen)
        except Exception as e:
            st.error(f"Error procesando {file.name}: {e}")

    if resumenes_global:
        st.success(f"¡{len(resumenes_global)} factura(s) procesada(s) con éxito!")
        
        tab1, tab2 = st.tabs(["📊 Vista Resumen", "📄 Vista Detalle de Ítems"])
        
        df_resumen = pd.DataFrame(resumenes_global)
        df_detalle = pd.DataFrame(detalles_global)

        with tab1:
            st.dataframe(df_resumen, use_container_width=True)
            csv_res = df_resumen.to_csv(sep='|', index=False).encode('utf-8')
            st.download_button("📥 Descargar Reporte Resumen (.txt)", csv_res, "reporte_resumen.txt", "text/plain")

        with tab2:
            st.dataframe(df_detalle, use_container_width=True)
            csv_det = df_detalle.to_csv(sep='|', index=False).encode('utf-8')
            st.download_button("📥 Descargar Reporte Detalle (.txt)", csv_det, "reporte_detalle.txt", "text/plain")
