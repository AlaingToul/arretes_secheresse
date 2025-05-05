# -*- coding: utf-8 -*----------------------------------------------------------
# Name:        app.py
# Purpose:     Construction et présentation de la carte de suivi des
#              arrêtés sécheresse en vigueur pour les eaux superficielles
#
# Author:      Alain Gauthier
#
# Created:     30/04/2025
# Licence:     GPL V3
#-------------------------------------------------------------------------------

import io
import os
import datetime as dt
import requests
import geopandas as gpd
import folium
import streamlit as st

from streamlit_folium import st_folium

# dossier racine où se trouvent les données récupérées et à présenter
Racine = "./donnees"

#-------------------------------------------------------------------------------

def get_zones_secheresse():
    """Requête de récupération des zones d'arrêté sécheresse.
    Renvoie uniquement les zones de type 'SUP' pour les eaux superficielles

    Returns:
        geoDataFrame: zones filtrées sur le type 'SUP'
    """
    # URL stable de la couche
    url_zones_arretes = "https://www.data.gouv.fr/fr/datasets/r/bfba7898-aed3-40ec-aa74-abb73b92a363"

    # requête du fichier (ATTENTION, vérification certificat SSL désactivée)
    rep = requests.get(url_zones_arretes, verify=False)

    fio = io.BytesIO(rep.content)
    # dans geopandas
    zones_arretes = gpd.read_file(fio)

    # on ne garde que le type 'SUP'
    zones_arretes = zones_arretes[zones_arretes["type"] == "SUP"]
    # fin
    return zones_arretes

#-------------------------------------------------------------------------------

@st.cache_data
def lire_geopandas(fic_couche):
    """lecture de la couche depuis le fichier passé en paramètre.
    Activation du cache dans l'application Streamlit

    Args:
        fic_couche (str): nom de fichier local à lire

    Returns:
        GeoDataFrame: couche lue
    """
    gdf = gpd.read_file(fic_couche)
    return gdf

#-------------------------------------------------------------------------------

def construire_carte(itineraire, zones_arrete):
    """construction de la carte folium basée sur les deux couches passées en paramètre

    Args:
        itineraire (GeoDataFrame): couche des itinéraires COP
        zones_arrete (GeoDataFrame): couche des zones de sécheresse à afficher

    Returns:
        map: instance de carte folium
    """

    # copie locale
    czones_arrete = gpd.GeoDataFrame(zones_arrete)

    # codes couleur des zones d'arrêtés selon le niveau de gravité
    niveaux  = ["vigilance", "alerte",  "alerte renforcée", "crise"]
    couleurs = ["#ffeda0",   "#feb24c", "#fc4e2a",          "#b10026"]
    czones_arrete["couleur"] = czones_arrete["niveauGravite"].map(dict(zip(niveaux,couleurs)))

    # carte centrée sur ce point choisi manuellement
    centre = [46.463,2.661]
    # limites : celle des itinéraires
    bounds =itineraire.total_bounds

    carte = folium.Map(
        location=centre,
        tiles="OpenStreetMap",
    )

    carte.fit_bounds([[bounds[1],bounds[0]],
                      [bounds[3],bounds[2]]])

    # ajout des zones d'arrêté avec contrôle de la légende
    czones_arrete.explore(m=carte,
        column='niveauGravite',
        tooltip='niveauGravite',
        categorical=True,
        categories=niveaux,
        k=len(niveaux),
        cmap=couleurs,
        popup=True,
        legend=True,
        legend_kwds={"caption":"Niveau de gravité"},
        map_kwds={'name':"Zones d'arrêtés sécheresse"},
        )

    # ajout de la couche itinéraire
    folium.GeoJson(itineraire,
                  name="Itinéraire COP",
                  style_function=lambda x: {"color": "#0000ff", "weight": 2},
                  ).add_to(carte)

    # ajout du titre de la carte
    title_html = f'''
      <h3 align="center" style="font-size:20px"><b>Zones d'arrêtés sécheresse</b>
      en date du {dt.date.today().strftime("%d/%m/%Y")}</h3>
               '''
    carte.get_root().html.add_child(folium.Element(title_html))

    # fin
    return carte

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

def main():
    """Fonction principale
    """
    # titre de page
    st.set_page_config(page_title="Zones d'arrêtés sécheresse en vigueur")
    st.title("Zones d'arrêtés sécheresse en vigueur")

    # itinéraires COP
    fic_couche = os.path.join(Racine,"Export_Itineraire_COP.gpkg")
    itineraire = lire_geopandas(fic_couche)
    # conversion du CRS en wgs 84
    itineraire = itineraire.to_crs("EPSG:4326")

    zones_arretes = get_zones_secheresse()
    # conversion dans le même CRS que l'itinéraire
    zones_arretes = zones_arretes.to_crs(itineraire.crs)

    # création de la carte
    carte = construire_carte(itineraire, zones_arretes)

    # visualisation

    st_folium(carte,
        height=700,
        width=700,
    )

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
