# DownloadOrganizer.py
# Tuodaan tarvittavat kirjastot
import os  # Os-kirjasto tiedostojen ja kansioiden käsittelyyn
import shutil  # Shutil-kirjasto tiedostojen siirtämiseen ja kopioimiseen
import csv  # CSV-kirjasto tiedostojen lukemiseen ja kirjoittamiseen
from watchdog.observers import (
    Observer,
)  # Watchdog-kirjaston Observer-luokka tiedostojärjestelmän muutosten seuraamiseen
from watchdog.events import (
    FileSystemEventHandler,
)  # Watchdogin FileSystemEventHandler-tapahtumankäsittelijä
import time  # Time-kirjasto viivästysten hallintaan
from datetime import datetime  # Datetime-kirjasto aikaleimojen luomiseen
import os
import shutil
import csv
import re
import time
from datetime import datetime
from dotenv import load_dotenv

# Ladataan ympäristö muuttujat .env tiedostosta.
load_dotenv()
valvottu = os.getenv("VALVOTTU")
logit = os.getenv("LOGIT")

# Lataukset-kansion polku, tämä kansio on se joka on valvottu (Watchdogs).
lataukset_kansio = valvottu

# Kansiot ja tiedostopäätteet eri kategorioille.
kategoriat = {
    "01___Kuvat": [
        ".jpg",
        ".jpeg",
        ".jpg!d",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".svg",
        ".heic",
        ".raw",
    ],  # Kuvien tiedostopäätteet.
    "02___Videot": [
        ".mp4",
        ".mkv",
        ".mov",
        ".avi",
        ".flv",
        ".wmv",
        ".webm",
        ".m4v",
    ],  # Videoiden tiedostopäätteet.
    "03___Dokumentit": [
        ".pdf",
        ".doc",
        ".docx",
        ".odt",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".txt",
        ".rtf",
        ".md",
    ],  # Dokumenttien tiedostopäätteet.
    "04___Musiikki": [
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
        ".m4a",
        ".wma",
    ],  # Musiikkitiedostojen tiedostopäätteet.
    "05___Ohjelmat": [
        ".exe",
        ".msi",
        ".apk",
        ".dmg",
        ".pkg",
        ".iso",
        ".bat",
        ".sh",
    ],  # Ohjelmien tiedostopäätteet.
    "06___Paketit": [
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
    ],  # Pakattujen tiedostojen päätteet.
    "07___Koodit": [
        ".py",
        ".js",
        ".html",
        ".css",
        ".c",
        ".cpp",
        ".java",
        ".rb",
        ".php",
        ".swift",
        ".go",
        ".ts",
        ".ipynb",
    ],  # Kooditiedostojen päätteet.
    "08___Fontit": [".ttf", ".otf", ".woff", ".woff2"],  # Fonttitiedostojen päätteet.
    "09___Mallit": [
        ".stl",
        ".obj",
        ".fbx",
        ".dwg",
        ".dxf",
    ],  # Mallitiedostojen päätteet.
    "10___Data": [
        ".csv",
        ".json",
        ".xml",
        ".sql",
        ".db",
        ".sqlite",
        ".log",
    ],  # Data-tiedostojen päätteet.
    "11___Kirjat": [".epub", ".mobi", ".azw", ".azw3"],  # Kirjatiedostojen päätteet.
    "12___Sähköpostit": [
        ".eml",
        ".msg",
        ".pst",
        ".ost",
    ],  # Sähköpostitiedostojen päätteet.
    "13___Muut": [
        ".ics",
        ".bak",
        ".rdp",
    ],  # Muut tiedostot, joita ei ole määritelty kategorioissa.
}

# CSV-log-tiedoston polku, johon siirroista kirjataan merkinnät.
log_file = logit

# Lisää tämä funktio tiedoston koon tarkistamiseen
def onko_lataus_valmis(tiedosto_polku):
    """
    Tarkistaa, onko tiedoston lataus valmis vertaamalla tiedoston kokoa.
    Jos tiedoston koko ei muutu tietyssä ajassa, oletetaan, että lataus on valmis.
    """
    max_yrittaa = 20  # Yritetään 20 kertaa
    odotus_aika = 1  # Odotetaan 1 sekunti kokeiden välillä

    for _ in range(max_yrittaa):
        if not os.path.exists(tiedosto_polku):
            print(f"Varoitus: Tiedosto '{tiedosto_polku}' ei enää löydy.")
            return False  # Tiedosto ei löydy

        koko_ennen = os.path.getsize(tiedosto_polku)
        time.sleep(odotus_aika)  # Odotetaan ennen seuraavaa tarkistusta
        koko_jalkeen = os.path.getsize(tiedosto_polku)

        if koko_ennen == koko_jalkeen:
            return True  # Tiedoston koko ei ole muuttunut, lataus valmis
    print(f"Varoitus: Tiedoston '{tiedosto_polku}' lataus ei ollut valmis aikarajassa.")
    return False  # Lataus ei ollut valmis


