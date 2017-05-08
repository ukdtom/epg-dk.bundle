####################################################################################################
#	This plugin will downloads a danish program guide from YouSee
#
#	Made by 
#	dane22....A Plex Community member
#
####################################################################################################

# Imports
import io, os
from lxml import etree as ET
import re
import pytz
from datetime import datetime, timedelta

# Consts used
VERSION = ' V0.0.0.10'
NAME = 'epg-dk'
DESCRIPTION = 'Download a program Guide from YouSee Denmark'
ART = 'art-default.jpg'
ICON = 'epg-dk.png'
PREFIX = '/applications/epg-dk'
APPGUID = '76a8cf36-7c2b-11e4-8b4d-00079cdf80b2'
BASEURL = 'http://api.yousee.tv/rest/tvguide/'
HEADER = {'X-API-KEY' : 'HCN2BMuByjWnrBF4rUncEfFBMXDumku7nfT3CMnn'}
PROGRAMSTOGRAB = '10'
bFirstRun = False
DEBUGMODE = False
FIELDS = 'id,channel,begin,end,title,description,imageprefix,images_fourbythree,is_series,series_name,series_info,category_string,subcategory_string,directors,cast/startIndex'

####################################################################################################
# Start function
####################################################################################################
def Start():
	global DEBUGMODE
	global OFFSET
	# Switch to debug mode if needed
	debugFile = Core.storage.join_path(Core.app_support_path, Core.config.bundles_dir_name, NAME + '.bundle', 'debug')
	DEBUGMODE = os.path.isfile(debugFile)
	if DEBUGMODE:
		print("********  Started %s on %s  ********** DEBUG MODE ********" %(NAME  + ' ' + VERSION, Platform.OS))
		Log.Debug("*******  Started %s on %s  *********** DEBUG MODE ********" %(NAME  + VERSION, Platform.OS))
	else:
		Log.Debug("*******  Started %s on %s  ***********" %(NAME  + VERSION, Platform.OS))
	OFFSET = getOffSet()
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
	oc.add(DirectoryObject(key=Callback(createXMLFile, menuCall=True), title='Force create XML File', summary='Force create XML File'))
#	oc.add(DirectoryObject(key=Callback(refreshEPG, menuCall=True), title='Refresh EPG', summary='Refresh EPG'))
	oc.add(PrefsObject(title='Preferences', thumb=R(ICON)))
	Log.Debug("**********  Ending MainMenu  **********")
	return oc

