# Facturas — Extractor de Facturas Electrónicas DIAN (UBL 2.1)

Aplicación web en **Streamlit** que lee archivos XML de facturación electrónica colombiana (formato UBL 2.1 de la DIAN) y muestra su información en tablas estructuradas, listas para revisar o copiar a Excel.

## ¿Qué hace?

- Permite cargar **varios archivos XML a la vez**.
- Reconoce dos formatos de archivo:
  - **Invoice** directo (el XML de la factura).
  - **AttachedDocument** (el contenedor que envían los proveedores por correo). La app extrae automáticamente la factura incrustada en el CDATA de `cac:Attachment`.
- Ignora los prefijos de namespace (`cbc:`, `cac:`, etc.), así que funciona con XML generados por distintos proveedores tecnológicos.
- Presenta los resultados en dos pestañas:

| Pestaña | Una fila por… | Campos |
|---|---|---|
| 📊 **Vista Resumen** | factura | Archivo, Factura_No, Fecha, Emisor, Cliente, Cantidad_Items, Resumen_Descripcion, Subtotal, Total_Pagar |
| 📄 **Vista Detalle de Ítems** | línea de la factura | Archivo, Factura_No, Fecha, Emisor, Item, Descripcion, Cantidad, Total_Linea |

Si un archivo no tiene estructura de factura DIAN, la app muestra un error para ese archivo y sigue procesando los demás.

### Origen de cada campo en el XML

| Campo | Elemento UBL |
|---|---|
| Factura_No | `cbc:ID` |
| Fecha | `cbc:IssueDate` |
| Emisor / Cliente | `cac:PartyName/cbc:Name` o, si no existe, `cac:PartyLegalEntity/cbc:RegistrationName` dentro de `AccountingSupplierParty` / `AccountingCustomerParty` |
| Subtotal | `cac:LegalMonetaryTotal/cbc:LineExtensionAmount` |
| Total_Pagar | `cac:LegalMonetaryTotal/cbc:PayableAmount` |
| Descripcion | `cac:InvoiceLine/cac:Item/cbc:Description` |
| Cantidad | `cbc:InvoicedQuantity` |
| Total_Linea | `cac:InvoiceLine/cbc:LineExtensionAmount` |

## Requisitos

- Python 3.11
- Dependencias (`requirements.txt`):
  - `streamlit==1.35.0`
  - `xmltodict==0.13.0`

## Ejecución local

```bash
git clone https://github.com/CristianP95/Facturas.git
cd Facturas
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

La app queda disponible en `http://localhost:8501`.

## Ejecución en GitHub Codespaces / Dev Container

El repositorio incluye `.devcontainer/devcontainer.json`. Al abrirlo en Codespaces (o en VS Code con *Dev Containers*):

1. Se instalan las dependencias automáticamente.
2. Se inicia `streamlit run app.py` y se abre la vista previa en el puerto **8501**.

## Estructura del proyecto

```
Facturas/
├── app.py                      # Lógica de extracción + interfaz Streamlit
├── requirements.txt            # Dependencias de Python
├── runtime.txt                 # Versión de Python para despliegue
├── .devcontainer/
│   └── devcontainer.json       # Configuración de Codespaces / Dev Container
└── .gitignore
```

## Limitaciones conocidas

- **Notas crédito y débito:** el archivo se acepta y se leen el encabezado y los totales, pero sus líneas no aparecen. Esas notas usan `CreditNoteLine` / `DebitNoteLine` en lugar de `InvoiceLine`, así que *Cantidad_Items* sale en 0. En las notas débito, los totales están en `RequestedMonetaryTotal`.
- **Codificación:** el XML se decodifica como UTF-8. En archivos guardados en ISO-8859-1 se pierden las tildes y la ñ (por ejemplo, “consultoría” aparece como “consultora”).
- **No valida la factura:** no verifica la firma digital, el CUFE ni el estado ante la DIAN. Solo extrae los datos.
- **Valores como texto:** los montos se muestran como texto sin la moneda (`currencyID`), por eso no se pueden sumar directamente en la tabla.
- **NIT:** el código ya calcula el NIT del emisor y del cliente, pero todavía no los muestra en las tablas.
- **Sin exportación directa:** no hay botón para descargar en CSV o Excel. Se puede copiar la tabla o usar el menú de descarga de `st.dataframe`.

## Posibles mejoras

- Soportar las líneas de notas crédito y débito.
- Pasar los bytes originales a `xmltodict` para que respete la codificación declarada en el XML.
- Agregar columnas de NIT, CUFE, moneda e impuestos (`TaxTotal`).
- Convertir los montos a número y añadir un botón de exportación a Excel.
