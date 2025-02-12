import requests
from bs4 import BeautifulSoup
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
import urllib3
import openpyxl
from openpyxl.utils import get_column_letter 
# import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def datos_valparaiso(url):
    html_texto = requests.get(url, verify=False).text
    soup = BeautifulSoup(html_texto, 'html.parser')
    
    sitios = []
    for i in range(7, 15): 
        sitio_div = soup.find("div", class_=f"pln-titulo{i}")
        if sitio_div:
            sitio_nombre = sitio_div.find("span").text.strip() 
            sitios.append(sitio_nombre)
    
    datos = []
    
    fecha = []
    for i in range(7):  
        cellinfo = soup.find("div", class_=f"cellinfo-{i}-0")  
        fecha_result = "fecha no disponible"
        
        if cellinfo:
            dia_element = cellinfo.find("span", class_="text-dark pln-cell-fecha")
            mes_element = dia_element.find_next("span", class_="text-dark pln-cell-fecha") if dia_element else None
            
            if dia_element and mes_element:
                fecha_result = f"{dia_element.text.strip()} {mes_element.text.strip()}"
        
        fecha.append(fecha_result)

    for fila_idx in range(7): 
        for columna_idx in range(0, 9):  
            cellinfo = soup.find("div", class_=f"cellinfo-{fila_idx}-{columna_idx}")
            
            nombre_nave = ""
            hora = ""
            posicion = ""
            
            if cellinfo:
                nombre_nave_element = cellinfo.find("span", class_="pln-nombre-nave")
                posicion_element = cellinfo.find("span", class_="pln-posicion")
                hora_element = cellinfo.find("span", class_="pln-cell-hora text-primary")
                
                nombre_nave = nombre_nave_element.text.strip() if nombre_nave_element else "N/A"
                posicion = posicion_element.text.strip() if posicion_element else "N/A"
                hora = hora_element.text.strip() if hora_element else "N/A"

            datos.append({
                "Nombre Nave": nombre_nave,
                "Fecha": fecha[fila_idx],  
                "Hora": hora,
                "Posición": posicion,
                "Sitio": sitios[columna_idx - 1] if columna_idx - 1 < len(sitios) else "Sin Sitio"
            })
    
    return [nave for nave in datos if nave["Nombre Nave"] != "N/A"]

def datos_san_antonio(url):  
    html_texto = requests.get(url, verify=False).text
    soup = BeautifulSoup(html_texto, 'html.parser')
    
    encabezados_tr = soup.find('tr', class_='GridViewHeader')
    encabezados = encabezados_tr.find_all('th') if encabezados_tr else []
    encabezado_texto = [encabezado.text.strip() for encabezado in encabezados]
    
    filas = soup.find_all('tr', class_='GridView')
    
    datos = []
    for fila in filas:
        columnas = fila.find_all('td')
        if len(columnas) >= len(encabezado_texto):  
            fila_datos = {encabezado_texto[i]: columnas[i].text.strip() for i in range(len(encabezado_texto))}
            
            if all(value != '' for value in fila_datos.values()):
                datos.append(fila_datos)
    
    return datos

def cargar_datos(opcion):
    if opcion == "Valparaíso":
        url = "https://pln.puertovalparaiso.cl/pln/"
        datos = datos_valparaiso(url)
        return datos, "Nombre Nave"
    elif opcion == "San Antonio":
        url = "https://gessup.puertosanantonio.com/Planificaciones/general.aspx"
        datos = datos_san_antonio(url)
        # return datos, "Nombre Nave"
        return datos, "Nave"
    return [], ""

def index(request):
    if request.method == "POST":
        puerto = request.POST.get('puerto', 'Valparaíso')
    else:
        puerto = request.GET.get('puerto', 'Valparaíso')
        
    datos, clave = cargar_datos(puerto)

    if 'selected_ships' not in request.session:
        request.session['selected_ships'] = {}
    global_selected_ships = request.session['selected_ships']
    selected_ships = global_selected_ships.get(puerto, [])

    if request.method == "POST":
        try:
            selected_indices = [int(idx) for idx in request.POST.getlist('selected_ship')]
        except ValueError:
            selected_indices = []
        global_selected_ships[puerto] = selected_indices
        request.session['selected_ships'] = global_selected_ships
        selected_ships = selected_indices

    context = {
        'puerto': puerto,
        'datos': datos,
        'clave': clave,
        'selected_ships': selected_ships,
    }
    return render(request, 'info/index.html', context)


