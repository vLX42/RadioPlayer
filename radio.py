import RPi.GPIO as GPIO
import time
import subprocess
import sys
import requests
import json
import Adafruit_Nokia_LCD as LCD
import Adafruit_GPIO.SPI as SPI
import textwrap
import json

from time import sleep
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

sp_config = {
				'client'	: '127.0.0.1',
				'port'		: '4000',
				'status'	: ('/api/info/status',	 'i'),
				'metadata': ('/api/info/metadata', 'i'),
				'pause'	 : ('/api/playback/pause','p'),
				'play'		: ('/api/playback/play', 'p'),
				'next'		: ('/api/playback/next', 'p'),
				'prev'		: ('/api/playback/prev', 'p')
}


# Raspberry Pi hardware SPI config:
DC = 23
RST = 24
SPI_PORT = 0
SPI_DEVICE = 0

#adjust for where your switch is connected
buttonPin = 20
#38
buttonPin2 = 26
#37
buttonPin3 = 16
#36
buttonPin4 = 19
#35


#GPIO.setup(buttonPin3,GPIO.IN)
#GPIO.setup(buttonPin4,GPIO.IN)
playIndex = 0
playMax = 11
onoffDelay = 0
onoffDelayMax = 5

spotifyTitle = 0
spotifyTitleMax = 10

playingRadio = False
bSpotify = False
bShowSpotifyLogo = False
bSpeakerOn = True

disp = LCD.PCD8544(DC, RST, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=4000000))

# Software SPI usage (defaults to bit-bang SPI interface):
#disp = LCD.PCD8544(DC, RST, SCLK, DIN, CS)

# Initialize library.
disp.begin(contrast=100)
ledPin = 17

GPIO.setmode(GPIO.BCM)

GPIO.setup(ledPin, GPIO.OUT)


GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(buttonPin2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(buttonPin3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(buttonPin4, GPIO.IN, pull_up_down=GPIO.PUD_UP)


with open('radio.json') as json_data:
    json_radio = json.load(json_data)
	
playMax = len(json_radio)	



def speakerOn():
	bSpeakerOn = True
	GPIO.output(ledPin, GPIO.HIGH)

def speakerOff():
	bSpeakerOn = False
	disp.clear()
	disp.display()
	GPIO.output(ledPin, GPIO.LOW)

def displaySpoitfyTitle():
	disp.clear()
	disp.display()
	image = Image.new('1', (LCD.LCDWIDTH, LCD.LCDHEIGHT))
	
	# Get drawing object to draw on image.
	draw = ImageDraw.Draw(image)
	draw.rectangle((0,0,LCD.LCDWIDTH,LCD.LCDHEIGHT), outline=255, fill=255)
	# Load default font.
	font = ImageFont.load_default()
	 
	# Alternatively load a TTF font.
	# Some nice fonts to try: http://www.dafont.com/bitmap.php
	# font = ImageFont.truetype('Minecraftia.ttf', 8)
	 
	# Write some text.
	text = "-=SPOTIFY=-   " +  spconnect('metadata','track_name')  +" - " + spconnect('metadata','artist_name')
	print text
	# draw.text((8,30), spconnect('metadata','track_name'), font=font)
	MAX_W, MAX_H = (LCD.LCDWIDTH, LCD.LCDHEIGHT)
	lines = textwrap.wrap(text, width=12)
	current_h, pad = 1, 1
	for line in lines:
		w, h = draw.textsize(line, font=font)
		draw.text(((MAX_W - w) / 2, current_h), line, font=font)
		current_h += h + pad
	
	# Display image.
	disp.image(image.rotate(180))
	disp.display()
	
def spconnect (command, parameter): 


	# send http request to get data from spotify client
	sOut = ''
	try:
		rdata = requests.get('http://'+ sp_config['client'] + ':' + sp_config['port'] + sp_config[command][0])
		if rdata.ok :
			if sp_config[command][1] == 'p' :
				sOut += 'OK'
			else :
				if not parameter :
					for parameter,pvalue in rdata.encode('utf-8').json().items():
						sOut +=	('%s : %s' % (parameter, pvalue))
				else :
					sOut +=	str(rdata.json()[parameter])
		else :
			sOut +=	('Error: %s' % rdata.status_code)
	
	except requests.exceptions.ConnectionError as error:
		sOut +=	('Connection Error: %s' % error)
	except requests.exceptions.HTTPError as error:
		sOut +=	('HTTP Error: %s' % error)
	except:
		sOut += "Unknown error"
	return sOut

def mpcPlaying (): 
	cmd = subprocess.Popen("mpc status",shell=True, stdout=subprocess.PIPE)
	status = cmd.stdout.readlines()
	if "[playing]" in str(status):
		return True
	else:
		return False

def PlayStation(url):
	subprocess.call("mpc clear & mpc add " + url + " & sleep 0.1 & mpc add " + url + " & mpc add " + url + " & sleep 0.1 & mpc add " + url + " & sleep 0.1 & mpc play 1", shell=True)

def StopAll(channel):
	time.sleep(0.01)         # need to filter out the false positive of some power fluctuation
	if GPIO.input(channel) != GPIO.HIGH:
		return       
	print "Stop All!!"
	subprocess.call("mpc stop", shell=True)
	spconnect('pause','')
	speakerOff()



def DisplayImage(file):
	disp.clear()
	disp.display()
	image = Image.open(file).convert('1').rotate(180) 
	disp.image(image)
	disp.display()	
	global playingRadio
	global bSpotify
	if playingRadio:
		bSpotify = True
		playingRadio = False
	else:
		bSpotify = False	

def TogglePlay(channel):
	time.sleep(0.01)         # need to filter out the false positive of some power fluctuation
	if GPIO.input(channel) != GPIO.HIGH:
		return      
	global playingRadio
	global bSpotify
	if playingRadio:
		print "switch to spotify"
		subprocess.call("mpc stop", shell=True)
		spconnect('play','') 
		bSpotify = True
		playingRadio = False
	else:
		print "switch to radio"
		bSpotify = False
		PlayRadio(channel)
		#bSpotify = False
		#playingRadio = True
	speakerOn()	
	
def PlayRadio(channel):
	time.sleep(0.01)         # need to filter out the false positive of some power fluctuation
	if GPIO.input(channel) != GPIO.HIGH:
		return    
	if bSpotify:
		print "spotify command"
		if (channel==buttonPin):
			spconnect('next','')
		if (channel==buttonPin2):
			spconnect('prev','')
		displaySpoitfyTitle()
	else:
		print "Radio tryk start"
		# Internal button, to open the gate
		global playIndex
		global playingRadio
		global bShowSpotifyLogo
		global json_radio
		bPlay = False
		#assuming the script to call is long enough we can ignore bouncing
		
		if (channel==buttonPin3):
			print 'Start Radio Pin ' + str(buttonPin3)
			bPlay = True
			spconnect('pause','')
		if (channel==buttonPin):
			print 'Pin ' + str(buttonPin)
			playIndex += 1
			bPlay = True
		if (channel==buttonPin2):
			print 'Pin ' + str(buttonPin2)
			playIndex -= 1
			bPlay = True
		if bPlay == True:
			if playIndex < 1:
				playIndex = playMax
			if playIndex > playMax:
				playIndex = 1
             
			print json_radio[playIndex]['Name']
			PlayStation(json_radio[playIndex]['Url'])
			DisplayImage(json_radio[playIndex]['Logo'])
			
			bShowSpotifyLogo = False
			playingRadio = True
			speakerOn()
		print "event end"

def loop():
	global bSpotify
	global playingRadio
	global bShowSpotifyLogo
	global onoffDelay
	global spotifyTitle
	if spconnect('status','playing')=="True":
		bSpotify = True 
		#ImageLoad = True
		if bShowSpotifyLogo == False:
			DisplayImage('logos/spotify.pbm')
			bShowSpotifyLogo = True
			
		if playingRadio:
			print "playingRadio"
			print "spotify stop"
			playingRadio = False 
			subprocess.call("mpc pause", shell=True)
			spconnect('pause','')
			spconnect('play','') 
		speakerOn()
		spotifyTitle +=1
		if spotifyTitle >= spotifyTitleMax:
			displaySpoitfyTitle()
			spotifyTitle = 0
	else:
		bSpotify = False
		onoffDelay +=1
		if onoffDelay >= onoffDelayMax:
			if (mpcPlaying()):
				speakerOn()
			else:
				speakerOff()
			onoffDelay = 0
	
GPIO.add_event_detect(buttonPin2, GPIO.BOTH, callback=PlayRadio, bouncetime=600)
GPIO.add_event_detect(buttonPin, GPIO.BOTH, callback=PlayRadio, bouncetime=600)
GPIO.add_event_detect(buttonPin3, GPIO.BOTH, callback=TogglePlay, bouncetime=600)
GPIO.add_event_detect(buttonPin4, GPIO.BOTH, callback=StopAll, bouncetime=600)
	
while True:	
	
	loop()
	# Here everythink to loop normally
	sleep(1);
	
GPIO.cleanup()
