'''
DICT OF ITEMS IN CONFIG WHICH AFFECT THIS KODI SETTING

kodi_setting_id:    { 
	
	KODI_ITEM:
			{
			config_get_patterns: [	LIST OF DICTS WITH AN IDENTIFY REGEX AND AN EXTRACT REGEX

							IDENTIFY REGEX'S ARE THERE TO SPECIFICALLY FIND THE LINES
							EXTRACT REGEXES ARE THERE TO GET THE SPECIFIC SETTING VALUE
						],
			
			
			config_set : FUNCTION TO CHANGE THE SETTING IN THE CONFIG,
							# this code should cycle through the config line list, search for each config_key, then substitute that line with the new one

			config_validation: FUNCTION TO VALIDATE THE VALUE FROM THE CONFIG, this also converts the value into a form kodi settings will recognise
								i.e. it should convert binary 0:1 to 'false'|'true'

			kodi_set: additional function that can be used to do more specific conversion from the config to kodi.
				for instance, if a single setting in kodi relies upon two different settings in the config, this can combine them

			setting_stub: a stub of the string that will replace the lines in the config.txt, the value is inserted into it
			},

	# ...


NEEDS A REMOVE LIST
NEEDS A FINAL CHECK FOR HDMI_SAFE to make sure the entries related to it are removed if it is on 
		hdmi_safe can be checked in the dict immediately after the settings are extracted from kodi
		that way the other values can be set and override the ones taken from kodi

'''
import re


def config_to_kodi(MASTER_SETTINGS, config):
	''' Takes the existing config and uses the protocols in the MASTER_SETTINGS to extract the settings 
		for use in kodi.

		Returns a dictionary of kodi settings and kodi values.'''

	extracted_settings_for_kodi = {}

	for setting, protocols in MASTER_SETTINGS.iteritems():

		value = general_config_get(config, **protocols)

		extracted_settings_for_kodi[setting] = value

	return extracted_settings_for_kodi


def general_config_get(config, config_get_patterns, config_validation, kodi_set, default, **kwargs):
	''' Searches the config.txt for specific settings and returns the values when they are found.

		Uses the validation and kodi_set protocols to convert the config settings into kodi settings.

		Returns a valid kodi setting value. '''

	results = []

	# the config is reviewed in reverse order so that the final of any duplicate settings is first in the results list
	# this is consistent with how the rPi does it's config parsing
	for line in config[::-1]:

		# ignore blank lines
		if not line.strip():
			continue

		# ignore commented out lines
		if line.strip().startswith('#'):
			continue

		# strip the line of any inline comments
		if '#' in line: 
			line = line[:line.index('#')]

		for pair in config_get_patterns:

			matched = re.search(pair['identify'], line, re.IGNORECASE)

			if matched:

				raw_value = re.search(pair['extract'], line, re.IGNORECASE)

				if raw_value:

					result = config_validation(raw_value.group(1))

					if result is not None:

						results.append(result)

	kodi_setting = kodi_set(results)

	if kodi_setting is None:

		kodi_setting = retrieve_default(**default)

	return kodi_setting


def retrieve_default(function, value):

	if function is not None:

		value = function()

	return value


def kodi_to_config(MASTER_SETTINGS, config, new_settings):
	''' Takes the existing config.txt (as a list of lines) and constructs a new one using the settings
		from kodi. 

		Returns a brand new config (list of lines)'''

	for setting, new_value in new_settings.iteritems():

		setting_protocols = MASTER_SETTINGS.get(setting, None)

		if setting_protocols == None: continue

		config = general_config_set(config, new_settings, new_value, **setting_protocols)

	return config