####################################################################################################
# ValidatePrefs
####################################################################################################
@route(PREFIX + '/ValidatePrefs')
def ValidatePrefs():
	scheduler()

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
# Create XMLTV File Thread
####################################################################################################
@route(PREFIX + '/createXMLFile')
def createXMLFile(menuCall = False):
	message = 'XML Generation started'
	oc = ObjectContainer(title1='Create XML File', no_cache=True, message=message)
	Thread.CreateTimer(1, doCreateXMLFile, menuCall = menuCall)
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
	root.set('Sourcecode', 'https://github.com/ukdtom/epg-dk.bundle')
	root.set('Credits', 'Tommy Winther: https://github.com/twinther/script.tvguide')
	Channels = getChannelsList()
	for Channel in Channels:
		channel = ET.SubElement(root, 'channel', id=str(Channel['id']))
		ET.SubElement(channel, 'display-name').text = ValidateXMLStr(Channel['name'])
		ET.SubElement(channel, 'icon', src=Channel['logo'])
	# Just a brief check to make sure, that bFirstRun is stamped correctly
	getChannelsEnabled()
	if not bFirstRun:
		Programs = getChannelInfo()
		DSTHOURS = int((OFFSET)[2:-2])
		rxSubtitleParentes = re.compile('^\(([^\)]+)\)(\.)?')
		rxSubtitleQuoted = re.compile('^\"([^\"]+)\"(\.)?')
		for Program in Programs:		
			startTime = (datetime.utcfromtimestamp(Program['begin']) + timedelta(hours=DSTHOURS)).strftime('%Y%m%d%H%M%S') + ' ' + OFFSET
			stopTime = (datetime.utcfromtimestamp(Program['end']) + timedelta(hours=DSTHOURS)).strftime('%Y%m%d%H%M%S') + ' ' + OFFSET
			poster = Program['imageprefix'] + Program['images_fourbythree']['xxlarge']
			program = ET.SubElement(root, 'programme', start=startTime, stop=stopTime, channel=str(Program['channel']), id=str(Program['id']))
			title = ValidateXMLStr(Program['title'])
			description = ValidateXMLStr(Program['description'])
			# Sub-title (regex)
			subtitle = ''
			bSubtitleFound = False			
			mSubtitle = rxSubtitleParentes.match(description)
			if not mSubtitle:
				mSubtitle = rxSubtitleQuoted.match(description)	
			if mSubtitle:
				# Extract sub-title from description
				subtitle = mSubtitle.group(1).strip()
				# Remove extracted sub-title from description
				description = description.replace(mSubtitle.group(0), '').lstrip()
				description = description.replace(subtitle + '.', '').lstrip()
				if subtitle != title:
					# Check if title starts with extracted sub-title (switch)
					if title.startswith(subtitle):
						titleTemp = title.replace(subtitle + ': ', '').lstrip()
						title = subtitle
						subtitle = titleTemp
					bSubtitleFound = True
			ET.SubElement(program, 'title', lang='da').text = title
			if bSubtitleFound:
				ET.SubElement(program, 'sub-title', lang='da').text = subtitle.replace(title + ': ', '').lstrip()
			ET.SubElement(program, 'desc', lang='da').text = description
			ET.SubElement(program, 'icon', src=poster)
			# Category
			Program['category_string'] = ValidateXMLStr(Program['category_string'])
			ET.SubElement(program, 'category', lang='da').text = ValidateXMLStr(Program['category_string'])
			if Program['category_string'] == 'Nyheder':
				ET.SubElement(program, 'category', lang='en').text = 'news'
			if Program['category_string'] == 'Sport':
				ET.SubElement(program, 'category', lang='en').text = 'sports'
			if ValidateXMLStr(Program['subcategory_string']) != ValidateXMLStr(Program['category_string']):
				ET.SubElement(program, 'category', lang='da').text = ValidateXMLStr(Program['subcategory_string'])
			#Episode info
			try:
				if Program['is_series']:
					if Program['series_info'] != '':
						if ':' in Program['series_info']:
							Episode, Total = Program['series_info'].split(':')
						else:
							Episode = Program['series_info']
							Total = 1
						Episode = str(int(Episode)-1)
						Total = str(int(Total)-1)
					else:
						# Episode Missing :-(
						Episode = '0'
						Total = '0'
						Log.Debug('Missing episode info for "%s", so adding dummy info as %s:%s' %(title, Total, Episode))
					ET.SubElement(program, 'episode-num', system='xmltv_ns').text = Total + '.' + Episode + '.'
			except Exception, e:
				Log.Exception('Exception when digesting %s with the error %s' %(title, str(e)))
				continue
			#Credits
			credits = ET.SubElement(program, 'credits', lang='da')
			# Directors if present
			Director_list = ValidateXMLStr(Program['directors'])
			if len(Director_list) > 0:
				Director_list = Director_list.split(",")
				for director in Director_list:
					if director.startswith(" "): director = director[1:]
					ET.SubElement(credits, 'director', lang='da').text = director
			# Actor if present
			Actor_list = ValidateXMLStr(Program['cast'])
			if len(Actor_list) > 0:
				Actor_list = Actor_list.split(",")
				for actor in Actor_list:
					# Replace strange :|apostrofe|;
					actor = actor.replace(":|apostrofe|;", "'")
					# Some times YouSee has "Character: Actor) syntax, so let's get rid of the character
					if actor.rfind(':') > -1:
						actor = actor[actor.rfind(':') + 1:]
					# Skip leading space
					if actor.startswith(" "): actor = actor[1:]
					ET.SubElement(credits, 'actor', lang='da').text = actor
			# Video details....Here we lie, but should be correct in about 90% of the times
			video = ET.SubElement(program, 'video', lang='en')
			ET.SubElement(video, 'quality', lang='en').text = 'HDTV'
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
		return
	programPartURL = '/format/json/apiversion/2/fields/' + FIELDS + '/'
	Log.Debug('Enabled channels to fetch: ' + str(ChannelsEnabled))
	result = []
	for id in ChannelsEnabled:		
		offsetTime = -1
		while True:			
			# Get amount of items
			URL = url + 'channel_id/' + str(id) + '/offset/' + str(offsetTime) + '/format/json/apiversion/2/fields/totalprograms'
			totaljson = JSON.ObjectFromURL(URL, headers=HEADER)
			total = totaljson.get('totalprograms')
			Log.Debug('Total amount to fetch for channel %s is %s' %(str(id), total))
			# Now grab program info in small chuncks
			count = 0
			while True:
				URL = url + 'channel_id/' + str(id) + '/offset/' + str(offsetTime) + programPartURL + str(count) + '/itemCount/' + PROGRAMSTOGRAB
				Info = JSON.ObjectFromURL(URL, headers=HEADER)
				Programs = Info['programs']
				for Program in Programs:			
					result.append(Program)
				count += int(PROGRAMSTOGRAB)
				if count > total:
					break
			offsetTime += 1
			if offsetTime > int(Prefs['DaysToFetch']):
				break
	Log.Debug('Returning %s programs' %(str(len(result))))
	Log.Debug('*** Ending fetch of Program Info ***')
	return result

####################################################################################################
# Get Channels enabled from DVR
####################################################################################################
@route(PREFIX + '/getChannelsEnabled')
def getChannelsEnabled():
	global bFirstRun
	# Get a list of channels to download from
	identifiers = []
	# Start by getting enabled channels
	url = 'http://127.0.0.1:32400/livetv/dvrs'
	urlYouSee = BASEURL + 'channels/format/json/fields/id'
	enableList = XML.ObjectFromURL(url, cacheTime=0)
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
		bFirstRun = False
		enabled = enableList.xpath('//ChannelMapping')
		for channel in enabled:
			if channel.get('enabled') == '1':
				identifiers.append(channel.get('lineupIdentifier'))
	return identifiers

####################################################################################################
# Scheduler
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
		Log.Debug('We should autorun at: ' + runTime.strftime(FMT))
		Log.Debug('Time is now: ' + nowTime.strftime(FMT))
		Log.Debug('Amount of seconds to next run is: ' + str(deltaTimeInSec))
		Thread.CreateTimer(deltaTimeInSec, doCreateXMLFile)
	else:
		Log.Debug('Scheduler disabled')

####################################################################################################
# Validate XML String
####################################################################################################
@route(PREFIX + '/ValidateXMLStr')
def ValidateXMLStr(xmlstr):
	# Replace valid utf-8 characters, that doesn't work in an xml file with a questionmark
	RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                 u'|' + \
                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                  (unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                   unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                   unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff))
	xmlstr = re.sub(RE_XML_ILLEGAL, "?", xmlstr)
	return xmlstr

####################################################################################################
# Get Summer/Winter time Offset
####################################################################################################
@route(PREFIX + '/getOffSet')
def getOffSet():
	return datetime.now(pytz.timezone('Europe/Copenhagen')).strftime('%z')
