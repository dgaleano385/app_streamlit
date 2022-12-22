import requests
import os
from dotenv import load_dotenv
import logging
import googlemaps
import pandas as pd
import json
import urllib.parse
import urllib.request
import numpy as np



def authentication ():
    load_dotenv()
    API_KEY = os.getenv("API_KEY")

    #NOTE: you must manually set API_KEY below using information retrieved from your IBM Cloud account.
    token_response = requests.post('https://iam.cloud.ibm.com/identity/token', data={"apikey": API_KEY, 
                                                                                    "grant_type": 'urn:ibm:params:oauth:grant-type:apikey'}
                                  )
    return token_response.json()["access_token"]
    

def payload (ACCESS_TOKEN, rows):
    header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' +  ACCESS_TOKEN }

    # NOTE: manually define and pass the array(s) of values to be scored in the next line
    payload_scoring = { "input_data": [ {"fields":[ "distancia",
                                  "nublado_porcentaje",
                                  "visibilidad", 
                                  "truck_num",
                                  "start_dt_day_of_year",
                                  "group",
                                  "state",
                                  "humedad",
                                  "condicion", 
                                  "truck Type",
                                  "precip",
                                  "tempmin",
                                  "precipcover",
                                  "viento_insta",
                                  "start_dt_hour",
                                  "start_dt_week",
                                  "viento_dir"
                                ],
                        "values": rows
                                  }
                    ]

    }


    response_scoring = requests.post('https://us-south.ml.cloud.ibm.com/ml/v4/deployments/4d9cfec0-57b4-4d82-8d3a-076041963248/predictions?version=2022-12-07', 
                                    json=payload_scoring,
                                    headers=header)

    print("Scoring response")
    return response_scoring.json()

def buscar_coordenadas (df_coordenadas):
    load_dotenv()
    API_KEY = os.getenv("API_KEY_G")
    gmaps = googlemaps.Client(key=API_KEY)
    bayer_lat = -34.2031478
    bayer_lon = -60.6939654
    
    for i in range(df_coordenadas.shape[0]):
        lat = df_coordenadas.loc[i,"latitud"]
        lon = df_coordenadas.loc[i,"longitud"]
        
        try:
            result = gmaps.distance_matrix( origins = {"lat":bayer_lat, "lng":bayer_lon},
                                        destinations ={"lat":lat, "lng":lon},
                                        language = "es-ar",

                                    )
    
            destino = result["destination_addresses"][0]
            distancia = result["rows"][0]["elements"][0]["distance"]["text"]
            duracion = result["rows"][0]["elements"][0]["duration"]["text"]
            distancia_value = result["rows"][0]["elements"][0]["distance"]["value"]
            duracion_value = result["rows"][0]["elements"][0]["duration"]["value"]
        except:
            destino,distancia,distancia_value,duracion,duracion_value = 0,0,0,0,0

        df_coordenadas.loc[i,"destino"] = destino
        df_coordenadas.loc[i,"distancia"] = distancia
        df_coordenadas.loc[i,"distancia_value_mts"] = distancia_value
        df_coordenadas.loc[i,"duracion"] = duracion
        df_coordenadas.loc[i,"duracion_min"] = duracion_value
    df_coordenadas["ciudad"] = df_coordenadas.destino.str.split(",",expand=True)[0]
    df_coordenadas["state"] = df_coordenadas.destino.str.split(",",expand=True)[1]
    df_coordenadas.drop("destino",axis=1,inplace=True)
    df_coordenadas.distancia = df_coordenadas.distancia_value_mts/1000
    df_coordenadas.distancia = df_coordenadas.distancia.round().astype(int)
    df_coordenadas.duracion_min = df_coordenadas.duracion_min / 60
    #df_coordenadas.columns = ["zone", "establecimiento","latitud","longitud","distancia","distancia_value_mts","duracion","duracion_min","city","state"]
    
    return df_coordenadas


def getWeather(lat, lon,start_dt):
    load_dotenv()
    API_KEY = os.getenv("API_KEY_W")
    latitud = lat
    longitud = lon
    date1= start_dt
    date2= start_dt
    requestUrl = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{latitud}%2C%20{longitud}/{date1}/{date2}?unitGroup=metric&include=days&key={API_KEY}"
    try:
        req = urllib.request.urlopen(requestUrl)
        data = req.read()
        req.close()
        data = json.loads(data)
        days = data['days']
        df = pd.DataFrame(days)
        df ["latitud"] = lat
        df ["longitud"] = lon
        return df
    except Exception as ex:
        print ("Error",ex)