def general_config_set(config, new_settings, new_value, config_get_patterns, config_set, already_set, setting_stub, **kwargs):
	''' Runs through the config.txt looking for a specific setting and replaces the existing 
		values when they are found. If there are duplicate entries, the last entry is kept, the others
		are commented out.

		If not found, then the setting value is added to the end.

		Returns a new list of config lines. '''

	new_config = []

	# pass the new_value through the config_set protocol to prepare it for inclusion in the config.txt
	new_value = config_set(new_value, new_settings)

	#print config
	#print config[::-1]

	# the original config is run through backwards so that the last setting of any duplicates is kept
	for line in config[::-1]:

		#print '---'
		#print 'subject line : %s ' % line.strip()

		# pass blank lines straight through
		if not line.strip():
			new_config.append(line)
			#print 'passed through blank'
			continue			

		# pass commented out lines straight through
		if line.strip().startswith('#'):
			new_config.append(line)
			#print 'passed through comment'
			continue

		# ignore inline comments on the line
		try:
			cf_line = line[:line.index('#')]
			comment = line[line.index('#'):]
		except ValueError:
			cf_line = line
			comment = ''

		line_matches = False

		for pair in config_get_patterns:

			matched = re.search(pair['identify'], cf_line, re.IGNORECASE)

			if matched:

				line_matches = True

				#print 'found'

				# if a match happens but the value is 'remove_this_line', then dont add the line to the
				# new config.txt
				if new_value == 'remove_this_line':
					#print 'setting to remove'
					continue

				# if the value has been set already, then comment out this line
				if already_set:

					# comment out any duplicated entries (this could be changed to removal if we want)
					new_config.append('#' + line.replace('\n','') + ' # DUPLICATE')
					#print 'alreadyset'
					continue

				# otherwise update the line
				new_config.append(setting_stub % new_value + '  %s' % comment)
				#print 'updated value'
				already_set = True


		# if no match actually occured then pass the line through to the new config
		if not line_matches:
			new_config.append(line)
			#print 'passed through unmatched'

	# flip the config back around the other way, so new entries are added at the end
	new_config = new_config[::-1]

	if not already_set and new_value != 'remove_this_line':
		new_config.append(setting_stub % new_value)

	#print new_config

	return new_config



'''
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@ 
										VALIDATION FUNCTIONS
                                                                                       @@@@@@@@@@@@@@@@@@@@@@@@
Settings coming FROM the config.txt pass through one of these.                         @@@@@@@@@@@@@@@@@@@@@@@@
They can be tested for accuracy, valid ranges, and (if it is a simple 1 for 1)         @@@@@@@@@@@@@@@@@@@@@@@@
converted to what is recognised by the settings in Kodi. 	            			   @@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

'''



def generic_bool_validation(config_value):

	permitted = {
		'0' : 'false',
		'1' : 'true'
		}

	return permitted.get(config_value, None) 


def generic_range_validation(config_value, myrange):

	try:
		if int(config_value) in myrange:
			return config_value
		else:
			raise ValueError
	except (TypeError, ValueError):
		return None



def onoff_validation(config_value):

	permitted = {
		'off' : 'false',
		'on' : 'true'
		}

	return permitted.get(config_value, None) 		


def config_hdmi_boost_validation(config_value):

	return generic_range_validation(config_value, range(1,12))


def soundcard_dac_validation(config_value):

	permitted = [
		'hifiberry-dac-overlay',
		'hifiberry-dacplus-overlay',
		'hifiberry-digi-overlay',
		'iqaudio-dac-overlay',
		'iqaudio-dacplus-overlay'
		]

	try:
		return str(permitted.index(config_value) + 1)
	except IndexError:
		return None


def lirc_rpi_validation(config_value):

	permitted = [
		"lirc-rpi-overlay",
		"lirc-rpi"
		]

	if config_value in permitted:
		return 'true'


def gpio_pin_validation(config_value):

	return generic_range_validation(config_value, range(1,26))


def gpio_updown_validation(config_value):

	permitted = [
			'up',
			'down'
			]

	try:
		return str(permitted.index(config_value) + 1)
	except IndexError:
		return None


