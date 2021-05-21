#!/usr/bin/env python3
import sys
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
parser = argparse.ArgumentParser()
parser.add_argument("-b", "--broadcast", action="store_true")
args = parser.parse_args()

sys.stdin.reconfigure(encoding='utf-8')

BROADCAST = args.broadcast
MIN_DATE = datetime.datetime.strptime("2021-06-07", '%Y-%m-%d')

IMPFEN = {
   "IZ TXL-Moderna": {
      "availabilities_url": "visit_motive_ids=2537716&agenda_ids=465527-465550-465592-465598-465601-465651-465543-465615-465553-465594-465630-465678-465575-465653-466144-466139-466141-466153-466157-465701-465532-465609-466127-466128-466129-466130-466131-466132-466133-466134-466135-466136-466137-466138-466140-466143-466145-466147-466148-466149-466150-466151-466152-466154-466155-466156-466158-466159-466160-466161-465555-465558-465580-465582-465584-465619-465534-466146-465526&insurance_sector=public&practice_ids=158436&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158436"
   },
   "IZ TXL-Biontech": {
      "availabilities_url": "visit_motive_ids=2495719&agenda_ids=457379-457323-457329-457374-457334-457346-457253-457255-457256-457294-457317-457335-457399-457514-457350-457326-457330-457254-457267-457303-457275-457276-457281-457289-457300-457301-457302-457307-457309-457314-457331-457355-457388-457515-457338-457263-457266-457277-457286-457287-457308-457320-457343-457268-457500-397841-457512-457382-457385-457324-457460-457513-457285-457392-457395-457251-397843-457252-457264-457271-457279-457290-457292-457318-457358-457327-457341-457293-457250-457305-457377-457396-457333-457349-457265-457313-457316-457352-457295-457390-457363-457282-457297-397842-457336-457337-457413-404656-457510&insurance_sector=public&practice_ids=158436&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158436"
   },
   "IZ THF-Moderna": {
      "availabilities_url": "visit_motive_ids=2537716&agenda_ids=467896-467894-467900-467908-467934-467937-467912-467901-467933-467893-467938-467939-467940-467903-467905-467906-467907-467910-467911-467935-467936-467897-467898-467899-467895&insurance_sector=public&practice_ids=158433&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158433"
   },
   "IZ THF-Astra": {
      "availabilities_url": "visit_motive_ids=2597576&agenda_ids=404658-397960-397955-397956&insurance_sector=public&practice_ids=158433&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158433"
   },
   "IZ Velodrom": {
      "availabilities_url": "visit_motive_ids=2495719&agenda_ids=404654-457215-457244-397972-457210-457239-457213-457278-457283-457304-457306-457229-457234-457299-457212-457216-457288-457291-457315-457227-457204-457237-457296-397974-457312-457280-457206-457310-457319-397973-457243-457208-457218-457245-457274-457321&insurance_sector=public&practice_ids=158435&destroy_temporary=true&limit=4",      
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158435"
   },
   "IZ Eisstadion": {
      "availabilities_url": "visit_motive_ids=2537716&agenda_ids=397976-397975-457975-457951-457902-457907-457917-457924-457933-457947-457946-457971-457961-457964-457945-457955-457940-457953-457968-457920-457960-457963-457906-404655-457973-457977-457931-457956-457952-457903-457912-457916-457928-457976-457943-457954-457901-457915-457913-457918-457922-457938-457939-457927-457935-457936-457979-457966-457970-457930-457967-457944-457910-397977-457959-457926-457941-457923-457937&insurance_sector=public&practice_ids=158437&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158437"
   },
   "IZ Messe": {
         "availabilities_url": "visit_motive_ids=2495719&agenda_ids=457591-457443-457477-457487-457405-457414-457511-457594-457432-397846-457408-457421-457435-457489-457563-457567-457569-457439-457493-457453-457406-457416-457418-457426-457400-457404-457409-457419-457420-457427-457448-457483-457425-457428-457415-457504-457597-457566-457412-457457-457436-457463-397845-397844-457411-457497-457424-457429-457430-457442-457470-404659-457596-457407-457410-457593&insurance_sector=public&practice_ids=158434&destroy_temporary=true&limit=4",
         "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158434"
   },
   "IZ Arena":  {
      "availabilities_url": "visit_motive_ids=2495719&agenda_ids=397800-397776-402408-397766&insurance_sector=public&practice_ids=158431&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/institut/berlin/ciz-berlin-berlin?pid=practice-158431"
   },
   "Dr. Buck-Astra": {
      "availabilities_url": "visit_motive_ids=2781225&agenda_ids=449606&insurance_sector=public&practice_ids=177519&destroy_temporary=true&limit=4",
      "booking_url": "https://doctolib.de/praxis/berlin/hausarztpraxis-dr-buck"
   },
   "Dr. Vallee-Astra": {
      "availabilities_url": "visit_motive_ids=2854065&agenda_ids=473564-473533&insurance_sector=public&practice_ids=110842&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/praxis-dr-vallee"
   },
   "Dr. Vallee-JJ": {
      "availabilities_url": "visit_motive_ids=2885284&agenda_ids=473564-473533&insurance_sector=public&practice_ids=110842&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/praxis-dr-vallee"
   },
   "Kardios-Astra": {
      "availabilities_url": "visit_motive_ids=2854139&agenda_ids=469346&insurance_sector=public&practice_ids=76464&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/kardios-kardiologen-in-berlin-berlin"   
   },
   "HNO FHain-Astra": {
      "availabilities_url": "visit_motive_ids=2731200&agenda_ids=444712&insurance_sector=public&practice_ids=146434&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/praxis/berlin/hno-praxis-am-friedrichshain"   
   },
   "Bonedoctor-Astra": {
      "availabilities_url": "visit_motive_ids=2774169&agenda_ids=457175&insurance_sector=public&practice_ids=181755&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/gemeinschaftspraxis/berlin/bonedoctor-christian-rose-baharak-djohar"   
   },
   "Bonedoctor-Biontech": {
      "availabilities_url": "visit_motive_ids=2797297&agenda_ids=462529&insurance_sector=public&practice_ids=181755&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/gemeinschaftspraxis/berlin/bonedoctor-christian-rose-baharak-djohar"   
   },
   "MVZ Dr. Kaleth & Kollegen-Astra": {
      "availabilities_url": "visit_motive_ids=2780870&agenda_ids=284796-465045&insurance_sector=public&practice_ids=112562&destroy_temporary=true&limit=4",
      "booking_url": "https://www.doctolib.de/medizinisches-versorgungszentrum-mvz/berlin/mvz-dr-kaleth-kollegen"   
   },
   "MVZ Ambulantes Gynäkologisches Operationszentrum-JJ": {
      "availabilities_url": "visit_motive_ids=2880391&agenda_ids=480095&insurance_sector=public&practice_ids=107774&limit=4",
      "booking_url": "https://www.doctolib.de/medizinisches-versorgungszentrum-mvz/berlin/ambulantes-gynaekologisches-operationszentrum"   
   },
   # "Dr. Burkhard Schlich & Dr. Kai Schorn-Astra": {
   #    "availabilities_url": "visit_motive_ids=2884322&agenda_ids=444401&insurance_sector=public&practice_ids=141729&destroy_temporary=true&limit=4",
   #    "booking_url": "https://www.doctolib.de/praxis/berlin/dr-burkhard-schlich-dr-kai-schorn"   
   # },
   # "Dr. Burkhard Schlich & Dr. Kai Schorn-Biontech": {
   #    "availabilities_url": "visit_motive_ids=2884324&agenda_ids=444401&insurance_sector=public&practice_ids=141729&destroy_temporary=true&limit=4",
   #    "booking_url": "https://www.doctolib.de/praxis/berlin/dr-burkhard-schlich-dr-kai-schorn"   
   # },
   # "Dr. Burkhard Schlich & Dr. Kai Schorn-JJ": {
   #    "availabilities_url": "visit_motive_ids=2884332&agenda_ids=444401&insurance_sector=public&practice_ids=141729&limit=4",
   #    "booking_url": "https://www.doctolib.de/praxis/berlin/dr-burkhard-schlich-dr-kai-schorn"   
   # },
}