def detalle(request, index):
    puerto = request.GET.get('puerto', 'Valparaíso')
    datos, clave = cargar_datos(puerto)
    
    try:
        elemento = datos[index]
    except IndexError:
        return JsonResponse({"error": "Elemento no encontrado"}, status=404)
    
    return JsonResponse({
        'puerto': puerto,
        'elemento': elemento,
    })

def descargar_excel(request):
    print("Entrando en la vista descargar_excel...")
    
    if 'descargar_excel' in request.POST:
        print("Formulario recibido con la opción de descarga.")

        puerto = request.POST.get('puerto', 'Valparaíso')
        print(f"Puerto seleccionado: {puerto}")
        
        global_selected_ships = request.session.get('selected_ships', {})
        seleccionados = global_selected_ships.get(puerto, [])
        if not seleccionados:
            print("No hay naves seleccionadas.")
            return HttpResponse("No hay naves seleccionadas.", status=400)

        datos_seleccionados = []
        if puerto == 'Valparaíso':
            datos, clave = cargar_datos("Valparaíso")
        elif puerto == 'San Antonio':
            datos, clave = cargar_datos("San Antonio")
        else:
            return HttpResponse("Puerto no válido.", status=400)

        for idx in seleccionados:
            if idx < len(datos):
                datos_seleccionados.append(datos[idx])

        if not datos_seleccionados:
            print("No se encontraron datos de las naves seleccionadas.")
            return HttpResponse("No se encontraron datos de las naves seleccionadas.", status=400)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Naves Seleccionadas"

        if puerto == 'Valparaíso':
            encabezados = ["Nombre Nave", "Fecha", "Hora", "Posición", "Sitio"]
        elif puerto == 'San Antonio':
            encabezados = ["Nave", "E.T.A.", "Agencia", "Eslora", "Terminal", "Emp. muellaje", "Carga", "Detalle", "Cantidad", "Operación"]
        
        ws.append(encabezados)

        for nave in datos_seleccionados:
            if puerto == 'Valparaíso':
                row = [
                    nave.get("Nombre Nave", "N/A"),
                    nave.get("Fecha", "N/A"),
                    nave.get("Hora", "N/A"),
                    nave.get("Posición", "N/A"),
                    nave.get("Sitio", "Sin Sitio"),
                ]
            elif puerto == 'San Antonio':
                row = [
                    nave.get("Nave", "N/A"),
                    nave.get("E.T.A.", "N/A"),
                    nave.get("Agencia", "N/A"),
                    nave.get("Eslora", "N/A"),
                    nave.get("Terminal", "N/A"),
                    nave.get("Emp. muellaje", "N/A"),
                    nave.get("Carga", "N/A"),
                    nave.get("Detalle", "N/A"),
                    nave.get("Cantidad", "N/A"),
                    nave.get("Operación", "N/A"),
                ]
            ws.append(row)

        for col_num in range(1, len(encabezados) + 1):
            column_letter = get_column_letter(col_num)
            ws.column_dimensions[column_letter].width = 20

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = f'attachment; filename=naves_seleccionadas_{puerto}.xlsx'
        
        wb.save(response)

        return response
    else:
        print("Solicitud no válida")
        return HttpResponse("Solicitud no válida", status=400)

def seleccionar_naves(request):
    if request.method == "POST":
        seleccionados_valores = request.POST.getlist("selected_ship")
        seleccionados = []
        for valor in seleccionados_valores:
            try:
                puerto, idx_str = valor.split("-", 1)
                idx = int(idx_str)
                datos, clave = cargar_datos(puerto)
                nave = datos[idx]
                nave['Puerto'] = puerto
                seleccionados.append(nave)
            except (ValueError, IndexError):
                continue  

        request.session['selected_ships'] = seleccionados

        if "descargar_excel" in request.POST:
            return descargar_excel(request)

        context = {'seleccionados': seleccionados}
        return render(request, 'info/seleccionados.html', context)
    else:
        datos_val, clave_val = cargar_datos("Valparaíso")
        datos_sa, clave_sa = cargar_datos("San Antonio")
        context = {
            'datos_val': datos_val,
            'clave_val': clave_val,
            'datos_sa': datos_sa,
            'clave_sa': clave_sa,
        }
        return render(request, 'info/seleccionar.html', context)


def eliminar_nave(request, puerto, idx):
    global_selected_ships = request.session.get('selected_ships', {})
    selected_list = global_selected_ships.get(puerto, [])
    if idx in selected_list:
        selected_list.remove(idx)
        global_selected_ships[puerto] = selected_list
        request.session['selected_ships'] = global_selected_ships
    return redirect(f"/?puerto={puerto}")

