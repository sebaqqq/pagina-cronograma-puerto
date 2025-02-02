# info/views.py
import requests
from bs4 import BeautifulSoup
from django.shortcuts import render
from django.http import HttpResponse
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
    # Se obtiene el puerto seleccionado vía parámetros GET; por defecto Valparaíso
    puerto = request.GET.get('puerto', 'Valparaíso')
    datos, clave = cargar_datos(puerto)
    
    context = {
        'puerto': puerto,
        'datos': datos,
        'clave': clave,
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