def blank_check_validation(config_value):

	if config_value:
		return config_value


def display_rotate_validation(config_value):

	permitted = [
		'0',
		'1',
		'2',
		'3',
		'0x10000',
		'0x20000'
		]

	if config_value in permitted:
		return config_value


def gpu_mem_1024_validation(config_value):

	return generic_range_validation(config_value, range(16,321))


def gpu_mem_512_validation(config_value):

	return generic_range_validation(config_value, range(16,257))


def gpu_mem_256_validation(config_value):

	return generic_range_validation(config_value, range(16,193))


def hdmi_group_validation(config_value):

	return generic_range_validation(config_value, range(0,3))


def hdmi_mode_validation(config_value):

	return generic_range_validation(config_value, range(1,87))


def hdmi_pixel_encoding_validation(config_value):

	return generic_range_validation(config_value, range(0,5))


def sdtv_aspect_validation(config_value):

	return generic_range_validation(config_value, range(1,4))


def sdtv_mode_validation(config_value):

	return generic_range_validation(config_value, range(0,4))


def w1gpio_validation(config_value):

	permitted = [
		'w1-gpio-overlay',
		'w1-gpio-pullup-overlay'
		]

	try:
		return str(permitted.index(config_value) + 1)
	except (ValueError, IndexError):
		return None


def bcm2835_validation(config_value):

	permitted = [
		'spi-bcm2835-overlay',
		]

	if config_value in permitted:
		return 'true'


def hdmi_ignore_edid_validation(config_value):

	permitted = [
		'0xa5000080',
		]

	if config_value in permitted:
		return 'true'

'''
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@ 
								CUSTOM DEFAULT FUNCTIONS
                                                                                       @@@@@@@@@@@@@@@@@@@@@@@@
Allows for customisable default values, i.e. default values determined by some 		   @@@@@@@@@@@@@@@@@@@@@@@@
external analysis                                                                      @@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

'''

def hdmi_boost_custom_default():
	''' Tests the users system to see which hdmi_boost figure should be used. '''
	''' Yet to be implemented '''

	return '2'


'''
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@ 
								CUSTOM CONFIG SET FUNCTIONS
                                                                                       @@@@@@@@@@@@@@@@@@@@@@@@
Converts the kodi settings into the settings values required in the config.txt  	   @@@@@@@@@@@@@@@@@@@@@@@@
							                                                           @@@@@@@@@@@@@@@@@@@@@@@@
Takes both the new value of the setting and all the other settings for reference       @@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

'''

def generic_bool_config_set(kodi_setting, all_settings):

	if kodi_setting == 'true':
		return '1'
	else:
		return 'remove_this_line'


def generic_passthrough_config_set(kodi_setting, all_settings):

	if kodi_setting:

		return kodi_setting

	else:

		return 'remove_this_line'


def audio_config_set(kodi_setting, all_settings):

	if kodi_setting == 'true' or all_settings.get('spi-bcm2835-overlay', None) == 'true':

		return 'on'

	else:

		return 'remove_this_line'


def config_hdmi_boost_config_set(kodi_setting, all_settings):

	# if hdmi_safe is active, then remove this conflicting line
	kodi_setting = hdmi_safe_group_removal(kodi_setting, all_settings)	

	if kodi_setting in [str(x) for x in range(1,12)]:

		return kodi_setting

	else:

		return 'remove_this_line'


def display_rotate_config_set(kodi_setting, all_settings):

	permitted = [
		'remove_this_line',
		'1',
		'2',
		'3',
		'0x10000',
		'0x20000'
		]

	try:
		return permitted[int(kodi_setting)]
	except (IndexError, ValueError):
		return 'remove_this_line'


def store_hdmi_to_file_config_set(kodi_setting, all_settings):
	"hdmi_force_hotplug=%s\nhdmi_edid_file=%s"

	# if hdmi_safe is active, then remove this conflicting line
	kodi_setting = hdmi_safe_group_removal(kodi_setting, all_settings)

	if kodi_setting == 'true':

		return ('1', '1')

	else:

		return ('remove_this_line', 'remove_this_line')


