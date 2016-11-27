####################################################################################################
#	This plugin will download a program guide from YouSee
#
#	Made by 
#	dane22....A Plex Community member
#
####################################################################################################

# Imports
import io
import json
from lxml import etree as et
from datetime import datetime
from io import BytesIO

try:
	import xml.etree.cElementTree as ET
except ImportError:
	import xml.etree.ElementTree as ET

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


####################################################################################################
# Start function
####################################################################################################
def Start():
	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
	Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME  + VERSION
	DirectoryObject.thumb = R(ICON)
	HTTP.CacheTime = 0
	print 'Ged start YouSee'
#	refreshEPG()
#	getChannelInfo()
#	getChannelsList()
	createXMLFile()

####################################################################################################
# Main menu
####################################################################################################
@handler(PREFIX, NAME, thumb=ICON, art=ART)
@route(PREFIX + '/MainMenu')
def MainMenu():
	Log.Debug("**********  Starting MainMenu  **********")
	global sectiontype
	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME  + VERSION
	oc = ObjectContainer()
	oc.view_group = 'List'
	oc.add(DirectoryObject(key=Callback(createXMLFile, menuCall=True), title='Create XML File', summary='Create XML File'))
	oc.add(DirectoryObject(key=Callback(refreshEPG, menuCall=True), title='Refresh EPG', summary='Refresh EPG'))
	oc.add(PrefsObject(title='Preferences', thumb=R(ICON)))
	Log.Debug("**********  Ending MainMenu  **********")
	return oc

####################################################################################################
# Init Internal storage
####################################################################################################
#TODO: Do we need this?

####################################################################################################
# Refresh EPG
####################################################################################################
#TODO: This sadly and strangly doesn't work
def refreshEPG(menuCall = False):
	# Lets start by grapping the device number
	URL = 'http://127.0.0.1:32400/livetv/dvrs'
	deviceId = XML.ElementFromURL(URL).xpath('//Dvr')[0].get('key')
	print 'Ged Device ID1', deviceId
	# And now let's refresh EPG
	URL = 'http://127.0.0.1:32400/livetv/dvrs/' + deviceId + '/reloadGuide'
	# Now send the request
	HTTP.Request(URL, method='POST')
	print 'Ged33 done'
	if menuCall:
		oc2 = ObjectContainer(title1="EPG Refreshed")
		return oc2
	else:
		return

####################################################################################################
# Create XMLTV File
####################################################################################################
def createXMLFile(menuCall = False):
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
	Programs = getChannelInfo()
	for Program in Programs:
		startTime = datetime.fromtimestamp(Program['begin']).strftime('%Y%m%d%H%M%S +0100')
		stopTime = datetime.fromtimestamp(Program['end']).strftime('%Y%m%d%H%M%S +0100')
		poster = Program['imageprefix'] + Program['images_fourbythree']['small']
		
		if Program['is_series']:
			print 'Ged SeriesInfo', Program['series_info'], Program['title']


#<episode-num system="xmltv_ns">3.1.</episode-num>


		program = ET.SubElement(root, 'programme', start=startTime, stop=stopTime, channel=str(Program['channel']))
		ET.SubElement(program, 'title', lang='da').text = Program['title']
		ET.SubElement(program, 'desc', lang='da').text = Program['description']
		ET.SubElement(program, 'icon', src=poster)
		try:
			if Program['is_series']:
				print 'Ged SeriesInfo', Program['series_info'], Program['title']
				if Program['series_info'] != '':
					if ':' in Program['series_info']:
						Episode, Total = Program['series_info'].split(':')
					else:
						Episode = Program['series_info']
						Total = Episode	
					print 'Ged Episode', Episode
					print 'Ged total', Total
					Episode = str(int(Episode)-1)
					Total = str(int(Total)-1)
				else:
					Episode = '1'
					Total = '1'
				ET.SubElement(program, 'episode-num', system='xmltv_ns').text = Episode + '.' + Total + '.'			
#					ET.SubElement(program, 'episode-num', system='xmltv_ns').text = 'Gummiged'

				#<episode-num system="xmltv_ns">3.1.</episode-num>
		except:
			print 'Ged SeriesInfo FEJL******* -' + Program['series_info'] + '-', Program['title']
			continue


	tree = ET.ElementTree(root)
	f = io.open(xmlFile, 'wb')
	tree.write(f, xml_declaration=True)
	f.close()

	print 'Ged done'

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
	grablist = getChannelsEnabled()
	prugramPartURL = '/offset/0/format/json/apiversion/2/fields/id,channel,begin,end,title,description,imageprefix,images_fourbythree,is_series,series_name,series_info/startIndex/'
	Log.Debug('Enabled channels to fetch: ' + str(grablist))
	result = []
	for id in grablist:
		count = 0
		# Get amount of items
		URL = url + 'channel_id/' + str(id) + '/offset/0/format/json/apiversion/2/fields/totalprograms'
		totaljson = JSON.ObjectFromURL(URL, headers=HEADER)
		total = totaljson.get('totalprograms')
		Log.Debug('Total amount to fetch for channel %s is %s' %(str(id), total))
		# Now grab program info in small chuncks
		while True:
			URL = url + 'channel_id/' + str(id) + prugramPartURL + str(count) + '/itemCount/' + PROGRAMSTOGRAB
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
	# Get a list of channels to download from
	identifiers = []
	# Start by getting enabled channels
	url = 'http://127.0.0.1:32400/livetv/dvrs'
	urlYouSee = BASEURL + 'channels/format/json/fields/id'
	enableList = XML.ObjectFromURL(url)
	# First run or not
	if int(enableList.get('size')) == 0:
		Log.Debug(NAME + ' is running for the first time, so grap all channels')
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






