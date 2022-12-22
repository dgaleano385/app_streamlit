import streamlit as st 
import pandas as pd
import numpy as np
import ibmcpd
from datetime import datetime,date
from st_aggrid import AgGrid
from joblib import  load
import os.path as path
import time
from sklearn.cluster import KMeans
import warnings
from io import BytesIO
import xlsxwriter


warnings.filterwarnings("ignore")

path_libs = "libs/"
    
def min_to_horas (minutos):
    horas = int(divmod(minutos,60)[0])
    minutos = int(divmod(minutos,60)[1])
    horas_s = f"{horas}"
    minutos_s = f"{minutos}"
    if(horas < 10):
        horas_s = f"0{horas}"
    if (minutos < 10):
        minutos_s = f"0{minutos}"
    tiempo = f"{horas_s}:{minutos_s}"
    return tiempo

st.set_page_config(
    page_title="Demo IBM Transit Times",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"

)



ACCESS_TOKEN_MODEL = ibmcpd.authentication()

establecimientos = pd.read_excel("data/establecimientos.xlsx",sheet_name="Sheet1")
inputs = pd.DataFrame(columns = ["subZone","establecimiento","latitud","longitud","start_dt","truck_num","truck Type","start_dt_hour","Estimacion"])


if 'df' not in st.session_state:
    st.session_state.df = inputs
if "bot_agregar" not in st.session_state:
    st.session_state.bot_agregar = False

st.write(""" 
         # Demo IBM **Estimador Tiempos De Viaje!**
         """
)

col_title_table,col_title_form = st.columns((4,2))
col_title_table.subheader("Tabla de datos a enviar")
col_title_form.subheader("Valores del Modelo")


# Genero Layout de tres columnas con distintas medidas cada una

col_table,col_form_1 = st.columns ((4,2))

col_button_space,col_button_agregar,col_button_submit = st.columns((4,1,1))

#Formulario entrada de datos en la columna dos
nuevo_establecimiento = col_form_1.select_slider("Establecimiento:", ["Historico", "Nuevo"])


    

if nuevo_establecimiento == "Nuevo":
   
    nuevo_establecimiento_nombre = col_form_1.text_input (label="Nombre establecimiento",
                                                        help="Ingrese nombre del nuevo establecimiento")
 

    nuevo_subzone = col_form_1.selectbox("Seleccione zona", 
                                      pd.unique(establecimientos.zone.unique()))
    nuevo_establecimiento_lat = col_form_1.text_input (label="Latitud",
                                                        help="Latitud geografica del campo, recuerde que este campo es critico")
    nuevo_establecimiento_lon = col_form_1.text_input (label="Longitud",
                                                    help="Longitud geografica del campo, recuerde que este campo es critico")

else:
    select_establecimiento = col_form_1.selectbox ("Nombre establecimiento", establecimientos.establecimiento.unique())
    
start_dt = col_form_1.date_input("Dia de salida")
start_time = col_form_1.time_input("Horario de Salida")
truck_number = col_form_1.number_input ("Truck Number",value=1,step=1,format="%d")
truck_type = col_form_1.selectbox("Tipo de Camion", ["CH","WF"])    


boton_agregar = col_button_agregar.button ("Agregar" ,disabled = st.session_state.bot_agregar)
button_submit =  col_button_submit.button("Estimar Transit Times",type="primary" ,disabled=False if boton_agregar == True else True, args=(True,))

if boton_agregar:
    
    if nuevo_establecimiento == "Historico":
        aux = establecimientos.loc[establecimientos["establecimiento"]==select_establecimiento].copy().reset_index()
        zone = aux.loc[0,"zone"]
        establecimiento = select_establecimiento
        lat = aux.loc[0,"latitud"]
        lon = aux.loc[0,"longitud"]
    else:
        zone = nuevo_subzone
        establecimiento = nuevo_establecimiento_nombre
        lat = nuevo_establecimiento_lat
        lon = nuevo_establecimiento_lon    
    col_form_1.write(":smile:")
    dict_inputs = {
        "subZone": zone,
        "establecimiento": establecimiento,
        "latitud":lat,
        "longitud":lon,
        "start_dt": start_dt,
        "start_dt_hour": start_time.hour,
        "truck_num":truck_number,
        "truck Type": truck_type,
        "Estimacion":""
    }
    series_inputs = pd.Series(dict_inputs)

    st.session_state.df = pd.concat([st.session_state.df, series_inputs.to_frame().T],ignore_index=True)



output = pd.DataFrame()

