####################################################################################################
#	This plugin will download a program guide from YouSee
#
#	Made by 
#	dane22....A Plex Community member
#
####################################################################################################

# Imports
import io, os
import json
from lxml import etree as ET
from datetime import datetime
import time
import threading
from threading import Timer
from datetime import datetime


# Consts used
VERSION = ' V0.0.0.1'
NAME = 'DVR-YouSee'
DESCRIPTION = 'Download a program Guide from YouSee Denmark'
ART = 'art-default.jpg'
ICON = 'youSee.png'
PREFIX = '/applications/DVR-YouSee'
APPGUID = '76a8cf36-7c2b-11e4-8b4d-00079bd310b2'
BASEURL = 'http://api.yousee.tv/rest/tvguide/'
HEADER = {'X-API-KEY' : Prefs['API_Key']}
PROGRAMSTOGRAB = '5'
bFirstRun = False

####################################################################################################
# Start function
####################################################################################################
def Start():
	# Switch to debug mode if needed
	debugFile = Core.storage.join_path(Core.app_support_path, Core.config.bundles_dir_name, NAME + '.bundle', 'debug')
	DEBUGMODE = os.path.isfile(debugFile)
	if DEBUGMODE:
		print("********  Started %s on %s  ********** DEBUG MODE ********" %(NAME  + ' ' + VERSION, Platform.OS))
		Log.Debug("*******  Started %s on %s  *********** DEBUG MODE ********" %(NAME  + VERSION, Platform.OS))
	else:
		Log.Debug("*******  Started %s on %s  ***********" %(NAME  + VERSION, Platform.OS))
	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
	Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME  + VERSION
	DirectoryObject.thumb = R(ICON)
	HTTP.CacheTime = 0
	scheduler()

####################################################################################################
# Main menu
####################################################################################################
@handler(PREFIX, NAME, thumb=ICON, art=ART)
@route(PREFIX + '/MainMenu')
def MainMenu():
	Log.Debug("**********  Starting MainMenu  **********")
	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME  + VERSION
	oc = ObjectContainer()
	oc.view_group = 'List'
	oc.add(DirectoryObject(key=Callback(createXMLFile, menuCall=True), title='Force create XML File', summary='Create XML File'))
#	oc.add(DirectoryObject(key=Callback(refreshEPG, menuCall=True), title='Refresh EPG', summary='Refresh EPG'))
	oc.add(PrefsObject(title='Preferences', thumb=R(ICON)))
	Log.Debug("**********  Ending MainMenu  **********")
	return oc

####################################################################################################
# Init Internal storage
####################################################################################################
#TODO: Do we need this?

####################################################################################################
# ValidatePrefs
####################################################################################################
@route(PREFIX + '/ValidatePrefs')
def ValidatePrefs():
	# Restart plugin after changing prefs

	HTTP.Request('http://127.0.0.1:32400/:/plugins/com.plexapp.plugins.dvr-yousee.bundle/restart', immediate=True, cacheTime=0)

####################################################################################################
# Refresh EPG			*** Not used ***
####################################################################################################
#TODO: This sadly and strangely doesn't work
def refreshEPG(menuCall = False):
	# Lets start by grapping the device number
	URL = 'http://127.0.0.1:32400/livetv/dvrs'
	deviceId = XML.ElementFromURL(URL).xpath('//Dvr')[0].get('key')
	# And now let's refresh EPG
	URL = 'http://127.0.0.1:32400/livetv/dvrs/' + deviceId + '/reloadGuide'
	# Now send the request
	HTTP.Request(URL, method='POST')
	if menuCall:
		oc2 = ObjectContainer(title1="EPG Refreshed")
		return oc2
	else:
		return

####################################################################################################
# Create XMLTV File
####################################################################################################
@route(PREFIX + '/createXMLFile')
def createXMLFile(menuCall = False):
	message = 'All done'
	oc = ObjectContainer(title1='Create XML File', no_cache=True, message=message)
	doCreateXMLFile(menuCall = menuCall)
	return oc

####################################################################################################
# Create XMLTV File
####################################################################################################
@route(PREFIX + '/createXMLFile')
def doCreateXMLFile(menuCall = False):
	xmlFile = Prefs['Store_Path']
	root = ET.Element("tv")
	root.set('generator-info-name', NAME)
	root.set('date', datetime.now().strftime('%Y%m%d%H%M%S'))
	root.set('source-info-name','YouSee')
	root.set('Author','dane22, a Plex Community member')
	root.set('Credits', 'Tommy Winther: https://github.com/twinther/script.tvguide')
	Channels = getChannelsList()
	for Channel in Channels:
		channel = ET.SubElement(root, 'channel', id=str(Channel['id']))
		ET.SubElement(channel, 'display-name').text = Channel['name']
		ET.SubElement(channel, 'icon', src=Channel['logo'])
	if not bFirstRun:
		Programs = getChannelInfo()
		for Program in Programs:
			startTime = datetime.fromtimestamp(Program['begin']).strftime('%Y%m%d%H%M%S +0100')
			stopTime = datetime.fromtimestamp(Program['end']).strftime('%Y%m%d%H%M%S +0100')
			poster = Program['imageprefix'] + Program['images_fourbythree']['small']
			program = ET.SubElement(root, 'programme', start=startTime, stop=stopTime, channel=str(Program['channel']))
			ET.SubElement(program, 'title', lang='da').text = Program['title']
			ET.SubElement(program, 'desc', lang='da').text = Program['description']
			ET.SubElement(program, 'icon', src=poster)
			#Episode info
			try:
				if Program['is_series']:
					if Program['series_info'] != '':
						if ':' in Program['series_info']:
							Episode, Total = Program['series_info'].split(':')
						else:
							Episode = Program['series_info']
							Total = Episode	
						Episode = str(int(Episode)-1)
						Total = str(int(Total)-1)
					else:
						# Episode Missing :-(					
						Episode = '0'
						Total = '0'
						Log.Debug('Missing episode info for %s, so adding dummy info as %s:%s' %(Program['title'], Episode, Total))
					ET.SubElement(program, 'episode-num', system='xmltv_ns').text = Episode + '.' + Total + '.'	
			except Exception, e:
				Log.Exception('Exception when digesting %s with the error %s' %(Program['title'], e))
				continue
			# Category
			ET.SubElement(program, 'category', lang='da').text = Program['category_string']
	tree = ET.ElementTree(root)
	xmlstr = unicode(ET.tostring(tree.getroot(), xml_declaration=True, encoding="utf-8", pretty_print=True, doctype='<!DOCTYPE tv SYSTEM "xmltv.dtd">'))	
	with io.open(xmlFile, "w", encoding="utf-8") as f:
		f.write(xmlstr)
	Log.Info('All done creating the XML File')
	scheduler()
	if menuCall:	
		oc2 = ObjectContainer(title1="XML File Generated")
		return oc2
	else:
		return

