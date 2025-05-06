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

import branca as bc

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

def _categorical_legend(m, title, categories, colors):
    """
    MODIFICATION POUR POSITIONNER LA LEGENDE
    FONCTION D'ORIGINE DANS geopandas/explore.py

    --> CHANGEMENT : postition par rapport au coin (left, top) au lieu de (right, bottom)

    Add categorical legend to a map

    The implementation is using the code originally written by Michel Metran
    (@michelmetran) and released on GitHub
    (https://github.com/michelmetran/package_folium) under MIT license.

    Copyright (c) 2020 Michel Metran

    Parameters
    ----------
    m : folium.Map
        Existing map instance on which to draw the plot
    title : str
        title of the legend (e.g. column name)
    categories : list-like
        list of categories
    colors : list-like
        list of colors (in the same order as categories)
    """

    # Header to Add
    head = """
    {% macro header(this, kwargs) %}
    <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
    <script>$( function() {
        $( ".maplegend" ).draggable({
            start: function (event, ui) {
                $(this).css({
                    right: "auto",
                    top: "auto",
                    bottom: "auto"
                });
            }
        });
    });
    </script>
    <style type='text/css'>
      .maplegend {
        position: absolute;
        z-index:9999;
        background-color: rgba(255, 255, 255, .8);
        border-radius: 5px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2);
        padding: 10px;
        font: 12px/14px Arial, Helvetica, sans-serif;
        left: 10px;
        top: 120px;
      }
      .maplegend .legend-title {
        text-align: left;
        margin-bottom: 5px;
        font-weight: bold;
        }
      .maplegend .legend-scale ul {
        margin: 0;
        margin-bottom: 0px;
        padding: 0;
        float: left;
        list-style: none;
        }
      .maplegend .legend-scale ul li {
        list-style: none;
        margin-left: 0;
        line-height: 16px;
        margin-bottom: 2px;
        }
      .maplegend ul.legend-labels li span {
        display: block;
        float: left;
        height: 14px;
        width: 14px;
        margin-right: 5px;
        margin-left: 0;
        border: 0px solid #ccc;
        }
      .maplegend .legend-source {
        color: #777;
        clear: both;
        }
      .maplegend a {
        color: #777;
        }
    </style>
    {% endmacro %}
    """

    # Add CSS (on Header)
    macro = bc.element.MacroElement()
    macro._template = bc.element.Template(head)
    m.get_root().add_child(macro)

    body = f"""
    <div id='maplegend {title}' class='maplegend'>
        <div class='legend-title'>{title}</div>
        <div class='legend-scale'>
            <ul class='legend-labels'>"""

    # Loop Categories
    for label, color in zip(categories, colors):
        body += f"""
                <li><span style='background:{color}'></span>{label}</li>"""

    body += """
            </ul>
        </div>
    </div>
    """

    # Add Body
    body = bc.element.Element(body, "legend")
    m.get_root().html.add_child(body)

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
        legend=False,
        name= "Zones d'arrêtés sécheresse",
        )

    # légende "à la main" issue de la fonction d'explore,
    # mais avec positionnement adapté à cette carte
    _categorical_legend(carte,
                        title='Niveau de gravité',
                        categories=niveaux,
                        colors=couleurs)

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

    # ajout du contrôle des couches
    folium.map.LayerControl().add_to(carte)

    # fin
    return carte

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

def main():
    """Fonction principale
    """
    # titre de page
    st.set_page_config(page_title="Zones d'arrêtés sécheresse en vigueur")
    st.title("Arrêtés sécheresse en vigueur")

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