def check_updates(request):
    puerto = request.GET.get('puerto', 'Valparaíso')
    datos, clave = cargar_datos(puerto)
    
    global_selected_ships = request.session.get('selected_ships', {})
    selected_ships = global_selected_ships.get(puerto, [])

    if 'last_info' not in request.session:
        request.session['last_info'] = {}
    last_info = request.session['last_info']
    
    updates = []
    for idx in selected_ships:
        if idx < len(datos):
            current_ship = datos[idx]
            key = f"{puerto}-{idx}"
            if key in last_info and last_info[key] != current_ship:
                updates.append(current_ship)

            last_info[key] = current_ship
            
    request.session['last_info'] = last_info
    return JsonResponse({'updates': updates})













# def datos_san_antonio(url):
#     html_texto = requests.get(url, verify=False).text
#     soup = BeautifulSoup(html_texto, 'html.parser')
    
#     # Verificar si la tabla contiene la clase correcta
#     tabla = soup.find('table', class_='planificacion')
#     if not tabla:
#         print("No se encontró la tabla con la clase 'planificacion'")
#         return []

#     # Buscar todas las tablas dentro de las celdas (tr > td > table)
#     tablas = soup.select('.planificacion > tbody > tr > td > table')
#     datos = []

#     for tabla_interna in tablas:
#         # Obtener el contenido de las celdas dentro de esta tabla interna
#         celdas = tabla_interna.find_all('td')
        
#         # Asegurarse de que hay suficientes celdas y que no estamos extrayendo información no deseada
#         if len(celdas) >= 4:
#             # Extraer el texto de cada celda
#             nave_nombre = celdas[0].text.strip()
#             hora_inicio = celdas[1].text.strip()
#             hora_fin = celdas[2].text.strip()
#             metros = celdas[3].text.strip()
#             nombre_buque = celdas[4].text.strip() if len(celdas) > 4 else ''

#             # Filtrar filas que contienen "Longitud", "Calado", "Sitio", etc.
#             if 'Sitio' in nave_nombre or 'Longitud' in nave_nombre or 'Calado' in nave_nombre:
#                 continue  # Ignorar esta fila si contiene datos no deseados

#             # Guardar la información en un diccionario
#             datos.append({
#                 'Nombre Nave': nave_nombre,
#                 'Hora Inicio': hora_inicio,
#                 'Hora Fin': hora_fin,
#                 'Metros': metros,
#                 'Nombre Buque': nombre_buque
#             })

#     # Verificar los datos extraídos
#     print("Datos extraídos:", datos)
#     return datos


# def datos_san_antonio(url):
#     html_texto = requests.get(url, verify=False).text
#     soup = BeautifulSoup(html_texto, 'html.parser')
    
#     # Verificar si la tabla contiene la clase correcta
#     tabla = soup.find('table', class_='planificacion')
#     if not tabla:
#         print("No se encontró la tabla con la clase 'planificacion'")
#         return []

#     # Buscar todas las filas de la tabla
#     filas = tabla.find_all('tr')
#     datos = []

#     # Iterar sobre cada fila para extraer los datos de las celdas
#     for fila in filas:
#         celdas = fila.find_all('td')
        
#         # Verificar que la fila tiene al menos 4 celdas y no contiene datos no deseados
#         if len(celdas) >= 4:
#         # Extraer el texto de cada celda y guardarla en un diccionario
#             nave_nombre = celdas[0].text.strip()
#             hora_inicio = celdas[1].text.strip()
#             hora_fin = celdas[2].text.strip()
#             metros = celdas[3].text.strip()
#             nombre_buque = celdas[4].text.strip() if len(celdas) > 4 else ''

#             # Filtrar filas que contienen "Longitud", "Calado", "Sitio", etc.
#             if 'Sitio' in nave_nombre or 'Longitud' in nave_nombre or 'Calado' in nave_nombre:
#                 continue  # Ignorar esta fila si contiene datos no deseados

#             # Guardar la información en un diccionario
#             datos.append({
#                 'Nombre Nave': nave_nombre,
#                 'Hora Inicio': hora_inicio,
#                 'Hora Fin': hora_fin,
#                 'Metros': metros,
#                 'Nombre Buque': nombre_buque
#             })

#     # Verificar los datos extraídos
#     print(json.dumps(datos, indent=4))
#     return datos