####################################################################################################
# Get Channel list from YouSee
####################################################################################################
@route(PREFIX + '/getChannelsList')
def getChannelsList():
	URL = BASEURL + 'channels/format/json/fields/id,name,logo'
	# Get the json from TDC
	Channellist = JSON.ObjectFromURL(URL, headers=HEADER)
	# Walk the channel list one by one
	for Group in Channellist:
		# Only get "All"
		if Group['name'] == 'All':
			Channels = Group['channels']
			return Channels

####################################################################################################
# Get Channel Info from YouSee
####################################################################################################
@route(PREFIX + '/getChannelInfo')
def getChannelInfo():
	Log.Debug('*** Starting to fetch Program Info ***')
	url = BASEURL + 'programs/'
	# Get a list of channels to download from
	ChannelsEnabled = getChannelsEnabled()
	if bFirstRun:
		print 'Ged First run, so eject now'
		return
	programPartURL = '/offset/0/format/json/apiversion/2/fields/id,channel,begin,end,title,description,imageprefix,images_fourbythree,is_series,series_name,series_info,category_string/startIndex/'
	Log.Debug('Enabled channels to fetch: ' + str(ChannelsEnabled))
	result = []
	for id in ChannelsEnabled:
		count = 0
		# Get amount of items
		URL = url + 'channel_id/' + str(id) + '/offset/0/format/json/apiversion/2/fields/totalprograms'
		totaljson = JSON.ObjectFromURL(URL, headers=HEADER)
		total = totaljson.get('totalprograms')
		Log.Debug('Total amount to fetch for channel %s is %s' %(str(id), total))
		# Now grab program info in small chuncks
		while True:
			URL = url + 'channel_id/' + str(id) + programPartURL + str(count) + '/itemCount/' + PROGRAMSTOGRAB
			Info = JSON.ObjectFromURL(URL, headers=HEADER)
			Programs = Info['programs']
			for Program in Programs:
				result.append(Program)
			count += int(PROGRAMSTOGRAB)
			if count > total:
				break
	Log.Debug('Returning %s programs' %(str(len(result))))
	Log.Debug('*** Ending fetch of Program Info ***')
	return result

####################################################################################################
# Get Channels enabled from YouSee
####################################################################################################
@route(PREFIX + '/getChannelsEnabled')
def getChannelsEnabled():
	global bFirstRun
	# Get a list of channels to download from
	identifiers = []
	# Start by getting enabled channels
	url = 'http://127.0.0.1:32400/livetv/dvrs'
	urlYouSee = BASEURL + 'channels/format/json/fields/id'
	enableList = XML.ObjectFromURL(url)
	# First run or not
	if int(enableList.get('size')) == 0:
		Log.Debug(NAME + ' is running for the first time, so grap all channels')
		bFirstRun = True
		Channellist = JSON.ObjectFromURL(urlYouSee, headers=HEADER)
		for Group in Channellist:
			# Only get "All"
			if Group['name'] == 'All':
				Channels = Group['channels']
				for channel in Channels:
					identifiers.append(channel['id'])
	else:
		Log.Debug(NAME + ' is already enabled, so grap the enabled channels')
		enabled = enableList.xpath('//ChannelMapping')
		for channel in enabled:
			if channel.get('enabled') == '1':
				identifiers.append(channel.get('lineupIdentifier'))
	return identifiers

####################################################################################################
# Get Scheduler
####################################################################################################
@route(PREFIX + '/scheduler')
def scheduler():
	if Prefs['EnableSchedule']:
		# Format of time:min
		FMT = '%H:%M'	
		runTime = datetime.strptime(Prefs['Schedule'], FMT)
		nowTime = datetime.strptime(datetime.now().strftime(FMT), FMT)
		deltaTimeInSec = (runTime - nowTime).total_seconds()
		# Did the moment already pass?
		if deltaTimeInSec < 0:
			# Darn, we missed it, so adding 24 hours here
			deltaTimeInSec += 86400
		Log.Debug('Time is now: ' + runTime.strftime(FMT))
		Log.Debug('We should autorun at: ' + nowTime.strftime(FMT))
		Log.Debug('Amount of seconds to next run is: ' + str(deltaTimeInSec))
		threading.Timer(deltaTimeInSec, doCreateXMLFile).start()
	else:
		Log.Debug('Scheduler disabled')


