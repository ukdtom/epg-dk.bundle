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
	getChannelInfo()
#	getChannelsList()
#	createXMLFile()

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
	oc.add(PrefsObject(title='Preferences', thumb=R(ICON)))
	Log.Debug("**********  Ending MainMenu  **********")
	return oc

####################################################################################################
# Init Internal storage
####################################################################################################
#TODO: Do we need this?

####################################################################################################
# Create XMLTV File
####################################################################################################
def createXMLFile():
	xmlFile = Prefs['Store_Path']
	root = ET.Element("tv")
	root.set('generator-info-name', NAME)
	root.set('date', datetime.now().strftime('%Y%m%d%H%M%S'))
	root.set('source-info-name','YouSee')
	Channels = getChannelsList()
	for Channel in Channels:
		channel = ET.SubElement(root, 'channel', id=str(Channel['id']))
		ET.SubElement(channel, 'display-name').text = Channel['name']
		ET.SubElement(channel, 'logo').text = Channel['logo']



	tree = ET.ElementTree(root)
	f = io.open(xmlFile, 'wb')
#	tree.write(f, encoding='utf-8', xml_declaration=True)
	tree.write(f, xml_declaration=True)
	f.close()
	print 'Done'

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
	url = BASEURL + 'programs/'
	# Get a list of channels to download from
	grablist = getChannelsEnabled()
	print 'Ged Tommy', grablist
	count = 0
	for id in grablist:
		# Get amount of items
		URL = url + 'channel_id/' + str(id) + '/offset/0/format/json/apiversion/2/fields/totalprograms'
		totaljson = JSON.ObjectFromURL(URL, headers=HEADER)
		total = totaljson.get('totalprograms')
		print 'Ged 1', total


		URL = url + 'channel_id/' + str(id) + '/offset/0/format/json/apiversion/2/startIndex/' + str(count) + '/itemCount/' + PROGRAMSTOGRAB

		print URL
#		programs = JSON.ObjectFromURL(URL, headers=HEADER)
#		print 'Ged 1112', programs


#		for program in programs:
#			print program['title']


	return

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






