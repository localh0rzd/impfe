#!/usr/bin/env python3
import sys
import traceback
import urllib.request
import urllib.parse
import json
import argparse
import datetime
import json
import re
import os
import asyncio
from timeit import default_timer
from concurrent.futures import ThreadPoolExecutor
from settings import settings
from time import sleep
from itertools import groupby
parser = argparse.ArgumentParser()
parser.add_argument("-b", "--broadcast", action="store_true")
parser.add_argument("-l", "--list", action="store_true")
args = parser.parse_args()

#sys.stdin.reconfigure(encoding='utf-8')

BROADCAST = args.broadcast
LIST = args.list
MIN_DATE = datetime.datetime.strptime("2021-06-07", '%Y-%m-%d')

def splitter(msg):
   if len(msg) > 4096:
      msgs = []
      while len(msg) > 4096:                  
         newline_starts = [m.start() for m in re.finditer('\n', msg)]
         closest = min(newline_starts, key=lambda x:abs(x-4096))
         msgs.append(msg[:closest])
         msg = msg[closest+1:]
      msgs.append(msg)
      return msgs   
   return [msg]



def stringify_list():
   practices = sorted(filter((lambda x: True if len(x['name']) > 1 else False), IMPFEN), key=lambda x: x['name'])
   for key, group in groupby(practices, lambda x: x['name']):
    print(f"{key}, {next(group)['booking_url']}")
    print("")
   msg = "<b>Liste aktuell abgerufener Praxen:</b>\n"
   for key, group in groupby(practices, lambda x: x['name']):
      e = next(group)
      msg += f"<a href='{e['booking_url']}'>{e['name']}</a>\n"
   for part in splitter(msg):
      print(part)
      send_msg(part, settings['PRIVATE_CHAT'] if not args.broadcast else settings['BROADCAST_CHAT'])

def format_exc(e):
   return "".join("".join(traceback.TracebackException.from_exception(e).format()).splitlines()[-2:])

def fetch_helios(v):
   try:
      req = urllib.request.Request(v['availabilities_url'], headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
         "Content-Type": "application/json; charset=utf-8",
         'Referer': 'https://patienten.helios-gesundheit.de/'})
      jsondata = json.dumps(v["availiabilities_payload"])
      jsondataasbytes = jsondata.encode('utf-8')   # needs to be bytes
      req.add_header('Content-Length', len(jsondataasbytes))
      with urllib.request.urlopen(req, jsondata.encode('utf-8'), timeout=30) as req:
         print(f"Fetched {v['name']}")
         res = json.loads(req.read().decode("utf-8"))
         if len(res) > 0:
            dates = list(set(map(lambda x: x["begin"][:10], res)))
            if len(dates) > 1:
               date_str = f"{min(dates)} - {max(dates)}"
            else:
               date_str = dates[0]
            return {"next_date": f"{date_str}, {len(res)} slot{'s' if len(res) > 1 else ''}", "booking_url": v["booking_url"], "vaccine": v["vaccine"], "name": v["name"]}
         else:
            return {"next_date": None, "booking_url": v["booking_url"], "vaccine": v["vaccine"], "name": v["name"]}
   except Exception as e:
      print(f"Error in fetcher_helis: {e}")
      return {"next_date": None, "booking_url": v["booking_url"], "vaccine": v["vaccine"], "name": v["name"], "error": format_exc(e)}

def fetch_jameda(v):
   try:
      req = urllib.request.Request(v['availabilities_url'], headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
         "Content-Type": "application/json; charset=utf-8"})
      with urllib.request.urlopen(req) as req:
         print(f"Fetched {v['name']}")
         res = json.loads(req.read().decode("utf-8"))
         if "code" in res and res["code"] == 2000:
            return {"next_date": None, "booking_url": v["booking_url"], "vaccine": v["vaccine"], "name": v["name"]}
         else:
            if isinstance(res, list) is True:
               return {"next_date": res[0]["slot"][:10], "booking_url": v["booking_url"], "vaccine": v["vaccine"], "name": v["name"]}
            else:
               return {"next_date": "(date unknown)", "booking_url": v["booking_url"], "vaccine": v["vaccine"], "name": v["name"]}
   except Exception as e:
      print(f"Error in fetch_jameda: {e}")
      return {"next_date": None, "booking_url": v["booking_url"], "vaccine": v["vaccine"], "name": v["name"], "error": format_exc(e)}