# Funktio lisänimen luomiseksi, jos tiedosto on jo olemassa.
def luo_uusi_nimi(kohdepolku):
    """
    Tämä funktio luo uuden tiedostonimen, jos tiedosto on jo olemassa.
    Lisätään hakasulkeisiin numerointia tiedoston nimeen.
    """
    nimi, paatos = os.path.splitext(
        kohdepolku
    )  # Erotetaan tiedostonimi ja tiedostopääte.
    laskuri = 1  # Aloitetaan laskuri yhdestä.
    while os.path.exists(
        kohdepolku
    ):  # Jos tiedosto on jo olemassa, lisätään numerointi.
        kohdepolku = f"{nimi}[{laskuri}]{paatos}"
        laskuri += (
            1  # Kasvatetaan laskuria sitä mukaan kun samannimisiä tiedostoja ilmenee.
        )
    return kohdepolku


# Loggausfunktio, joka kirjoittaa siirrot CSV-tiedostoon.
def loggaa(tiedosto, kategoria, siirto_tyyppi):
    """
    Tämä funktio kirjoittaa tiedostosiirrosta tiedot log-tiedostoon.
    Kirjataan aikaleima, tiedostonimi, kategoria ja siirron tyyppi.
    """
    aika = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Haetaan nykyinen aika.
    with open(
        log_file, mode="a", newline=""
    ) as file:  # Avataan log-tiedosto kirjoittamista varten.
        writer = csv.writer(file)
        writer.writerow(
            [aika, tiedosto, kategoria, siirto_tyyppi]
        )  # Kirjoitetaan tiedot uuteen riviin.


def siirra_tiedosto(tiedosto_polku, tiedosto):
    tiedosto_paatos = os.path.splitext(tiedosto)[1].lower()  # Tiedostopääte pienellä
    siirretty = False  # Oletuksena tiedosto ei ole siirretty.
    lopullinen_nimi = tiedosto  # Oletetaan, että tiedoston nimi ei muutu.

    tiedosto_polku = os.path.join(
        os.path.dirname(tiedosto_polku), tiedosto
    )  # Päivitetään tiedoston polku

    # Jos tiedosto on väliaikainen (tmp), jätetään se huomiotta
    if tiedosto.lower().endswith(".tmp"):
        print(f"Väliaikainen tiedosto jätettiin huomiotta: {tiedosto}")
        loggaa(tiedosto, "13___Muut", "Ei siirretty .tmp-tiedostoa")
        return

    # Käydään läpi kaikki kategoriat ja tarkistetaan, mihin kategoriaan tiedosto kuuluu.
    for kategoria, paatteet in kategoriat.items():
        if tiedosto_paatos in paatteet:
            kohdekansio = os.path.join(lataukset_kansio, kategoria)
            if not os.path.exists(kohdekansio):
                os.makedirs(kohdekansio)  # Luodaan kohdekansio tarvittaessa.

            kohdepolku = os.path.join(kohdekansio, tiedosto)
            if not os.path.exists(kohdepolku):
                try:
                    shutil.move(tiedosto_polku, kohdepolku)  # Siirretään tiedosto
                    loggaa(tiedosto, kategoria, "Siirretty")
                    print(f"Tiedosto '{tiedosto}' siirretty kategoriaan '{kategoria}'.")
                    siirretty = True
                except Exception as e:
                    print(f"Virhe tiedoston siirrossa: {e}")

            else:
                print(f"Tiedosto '{tiedosto}' on jo olemassa, luodaan uusi nimi.")
                kohdepolku = luo_uusi_nimi(kohdepolku)  # Luodaan uusi nimi.
                lopullinen_nimi = os.path.basename(kohdepolku)
                try:
                    shutil.move(tiedosto_polku, kohdepolku)  # Siirretään tiedosto
                    loggaa(lopullinen_nimi, kategoria, "Siirretty")
                    print(
                        f"Tiedosto '{lopullinen_nimi}' siirretty kategoriaan '{kategoria}' uudella nimellä."
                    )
                    siirretty = True
                except Exception as e:
                    print(f"Virhe tiedoston siirrossa: {e}")
            break
    # Jos tiedosto ei ole siirretty ja se ei ollut väliaikainen, siirretään se "Muut"-kansioon
    if not siirretty:
        if not tiedosto.lower().endswith(".tmp"):
            kohdekansio = os.path.join(lataukset_kansio, "13___Muut")
            os.makedirs(kohdekansio, exist_ok=True)
            kohdepolku = os.path.join(kohdekansio, tiedosto)

            if os.path.exists(kohdepolku):
                kohdepolku = luo_uusi_nimi(kohdepolku)
                lopullinen_nimi = os.path.basename(kohdepolku)

            try:
                shutil.move(tiedosto_polku, kohdepolku)
                print(lopullinen_nimi, "13___Muut", "OK")
                loggaa(lopullinen_nimi, "13___Muut", "OK")
            except FileNotFoundError:
                print(f"Tiedostoa ei löydy: {tiedosto}")
                loggaa(tiedosto, "13___Muut", "Tiedosto ei löydy")


