#Script to read multiple rss feeds and seleect a podcast to listen to
#!python3
import paho.mqtt.client as mqtt  #import the client1
import time
import feedparser
import requests
import json
from datetime import datetime
from time import mktime

#Variables
podcast_list = '/home/user/scripts/podcast/podcasts_to_listen_to.json'
tonight_podcast = '/home/user/dockercompose/files/tonights_podcast.txt'
mqtt_username = 'USERNAME'
mqtt_password = 'PASSWORD'
broker="192.168.1.10"

bitly_token = 'bitlytoken'

mqtt_date = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
mqtt_id = "Podcast_{}".format (mqtt_date)

def shorten_url(bitly_token,long_url):
    headers = {
        'Authorization': bitly_token,
        'Content-Type': 'application/json',
    }

    #data = { "long_url": long_url, "domain": "bit.ly"}
    data = '{ "long_url": "long_url_address", "domain": "bit.ly" }'
    data= data.replace('long_url_address',long_url)

    response = requests.post('https://api-ssl.bitly.com/v4/shorten', headers=headers, data=data)

    return json.loads(response.content)

def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    #print("message topic=",message.topic)
    #print("message qos=",message.qos)
    #print("message retain flag=",message.retain)
    update_podcast(str(message.payload.decode("utf-8")))

def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True #set flag
        print("connected OK")
    else:
        print("Bad connection Returned code=",rc)

def update_podcast(payload):
    podcast_output_list = []
    print ("Updating podcast")
    #Load current episodes to listen too
    try:
        with open (podcast_list, 'r') as podcasts:
            content = podcasts.read()
            podcasts_list = json.loads(content)
    except:
        print('No podcast list found to load')
        podcasts_list = []

    #My favorite Podcasts
    podcast_rss_dic = {
                    '5 live Science' : {'url':'https://podcasts.files.bbci.co.uk/p02pc9ny.rss','rating': '1'},
                    'The life Scientific' : {'url': 'https://podcasts.files.bbci.co.uk/b015sqc7.rss','rating': '3'},
                    'Science in Action' : {'url': 'https://podcasts.files.bbci.co.uk/p002vsnb.rss','rating': '3'} ,
                    'Future Tense': {'url':'https://www.abc.net.au/feeds/2883726/podcast.xml','rating': '4'},
                    'Late Night Live': {'url': 'https://www.abc.net.au/radionational/programs/latenightlive/feed/2890646/podcast.xml', 'rating': '5'},
                    'Intelligence Squared' : {'url': 'https://rss.acast.com/intelligencesquared','rating' :'8'}
                    }



    #New podcasts today
    todays_podcasts = []

    if payload == 'update':
        # End functions
        #log.info("Payload update checking new podcasts")
        for key in podcast_rss_dic:
            try:
                rss_feed_url = feedparser.parse(podcast_rss_dic[key]['url'])
                #for abc
                if not rss_feed_url['entries'] and "not well-formed" in str(rss_feed_url['bozo_exception']):
                    rss1 = requests.get(podcast_rss_dic[key]['url']).content.decode("utf-8")
                    rss1 = rss1.replace("utf-16","unicode")
                    rss_feed_url = feedparser.parse(rss1)
                podcast_url = rss_feed_url.entries[0].enclosures[0]['href']
                #podcast_description = (rss_feed_url.entries[0]['summary_detail'].value)
                podcast_title = rss_feed_url.entries[0]['title']

                #rss_feed_url.entries[0]['media_content'][0]['url']
                todays_date = datetime.now().strftime("%d-%m-%Y")
                podcast_date = datetime.fromtimestamp(mktime(rss_feed_url.entries[0]['published_parsed'])).strftime("%d-%m-%Y")
                time_since_published = datetime.utcnow() - datetime.fromtimestamp(mktime(rss_feed_url.entries[0]['published_parsed'])) 
                time_since_published_hours = time_since_published.total_seconds() /3600

                #Pocast is new
                podcast_already_added = 0

                #If podcast from the past 24 hours
                if time_since_published_hours <= 24:

                    #Check if podcast url already in the list
                    for podcast in podcasts_list:
                        if podcast['url'] == podcast_url:
                            podcast_already_added = 1

                    #If not in the list then add it
                    if podcast_already_added == 0:
                        podcasts_list.append({
                                                'date' :todays_date,
                                                'podcast': key,
                                                'title': podcast_title,
                                                'url': podcast_url,
                                                'rating': podcast_rss_dic[key]["rating"]
                                                            })

            except Exception as e: print(e)
    
    else:
        #log.info("payload was not update")
        #log.info(payload)
        print("Payload was not update")
        print(payload)

    #Find most suitable podcast
    podcast_for_tonight = 0

    for podcast in podcasts_list:
        if podcast_for_tonight == 0:
            podcast_for_tonight = podcast

        elif podcast_for_tonight['rating'] > podcast['rating']:
            podcast_for_tonight = podcast

    for podcast in podcasts_list:
        if podcast['url'] != podcast_for_tonight['url']:
            #todays_date = datetime.now().strftime("%d-%m-%Y")
            podcast_date = datetime.strptime(podcast['date'], '%d-%m-%Y')
            time_since_published = datetime.utcnow() - podcast_date 
            time_since_published_days = time_since_published.total_seconds() /86400
            if time_since_published_days < 30:
                podcast_output_list.append(podcast)

    with open (podcast_list, 'w') as podcasts:
        podcasts.write(json.dumps(podcast_output_list))

    #with open(tonight_podcast,'w') as tonights_podcast_file:
    short_url_obj = shorten_url(bitly_token,podcast_for_tonight['url'])
    #tonights_podcast_file.write(short_url_obj['link'])
    client.publish("scripts/podcast",short_url_obj['link'])

mqtt.Client.connected_flag=False#create flag in class
client = mqtt.Client(mqtt_id)#create new instance
client.username_pw_set(username= mqtt_username,password= mqtt_password)
client.on_connect=on_connect  #bind call back function
print ("mqtt_id {0}".format (mqtt_id))
#log.info("mqtt_id {0}".format (mqtt_id))
client.on_message=on_message
print("Connecting to broker ",broker)
#log.info("connecting to broker")
client.connect(broker)      #connect to broker
client.subscribe("scripts/podcast_control", qos=0)
client.loop_forever()