def fetch_doctolib(v):
   try:
      #if "IZ " in v["name"]:
      #   start_date = "2021-06-07"
      #else:
      start_date = str(datetime.date.today())
      req = urllib.request.Request(f"https://www.doctolib.de/availabilities.json?start_date={str(datetime.date.today())}&{v['availabilities_url']}", headers={"User-Agent": "lol"})
      with urllib.request.urlopen(req) as req:
            res = json.loads(req.read().decode("utf-8"))
            #print(f'{v["name"]}: {res}')
            print(f'Fetched {v["name"]}')
            #first_slot = [item for sublist in list(filter(None, map(lambda x: x["slots"], res["availabilities"]))) for item in sublist]
            #if len(first_slot) > 0 and not isinstance(first_slot[0], str):
            #   first_slot = first_slot[0]
            next_date = next((appdate["date"] for appdate in list(filter(lambda y: len(y["slots"]) > 0, res["availabilities"]))), None)
            #next_date = None
            if "next_slot" in res:
               next_date = res["next_slot"]
            #try:         
            #   if len(first_slot) > 0:
            #      if isinstance(next_date, str):
            #         next_date = first_slot[0][:10]
            #      else:
            #         next_date = first_slot[0]["start_date"][:10]

            #except Exception as e:
            #   if not os.path.exists("error.log"):
            #      os.mknod("error.log")
            #   with open("error.log", "a") as log:
            #      log.write(f"Error while parsing first_slot {json.dumps(res['availabilities'])}:\n{''.join(''.join(traceback.TracebackException.from_exception(e).format()))}\n")
            if next_date is not None and datetime.datetime.strptime(next_date, '%Y-%m-%d') < MIN_DATE and "IZ " in v["name"]:
               next_date = None 
            return {"next_date": next_date, "booking_url": v["booking_url"], "vaccine": v["vaccine"], "name": v["name"], "total": res["total"]}
   except Exception as e:
      if not os.path.exists("error.log"):
         os.mknod("error.log")
      with open("error.log", "a") as log:
         try:
            log.write(f"Error in fetcher:\n{json.dumps(res)}\n{''.join(''.join(traceback.TracebackException.from_exception(e).format()))}\n")
         except Exception as ex:
            log.write(f"Error in logging fetcher error:\n{''.join(''.join(traceback.TracebackException.from_exception(ex).format()))}\n")


      print(f"Error in fetcher: {e}")
      return {"next_date": None, "booking_url": v["booking_url"], "vaccine": v["vaccine"], "name": v["name"], "error": format_exc(e)}



