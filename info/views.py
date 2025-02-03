import requests
from bs4 import BeautifulSoup
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
import urllib3

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
    for fila_idx in range(7):  
        for columna_idx in range(1, 9): 
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
        return HttpResponse("Elemento no encontrado", status=404)
    
    context = {
        'puerto': puerto,
        'elemento': elemento,
    }
    return render(request, 'info/detalle.html', context)

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