# Muokataan LatauksetHandler-luokan on_created-metodia
class LatauksetHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:  # Käsitellään vain tiedostoja
            tiedosto_polku = event.src_path  # Tiedoston polku
            tiedosto = os.path.basename(tiedosto_polku)  # Tiedoston nimi

            # Ohitetaan .tmp-tiedostot
            if tiedosto.endswith(".tmp"):
                print(f"Ohitetaan väliaikainen tiedosto: {tiedosto}")
                return

            # Odotetaan, että lataus on valmis ennen siirtoa
            if not onko_lataus_valmis(tiedosto_polku):
                print(f"Tiedoston '{tiedosto}' lataus ei ole valmis. Ei siirretä.")
                return  # Lataus ei ole valmis, ei siirretä

            # Siirretään tiedosto, kun lataus on valmis
            siirra_tiedosto(tiedosto_polku, tiedosto)

    def on_modified(self, event):
        """
        Tämä funktio reagoi tiedostojärjestelmämuutoksiin (tiedoston lisäykset).
        Se tarkistaa, onko tiedosto valmis siirrettäväksi ja suorittaa siirron.
        """
        if event.is_directory:
            return  # Ei käsitellä hakemistoja.

        tiedosto = event.src_path
        if not tiedosto.lower().endswith(
            tuple([p for sublist in kategoriat.values() for p in sublist])
        ):
            return  # Jos tiedosto ei ole tarkasteltavien tiedostopäätteiden joukossa, ohitetaan

        if onko_lataus_valmis(tiedosto):
            siirra_tiedosto(tiedosto, os.path.basename(tiedosto))


# Alustetaan log.csv-tiedosto, jos se ei ole olemassa.
if not os.path.exists(log_file):
    with open(
        log_file, mode="w", newline=""
    ) as file:  # Luodaan uusi log-tiedosto, jos sitä ei ole.
        writer = csv.writer(file)
        writer.writerow(
            ["Päivämäärä", "Tiedosto", "Kategoria", "Siirron tyyppi"]
        )  # Kirjoitetaan otsikkorivi.


# Watchdogin asetukset.
observer = Observer()  # Luodaan Watchdogin observer-olio.
event_handler = LatauksetHandler()  # Luodaan tapahtumankäsittelijä.
observer.schedule(
    event_handler, lataukset_kansio, recursive=False
)  # Asetetaan valvottava kansio.

# Käynnistetään Watchdog.
observer.start()
print(
    f"Lataukset-kansion valvonta käynnistetty [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]..."
)
# Kirjataan aloituslogi.
loggaa("Lataukset-kansion valvonta käynnistetty", "N/A", "Aloitus")

# Käydään läpi jo valmiiksi olemassa olevat tiedostot lataukset-kansiossa
for tiedosto in os.listdir(lataukset_kansio):
    tiedosto_polku = os.path.join(lataukset_kansio, tiedosto)
    if os.path.isfile(
        tiedosto_polku
    ):  # Varmistetaan, että kohde on tiedosto, ei kansio
        siirra_tiedosto(
            tiedosto_polku, tiedosto
        )  # Siirretään tiedosto oikeaan kansioon


try:
    while True:  # Pidetään ohjelma käynnissä.
        time.sleep(0.01)
except KeyboardInterrupt:  # Käyttäjä keskeytti ohjelman (Ctrl+C).
    observer.stop()  # Lopetetaan valvonta.
observer.join()  # Odotetaan valvonnan lopettamista.