IMPFEN = [
   {
      "availabilities_url": "visit_motive_ids=2537716&agenda_ids=465615-465575-466153-466143-466151-465558-465582-465619-465592-465651-466157-465701-465526-465630-465527-465532-465543-465550-465553-465580-465594-465598-465601-465653-465678-466127-466133-466139-466141-466144-466146-465609-466128-466129-466130-466131-466132-466134-466135-466136-466137-466138-466140-466145-466147-466148-466149-466150-466152-466154-466155-466156-466158-466159-466160-466161-465555-465584-465534&insurance_sector=public&practice_ids=191612&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-191612",
      "vaccine": "Moderna",
      "name": "IZ TXL"
   },
   {
      "availabilities_url": "visit_motive_ids=2495719&agenda_ids=457323-457329-457334-457346-457253-457255-457256-457399-457388-457263-457266-457277-457286-457320-457343-457268-457500-457382-457385-457324-457460-457251-397843-457264-457271-457279-457290-457292-457318-457327-457341-457293-457250-457265-457313-457413-457379-457374-457294-457317-457335-457514-457350-457326-457330-457254-457267-457303-457275-457276-457281-457289-457300-457301-457302-457307-457309-457314-457331-457355-457515-457338-457287-457308-397841-457512-457513-457285-457392-457395-457252-457358-457305-457377-457396-457333-457349-457316-457352-457295-457390-457363-457282-457297-397842-457336-457337-404656-457510&insurance_sector=public&practice_ids=158436&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158436",
      "vaccine": "Biontech",
      "name": "IZ TXL"
   },
   {
      "availabilities_url": "visit_motive_ids=2537716&agenda_ids=493635-493640-493645-493646-493648-493630-493631-493632-493636-493638-493639-493642-493643-493647-493649-493650-493652-493653-493634-493644&insurance_sector=public&practice_ids=191611&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-191611",
      "vaccine": "Moderna",
      "name": "IZ THF"
   },
   {
      "availabilities_url": "visit_motive_ids=2495719&agenda_ids=404654-457215-457244-397972-457210-457239-457213-457278-457283-457304-457306-457229-457234-457299-457212-457216-457288-457291-457315-457227-457204-457237-457296-397974-457312-457280-457206-457310-457319-397973-457243-457208-457218-457245-457274-457321&insurance_sector=public&practice_ids=158435&destroy_temporary=true&limit=4",      
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158435",
      "vaccine": "Biontech",
      "name": "IZ Velodrom"
   },
   {
      "availabilities_url": "visit_motive_ids=2537716&agenda_ids=397976-397975-457975-457951-457902-457907-457917-457924-457933-457947-457946-457971-457961-457964-457945-457955-457940-457953-457968-457920-457960-457963-457906-404655-457973-457977-457931-457956-457952-457903-457912-457916-457928-457976-457943-457954-457901-457915-457913-457918-457922-457938-457939-457927-457935-457936-457979-457966-457970-457930-457967-457944-457910-397977-457959-457926-457941-457923-457937&insurance_sector=public&practice_ids=158437&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158437",
      "vaccine": "Moderna",
      "name": "IZ Eisstadion"
   },
   {
      "availabilities_url": "visit_motive_ids=2495719&agenda_ids=457591-457443-457477-457487-457405-457414-457511-457594-457432-397846-457408-457421-457435-457489-457563-457567-457569-457439-457493-457453-457406-457416-457418-457426-457400-457404-457409-457419-457420-457427-457448-457483-457425-457428-457415-457504-457597-457566-457412-457457-457436-457463-397845-397844-457411-457497-457424-457429-457430-457442-457470-404659-457596-457407-457410-457593&insurance_sector=public&practice_ids=158434&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158434",
      "vaccine": "Biontech",
      "name": "IZ Messe"
   },
   {
      "availabilities_url": "visit_motive_ids=2597576&agenda_ids=493308-493317-493328-493350-494972-493320-493322-493324-493331-493314-493329-493334-493335-493339-493338-493340-493300-493306-493326-493333-493353-493343-493345-493347-493348-493352-493298-494957-494952-494968-494981-494954-494974-494962-494977-494978-494964-494950-494966-494979&insurance_sector=public&practice_ids=195952&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-195952",
      "vaccine": "Astra",
      "name": "IZ Messe"
   },
   {
      "availabilities_url": "visit_motive_ids=2495719&agenda_ids=397800-397776-402408-397766&insurance_sector=public&practice_ids=158431&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158431",
      "vaccine": "Biontech",
      "name": "IZ Arena"
   },
   {
      "availabilities_url": "visit_motive_ids=2781225&agenda_ids=449606&insurance_sector=public&practice_ids=177519&destroy_temporary=true&limit=4",
      "booking_url": "https://doctolib.de/praxis/berlin/hausarztpraxis-dr-buck",
      "vaccine": "Astra",
      "name": "Dr. Buck"
   },
   {
      "availabilities_url": "visit_motive_ids=2854065&agenda_ids=473564-473533&insurance_sector=public&practice_ids=110842&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/praxis-dr-vallee",
      "vaccine": "Astra",
      "name": "Dr. Vallée"
   },
   {
      "availabilities_url": "visit_motive_ids=2885284&agenda_ids=473564-473533&insurance_sector=public&practice_ids=110842&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/praxis-dr-vallee",
      "vaccine": "J&J",
      "name": "Dr. Vallée"
   },
   {
      "availabilities_url": "visit_motive_ids=2854139&agenda_ids=469346&insurance_sector=public&practice_ids=76464&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/kardios-kardiologen-in-berlin-berlin",
      "vaccine": "Astra",
      "name": "Kardios"  
   },
   {
      "availabilities_url": "visit_motive_ids=2731200&agenda_ids=444712&insurance_sector=public&practice_ids=146434&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/hno-praxis-am-friedrichshain",
      "vaccine": "Astra",
      "name": "HNO FHain"   
   },
   {
      "availabilities_url": "visit_motive_ids=2774169&agenda_ids=457175&insurance_sector=public&practice_ids=181755&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/gemeinschaftspraxis/berlin/bonedoctor-christian-rose-baharak-djohar",
      "vaccine": "Astra",
      "name": "Bonedoctor"   
   },
   {
      "availabilities_url": "visit_motive_ids=2797297&agenda_ids=462529&insurance_sector=public&practice_ids=181755&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/gemeinschaftspraxis/berlin/bonedoctor-christian-rose-baharak-djohar",
      "vaccine": "Biontech",
      "name": "Bonedoctor"   
   },
   {
      "availabilities_url": "visit_motive_ids=2780870&agenda_ids=284794-284796-465045-340728&insurance_sector=public&practice_ids=112562&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/medizinisches-versorgungszentrum-mvz/berlin/mvz-dr-kaleth-kollegen",
      "vaccine": "Astra",   
      "name": "MVZ Dr. Kaleth & Kollegen"
   },
   {
      "availabilities_url": "visit_motive_ids=2880391&agenda_ids=480095&insurance_sector=public&practice_ids=107774&limit=4",
      "booking_url": "https://www.doctolib.de/medizinisches-versorgungszentrum-mvz/berlin/ambulantes-gynaekologisches-operationszentrum",
      "vaccine": "J&J",
      "name": "MVZ Ambulantes Gynäkologisches Operationszentrum"   
   },
#   {
#      "availabilities_url": "visit_motive_ids=2727573&agenda_ids=445656&insurance_sector=public&practice_ids=107708&destroy_temporary=true&limit=4",
#      "booking_url": "https://www.doctolib.de/praxis/berlin/diabetes-berlin",
#      "vaccine": "Astra",
#      "name": "Diabeteszentrum Kreuzberg"
#   },
   {
      "availabilities_url": "visit_motive_ids=2827714&agenda_ids=460952&insurance_sector=public&practice_ids=101708&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/praxis-dipl-med-rainer-schwitzkowski-fuer-kinder-und-jugendmedizin",
      "vaccine": "Astra",
      "name": "Praxis für Kinder- und Jugendmedizin - Dr. med. Schönbeck & Dipl. med. Rainer Schwitzkowski"
   },
   {
      "availabilities_url": "visit_motive_ids=2811098&agenda_ids=464630&insurance_sector=public&practice_ids=114350&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/einzelpraxis/berlin/dr-med-frank-werner-kirstein",
      "vaccine": "Astra",
      "name": "Praxis für Kinder- und Jugendmedizin - Dr. med. Schönbeck & Dipl. med. Rainer Schwitzkowski"
   },
   {
      "availabilities_url": "visit_motive_ids=2836657&agenda_ids=469719&practice_ids=162056&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/krankenhaus/berlin/gkh-havelhoehe-impfzentrum",
      "vaccine": "Astra",
      "name": "GKH Havelhöhe - Impfzentrum"
   },
   {
      "availabilities_url": "visit_motive_ids=2806955&agenda_ids=469719&insurance_sector=public&practice_ids=162056&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/krankenhaus/berlin/gkh-havelhoehe-impfzentrum",
      "vaccine": "Biontech",
      "name": "GKH Havelhöhe - Impfzentrum"
   },
   {
      "availabilities_url": "visit_motive_ids=2898162&agenda_ids=469719&insurance_sector=public&practice_ids=162056&limit=4",
      "booking_url": "https://www.doctolib.de/krankenhaus/berlin/gkh-havelhoehe-impfzentrum",
      "vaccine": "J&J",
      "name": "GKH Havelhöhe - Impfzentrum"
   },
   {
      "availabilities_url": "visit_motive_ids=2871021&agenda_ids=477570&insurance_sector=public&practice_ids=153998&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/zahnarztpraxis/berlin/aubacke-zahnarztpraxis-daniel-und-pirk",
      "vaccine": "Astra",
      "name": "Aubacke - Zahnarztpraxis Daniel und Pirk"
   },
   {
      "availabilities_url": "visit_motive_ids=2828563&agenda_ids=466062&insurance_sector=public&practice_ids=23239&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/frauenarzt/berlin/susanne-eipper",
      "vaccine": "Astra",
      "name": "Susanne Eipper"  
   },
   {
      "availabilities_url": "visit_motive_ids=2810579&agenda_ids=466062&insurance_sector=public&practice_ids=23239&limit=4",
      "booking_url": "https://www.doctolib.de/frauenarzt/berlin/susanne-eipper",
      "vaccine": "Astra",
      "name": "Susanne Eipper"  
   },
   {
      "availabilities_url": "visit_motive_ids=2769431&agenda_ids=466062&insurance_sector=public&practice_ids=23239&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/frauenarzt/berlin/susanne-eipper",
      "vaccine": "Biontech",
      "name": "Susanne Eipper"  
   },
   {
      "availabilities_url": "https://api.patienten.helios-gesundheit.de/api/appointment/booking/querytimeline",
      "availiabilities_payload": {"begin":"2021-05-26T12:56:49.097+01:00","end":"2021-08-31T12:56:49.097+01:00","purposeQuery":{"minRequiredPeriodString":"PT5M","purposeUuid":"05fe557f-7f0b-4cd0-bf4f-cc79e980a528"},"resourceUuids":["abc2e453-0ffb-4b18-a44b-557bdc548061"],"userGroupUuid":"9cfb637a-7b06-4fdf-bece-cb164fccb8f9"},
      "booking_url": "https://patienten.helios-gesundheit.de/appointments/book-appointment?facility=10&physician=21646&purpose=33239",
      "vaccine": "Biontech",
      "name": "Helios Klinikum Berlin Buch",
      "fetcher": fetch_helios
   },
#   {
#      "availabilities_url": "https://booking-service.jameda.de/public/resources/80279091/slots?serviceId=93860",
#      "booking_url": "https://www.jameda.de/berlin/aerzte/innere-allgemeinmediziner/thomas-hilzinger/uebersicht/80279091_1/",
#      "vaccine": "Biontech",
#      "name": "Thomas Hilzinger",
#      "fetcher": fetch_jameda  
#   },
   {
      "availabilities_url": "https://booking-service.jameda.de/public/resources/80085713/slots?serviceId=91657",
      "booking_url": "https://www.jameda.de/berlin-friedenau/aerzte/frauenaerzte-gynaekologen/dr-cornelius-schwarz/uebersicht/80085713_1/",
      "vaccine": "Astra",
      "name": "Dr. med. Cornelius Schwarz",
      "fetcher": fetch_jameda  
   },
   {
      "availabilities_url": "visit_motive_ids=2764198&agenda_ids=190434&insurance_sector=public&practice_ids=114976&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/allgemeinmedizin/berlin/sophie-ruggeberg",
      "vaccine": "Astra",
      "name": "Dr. med. Sophie Rüggeberg"  
   },
   {
      "availabilities_url": "visit_motive_ids=2886231&agenda_ids=190434&insurance_sector=public&practice_ids=114976&limit=4",
      "booking_url": "https://www.doctolib.de/allgemeinmedizin/berlin/sophie-ruggeberg",
      "vaccine": "J&J",
      "name": "Dr. med. Sophie Rüggeberg"  
   },
   {
      "availabilities_url": "visit_motive_ids=2862419&agenda_ids=305777&insurance_sector=public&practice_ids=120549&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/facharzt-fur-hno/berlin/babak-mayelzadeh",
      "vaccine": "Astra",
      "name": "Dr. med. Babak Mayelzadeh"  
   },
   {
      "availabilities_url": "visit_motive_ids=2879179&agenda_ids=305777&insurance_sector=public&practice_ids=120549&limit=4",
      "booking_url": "https://www.doctolib.de/facharzt-fur-hno/berlin/babak-mayelzadeh",
      "vaccine": "J&J",
      "name": "Dr. med. Babak Mayelzadeh"  
   },
   {
      "availabilities_url": "visit_motive_ids=2733996&agenda_ids=56915&insurance_sector=public&practice_ids=22563&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/facharzt-fur-hno/berlin/rafael-hardy",
      "vaccine": "Biontech",
      "name": "Dr. Rafael Hardy"  
   },
   {
      "availabilities_url": "visit_motive_ids=2754056&agenda_ids=452595&insurance_sector=public&practice_ids=132888&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/allgemeinmedizin/berlin/benjamin-lott",
      "vaccine": "Biontech",
      "name": "Benjamin Lott"  
   },
   {
      "availabilities_url": "visit_motive_ids=2779622&agenda_ids=452595&insurance_sector=public&practice_ids=132888&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/allgemeinmedizin/berlin/benjamin-lott",
      "vaccine": "Astra",
      "name": "Benjamin Lott"  
   },
   {
      "availabilities_url": "visit_motive_ids=2784656&agenda_ids=268801&insurance_sector=public&practice_ids=178663&limit=4",
      "booking_url": "https://www.doctolib.de/innere-und-allgemeinmediziner/berlin/oliver-staeck",
      "vaccine": "Astra",
      "name": "Priv.-Doz. Dr. med. Oliver Staeck"  
   },
   {
      "availabilities_url": "visit_motive_ids=2885945&agenda_ids=268801&insurance_sector=public&practice_ids=178663&limit=4",
      "booking_url": "https://www.doctolib.de/innere-und-allgemeinmediziner/berlin/oliver-staeck",
      "vaccine": "J&J",
      "name": "Priv.-Doz. Dr. med. Oliver Staeck"  
   },
   {
      "availabilities_url": "visit_motive_ids=2811460&agenda_ids=464751&insurance_sector=public&practice_ids=28436&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/praxis-fuer-orthopaedie-und-unfallchirurgie-neukoelln",
      "vaccine": "Astra",
      "name": "Karnas & Walczak-Pohlig"  
   },
   {
      "availabilities_url": "visit_motive_ids=2771550&agenda_ids=456547&insurance_sector=public&practice_ids=83901&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/gemeinschaftspraxis/berlin/privatpraxis-fuer-integrative-medizin-dr-med-michael-oppel-und-lucia-maria-braun",
      "vaccine": "Astra",
      "name": "Privatpraxis für integrative Medizin"  
   },
   {
      "availabilities_url": "visit_motive_ids=2902792&agenda_ids=456547&insurance_sector=public&practice_ids=83901&limit=4",
      "booking_url": "https://www.doctolib.de/gemeinschaftspraxis/berlin/privatpraxis-fuer-integrative-medizin-dr-med-michael-oppel-und-lucia-maria-braun",
      "vaccine": "J&J",
      "name": "Privatpraxis für integrative Medizin"  
   },
#   {
#      "availabilities_url": "visit_motive_ids=2884332&agenda_ids=444401&insurance_sector=public&practice_ids=141729&limit=4",
#      "booking_url": "https://www.doctolib.de/praxis/berlin/dr-burkhard-schlich-dr-kai-schorn",
#      "vaccine": "J&J",
#      "name": "Dr. Burkhard Schlich & Dr. Kai Schorn"  
#   },
   {
      "availabilities_url": "",
      "booking_url": "",
      "vaccine": "",
      "name": ""  
   },
   {
      "availabilities_url": "",
      "booking_url": "",
      "vaccine": "",
      "name": ""  
   },
   # "Dr. Burkhard Schlich & Dr. Kai Schorn-Biontech": {
   #    "availabilities_url": "visit_motive_ids=2884324&agenda_ids=444401&insurance_sector=public&practice_ids=141729&destroy_temporary=true&limit=4",
   #    "booking_url": "https://www.doctolib.de/praxis/berlin/dr-burkhard-schlich-dr-kai-schorn"   
   # },
]