#      "availabilities_url": "",
#      "booking_url": ""   

msg = ""

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

def send(text):
   if BROADCAST:
      return send_msg(text, settings["BROADCAST_CHAT"])
   else:
      return send_msg(text, settings["PRIVATE_CHAT"])

def fetch(k,v):
   req = urllib.request.Request(f"https://www.doctolib.de/availabilities.json?start_date={str(datetime.date.today())}&{v['availabilities_url']}", headers={"User-Agent": "lol"})
   with urllib.request.urlopen(req) as req:
         res = json.loads(req.read().decode("utf-8"))
         print("{}: {}".format(k, res))
         first_slot = [item for sublist in list(filter(None, map(lambda x: x["slots"], res["availabilities"]))) for item in sublist]
         next_date = None
         if "next_slot" in res:
            next_date = res["next_slot"]
         if len(first_slot) > 0:
            next_date = first_slot[0][:10]
         if next_date is not None and datetime.datetime.strptime(next_date, '%Y-%m-%d') < MIN_DATE and "IZ" in k:
            next_date = None 
         return {"k": k, "next_date": next_date, "booking_url": v["booking_url"]}

async def extract_all():
   with ThreadPoolExecutor(max_workers=10) as executor:
      loop = asyncio.get_event_loop()
      START_TIME = default_timer()
      tasks = [
          loop.run_in_executor(
              executor,
              fetch,
              *(i)
          )
          for i in IMPFEN.items()
      ]

      msg = ""
      responses = sorted(await asyncio.gather(*tasks), key=lambda v: v["k"])
      print(responses)
      for response in responses:
         if response["next_date"] is not None:
            msg += f'{response["k"]}: {response["next_date"]}\n{response["booking_url"]}\n\n'

      if len(msg) == 0: msg = "Nix frei ;("

      if not os.path.exists("impfe.json"):
          os.mknod("impfe.json")
          with open("impfe.json", 'a') as f: f.write('{"message": "", "last_message_metadata": ""}')
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
            msg_metadata = send(msg)
            store["last_message_metadata"] = msg_metadata
            store["message"] = msg
            file.seek(0)
            json.dump(store, file)
            file.truncate()


         # if file.read() != msg and len(msg) > 0:
         #    file.seek(0)
         #    file.write(msg)
         #    file.truncate()
         #    file.flush()
         #    send(msg)   

loop = asyncio.get_event_loop()
future = asyncio.ensure_future(extract_all())
loop.run_until_complete(future)