def hdmi_group_config_set(kodi_setting, all_settings):

	# if hdmi_safe is active, then remove this conflicting line
	kodi_setting = hdmi_safe_group_removal(kodi_setting, all_settings)	

	if kodi_setting in [str(x) for x in range(1,3)]:

		return kodi_setting

	else:

		return 'remove_this_line'


def hdmi_mode_config_set(kodi_setting, all_settings):

	# if hdmi_safe is active, then remove this conflicting line
	kodi_setting = hdmi_safe_group_removal(kodi_setting, all_settings)	

	if kodi_setting in [str(x) for x in range(1,87)]:

		return kodi_setting

	else:

		return 'remove_this_line'


def hdmi_pixel_config_set(kodi_setting, all_settings):

	if kodi_setting in [str(x) for x in range(1,5)]:

		return kodi_setting

	else:

		return 'remove_this_line'


def hdmi_safe_group_removal(setting_key, all_settings):

	if all_settings.get('hdmi_safe', None) == 'true':

		return 'remove_this_line'


def hdmi_ignore_edid_config_set(kodi_setting, all_settings):

	# if hdmi_safe is active, then remove this conflicting line
	kodi_setting = hdmi_safe_group_removal(kodi_setting, all_settings)

	if kodi_setting == 'true':

		return '0xa5000080'

	else:

		return 'remove_this_line'


def sdtv_aspect_config_set(kodi_setting, all_settings):

	if kodi_setting in [str(x) for x in range(1,4)]:

		return kodi_setting

	else:

		return 'remove_this_line'		


def sdtv_mode_config_set(kodi_setting, all_settings):

	if kodi_setting in [str(x) for x in range(1,4)]:

		return kodi_setting

	else:

		return 'remove_this_line'		


def bcm2835_config_set(kodi_setting, all_settings):

	if kodi_setting == 'true':

		return 'spi-bcm2835-overlay'

	else:

		return 'remove_this_line'		


def w1gpio_config_set(kodi_setting, all_settings):


	permitted = [
		'remove_this_line',
		'w1-gpio-overlay',
		'w1-gpio-pullup-overlay'
		]

	try:

		return permitted[int(kodi_setting)]

	except (ValueError, IndexError):

		return 'remove_this_line'


def soundcard_dac_config_set(kodi_setting, all_settings):

	permitted = [
		'remove_this_line',
		'hifiberry-dac-overlay',
		'hifiberry-dacplus-overlay',
		'hifiberry-digi-overlay',
		'iqaudio-dac-overlay',
		'iqaudio-dacplus-overlay'
		]

	try:

		return permitted[int(kodi_setting)]

	except (ValueError, IndexError):

		return 'remove_this_line'


def lirc_rpi_config_set(kodi_setting, all_settings):

	if kodi_setting == 'true':

		return 'lirc-rpi'

	else:

		return 'remove_this_line'


def gpio_group_removal(kodi_setting, all_settings):

	if all_settings.get('lirc-rpi-overlay') != 'true':

		return 'remove_this_line'

	else:

		return kodi_setting


def gpio_pin_config_set(kodi_setting, all_settings):

	return gpio_group_removal(kodi_setting, all_settings)


def gpio_updown_config_set(kodi_setting, all_settings):

	kodi_setting = gpio_group_removal(kodi_setting, all_settings)

	permitted = [
			'remove_this_line'
			'up',
			'down'
			]

	if kodi_setting in ['0','1','2']:

		return permitted[int(kodi_setting)]

	else:

		return 'remove_this_line'