def delete_msg(chat, msg):
   data = {
      "chat_id": chat,
      "message_id": msg
   }

   req_data = urllib.parse.urlencode(data).encode()
   req = urllib.request.Request(f"https://api.telegram.org/bot{settings['BOT_TOKEN']}/deleteMessage", data=req_data)
   with urllib.request.urlopen(req) as f:
      res = json.loads(f.read().decode("utf-8"))
      return res

def send_msg(text, id):
   data = {
      "chat_id": id,
      "text": text,
      "disable_notification": True,
      "disable_web_page_preview": True,
      "parse_mode": "HTML"
   }

   req_data = urllib.parse.urlencode(data).encode()
   req = urllib.request.Request(f"https://api.telegram.org/bot{settings['BOT_TOKEN']}/sendMessage", data=req_data)
   try:
      with urllib.request.urlopen(req) as f:
         res = json.loads(f.read().decode("utf-8"))
         return res
   except urllib.error.HTTPError as e:
      print(e.read())
      print(text)
   except:
      print("An unknown error occured")
      print(text)

def send(text, premium=False):
   if BROADCAST:
      if premium == True:
         return send_msg(text, settings["PREMIUM_CHAT"])
      else:
         return send_msg(text, settings["BROADCAST_CHAT"])
   else:
      return send_msg(text, settings["PRIVATE_CHAT"])