if button_submit:
   
    input = st.session_state.df.copy()
    input = ibmcpd.buscar_coordenadas(input)
    
    df_cluster = input[[
                 'latitud',
                 'longitud',
                 'distancia_value_mts',
                 'duracion_min']].copy()

    kmeans = load(path.join(path_libs,"cluster_establecimientos.joblibs"))
    group = kmeans.predict(df_cluster)
    input ["group"] = group
    input.start_dt = pd.to_datetime(input["start_dt"])
    input["start_dt_day"] = input.start_dt.apply(lambda x: x.day)
    input["start_dt_month"] = input.start_dt.dt.month
    input["año"] = input.start_dt.dt.year
    input["start_dt_week"] = input.start_dt.dt.week
    input["start_dt_day_of_year"] = input.start_dt.dt.dayofyear
    
    
    calendar = input[["start_dt","latitud","longitud"]].copy()
    calendar.start_dt = calendar.start_dt.dt.date
    calendar = calendar.drop_duplicates()
    
    df_clima = pd.DataFrame()
    
    for i in calendar.index:
        df_clima = pd.concat([df_clima, ibmcpd.getWeather(calendar["latitud"][i],calendar["longitud"][i],calendar["start_dt"][i])])
        if (divmod(i,50)[1] == 0) & (i!=0):
            time.sleep(180)

    df_clima.columns=[ 'date', 'datetimeEpoch', 'tempmax', 'tempmin', 'temp',
       'sensacion_max', 'sensacion_min', 'sensacion', 'rocio', 'humedad',
       'precip', 'prob_precip', 'precipcover', 'preciptype', 'nieve',
       'nieve_prof', 'viento_insta', 'viento_vel', 'viento_dir', 'presion',
       'nublado_porcentaje', 'visibilidad', 'solarradiation', 'solarenergy', 'uvindex','severerisk',
       'salida_sol', 'sunriseEpoch', 'ocaso', 'sunsetEpoch', 'fase_luna',
       'condicion', 'descripcion', 'icon', 'stations', 'source', 'latitud',
       'longitud']
    df_clima = df_clima[[ 'date', 'tempmax', 'tempmin', 'temp',
       'sensacion_max', 'sensacion_min', 'sensacion', 'rocio', 'humedad',
       'precip', 'prob_precip', 'precipcover', 'preciptype', 
       'viento_insta', 'viento_vel', 'viento_dir', 'presion',
       'nublado_porcentaje', 'visibilidad', 'salida_sol', 'ocaso',
       'condicion', 'descripcion','latitud', 'longitud']]
    
    df_clima.loc[df_clima.preciptype.isna()==False,"preciptype"] = "rain"
    df_clima = df_clima.fillna({
                  "preciptype":"nada",
                  "viento_insta":0,
                  "presion":df_clima.presion.mean(),
                  "visibilidad":df_clima.visibilidad.mean()
    
                })
    df_clima = df_clima.fillna(0)
    df_clima = df_clima [[
        'date',
        'tempmax',
        'tempmin',
        'temp',
        'sensacion_max',
        'sensacion_min',
        'sensacion',
        'rocio',
        'humedad',
        'precip',
        'prob_precip',
        'precipcover',
        'preciptype',
        'viento_insta',
        'viento_vel',
        'viento_dir',
        'nublado_porcentaje',
        'visibilidad',
        'condicion',
        'latitud',
        'longitud']]
    df_clima.date = pd.to_datetime(df_clima.date)
    df_clima ["start_dt_day"] = df_clima.date.dt.day
    df_clima ["start_dt_month"] = df_clima.date.dt.month
    df_clima ["año"] = df_clima.date.dt.year
    
    input = input.merge(df_clima,"left",on=["latitud","longitud","año","start_dt_day","start_dt_month"])

    mask = [                     'distancia',
                             'nublado_porcentaje',
                             'visibilidad',
                             'truck_num',
                             'start_dt_day_of_year',
                             'group',
                             'state',
                             'humedad',
                             'condicion',
                             'truck Type',
                             'precip',
                             'tempmin',
                             'precipcover',
                             'viento_insta',
                             'start_dt_hour',
                             'start_dt_week',
                             'viento_dir',
                            ]
    
    input = input [mask]
    
    input.rename(columns={"start_dt_hour":"start_dt_hour_x"}, inplace=True)
    
    X = input.copy()
    
    columns = ["state",
              "truck_num",
              "truck Type",
              "condicion"]

    for col in columns:
        encoder = load(path.join(path_libs,f"encoder_{col}.joblibs"))
        encoder = dict (zip (encoder.classes_, encoder.transform(encoder.classes_)))
        X[col] = X[col].apply(lambda x: encoder.get(x,-1))
        
    scaler = load(path.join(path_libs,"scaler.joblibs"))
    
    X = scaler.transform (X)
    
    X = X.tolist()
    
    predict = ibmcpd.payload(ACCESS_TOKEN_MODEL, X)["predictions"][0]["values"]
    for i in range(len(predict)):    
        st.session_state.df.loc[[i],"Estimacion"] = predict [i]
    
    output = st.session_state.df.copy()

    
    output["Estimacion"] = output["Estimacion"].apply(lambda x: min_to_horas(x))
#Creamos un sidebar para scrollear entre las paginas
st.sidebar.markdown("""*Estimador de tiempos de viaje, 
                    de Productor a Planta* """)


col_table.write(st.session_state.df)

@st.cache
def to_excel(df):
    out = BytesIO()
    writer = pd.ExcelWriter(out, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Resultado')
    workbook = writer.book
    worksheet = writer.sheets['Resultado']  
    writer.save()
    processed_data = out.getvalue()
    return processed_data
csv = to_excel(output)

col_table.download_button(
    label="📥Descargar",
    data=csv,
    file_name='Estimacion.xlsx',
    mime='text/csv',
    disabled = False if button_submit == True else True
)

 
#values = [[0.43648112, 0 , 0.65267176, 0.12927757, 1.8030303 , 0.25, 0 , 0.28187919, 0 , 0, 0, 0.00330033, 0, 0.72987872, 0.34782609, 1.88888889, 0.97999403],
#          [0.43648112, 0 , 0.65267176, 0.12927757, 1.8030303 , 0.25, 0 , 0.28187919, 0 , 0, 0, 0.00330033, 0, 0.72987872, 0.34782609, 1.88888889, 0.97999403]]
#predict = ibmcpd.payload(ACCESS_TOKEN_MODEL,values)["predictions"][0]["values"]
#st.write(predict[0][0])