'''
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@ 
								CUSTOM KODI SET FUNCTIONS
                                                                                       @@@@@@@@@@@@@@@@@@@@@@@@
Allows for more complex conversion of config settings (including multiple settings)	   @@@@@@@@@@@@@@@@@@@@@@@@
into specific kodi settings.                                                           @@@@@@@@@@@@@@@@@@@@@@@@                                                                                       
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

'''

def generic_passthrough_kodi_set(results):
	''' Takes a results list, and simply returns the first value. '''

	try:
		setting_value = results[0]
	except IndexError:
		setting_value = None

	return setting_value


def store_hdmi_kodi_set(results):
	''' Checks whether either hdmi_force_hotplug or hdmi_edid_file is set in the 
		'''

	if any([True for x in results if x == 'true']):

		return 'true'


'''
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@ 
								KODI SETTINGS DICTIONARY
                                                                                       @@@@@@@@@@@@@@@@@@@@@@@@
Houses the protocols for the settings in Kodi which come from the config.txt           @@@@@@@@@@@@@@@@@@@@@@@@
                                                                                       @@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

'''

MASTER_SETTINGS =    {

		"audio": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "false"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*(?:dtparam|dtparams|device_tree_param|device_tree_params)\s*=.*audio\s*=",
				"extract"       : r"\s*(?:dtparam|dtparams|device_tree_param|device_tree_params)\s*=.*audio\s*=\s*(\w+)"
				},

				],
			"config_set"        : audio_config_set,
			"config_validation" : onoff_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "dtparam=audio=%s",
		},

		"config_hdmi_boost": { 
			"default"   : { 
				"function"      : hdmi_boost_custom_default, 
				"value"         : ""
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*(?:hdmi_boost|config_hdmi_boost)\s*=",
				"extract"       : r"\s*(?:hdmi_boost|config_hdmi_boost)\s*=\s*(\d*)"
				},

				],
			"config_set"        : config_hdmi_boost_config_set,
			"config_validation" : config_hdmi_boost_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "config_hdmi_boost=%s",
		},
	
		"decode_MPG2": { 
			"default"   : { 
				"function"      : None, 
				"value"         : ""
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*decode_MPG2\s*=\s*",
				"extract"       : r"\s*decode_MPG2\s*=\s*(\w+)"
				},

				],
			"config_set"        : generic_passthrough_config_set,
			"config_validation" : blank_check_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "decode_MPG2=%s",
		},

		"decode_WVC1": { 
			"default"   : { 
				"function"      : None, 
				"value"         : ""
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*decode_WVC1\s*=\s*",
				"extract"       : r"\s*decode_WVC1\s*=\s*(\w+)"
				},

				],
			"config_set"        : generic_passthrough_config_set,
			"config_validation" : blank_check_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "decode_WVC1=%s",
		},

		"display_rotate": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "0"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*display_rotate\s*=\s*",
				"extract"       : r"\s*display_rotate\s*=\s*(\w+)"
				},

				],
			"config_set"        : display_rotate_config_set,
			"config_validation" : display_rotate_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "display_rotate=%s",
		},

		"gpu_mem_1024": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "256"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*gpu_mem_1024\s*=",
				"extract"       : r"\s*gpu_mem_1024\s*=\s*(\d+)"
				},
				{
				"identify"      : r"\s*gpu_mem\s*=",
				"extract"       : r"\s*gpu_mem\s*=\s*(\d+)"
				},				

				],
			"config_set"        : generic_passthrough_config_set,
			"config_validation" : gpu_mem_1024_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "gpu_mem_1024=%s",
		},

		"gpu_mem_512": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "144"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*gpu_mem_512\s*=",
				"extract"       : r"\s*gpu_mem_512\s*=\s*(\d+)"
				},
				{
				"identify"      : r"\s*gpu_mem\s*=",
				"extract"       : r"\s*gpu_mem\s*=\s*(\d+)"
				},				
				],
			"config_set"        : generic_passthrough_config_set,
			"config_validation" : gpu_mem_512_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "gpu_mem_512=%s",
		},

		"gpu_mem_256": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "112"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*gpu_mem_256\s*=",
				"extract"       : r"\s*gpu_mem_256\s*=\s*(\d+)"
				},
				{
				"identify"      : r"\s*gpu_mem\s*=",
				"extract"       : r"\s*gpu_mem\s*=\s*(\d+)"
				},				
				],
			"config_set"        : generic_passthrough_config_set,
			"config_validation" : gpu_mem_256_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "gpu_mem_256=%s",
		},

		"store_hdmi_to_file": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "false"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*hdmi_force_hotplug\s*=",
				"extract"       : r"\s*hdmi_force_hotplug\s*=\s*(\d+)"
				},
		
				{
				"identify"      : r"\s*hdmi_edid_file\s*=",
				"extract"       : r"\s*hdmi_edid_file\s*=\s*(\d+)"
				},
				],
			"config_set"        : store_hdmi_to_file_config_set,
			"config_validation" : generic_bool_validation,
			"kodi_set"          : store_hdmi_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "hdmi_force_hotplug=%s\nhdmi_edid_file=%s",
		},

		"hdmi_group": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "0"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*hdmi_group\s*=",
				"extract"       : r"\s*hdmi_group\s*=\s*(\d+)"
				},

				],
			"config_set"        : hdmi_group_config_set,
			"config_validation" : hdmi_group_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "hdmi_group=%s",
		},

		"hdmi_ignore_cec": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "false"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*hdmi_ignore_cec\s*=",
				"extract"       : r"\s*hdmi_ignore_cec\s*=\s*(\d+)"
				},

				],
			"config_set"        : generic_bool_config_set,
			"config_validation" : generic_bool_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "hdmi_ignore_cec=%s",
		},

		"hdmi_ignore_cec_init": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "false"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*hdmi_ignore_cec_init\s*=",
				"extract"       : r"\s*hdmi_ignore_cec_init\s*=\s*(\d+)"
				},

				],
			"config_set"        : generic_bool_config_set,
			"config_validation" : generic_bool_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "hdmi_ignore_cec_init=%s",
		},

		"hdmi_ignore_edid": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "false"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*hdmi_ignore_edid\s*=",
				"extract"       : r"\s*hdmi_ignore_edid\s*=\s*(\w+)"
				},

				],
			"config_set"        : hdmi_ignore_edid_config_set,
			"config_validation" : hdmi_ignore_edid_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "hdmi_ignore_edid=%s",
		},

		"hdmi_mode": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "0"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*hdmi_mode\s*=",
				"extract"       : r"\s*hdmi_mode\s*=\s*(\d+)"
				},

				],
			"config_set"        : hdmi_mode_config_set,
			"config_validation" : hdmi_mode_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "hdmi_mode=%s",
		},

		"hdmi_pixel_encoding": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "0"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*hdmi_pixel_encoding\s*=",
				"extract"       : r"\s*hdmi_pixel_encoding\s*=\s*(\d+)"
				},

				],
			"config_set"        : hdmi_pixel_config_set,
			"config_validation" : hdmi_pixel_encoding_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "hdmi_pixel_encoding=%s",
		},

		"hdmi_safe": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "false"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*hdmi_safe\s*=",
				"extract"       : r"\s*hdmi_safe\s*=\s*(\d+)"
				},

				],
			"config_set"        : generic_bool_config_set,
			"config_validation" : generic_bool_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "hdmi_safe=%s",
		},

		"max_usb_current": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "false"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*max_usb_current\s*=",
				"extract"       : r"\s*max_usb_current\s*=\s*(\d+)"
				},

				],
			"config_set"        : generic_bool_config_set,
			"config_validation" : generic_bool_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "max_usb_current=%s",
		},

		"sdtv_aspect": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "1"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*sdtv_aspect\s*=",
				"extract"       : r"\s*sdtv_aspect\s*=\s*(\d+)"
				},

				],
			"config_set"        : sdtv_aspect_config_set,
			"config_validation" : sdtv_aspect_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "sdtv_aspect=%s",
		},

		"sdtv_mode": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "0"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*sdtv_mode\s*=",
				"extract"       : r"\s*sdtv_mode\s*=\s*(\d+)"
				},

				],
			"config_set"        : sdtv_mode_config_set,
			"config_validation" : sdtv_mode_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "sdtv_mode=%s",
		},

		"spi-bcm2835-overlay": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "false"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*(?:dtoverlay|device_tree_overlay)\s*=\s*[-\w\d]*spi-bcm2835[-\w\d]*",
				"extract"       : r"\s*(?:dtoverlay|device_tree_overlay)\s*=\s*([-\w\d]*spi-bcm2835[-\w\d]*)"
				},

				],
			"config_set"        : bcm2835_config_set,
			"config_validation" : bcm2835_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "dtoverlay=%s",
		},

		"w1gpio": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "0"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*(?:dtoverlay|device_tree_overlay)\s*=.*w1-gpio",
				"extract"       : r"\s*(?:dtoverlay|device_tree_overlay)\s*=\s*([-\w\d]*w1-gpio[-\w\d]*)"
				},

				],
			"config_set"        : w1gpio_config_set,
			"config_validation" : w1gpio_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "dtoverlay=%s",
		},

		"soundcard_dac": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "0"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*(?:dtoverlay|device_tree_overlay)\s*=\s*[-\w\d]*(?:hifiberry-d|iqaudio-d)",
				"extract"       : r"\s*(?:dtoverlay|device_tree_overlay)\s*=\s*([-\w\d]*(?:hifiberry-d|iqaudio-d)[-\w\d]*)"
				},

				],
			"config_set"        : soundcard_dac_config_set,
			"config_validation" : soundcard_dac_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "dtoverlay=%s",
		},

		"lirc-rpi-overlay": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "0"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*(?:dtoverlay|device_tree_overlay)\s*=\s*[-\w\d]*lirc-rpi[-\w\d]*",
				"extract"       : r"\s*(?:dtoverlay|device_tree_overlay)\s*=\s*([-\w\d]*lirc-rpi[-\w\d]*)"
				},

				],
			"config_set"        : lirc_rpi_config_set,
			"config_validation" : lirc_rpi_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "dtoverlay=%s",
		},

		"gpio_in_pin": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "18"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*(?:dtoverlay|device_tree_overlay|dtparam|dtparams|device_tree_param|device_tree_params)\s*=(?:lirc-rpi:)?.*gpio_in_pin[-\w\d]*=",
				"extract"       : r"\s*(?:dtoverlay|device_tree_overlay|dtparam|dtparams|device_tree_param|device_tree_params)\s*=(?:lirc-rpi:)?.*gpio_in_pin[-\w\d]*=\s*(\w*)"
				},

				],
			"config_set"        : gpio_pin_config_set,
			"config_validation" : gpio_pin_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "dtparam=gpio_in_pin=%s",
		},

		"gpio_in_pull": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "off"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*(?:dtoverlay|device_tree_overlay|dtparam|dtparams|device_tree_param|device_tree_params)\s*=(?:lirc-rpi:)?.*gpio_in_pull[-\w\d]*=",
				"extract"       : r"\s*(?:dtoverlay|device_tree_overlay|dtparam|dtparams|device_tree_param|device_tree_params)\s*=(?:lirc-rpi:)?.*gpio_in_pull[-\w\d]*=\s*(\d*)"
				},

				],
			"config_set"        : gpio_updown_config_set,
			"config_validation" : gpio_updown_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "dtparam=gpio_in_pull=%s",
		},

		"gpio_out_pin": { 
			"default"   : { 
				"function"      : None, 
				"value"         : "17"
				},
			"config_get_patterns": [
				{
				"identify"      : r"\s*(?:dtoverlay|device_tree_overlay|dtparam|dtparams|device_tree_param|device_tree_params)\s*=(?:lirc-rpi:)?.*gpio_out_pin[-\w\d]*=",
				"extract"       : r"\s*(?:dtoverlay|device_tree_overlay|dtparam|dtparams|device_tree_param|device_tree_params)\s*=(?:lirc-rpi:)?.*gpio_out_pin[-\w\d]*=\s*(\d*)"
				},

				],
			"config_set"        : gpio_pin_config_set,
			"config_validation" : gpio_pin_validation,
			"kodi_set"          : generic_passthrough_kodi_set,
			"already_set"       : False,
			"setting_stub"      : "dtparam=gpio_out_pin=%s",
		},
		
	}