async def extract_all():
   with ThreadPoolExecutor(max_workers=20) as executor:
      loop = asyncio.get_event_loop()
      START_TIME = default_timer()
      tasks = [
          loop.run_in_executor(
              executor,
              (i["fetcher"] if "fetcher" in i else fetch_doctolib),
              i
          )
          for i in [i for i in IMPFEN if i["name"] != ""]
      ]

      appointments = {
         "Biontech": [],
         "Moderna": [],
         "Astra": [],
         "J&J": []
      }
      responses = sorted(await asyncio.gather(*tasks), key=lambda v: v["name"])
      for response in responses:
         if response["next_date"] is not None:
            appointments[response["vaccine"]].append(f'{response["name"]}: <a href="{response["booking_url"]}">{response["next_date"]}</a>\n')
            #msg += f'{response["k"]}: {response["next_date"]}\n{response["booking_url"]}\n\n'

      #if len(msg) == 0: msg = "Nix frei 😔"
#      msg = f"""
#🦠 Impfeticker 🦠
#      """
      msg = ""
      premium_msg = ""
      for k,v in appointments.items():
         if len(appointments[k]) == 0: continue
         msg += f"""
<b>{k}</b>:
{"Nüscht 😕" if len(appointments[k]) == 0 else "".join(appointments[k])}
         """
      errorlist = list(filter(lambda x: "error" in x, responses))
      if len(errorlist) > 0:
         msg += f"""

<i>Kaputt</i>:
"""
         for error in errorlist:
            msg += f'<a href="{error["booking_url"]}">{error["name"]}</a>: {error["error"]} {type(error["error"]).__name__}\n'

      for k,v in { "Biontech": appointments["Biontech"], "Moderna": appointments["Moderna"] }.items():
         if len(appointments[k]) == 0: continue
         premium_msg += f"""
<b>{k}</b>:
{"Nüscht 😕" if len(appointments[k]) == 0 else "".join(appointments[k])}
         """
      if not os.path.exists("impfe.json"):
          os.mknod("impfe.json")
          with open("impfe.json", 'a') as f: f.write('{"message": "", "premium_message": ""}')
      with open("impfe.json", "r+") as file:
         store = json.load(file)
         if msg != store["message"]:
            if "last_message_metadata" in store:
               try:
                  delete_msg(store["last_message_metadata"]["result"]["chat"]["id"], store["last_message_metadata"]["result"]["message_id"])
                  del store["last_message_metadata"]
               except:
                  pass
            print(msg)
            #if len(msg) == 0: msg = "<i>Here be dragons</i>"
            if len(msg) > 0:
               msg_metadata = send(msg)
               store["last_message_metadata"] = msg_metadata
               store["message"] = msg
         if premium_msg != store["premium_message"]:
            if "last_premium_message_metadata" in store:
               try:            
                  delete_msg(store["last_premium_message_metadata"]["result"]["chat"]["id"], store["last_premium_message_metadata"]["result"]["message_id"])
                  del store["last_premium_message_metadata"]
               except:
                  pass
            print(premium_msg)
            #if len(premium_msg) == 0: premium_msg = "<i>Here be dragons</i>"
            if len(premium_msg) > 0:            
               premium_msg_metadata = send(premium_msg, True)
               store["last_premium_message_metadata"] = premium_msg_metadata
               store["premium_message"] = premium_msg
         file.seek(0)
         json.dump(store, file)
         file.truncate()


         # if file.read() != msg and len(msg) > 0:
         #    file.seek(0)
         #    file.write(msg)
         #    file.truncate()
         #    file.flush()
         #    send(msg)   

if not args.list:
   loop = asyncio.get_event_loop()
   future = asyncio.ensure_future(extract_all())
   loop.run_until_complete(future)
else:
   stringify_list()