def read_config_file(location):

	with open(location, 'r') as f:
		config = f.readlines()

	return config


def write_config_file(location, new_config):

	new_config = [x + '\n' if not x.endswith('\n') else x for x in new_config if 'remove_this_line' not in x]

	with open(location, 'w') as f:
		f.writelines(new_config)



if __name__ == "__main__":

	'''@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

		Anything in here is only run when the script is called directly rather than imported

		I use this section for testing only.

	   @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ '''

	config = read_config_file('C:\\temp\config.txt')

	extracted_settings = config_to_kodi(MASTER_SETTINGS, config)

	keys = sorted(extracted_settings.keys())




	original_values = {
			'audio' : 'true',
			'config_hdmi_boost' : '2',
			'decode_MPG2' : '0x9c7d03c1',
			'decode_WVC1' : '0x95f2b10e',
			'display_rotate' : '0',
			'gpio_in_pin' : 'off',
			'gpio_in_pull' : '18',
			'gpio_out_pin' : '17',
			'gpu_mem_1024' : '256',
			'gpu_mem_512' : '144',
			'gpu_mem_256' : '112',
			'hdmi_group' : '0',
			'hdmi_ignore_cec' : 'false',
			'hdmi_ignore_cec_init' : 'true',
			'hdmi_ignore_edid' : 'false',
			'hdmi_mode' : '0',
			'hdmi_pixel_encoding' : '0',
			'hdmi_safe' : 'false',
			'lirc-rpi-overlay' : '0',
			'max_usb_current' : 'true',
			'sdtv_aspect' : '0',
			'sdtv_mode' : '0',
			'soundcard_dac' : "0",
			'spi-bcm2835-overlay' : 'false',
			'store_hdmi_to_file' : 'false',
			'w1gpio' : '0',

	}

	test = {
		'audio' : 'true',
		'config_hdmi_boost' : '2',
		'decode_MPG2' : '0000',
		'decode_WVC1' : '0x95f2b10e',
		'display_rotate' : '0',
		'gpio_in_pin' : '18',
		'gpio_in_pull' : 'off',
		'gpio_out_pin' : '17',
		'gpu_mem_1024' : '256',
		'gpu_mem_512' : '144',
		'gpu_mem_256' : '112',
		'hdmi_group' : '0',
		'hdmi_ignore_cec' : 'false',
		'hdmi_ignore_cec_init' : 'true',
		'hdmi_ignore_edid' : 'true',
		'hdmi_mode' : '0',
		'hdmi_pixel_encoding' : '0',
		'hdmi_safe' : 'true',
		'lirc-rpi-overlay' : 'true',
		'max_usb_current' : 'true',
		'sdtv_aspect' : '0',
		'sdtv_mode' : '1',
		'soundcard_dac' : "2",
		'spi-bcm2835-overlay' : 'false',
		'store_hdmi_to_file' : 'false',
		'w1gpio' : '2',

	}

	config = read_config_file('C:\\temp\config.txt')
	
	new_settings = kodi_to_config(MASTER_SETTINGS, config, extracted_settings)

	#print new_settings

	write_config_file('C:\\temp\\results.txt', new_settings)
